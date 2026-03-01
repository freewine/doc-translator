"""
GraphQL resolvers for user management.

This module provides:
- UserQuery: Queries for user data
- UserMutation: Mutations for user management
"""
import logging
from typing import List, Optional

import strawberry
from strawberry.types import Info

from ..models.user import User, UserRole, UserStatus, AuthResult, AuthErrorCode
from ..services.user_service import (
    UserService,
    UserNotFoundError,
    UserAlreadyExistsError,
    PermissionDeniedError,
    ValidationError,
)
from .decorators import (
    require_auth,
    require_admin,
    get_current_user_from_context,
    AuthenticationError,
)
from .schema import UserRoleEnum, UserStatusEnum, UserInfo, AuthResultInfo

logger = logging.getLogger(__name__)


def user_info_from_model(user: User) -> UserInfo:
    """Create UserInfo from User model."""
    return UserInfo(
        username=user.username,
        role=UserRoleEnum(user.role.value),
        status=UserStatusEnum(user.status.value),
        must_change_password=user.must_change_password,
        failed_login_count=user.failed_login_count,
        created_at=user.created_at.isoformat() if hasattr(user.created_at, 'isoformat') else str(user.created_at),
        updated_at=user.updated_at.isoformat() if hasattr(user.updated_at, 'isoformat') else str(user.updated_at),
        deleted_at=user.deleted_at.isoformat() if user.deleted_at and hasattr(user.deleted_at, 'isoformat') else (str(user.deleted_at) if user.deleted_at else None),
    )


def auth_result_from_model(result: AuthResult) -> AuthResultInfo:
    """Create AuthResultInfo from AuthResult model."""
    return AuthResultInfo(
        success=result.success,
        token=result.token,
        must_change_password=result.must_change_password,
        error=result.error,
        error_code=result.error_code.value if result.error_code else None,
        remaining_attempts=result.remaining_attempts,
        user=user_info_from_model(result.user) if result.user else None,
    )


def get_user_service(info: Info) -> UserService:
    """Get UserService from context."""
    context = info.context
    if hasattr(context, "get"):
        service = context.get("user_service")
    else:
        service = getattr(context, "user_service", None)
    
    if not service:
        raise Exception("UserService not available in context")
    return service


@strawberry.type
class UserQuery:
    """GraphQL queries for user management."""
    
    @strawberry.field
    @require_admin
    async def users(
        self,
        info: Info,
        include_deleted: bool = False
    ) -> List[UserInfo]:
        """
        Get all users.

        Args:
            include_deleted: Whether to include soft-deleted users

        Returns:
            List of users
        """
        user_service = get_user_service(info)
        users = await user_service.get_users(include_deleted)
        return [user_info_from_model(u) for u in users]
    
    @strawberry.field
    @require_admin
    async def user(
        self,
        info: Info,
        username: str
    ) -> Optional[UserInfo]:
        """
        Get a specific user by username.

        Args:
            username: Username to look up

        Returns:
            User if found, None otherwise
        """
        user_service = get_user_service(info)
        user = await user_service.get_user(username)
        return user_info_from_model(user) if user else None
    
    @strawberry.field
    @require_auth
    async def me(self, info: Info) -> UserInfo:
        """
        Get the current authenticated user.

        Returns:
            Current user
        """
        current_user = get_current_user_from_context(info)
        if not current_user:
            raise AuthenticationError("Not authenticated")
        return user_info_from_model(current_user)


