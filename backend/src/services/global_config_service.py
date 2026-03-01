"""
Global configuration service for managing system-wide settings.

This service provides:
- Access to global configuration values
- Available models management
- Default settings retrieval
- Model validation
"""
import logging
from typing import Any, Dict, List, Optional

from src.models.config import (
    ConfigErrorCode,
    ConfigKey,
    GlobalConfig,
    ModelConfig,
    READONLY_CONFIG_KEYS,
)
from src.storage.dynamodb_repository import DynamoDBRepository

logger = logging.getLogger(__name__)


class GlobalConfigService:
    """
    Service for managing global system configuration.
    
    This service handles:
    - Retrieving global configuration values
    - Managing available translation models
    - Providing default user settings
    - Validating model IDs
    """
    
    def __init__(
        self,
        repository: DynamoDBRepository,
        logger_instance: Optional[logging.Logger] = None
    ):
        """
        Initialize the global config service.
        
        Args:
            repository: DynamoDB repository instance.
            logger_instance: Optional logger instance.
        """
        self.repository = repository
        self._logger = logger_instance or logger
    
    async def get_config(self, config_key: str) -> Optional[GlobalConfig]:
        """
        Get a global configuration by key.
        
        Args:
            config_key: Configuration key.
            
        Returns:
            GlobalConfig if found, None otherwise.
        """
        data = await self.repository.get_global_config(config_key)
        if data:
            return GlobalConfig.from_dict(data)
        return None
    
    async def get_available_models(self) -> List[ModelConfig]:
        """
        Get the list of available translation models.
        
        Returns:
            List of ModelConfig objects.
        """
        config = await self.get_config(ConfigKey.AVAILABLE_MODELS.value)
        
        if not config or not config.config_value:
            self._logger.warning("No available models configured, returning defaults")
            return self._get_default_models()
        
        models = []
        for model_data in config.config_value.get("models", []):
            models.append(ModelConfig.from_dict(model_data))
        
        return models
    
    async def get_default_settings(self) -> Dict[str, Any]:
        """
        Get the default user settings.
        
        Returns:
            Dictionary of default settings.
        """
        config = await self.get_config(ConfigKey.DEFAULT_SETTINGS.value)
        
        if not config or not config.config_value:
            self._logger.warning("No default settings configured, returning defaults")
            return self._get_default_settings_fallback()
        
        return config.config_value
    
    async def is_model_valid(self, model_id: str) -> bool:
        """
        Check if a model ID is valid (exists in available models).
        
        Args:
            model_id: Model ID to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        models = await self.get_available_models()
        return any(m.model_id == model_id for m in models)
    
    async def get_default_model_id(self) -> str:
        """
        Get the default model ID.
        
        Returns:
            Default model ID.
        """
        models = await self.get_available_models()
        
        # Find the default model
        for model in models:
            if model.is_default:
                return model.model_id
        
        # Return first model if no default set
        if models:
            return models[0].model_id
        
        # Fallback
        return "global.amazon.nova-2-lite-v1:0"
    
    async def update_config(
        self,
        config_key: str,
        config_value: Dict[str, Any],
        description: Optional[str] = None
    ) -> GlobalConfig:
        """
        Update a global configuration.
        
        Args:
            config_key: Configuration key.
            config_value: New configuration value.
            description: Optional description.
            
        Returns:
            Updated GlobalConfig.
            
        Raises:
            ValueError: If config key is read-only.
        """
        if config_key in READONLY_CONFIG_KEYS:
            raise ValueError(
                f"Configuration '{config_key}' is read-only and cannot be modified via API"
            )
        
        # Validate specific config types
        if config_key == ConfigKey.AVAILABLE_MODELS.value:
            self._validate_models_config(config_value)
        elif config_key == ConfigKey.DEFAULT_SETTINGS.value:
            self._validate_default_settings(config_value)
        
        updates = {"config_value": config_value}
        if description is not None:
            updates["description"] = description
        
        # Check if config exists
        existing = await self.get_config(config_key)
        
        if existing:
            data = await self.repository.update_global_config(config_key, **updates)
        else:
            data = await self.repository.create_global_config({
                "config_key": config_key,
                "config_value": config_value,
                "description": description or "",
            })
        
        return GlobalConfig.from_dict(data)
    
    async def create_config(
        self,
        config_key: str,
        config_value: Dict[str, Any],
        description: str = "",
    ) -> GlobalConfig:
        """
        Create a new global configuration.

        Args:
            config_key: Configuration key.
            config_value: Configuration value.
            description: Configuration description.

        Returns:
            Created GlobalConfig.
        """
        data = await self.repository.create_global_config({
            "config_key": config_key,
            "config_value": config_value,
            "description": description,
        })

        return GlobalConfig.from_dict(data)
    
    async def delete_config(self, config_key: str) -> bool:
        """
        Delete a global configuration.
        
        Args:
            config_key: Configuration key.
            
        Returns:
            True if deleted, False if not found.
            
        Raises:
            ValueError: If config key is read-only.
        """
        if config_key in READONLY_CONFIG_KEYS:
            raise ValueError(
                f"Configuration '{config_key}' is read-only and cannot be deleted"
            )
        
        return await self.repository.delete_global_config(config_key)
    
    def _validate_models_config(self, config_value: Dict[str, Any]) -> None:
        """Validate AVAILABLE_MODELS configuration."""
        models = config_value.get("models", [])
        
        if not models:
            raise ValueError("AVAILABLE_MODELS must contain at least one model")
        
        for model in models:
            if not model.get("model_id"):
                raise ValueError("Each model must have a model_id")
            if not model.get("display_name"):
                raise ValueError("Each model must have a display_name")
    
    def _validate_default_settings(self, config_value: Dict[str, Any]) -> None:
        """Validate DEFAULT_SETTINGS configuration."""
        required_fields = [
            "default_model_id",
            "ui_language",
            "translation_batch_size",
            "max_concurrent_tasks"
        ]
        
        for field in required_fields:
            if field not in config_value:
                raise ValueError(f"DEFAULT_SETTINGS must contain '{field}'")
    
    def _get_default_models(self) -> List[ModelConfig]:
        """Get default models when none are configured."""
        return [
            ModelConfig(
                model_id="global.amazon.nova-2-lite-v1:0",
                display_name="Nova 2 Lite",
                provider="amazon",
                is_default=True,
            ),
            ModelConfig(
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
                display_name="Claude 3.5 Sonnet",
                provider="anthropic",
                is_default=False,
            ),
        ]
    
    def _get_default_settings_fallback(self) -> Dict[str, Any]:
        """Get default settings when none are configured."""
        return {
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "zh",
            "translation_batch_size": 10,
            "max_concurrent_tasks": 3,
        }

    async def ensure_defaults_exist(self) -> None:
        """
        Seed default configuration entries if they don't exist.

        This method is idempotent - safe to call multiple times.
        Creates defaults for:
        - AVAILABLE_MODELS
        - DEFAULT_MODEL_ID
        - DEFAULT_LANGUAGE_PAIRS
        - DEFAULT_SETTINGS
        """
        from datetime import datetime, timezone

        defaults = {
            ConfigKey.AVAILABLE_MODELS.value: {
                "models": [
                    {"model_id": "global.amazon.nova-2-lite-v1:0", "display_name": "Nova 2 Lite", "provider": "amazon", "is_default": True},
                    {"model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0", "display_name": "Claude Sonnet 4.5", "provider": "anthropic", "is_default": False},
                    {"model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0", "display_name": "Claude Haiku 4.5", "provider": "anthropic", "is_default": False},
                ]
            },
            "DEFAULT_MODEL_ID": {"model_id": "global.amazon.nova-2-lite-v1:0"},
            ConfigKey.DEFAULT_LANGUAGE_PAIRS.value: {
                "language_pairs": [
                    {"source_language": "zh", "target_language": "vi", "display_name": "Chinese → Vietnamese"}
                ]
            },
            ConfigKey.DEFAULT_SETTINGS.value: {
                "default_model_id": "global.amazon.nova-2-lite-v1:0",
                "ui_language": "vi",
                "translation_batch_size": 10,
                "max_concurrent_tasks": 5
            }
        }

        now = datetime.now(timezone.utc).isoformat()

        for config_key, config_value in defaults.items():
            existing = await self.repository.get_global_config(config_key)
            if not existing:
                await self.repository.create_global_config({
                    "config_key": config_key,
                    "config_value": config_value,
                    "description": f"Default {config_key}",
                    "created_at": now,
                    "updated_at": now,
                })
                self._logger.info(f"Created default config: {config_key}")
