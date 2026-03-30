"""
Unit tests for UserService.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.user import User, UserRole, UserStatus
from src.services.user_service import (
    PasswordService,
    UserService,
    UserNotFoundError,
    UserAlreadyExistsError,
    PermissionDeniedError,
    ValidationError,
)


class TestPasswordService:
    """Tests for PasswordService."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = PasswordService.hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60
    
    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "test_password_123"
        hashed = PasswordService.hash_password(password)
        
        assert PasswordService.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "test_password_123"
        hashed = PasswordService.hash_password(password)
        
        assert PasswordService.verify_password("wrong_password", hashed) is False
    
    def test_passwords_match(self):
        """Test password comparison."""
        assert PasswordService.passwords_match("abc", "abc") is True
        assert PasswordService.passwords_match("abc", "def") is False


class TestUserService:
    """Tests for UserService."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        repo = MagicMock()
        repo.user_exists = AsyncMock(return_value=False)
        repo.create_user = AsyncMock()
        repo.get_user = AsyncMock(return_value=None)
        repo.get_users = AsyncMock(return_value=[])
        repo.update_user = AsyncMock()
        repo.count_active_admins = AsyncMock(return_value=2)
        return repo
    
    @pytest.fixture
    def user_service(self, mock_repository):
        """Create UserService with mock repository."""
        return UserService(mock_repository)
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data from repository."""
        return {
            "username": "testuser",
            "password_hash": "$2b$12$hashedpassword",
            "role": "user",
            "status": "active",
            "must_change_password": False,
            "failed_login_count": 0,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "deleted_at": None,
        }
    
    @pytest.fixture
    def admin_user(self):
        """Create an admin user for testing."""
        return User(
            username="admin",
            password_hash="$2b$12$hash",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
    
    # Create user tests
    
    async def test_create_user_success(self, user_service, mock_repository):
        """Test successful user creation."""
        mock_repository.create_user.return_value = {
            "username": "newuser",
            "password_hash": "$2b$12$hash",
            "role": "user",
            "status": "pending_password",
            "must_change_password": True,
            "failed_login_count": 0,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        
        user = await user_service.create_user("newuser", "password123")
        
        assert user.username == "newuser"
        assert user.role == UserRole.USER
        assert user.status == UserStatus.PENDING_PASSWORD
        assert user.must_change_password is True
        mock_repository.create_user.assert_called_once()
    
    async def test_create_user_invalid_username(self, user_service):
        """Test creating user with invalid username."""
        with pytest.raises(ValidationError) as exc_info:
            await user_service.create_user("ab", "password")  # Too short
        
        assert "3-50 characters" in str(exc_info.value)
    
    async def test_create_user_invalid_role(self, user_service):
        """Test creating user with invalid role."""
        with pytest.raises(ValidationError) as exc_info:
            await user_service.create_user("validuser", "password", role="superuser")
        
        assert "Role must be" in str(exc_info.value)
    
    async def test_create_user_already_exists(self, user_service, mock_repository):
        """Test creating user that already exists."""
        mock_repository.get_user.return_value = {
            "username": "existinguser",
            "status": "active",
        }

        with pytest.raises(UserAlreadyExistsError):
            await user_service.create_user("existinguser", "password")
    
    # Get user tests
    
    async def test_get_user_found(self, user_service, mock_repository, sample_user_data):
        """Test getting existing user."""
        mock_repository.get_user.return_value = sample_user_data
        
        user = await user_service.get_user("testuser")
        
        assert user is not None
        assert user.username == "testuser"
    
    async def test_get_user_not_found(self, user_service, mock_repository):
        """Test getting non-existent user."""
        mock_repository.get_user.return_value = None
        
        user = await user_service.get_user("nonexistent")
        
        assert user is None
    
    # Update user tests
    
    async def test_update_user_password(self, user_service, mock_repository, sample_user_data, admin_user):
        """Test updating user password."""
        mock_repository.get_user.return_value = sample_user_data
        mock_repository.update_user.return_value = {
            **sample_user_data,
            "must_change_password": True,
        }
        
        user = await user_service.update_user(
            "testuser",
            password="newpassword",
            current_user=admin_user
        )
        
        assert user is not None
        mock_repository.update_user.assert_called_once()
        call_kwargs = mock_repository.update_user.call_args[1]
        assert "password_hash" in call_kwargs
        assert call_kwargs["must_change_password"] is True
    
    async def test_update_user_role(self, user_service, mock_repository, sample_user_data, admin_user):
        """Test updating user role."""
        mock_repository.get_user.return_value = sample_user_data
        mock_repository.update_user.return_value = {
            **sample_user_data,
            "role": "admin",
        }
        
        user = await user_service.update_user(
            "testuser",
            role="admin",
            current_user=admin_user
        )
        
        assert user is not None
        mock_repository.update_user.assert_called_once()
    
    async def test_update_own_role_denied(self, user_service, mock_repository, sample_user_data):
        """Test that users cannot change their own role."""
        current_user = User.from_dict(sample_user_data)
        mock_repository.get_user.return_value = sample_user_data
        
        with pytest.raises(PermissionDeniedError) as exc_info:
            await user_service.update_user(
                "testuser",
                role="admin",
                current_user=current_user
            )
        
        assert "own role" in str(exc_info.value)
    
    async def test_update_user_not_found(self, user_service, mock_repository):
        """Test updating non-existent user."""
        mock_repository.get_user.return_value = None
        
        with pytest.raises(UserNotFoundError):
            await user_service.update_user("nonexistent", password="new")
    
    # Delete user tests
    
    async def test_delete_user_success(self, user_service, mock_repository, sample_user_data, admin_user):
        """Test successful user deletion."""
        mock_repository.get_user.return_value = sample_user_data
        
        result = await user_service.delete_user("testuser", admin_user)
        
        assert result is True
        mock_repository.update_user.assert_called_once()
        call_kwargs = mock_repository.update_user.call_args[1]
        assert call_kwargs["status"] == "deleted"
        assert "deleted_at" in call_kwargs
    
    async def test_delete_self_denied(self, user_service, admin_user):
        """Test that users cannot delete themselves."""
        with pytest.raises(PermissionDeniedError) as exc_info:
            await user_service.delete_user("admin", admin_user)
        
        assert "own account" in str(exc_info.value)
    
    async def test_delete_last_admin_denied(self, user_service, mock_repository, admin_user):
        """Test that last admin cannot be deleted."""
        admin_data = {
            "username": "otheradmin",
            "password_hash": "$2b$12$hash",
            "role": "admin",
            "status": "active",
            "must_change_password": False,
            "failed_login_count": 0,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        mock_repository.get_user.return_value = admin_data
        mock_repository.count_active_admins.return_value = 1
        
        with pytest.raises(PermissionDeniedError) as exc_info:
            await user_service.delete_user("otheradmin", admin_user)
        
        assert "last admin" in str(exc_info.value)
    
    # Unlock user tests
    
    async def test_unlock_user_success(self, user_service, mock_repository):
        """Test successful user unlock."""
        locked_user_data = {
            "username": "lockeduser",
            "password_hash": "$2b$12$hash",
            "role": "user",
            "status": "locked",
            "must_change_password": False,
            "failed_login_count": 5,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        mock_repository.get_user.return_value = locked_user_data
        mock_repository.update_user.return_value = {
            **locked_user_data,
            "status": "active",
            "failed_login_count": 0,
        }
        
        user = await user_service.unlock_user("lockeduser")
        
        assert user.status == UserStatus.ACTIVE
        mock_repository.update_user.assert_called_once()
    
    async def test_unlock_user_not_locked(self, user_service, mock_repository, sample_user_data):
        """Test unlocking user that is not locked."""
        mock_repository.get_user.return_value = sample_user_data
        
        with pytest.raises(PermissionDeniedError) as exc_info:
            await user_service.unlock_user("testuser")
        
        assert "not locked" in str(exc_info.value)
    
    # Restore user tests
    
    async def test_restore_user_success(self, user_service, mock_repository):
        """Test successful user restore."""
        deleted_user_data = {
            "username": "deleteduser",
            "password_hash": "$2b$12$hash",
            "role": "user",
            "status": "deleted",
            "must_change_password": False,
            "failed_login_count": 0,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "deleted_at": "2026-01-15T00:00:00+00:00",
        }
        mock_repository.get_user.return_value = deleted_user_data
        mock_repository.update_user.return_value = {
            **deleted_user_data,
            "status": "active",
            "deleted_at": None,
        }
        
        user = await user_service.restore_user("deleteduser")
        
        assert user.status == UserStatus.ACTIVE
        mock_repository.update_user.assert_called_once()
    
    # Change password tests
    
    async def test_change_password_success(self, user_service, mock_repository):
        """Test successful password change."""
        # Create a real hash for the current password
        current_password = "oldpassword"
        current_hash = PasswordService.hash_password(current_password)
        
        user_data = {
            "username": "testuser",
            "password_hash": current_hash,
            "role": "user",
            "status": "active",
            "must_change_password": False,
            "failed_login_count": 0,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        mock_repository.get_user.return_value = user_data
        
        result = await user_service.change_password(
            "testuser",
            current_password,
            "newpassword"
        )
        
        assert result is True
        mock_repository.update_user.assert_called_once()
    
    async def test_change_password_wrong_current(self, user_service, mock_repository):
        """Test password change with wrong current password."""
        user_data = {
            "username": "testuser",
            "password_hash": PasswordService.hash_password("realpassword"),
            "role": "user",
            "status": "active",
            "must_change_password": False,
            "failed_login_count": 0,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        mock_repository.get_user.return_value = user_data
        
        with pytest.raises(ValidationError) as exc_info:
            await user_service.change_password(
                "testuser",
                "wrongpassword",
                "newpassword"
            )
        
        assert "incorrect" in str(exc_info.value)
    
    async def test_first_password_change_same_password_denied(self, user_service, mock_repository):
        """Test that first password change cannot use same password."""
        initial_password = "initialpassword"
        user_data = {
            "username": "newuser",
            "password_hash": PasswordService.hash_password(initial_password),
            "role": "user",
            "status": "pending_password",
            "must_change_password": True,
            "failed_login_count": 0,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        mock_repository.get_user.return_value = user_data
        
        with pytest.raises(ValidationError) as exc_info:
            await user_service.change_password(
                "newuser",
                initial_password,
                initial_password  # Same as initial
            )
        
        assert "same as the initial" in str(exc_info.value)
    
    # Login failure tracking tests
    
    async def test_record_login_failure(self, user_service, mock_repository, sample_user_data):
        """Test recording login failure."""
        mock_repository.get_user.return_value = sample_user_data
        
        remaining = await user_service.record_login_failure("testuser")
        
        assert remaining == 4  # 5 max - 1 failure
        mock_repository.update_user.assert_called_once()
    
    async def test_record_login_failure_locks_account(self, user_service, mock_repository):
        """Test that 5 failures locks the account."""
        user_data = {
            "username": "testuser",
            "password_hash": "$2b$12$hash",
            "role": "user",
            "status": "active",
            "must_change_password": False,
            "failed_login_count": 4,  # One more will lock
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        mock_repository.get_user.return_value = user_data
        
        remaining = await user_service.record_login_failure("testuser")
        
        assert remaining == 0
        call_kwargs = mock_repository.update_user.call_args[1]
        assert call_kwargs["status"] == "locked"
