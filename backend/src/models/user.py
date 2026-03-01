"""
User-related data models for the authentication and user management system.

This module defines the data structures for:
- User entity with status and role management
- Authentication results and error codes
- JWT token payload
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import re


class UserStatus(Enum):
    """User account status."""
    PENDING_PASSWORD = "pending_password"  # New user, must change password
    ACTIVE = "active"                      # Normal active user
    LOCKED = "locked"                      # Locked due to failed login attempts
    DELETED = "deleted"                    # Soft deleted


class UserRole(Enum):
    """User role for access control."""
    ADMIN = "admin"
    USER = "user"


class AuthErrorCode(Enum):
    """Authentication error codes."""
    USER_NOT_FOUND = "USER_NOT_FOUND"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    USER_LOCKED = "USER_LOCKED"
    USER_DELETED = "USER_DELETED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    PERMISSION_DENIED = "PERMISSION_DENIED"


# Username validation pattern: 3-50 characters, alphanumeric and underscore only
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,50}$')


@dataclass
class User:
    """
    User entity representing a system user.
    
    Attributes:
        username: Unique identifier (3-50 chars, alphanumeric + underscore)
        password_hash: bcrypt hashed password
        role: User role (admin or user)
        status: Account status
        must_change_password: Whether user must change password on next login
        failed_login_count: Consecutive failed login attempts
        created_at: Account creation timestamp
        updated_at: Last modification timestamp
        deleted_at: Soft deletion timestamp (None if not deleted)
    """
    username: str
    password_hash: str
    role: UserRole
    status: UserStatus = UserStatus.PENDING_PASSWORD
    must_change_password: bool = True
    failed_login_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role.value,
            "status": self.status.value,
            "must_change_password": self.must_change_password,
            "failed_login_count": self.failed_login_count,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User from dictionary."""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        deleted_at = data.get("deleted_at")
        
        # Parse datetime strings if needed
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        if isinstance(deleted_at, str) and deleted_at:
            deleted_at = datetime.fromisoformat(deleted_at.replace("Z", "+00:00"))
        
        # Parse role enum
        role_value = data.get("role", "user")
        role = UserRole(role_value) if isinstance(role_value, str) else role_value
        
        # Parse status enum (case-insensitive for backwards compatibility)
        status_value = data.get("status", "pending_password")
        if isinstance(status_value, str):
            status = UserStatus(status_value.lower())
        else:
            status = status_value
        
        return cls(
            username=data["username"],
            password_hash=data["password_hash"],
            role=role,
            status=status,
            must_change_password=data.get("must_change_password", True),
            failed_login_count=data.get("failed_login_count", 0),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
            deleted_at=deleted_at,
        )
    
    def is_active(self) -> bool:
        """Check if user can perform actions."""
        return self.status == UserStatus.ACTIVE
    
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
    
    def can_login(self) -> bool:
        """Check if user can attempt login."""
        return self.status not in (UserStatus.LOCKED, UserStatus.DELETED)


@dataclass
class AuthResult:
    """
    Authentication result value object.
    
    Attributes:
        success: Whether authentication succeeded
        token: JWT token (if successful)
        user: User object (if successful)
        must_change_password: Whether user must change password
        error: Error message (if failed)
        error_code: Error code (if failed)
        remaining_attempts: Remaining login attempts before lockout
    """
    success: bool
    token: Optional[str] = None
    user: Optional[User] = None
    must_change_password: bool = False
    error: Optional[str] = None
    error_code: Optional[AuthErrorCode] = None
    remaining_attempts: Optional[int] = None


@dataclass
class TokenPayload:
    """
    JWT token payload value object.
    
    Attributes:
        username: User's username
        role: User's role
        exp: Expiration timestamp (Unix)
        iat: Issued at timestamp (Unix)
    """
    username: str
    role: str
    exp: int
    iat: int


def validate_username(username: str) -> tuple[bool, Optional[str]]:
    """
    Validate username format.
    
    Args:
        username: Username to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"
    
    if not USERNAME_PATTERN.match(username):
        return False, "Username must be 3-50 characters, containing only letters, numbers, and underscores"
    
    return True, None


def validate_role(role: str) -> tuple[bool, Optional[str]]:
    """
    Validate role value.
    
    Args:
        role: Role string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_roles = [r.value for r in UserRole]
    if role not in valid_roles:
        return False, f"Role must be one of: {', '.join(valid_roles)}"
    
    return True, None
