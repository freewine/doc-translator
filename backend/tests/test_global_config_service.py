"""
Unit tests for GlobalConfigService.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models.config import ConfigKey, GlobalConfig, ModelConfig, READONLY_CONFIG_KEYS
from src.services.global_config_service import GlobalConfigService


@pytest.fixture
def mock_repository():
    """Create a mock DynamoDB repository."""
    repo = MagicMock()
    repo.get_global_config = AsyncMock()
    repo.create_global_config = AsyncMock()
    repo.update_global_config = AsyncMock()
    repo.delete_global_config = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repository):
    """Create a GlobalConfigService instance."""
    return GlobalConfigService(repository=mock_repository)


class TestGetConfig:
    """Tests for get_config method."""
    
    async def test_get_existing_config(self, service, mock_repository):
        """Test getting existing configuration."""
        mock_repository.get_global_config.return_value = {
            "config_key": "AVAILABLE_MODELS",
            "config_value": {"models": []},
            "description": "Test",
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        result = await service.get_config("AVAILABLE_MODELS")
        
        assert result is not None
        assert result.config_key == "AVAILABLE_MODELS"
    
    async def test_get_nonexistent_config(self, service, mock_repository):
        """Test getting non-existent configuration."""
        mock_repository.get_global_config.return_value = None
        
        result = await service.get_config("NONEXISTENT")
        
        assert result is None


class TestGetAvailableModels:
    """Tests for get_available_models method."""
    
    async def test_get_available_models_from_config(self, service, mock_repository):
        """Test getting models from configuration."""
        mock_repository.get_global_config.return_value = {
            "config_key": "AVAILABLE_MODELS",
            "config_value": {
                "models": [
                    {
                        "model_id": "global.amazon.nova-2-lite-v1:0",
                        "display_name": "Nova 2 Lite",
                        "provider": "amazon",
                        "is_default": True,
                    },
                    {
                        "model_id": "anthropic.claude-3-sonnet",
                        "display_name": "Claude 3 Sonnet",
                        "provider": "anthropic",
                        "is_default": False,
                    },
                ]
            },
            "description": "Available models",
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        result = await service.get_available_models()
        
        assert len(result) == 2
        assert result[0].model_id == "global.amazon.nova-2-lite-v1:0"
        assert result[0].is_default is True
    
    async def test_get_available_models_returns_defaults_when_empty(
        self, service, mock_repository
    ):
        """Test that default models are returned when none configured."""
        mock_repository.get_global_config.return_value = None
        
        result = await service.get_available_models()
        
        assert len(result) > 0
        assert any(m.model_id == "global.amazon.nova-2-lite-v1:0" for m in result)


class TestGetDefaultSettings:
    """Tests for get_default_settings method."""
    
    async def test_get_default_settings_from_config(self, service, mock_repository):
        """Test getting default settings from configuration."""
        mock_repository.get_global_config.return_value = {
            "config_key": "DEFAULT_SETTINGS",
            "config_value": {
                "default_model_id": "global.amazon.nova-2-lite-v1:0",
                "ui_language": "vi",
                "translation_batch_size": 20,
                "max_concurrent_tasks": 5,
            },
            "description": "Default settings",
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        result = await service.get_default_settings()
        
        assert result["ui_language"] == "vi"
        assert result["translation_batch_size"] == 20
    
    async def test_get_default_settings_returns_fallback_when_empty(
        self, service, mock_repository
    ):
        """Test that fallback settings are returned when none configured."""
        mock_repository.get_global_config.return_value = None
        
        result = await service.get_default_settings()
        
        assert "default_model_id" in result
        assert "ui_language" in result


class TestIsModelValid:
    """Tests for is_model_valid method."""
    
    async def test_is_model_valid_returns_true(self, service, mock_repository):
        """Test that valid model ID returns True."""
        mock_repository.get_global_config.return_value = {
            "config_key": "AVAILABLE_MODELS",
            "config_value": {
                "models": [
                    {
                        "model_id": "global.amazon.nova-2-lite-v1:0",
                        "display_name": "Nova 2 Lite",
                        "provider": "amazon",
                        "is_default": True,
                    },
                ]
            },
            "description": "Available models",
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        result = await service.is_model_valid("global.amazon.nova-2-lite-v1:0")
        
        assert result is True
    
    async def test_is_model_valid_returns_false(self, service, mock_repository):
        """Test that invalid model ID returns False."""
        mock_repository.get_global_config.return_value = {
            "config_key": "AVAILABLE_MODELS",
            "config_value": {
                "models": [
                    {
                        "model_id": "global.amazon.nova-2-lite-v1:0",
                        "display_name": "Nova 2 Lite",
                        "provider": "amazon",
                        "is_default": True,
                    },
                ]
            },
            "description": "Available models",
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        result = await service.is_model_valid("invalid-model")
        
        assert result is False


class TestUpdateConfig:
    """Tests for update_config method."""
    
    async def test_update_config_success(self, service, mock_repository):
        """Test successful configuration update."""
        mock_repository.get_global_config.return_value = {
            "config_key": "DEFAULT_SETTINGS",
            "config_value": {"ui_language": "zh"},
            "description": "Old",
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        mock_repository.update_global_config.return_value = {
            "config_key": "DEFAULT_SETTINGS",
            "config_value": {
                "default_model_id": "global.amazon.nova-2-lite-v1:0",
                "ui_language": "vi",
                "translation_batch_size": 10,
                "max_concurrent_tasks": 3,
            },
            "description": "Updated",
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T11:00:00+00:00",
        }
        
        result = await service.update_config(
            config_key="DEFAULT_SETTINGS",
            config_value={
                "default_model_id": "global.amazon.nova-2-lite-v1:0",
                "ui_language": "vi",
                "translation_batch_size": 10,
                "max_concurrent_tasks": 3,
            },
            description="Updated",
        )
        
        assert result.config_value["ui_language"] == "vi"
    
    async def test_update_readonly_config_fails(self, service):
        """Test that updating read-only config fails."""
        with pytest.raises(ValueError, match="read-only"):
            await service.update_config(
                config_key="AWS_CONFIG",
                config_value={"region": "us-east-1"},
            )
    
    async def test_update_models_config_validates(self, service, mock_repository):
        """Test that AVAILABLE_MODELS config is validated."""
        mock_repository.get_global_config.return_value = None
        
        with pytest.raises(ValueError, match="at least one model"):
            await service.update_config(
                config_key="AVAILABLE_MODELS",
                config_value={"models": []},
            )
    
    async def test_update_default_settings_validates(self, service, mock_repository):
        """Test that DEFAULT_SETTINGS config is validated."""
        mock_repository.get_global_config.return_value = None
        
        with pytest.raises(ValueError, match="default_model_id"):
            await service.update_config(
                config_key="DEFAULT_SETTINGS",
                config_value={"ui_language": "zh"},
            )


class TestDeleteConfig:
    """Tests for delete_config method."""
    
    async def test_delete_config_success(self, service, mock_repository):
        """Test successful configuration deletion."""
        mock_repository.delete_global_config.return_value = True
        
        result = await service.delete_config("DEFAULT_SETTINGS")
        
        assert result is True
    
    async def test_delete_readonly_config_fails(self, service):
        """Test that deleting read-only config fails."""
        with pytest.raises(ValueError, match="read-only"):
            await service.delete_config("AWS_CONFIG")


class TestEnsureDefaultsExist:
    """Tests for ensure_defaults_exist method."""

    @pytest.mark.asyncio
    async def test_ensure_defaults_exist_seeds_empty_table(self, mock_repository):
        """Test that defaults are created when table is empty."""
        mock_repository.get_global_config.return_value = None
        mock_repository.create_global_config.return_value = {"config_key": "test"}

        service = GlobalConfigService(repository=mock_repository)
        await service.ensure_defaults_exist()

        # Should create 4 default configs
        assert mock_repository.create_global_config.call_count == 4

        # Verify keys were created
        calls = mock_repository.create_global_config.call_args_list
        config_keys = [call[0][0]["config_key"] for call in calls]
        assert "AVAILABLE_MODELS" in config_keys
        assert "DEFAULT_MODEL_ID" in config_keys
        assert "DEFAULT_LANGUAGE_PAIRS" in config_keys
        assert "DEFAULT_SETTINGS" in config_keys

    @pytest.mark.asyncio
    async def test_ensure_defaults_exist_is_idempotent(self, mock_repository):
        """Test that existing configs are not overwritten."""
        mock_repository.get_global_config.return_value = {
            "config_key": "AVAILABLE_MODELS",
            "config_value": {"models": []}
        }

        service = GlobalConfigService(repository=mock_repository)
        await service.ensure_defaults_exist()

        # Should not create any configs since they all exist
        mock_repository.create_global_config.assert_not_called()
