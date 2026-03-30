"""
User management service for CRUD operations and business logic.

This module provides:
- PasswordService: Password hashing and verification utilities
- UserService: User CRUD operations with business rule enforcement
"""
import bcrypt
import logging
from datetime import datetime, timezone
from typing import List, Optional

from ..models.user import (
    User,
    UserRole,
    UserStatus,
    validate_username,
    validate_role,
)
from ..storage.dynamodb_repository import DynamoDBRepository

logger = logging.getLogger(__name__)


class PasswordService:
    """
    Static utility class for password hashing and verification.
    
    Uses bcrypt with configurable cost factor (default: 12).
    """
    
    BCRYPT_ROUNDS = 12
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password to hash.
            
        Returns:
            Bcrypt hashed password as string.
            
        Note:
            Bcrypt has a 72-byte limit. Passwords longer than 72 bytes
            will be truncated before hashing.
        """
        password_bytes = password.encode('utf-8')[:72]
        salt = bcrypt.gensalt(rounds=PasswordService.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify.
            password_hash: Bcrypt hash to verify against.
            
        Returns:
            True if password matches hash, False otherwise.
        """
        try:
            password_bytes = password.encode('utf-8')[:72]
            return bcrypt.checkpw(password_bytes, password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    @staticmethod
    def passwords_match(password1: str, password2: str) -> bool:
        """
        Check if two passwords are identical.
        
        Args:
            password1: First password.
            password2: Second password.
            
        Returns:
            True if passwords match, False otherwise.
        """
        return password1 == password2


class UserServiceError(Exception):
    """Base exception for UserService errors."""
    pass


class UserNotFoundError(UserServiceError):
    """Raised when a user is not found."""
    pass


class UserAlreadyExistsError(UserServiceError):
    """Raised when trying to create a user that already exists."""
    pass


class PermissionDeniedError(UserServiceError):
    """Raised when an operation is not permitted."""
    pass


class ValidationError(UserServiceError):
    """Raised when validation fails."""
    pass


class UserService:
    """
    Service for user management operations.
    
    Provides CRUD operations with business rule enforcement:
    - Username validation
    - Role-based access control
    - Admin protection rules
    - Soft delete/restore functionality
    - Login failure tracking
    """
    
    MAX_LOGIN_ATTEMPTS = 5
    
    def __init__(self, repository: DynamoDBRepository):
        """
        Initialize UserService.
        
        Args:
            repository: DynamoDB repository for data access.
        """
        self.repository = repository
    
    async def create_user(
        self,
        username: str,
        password: str,
        role: str = "user"
    ) -> User:
        """
        Create a new user.
        
        Args:
            username: Unique username (3-50 chars, alphanumeric + underscore).
            password: Initial password (will be hashed).
            role: User role ('admin' or 'user', default: 'user').
            
        Returns:
            Created User object.
            
        Raises:
            ValidationError: If username or role is invalid.
            UserAlreadyExistsError: If username already exists.
        """
        # Validate username
        is_valid, error = validate_username(username)
        if not is_valid:
            raise ValidationError(error)
        
        # Validate role
        is_valid, error = validate_role(role)
        if not is_valid:
            raise ValidationError(error)
        
        # Check if user already exists
        existing = await self.repository.get_user(username)
        if existing and existing.get("status") != UserStatus.DELETED.value:
            raise UserAlreadyExistsError(f"User '{username}' already exists")

        # Hash password
        password_hash = PasswordService.hash_password(password)

        if existing and existing.get("status") == UserStatus.DELETED.value:
            # Overwrite the soft-deleted record
            stored_data = await self.repository.update_user(
                username,
                password_hash=password_hash,
                role=role,
                status=UserStatus.PENDING_PASSWORD.value,
                must_change_password=True,
                failed_login_count=0,
                deleted_at=None,
            )
            if not stored_data:
                raise UserAlreadyExistsError(f"Failed to recreate user '{username}'")
            logger.info(f"Recreated user '{username}' (was soft-deleted) with role '{role}'")
            return User.from_dict(stored_data)

        # Create new user
        user_data = {
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "status": UserStatus.PENDING_PASSWORD.value,
            "must_change_password": True,
            "failed_login_count": 0,
        }

        try:
            stored_data = await self.repository.create_user(user_data)
            logger.info(f"Created user '{username}' with role '{role}'")
            return User.from_dict(stored_data)
        except ValueError as e:
            raise UserAlreadyExistsError(str(e))
    
    async def get_user(self, username: str) -> Optional[User]:
        """
        Get a user by username.
        
        Args:
            username: The username to look up.
            
        Returns:
            User object if found, None otherwise.
        """
        user_data = await self.repository.get_user(username)
        if user_data:
            return User.from_dict(user_data)
        return None
    
    async def get_users(self, include_deleted: bool = False) -> List[User]:
        """
        Get all users.
        
        Args:
            include_deleted: Whether to include soft-deleted users.
            
        Returns:
            List of User objects.
        """
        users_data = await self.repository.get_users(include_deleted)
        return [User.from_dict(data) for data in users_data]
    
    async def update_user(
        self,
        username: str,
        password: Optional[str] = None,
        role: Optional[str] = None,
        current_user: Optional[User] = None
    ) -> User:
        """
        Update user information.
        
        Args:
            username: Target username to update.
            password: New password (optional).
            role: New role (optional).
            current_user: The user performing the update (for permission checks).
            
        Returns:
            Updated User object.
            
        Raises:
            UserNotFoundError: If user doesn't exist.
            PermissionDeniedError: If operation is not permitted.
            ValidationError: If role is invalid.
        """
        # Get target user
        target_user = await self.get_user(username)
        if not target_user:
            raise UserNotFoundError(f"User '{username}' not found")
        
        # Check self-modification restrictions
        if current_user and current_user.username == username:
            if role and role != target_user.role.value:
                raise PermissionDeniedError("Cannot modify your own role")
        
        updates = {}
        
        # Update password if provided
        if password:
            updates["password_hash"] = PasswordService.hash_password(password)
            # If admin resets another user's password, require password change
            if current_user and current_user.username != username:
                updates["must_change_password"] = True
        
        # Update role if provided
        if role:
            is_valid, error = validate_role(role)
            if not is_valid:
                raise ValidationError(error)
            updates["role"] = role
        
        if not updates:
            return target_user
        
        # Perform update
        updated_data = await self.repository.update_user(username, **updates)
        if not updated_data:
            raise UserNotFoundError(f"User '{username}' not found")
        
        logger.info(f"Updated user '{username}'")
        return User.from_dict(updated_data)
    
    async def delete_user(
        self,
        username: str,
        current_user: User
    ) -> bool:
        """
        Soft delete a user.
        
        Args:
            username: Username to delete.
            current_user: The user performing the deletion.
            
        Returns:
            True if deleted successfully.
            
        Raises:
            UserNotFoundError: If user doesn't exist.
            PermissionDeniedError: If operation is not permitted.
        """
        # Cannot delete yourself
        if current_user.username == username:
            raise PermissionDeniedError("Cannot delete your own account")
        
        # Get target user
        target_user = await self.get_user(username)
        if not target_user:
            raise UserNotFoundError(f"User '{username}' not found")
        
        # Check if already deleted
        if target_user.status == UserStatus.DELETED:
            raise PermissionDeniedError(f"User '{username}' is already deleted")
        
        # Check admin protection - must keep at least one admin
        if target_user.role == UserRole.ADMIN:
            admin_count = await self.repository.count_active_admins()
            if admin_count <= 1:
                raise PermissionDeniedError("Cannot delete the last admin user")
        
        # Soft delete
        now = datetime.now(timezone.utc).isoformat()
        await self.repository.update_user(
            username,
            status=UserStatus.DELETED.value,
            deleted_at=now
        )
        
        logger.info(f"Soft deleted user '{username}'")
        return True
    
    async def unlock_user(self, username: str) -> User:
        """
        Unlock a locked user account.
        
        Args:
            username: Username to unlock.
            
        Returns:
            Updated User object.
            
        Raises:
            UserNotFoundError: If user doesn't exist.
            PermissionDeniedError: If user is not locked.
        """
        user = await self.get_user(username)
        if not user:
            raise UserNotFoundError(f"User '{username}' not found")
        
        if user.status != UserStatus.LOCKED:
            raise PermissionDeniedError(f"User '{username}' is not locked")
        
        updated_data = await self.repository.update_user(
            username,
            status=UserStatus.ACTIVE.value,
            failed_login_count=0
        )
        
        logger.info(f"Unlocked user '{username}'")
        return User.from_dict(updated_data)
    
    async def restore_user(self, username: str) -> User:
        """
        Restore a soft-deleted user.
        
        Args:
            username: Username to restore.
            
        Returns:
            Updated User object.
            
        Raises:
            UserNotFoundError: If user doesn't exist.
            PermissionDeniedError: If user is not deleted.
        """
        # Need to include deleted users in search
        user_data = await self.repository.get_user(username)
        if not user_data:
            raise UserNotFoundError(f"User '{username}' not found")
        
        user = User.from_dict(user_data)
        if user.status != UserStatus.DELETED:
            raise PermissionDeniedError(f"User '{username}' is not deleted")
        
        updated_data = await self.repository.update_user(
            username,
            status=UserStatus.ACTIVE.value,
            deleted_at=None
        )
        
        logger.info(f"Restored user '{username}'")
        return User.from_dict(updated_data)
    
    async def change_password(
        self,
        username: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change a user's password.
        
        Args:
            username: Username whose password to change.
            current_password: Current password for verification.
            new_password: New password to set.
            
        Returns:
            True if password changed successfully.
            
        Raises:
            UserNotFoundError: If user doesn't exist.
            ValidationError: If current password is wrong or new password invalid.
        """
        user = await self.get_user(username)
        if not user:
            raise UserNotFoundError(f"User '{username}' not found")
        
        # Verify current password
        if not PasswordService.verify_password(current_password, user.password_hash):
            raise ValidationError("Current password is incorrect")
        
        # Check if first password change - new password cannot match initial
        if user.must_change_password:
            if PasswordService.passwords_match(current_password, new_password):
                raise ValidationError("New password cannot be the same as the initial password")
        
        # Hash and update password
        new_hash = PasswordService.hash_password(new_password)
        
        # Update user - clear must_change_password flag and set status to ACTIVE
        updates = {
            "password_hash": new_hash,
            "must_change_password": False,
        }
        
        # If user was in PENDING_PASSWORD status, activate them
        if user.status == UserStatus.PENDING_PASSWORD:
            updates["status"] = UserStatus.ACTIVE.value
        
        await self.repository.update_user(username, **updates)
        
        logger.info(f"Password changed for user '{username}'")
        return True
    
    async def record_login_failure(self, username: str) -> int:
        """
        Record a failed login attempt.
        
        Args:
            username: Username that failed to login.
            
        Returns:
            Remaining attempts before lockout.
            
        Raises:
            UserNotFoundError: If user doesn't exist.
        """
        user = await self.get_user(username)
        if not user:
            raise UserNotFoundError(f"User '{username}' not found")
        
        new_count = user.failed_login_count + 1
        updates = {"failed_login_count": new_count}
        
        # Lock account if max attempts reached
        if new_count >= self.MAX_LOGIN_ATTEMPTS:
            updates["status"] = UserStatus.LOCKED.value
            logger.warning(f"User '{username}' locked after {new_count} failed attempts")
        
        await self.repository.update_user(username, **updates)
        
        remaining = max(0, self.MAX_LOGIN_ATTEMPTS - new_count)
        return remaining
    
    async def reset_login_failures(self, username: str) -> None:
        """
        Reset failed login count after successful login.
        
        Args:
            username: Username to reset.
        """
        await self.repository.update_user(username, failed_login_count=0)
