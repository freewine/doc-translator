"""
Unit tests for UserSettingsService.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models.config import UserSettings
from src.services.user_settings_service import UserSettingsService


@pytest.fixture
def mock_repository():
    """Create a mock DynamoDB repository."""
    repo = MagicMock()
    repo.get_user_settings = AsyncMock()
    repo.create_user_settings = AsyncMock()
    repo.update_user_settings = AsyncMock()
    repo.delete_user_settings = AsyncMock()
    return repo


@pytest.fixture
def mock_global_config_service():
    """Create a mock GlobalConfigService."""
    service = MagicMock()
    service.get_default_settings = AsyncMock(return_value={
        "default_model_id": "global.amazon.nova-2-lite-v1:0",
        "ui_language": "zh",
        "translation_batch_size": 10,
        "max_concurrent_tasks": 3,
    })
    service.is_model_valid = AsyncMock(return_value=True)
    return service


@pytest.fixture
def service(mock_repository, mock_global_config_service):
    """Create a UserSettingsService instance."""
    return UserSettingsService(
        repository=mock_repository,
        global_config_service=mock_global_config_service,
    )


class TestGetUserSettings:
    """Tests for get_user_settings method."""
    
    async def test_get_existing_settings(self, service, mock_repository):
        """Test getting existing user settings."""
        mock_repository.get_user_settings.return_value = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "vi",
            "translation_batch_size": 20,
            "max_concurrent_tasks": 5,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        result = await service.get_user_settings("user-123")
        
        assert result.user_id == "user-123"
        assert result.ui_language == "vi"
        assert result.translation_batch_size == 20
    
    async def test_get_settings_initializes_from_defaults(
        self, service, mock_repository, mock_global_config_service
    ):
        """Test that settings are initialized from defaults if not exist."""
        mock_repository.get_user_settings.return_value = None
        mock_repository.create_user_settings.return_value = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "zh",
            "translation_batch_size": 10,
            "max_concurrent_tasks": 3,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        result = await service.get_user_settings("user-123")
        
        assert result.user_id == "user-123"
        assert result.ui_language == "zh"
        mock_global_config_service.get_default_settings.assert_called_once()
        mock_repository.create_user_settings.assert_called_once()


class TestUpdateUserSettings:
    """Tests for update_user_settings method."""
    
    async def test_update_settings_success(self, service, mock_repository):
        """Test successful settings update."""
        # First call for get_user_settings
        mock_repository.get_user_settings.return_value = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "zh",
            "translation_batch_size": 10,
            "max_concurrent_tasks": 3,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        mock_repository.update_user_settings.return_value = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "vi",
            "translation_batch_size": 50,
            "max_concurrent_tasks": 3,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T11:00:00+00:00",
        }
        
        result = await service.update_user_settings(
            user_id="user-123",
            ui_language="vi",
            translation_batch_size=50,
        )
        
        assert result.ui_language == "vi"
        assert result.translation_batch_size == 50
    
    async def test_update_settings_invalid_model(
        self, service, mock_repository, mock_global_config_service
    ):
        """Test that invalid model ID fails."""
        mock_repository.get_user_settings.return_value = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "zh",
            "translation_batch_size": 10,
            "max_concurrent_tasks": 3,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        mock_global_config_service.is_model_valid.return_value = False
        
        with pytest.raises(ValueError, match="Invalid model ID"):
            await service.update_user_settings(
                user_id="user-123",
                default_model_id="invalid-model",
            )
    
    async def test_update_settings_invalid_language(self, service, mock_repository):
        """Test that invalid UI language fails."""
        mock_repository.get_user_settings.return_value = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "zh",
            "translation_batch_size": 10,
            "max_concurrent_tasks": 3,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        with pytest.raises(ValueError, match="language"):
            await service.update_user_settings(
                user_id="user-123",
                ui_language="invalid",
            )
    
    async def test_update_settings_batch_size_too_low(self, service, mock_repository):
        """Test that batch size below 1 fails."""
        mock_repository.get_user_settings.return_value = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "zh",
            "translation_batch_size": 10,
            "max_concurrent_tasks": 3,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        with pytest.raises(ValueError, match="batch size"):
            await service.update_user_settings(
                user_id="user-123",
                translation_batch_size=0,
            )
    
    async def test_update_settings_batch_size_too_high(self, service, mock_repository):
        """Test that batch size above 100 fails."""
        mock_repository.get_user_settings.return_value = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "zh",
            "translation_batch_size": 10,
            "max_concurrent_tasks": 3,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        with pytest.raises(ValueError, match="batch size"):
            await service.update_user_settings(
                user_id="user-123",
                translation_batch_size=101,
            )
    
    async def test_update_settings_concurrent_tasks_too_low(self, service, mock_repository):
        """Test that concurrent tasks below 1 fails."""
        mock_repository.get_user_settings.return_value = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "zh",
            "translation_batch_size": 10,
            "max_concurrent_tasks": 3,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        with pytest.raises(ValueError, match="concurrent"):
            await service.update_user_settings(
                user_id="user-123",
                max_concurrent_tasks=0,
            )
    
    async def test_update_settings_concurrent_tasks_too_high(self, service, mock_repository):
        """Test that concurrent tasks above 10 fails."""
        mock_repository.get_user_settings.return_value = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "zh",
            "translation_batch_size": 10,
            "max_concurrent_tasks": 3,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        with pytest.raises(ValueError, match="concurrent"):
            await service.update_user_settings(
                user_id="user-123",
                max_concurrent_tasks=11,
            )


class TestResetUserSettings:
    """Tests for reset_user_settings method."""
    
    async def test_reset_settings(
        self, service, mock_repository, mock_global_config_service
    ):
        """Test resetting user settings to defaults."""
        mock_repository.delete_user_settings.return_value = True
        mock_repository.create_user_settings.return_value = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "zh",
            "translation_batch_size": 10,
            "max_concurrent_tasks": 3,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        result = await service.reset_user_settings("user-123")
        
        assert result.ui_language == "zh"
        assert result.translation_batch_size == 10
        mock_repository.delete_user_settings.assert_called_once_with("user-123")
        mock_repository.create_user_settings.assert_called_once()