@strawberry.type
class UserMutation:
    """GraphQL mutations for user management."""
    
    @strawberry.mutation
    @require_admin
    async def create_user(
        self,
        info: Info,
        username: str,
        password: str,
        role: str = "user"
    ) -> UserInfo:
        """
        Create a new user.

        Args:
            username: Unique username (3-50 chars)
            password: Initial password
            role: User role ('admin' or 'user')

        Returns:
            Created user
        """
        user_service = get_user_service(info)

        try:
            user = await user_service.create_user(username, password, role)
            logger.info(f"User '{username}' created via GraphQL")
            return user_info_from_model(user)
        except (ValidationError, UserAlreadyExistsError) as e:
            raise Exception(str(e))
    
    @strawberry.mutation
    @require_admin
    async def update_user(
        self,
        info: Info,
        username: str,
        password: Optional[str] = None,
        role: Optional[str] = None
    ) -> UserInfo:
        """
        Update a user's information.

        Args:
            username: Target username
            password: New password (optional)
            role: New role (optional)

        Returns:
            Updated user
        """
        user_service = get_user_service(info)
        current_user = get_current_user_from_context(info)

        try:
            user = await user_service.update_user(
                username,
                password=password,
                role=role,
                current_user=current_user
            )
            logger.info(f"User '{username}' updated via GraphQL")
            return user_info_from_model(user)
        except (ValidationError, UserNotFoundError, PermissionDeniedError) as e:
            raise Exception(str(e))
    
    @strawberry.mutation
    @require_admin
    async def delete_user(
        self,
        info: Info,
        username: str
    ) -> bool:
        """
        Soft delete a user.
        
        Args:
            username: Username to delete
            
        Returns:
            True if deleted successfully
        """
        user_service = get_user_service(info)
        current_user = get_current_user_from_context(info)
        
        try:
            result = await user_service.delete_user(username, current_user)
            logger.info(f"User '{username}' deleted via GraphQL")
            return result
        except (UserNotFoundError, PermissionDeniedError) as e:
            raise Exception(str(e))
    
    @strawberry.mutation
    @require_admin
    async def unlock_user(
        self,
        info: Info,
        username: str
    ) -> UserInfo:
        """
        Unlock a locked user account.

        Args:
            username: Username to unlock

        Returns:
            Unlocked user
        """
        user_service = get_user_service(info)

        try:
            user = await user_service.unlock_user(username)
            logger.info(f"User '{username}' unlocked via GraphQL")
            return user_info_from_model(user)
        except (UserNotFoundError, PermissionDeniedError) as e:
            raise Exception(str(e))
    
    @strawberry.mutation
    @require_admin
    async def restore_user(
        self,
        info: Info,
        username: str
    ) -> UserInfo:
        """
        Restore a soft-deleted user.

        Args:
            username: Username to restore

        Returns:
            Restored user
        """
        user_service = get_user_service(info)

        try:
            user = await user_service.restore_user(username)
            logger.info(f"User '{username}' restored via GraphQL")
            return user_info_from_model(user)
        except (UserNotFoundError, PermissionDeniedError) as e:
            raise Exception(str(e))
    
    @strawberry.mutation
    @require_auth
    async def change_my_password(
        self,
        info: Info,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change the current user's password.
        
        Args:
            current_password: Current password for verification
            new_password: New password to set
            
        Returns:
            True if password changed successfully
        """
        user_service = get_user_service(info)
        current_user = get_current_user_from_context(info)
        
        if not current_user:
            raise AuthenticationError("Not authenticated")
        
        try:
            result = await user_service.change_password(
                current_user.username,
                current_password,
                new_password
            )
            logger.info(f"Password changed for user '{current_user.username}' via GraphQL")
            return result
        except (UserNotFoundError, ValidationError) as e:
            raise Exception(str(e))
    
    @strawberry.mutation
    async def login_user(
        self,
        info: Info,
        username: str,
        password: str
    ) -> AuthResultInfo:
        """
        Authenticate a user and get JWT token.

        Args:
            username: Username
            password: Password

        Returns:
            Authentication result with token if successful
        """
        auth_service = info.context.get("auth_service") if hasattr(info.context, "get") else None

        if not auth_service:
            return AuthResultInfo(
                success=False,
                error="Authentication service not available",
                error_code="TOKEN_INVALID"
            )

        # Use DynamoDB-based authentication
        if not auth_service.user_service:
            return AuthResultInfo(
                success=False,
                error="User service not configured",
                error_code="TOKEN_INVALID"
            )

        result = await auth_service.authenticate_user(username, password)
        return auth_result_from_model(result)
