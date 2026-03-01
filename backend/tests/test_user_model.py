"""
Unit tests for user data models.
"""
import pytest
from datetime import datetime, timezone

from src.models.user import (
    AuthErrorCode,
    AuthResult,
    TokenPayload,
    User,
    UserRole,
    UserStatus,
    validate_role,
    validate_username,
)


class TestUserStatus:
    """Tests for UserStatus enum."""
    
    def test_status_values(self):
        """Test all status values exist."""
        assert UserStatus.PENDING_PASSWORD.value == "pending_password"
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.LOCKED.value == "locked"
        assert UserStatus.DELETED.value == "deleted"
    
    def test_status_from_string(self):
        """Test creating status from string."""
        assert UserStatus("active") == UserStatus.ACTIVE
        assert UserStatus("locked") == UserStatus.LOCKED


class TestUserRole:
    """Tests for UserRole enum."""
    
    def test_role_values(self):
        """Test all role values exist."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
    
    def test_role_from_string(self):
        """Test creating role from string."""
        assert UserRole("admin") == UserRole.ADMIN
        assert UserRole("user") == UserRole.USER


class TestAuthErrorCode:
    """Tests for AuthErrorCode enum."""
    
    def test_error_codes_exist(self):
        """Test all error codes exist."""
        assert AuthErrorCode.USER_NOT_FOUND.value == "USER_NOT_FOUND"
        assert AuthErrorCode.INVALID_PASSWORD.value == "INVALID_PASSWORD"
        assert AuthErrorCode.USER_LOCKED.value == "USER_LOCKED"
        assert AuthErrorCode.USER_DELETED.value == "USER_DELETED"
        assert AuthErrorCode.TOKEN_EXPIRED.value == "TOKEN_EXPIRED"
        assert AuthErrorCode.TOKEN_INVALID.value == "TOKEN_INVALID"
        assert AuthErrorCode.PERMISSION_DENIED.value == "PERMISSION_DENIED"


class TestUser:
    """Tests for User dataclass."""
    
    def test_create_user(self):
        """Test creating a user with required fields."""
        user = User(
            username="testuser",
            password_hash="$2b$12$hashedpassword",
            role=UserRole.USER,
        )
        
        assert user.username == "testuser"
        assert user.password_hash == "$2b$12$hashedpassword"
        assert user.role == UserRole.USER
        assert user.status == UserStatus.PENDING_PASSWORD
        assert user.must_change_password is True
        assert user.failed_login_count == 0
        assert user.deleted_at is None
    
    def test_create_admin_user(self):
        """Test creating an admin user."""
        user = User(
            username="admin",
            password_hash="$2b$12$hashedpassword",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        
        assert user.role == UserRole.ADMIN
        assert user.status == UserStatus.ACTIVE
        assert user.must_change_password is False
    
    def test_user_to_dict(self):
        """Test converting user to dictionary."""
        now = datetime.now(timezone.utc)
        user = User(
            username="testuser",
            password_hash="$2b$12$hash",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            must_change_password=False,
            failed_login_count=2,
            created_at=now,
            updated_at=now,
        )
        
        data = user.to_dict()
        
        assert data["username"] == "testuser"
        assert data["password_hash"] == "$2b$12$hash"
        assert data["role"] == "user"
        assert data["status"] == "active"
        assert data["must_change_password"] is False
        assert data["failed_login_count"] == 2
        assert data["deleted_at"] is None
    
    def test_user_from_dict(self):
        """Test creating user from dictionary."""
        data = {
            "username": "testuser",
            "password_hash": "$2b$12$hash",
            "role": "admin",
            "status": "active",
            "must_change_password": False,
            "failed_login_count": 0,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "deleted_at": None,
        }
        
        user = User.from_dict(data)
        
        assert user.username == "testuser"
        assert user.role == UserRole.ADMIN
        assert user.status == UserStatus.ACTIVE
        assert user.must_change_password is False
    
    def test_user_is_active(self):
        """Test is_active method."""
        active_user = User(
            username="active",
            password_hash="hash",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        locked_user = User(
            username="locked",
            password_hash="hash",
            role=UserRole.USER,
            status=UserStatus.LOCKED,
        )
        
        assert active_user.is_active() is True
        assert locked_user.is_active() is False
    
    def test_user_is_admin(self):
        """Test is_admin method."""
        admin = User(
            username="admin",
            password_hash="hash",
            role=UserRole.ADMIN,
        )
        user = User(
            username="user",
            password_hash="hash",
            role=UserRole.USER,
        )
        
        assert admin.is_admin() is True
        assert user.is_admin() is False
    
    def test_user_can_login(self):
        """Test can_login method."""
        active_user = User(
            username="active",
            password_hash="hash",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        pending_user = User(
            username="pending",
            password_hash="hash",
            role=UserRole.USER,
            status=UserStatus.PENDING_PASSWORD,
        )
        locked_user = User(
            username="locked",
            password_hash="hash",
            role=UserRole.USER,
            status=UserStatus.LOCKED,
        )
        deleted_user = User(
            username="deleted",
            password_hash="hash",
            role=UserRole.USER,
            status=UserStatus.DELETED,
        )
        
        assert active_user.can_login() is True
        assert pending_user.can_login() is True
        assert locked_user.can_login() is False
        assert deleted_user.can_login() is False


class TestAuthResult:
    """Tests for AuthResult dataclass."""
    
    def test_successful_auth_result(self):
        """Test creating successful auth result."""
        user = User(
            username="testuser",
            password_hash="hash",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        result = AuthResult(
            success=True,
            token="jwt_token_here",
            user=user,
            must_change_password=False,
        )
        
        assert result.success is True
        assert result.token == "jwt_token_here"
        assert result.user == user
        assert result.error is None
        assert result.error_code is None
    
    def test_failed_auth_result(self):
        """Test creating failed auth result."""
        result = AuthResult(
            success=False,
            error="Invalid password",
            error_code=AuthErrorCode.INVALID_PASSWORD,
            remaining_attempts=3,
        )
        
        assert result.success is False
        assert result.token is None
        assert result.user is None
        assert result.error == "Invalid password"
        assert result.error_code == AuthErrorCode.INVALID_PASSWORD
        assert result.remaining_attempts == 3


class TestTokenPayload:
    """Tests for TokenPayload dataclass."""
    
    def test_create_token_payload(self):
        """Test creating token payload."""
        payload = TokenPayload(
            username="testuser",
            role="admin",
            exp=1737676800,
            iat=1737072000,
        )
        
        assert payload.username == "testuser"
        assert payload.role == "admin"
        assert payload.exp == 1737676800
        assert payload.iat == 1737072000


class TestValidateUsername:
    """Tests for username validation."""
    
    def test_valid_usernames(self):
        """Test valid username formats."""
        valid_names = ["abc", "user123", "test_user", "Admin_01", "a" * 50]
        
        for name in valid_names:
            is_valid, error = validate_username(name)
            assert is_valid is True, f"Expected {name} to be valid"
            assert error is None
    
    def test_invalid_usernames(self):
        """Test invalid username formats."""
        invalid_cases = [
            ("", "empty"),
            ("ab", "too short"),
            ("a" * 51, "too long"),
            ("user@name", "special char @"),
            ("user-name", "special char -"),
            ("user.name", "special char ."),
            ("user name", "space"),
        ]
        
        for name, reason in invalid_cases:
            is_valid, error = validate_username(name)
            assert is_valid is False, f"Expected {name} to be invalid ({reason})"
            assert error is not None


class TestValidateRole:
    """Tests for role validation."""
    
    def test_valid_roles(self):
        """Test valid role values."""
        for role in ["admin", "user"]:
            is_valid, error = validate_role(role)
            assert is_valid is True
            assert error is None
    
    def test_invalid_roles(self):
        """Test invalid role values."""
        invalid_roles = ["Admin", "USER", "superuser", "guest", ""]
        
        for role in invalid_roles:
            is_valid, error = validate_role(role)
            assert is_valid is False
            assert error is not None
