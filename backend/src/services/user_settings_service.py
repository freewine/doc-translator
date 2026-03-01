"""
User settings service for managing user preference configurations.

This service provides:
- User settings CRUD operations
- Settings initialization from global defaults
- Settings validation
"""
import logging
from typing import Optional

from src.models.config import (
    ConfigErrorCode,
    UILanguage,
    UserSettings,
)
from src.storage.dynamodb_repository import DynamoDBRepository

logger = logging.getLogger(__name__)


class UserSettingsService:
    """
    Service for managing user preference settings.
    
    This service handles:
    - Retrieving user settings (with auto-initialization)
    - Updating user settings with validation
    - Resetting settings to defaults
    """
    
    def __init__(
        self,
        repository: DynamoDBRepository,
        global_config_service: "GlobalConfigService",
        logger_instance: Optional[logging.Logger] = None
    ):
        """
        Initialize the user settings service.
        
        Args:
            repository: DynamoDB repository instance.
            global_config_service: Global config service for defaults.
            logger_instance: Optional logger instance.
        """
        self.repository = repository
        self.global_config_service = global_config_service
        self._logger = logger_instance or logger
    
    async def get_user_settings(self, user_id: str) -> UserSettings:
        """
        Get user settings, creating from defaults if not exists.
        
        Args:
            user_id: User ID.
            
        Returns:
            UserSettings object.
        """
        data = await self.repository.get_user_settings(user_id)
        
        if data:
            return UserSettings.from_dict(data)
        
        # Initialize from global defaults
        self._logger.info(f"Initializing settings for user {user_id}")
        return await self._initialize_user_settings(user_id)
    
    async def update_user_settings(
        self,
        user_id: str,
        default_model_id: Optional[str] = None,
        ui_language: Optional[str] = None,
        translation_batch_size: Optional[int] = None,
        max_concurrent_tasks: Optional[int] = None
    ) -> UserSettings:
        """
        Update user settings.
        
        Args:
            user_id: User ID.
            default_model_id: New default model ID (optional).
            ui_language: New UI language (optional).
            translation_batch_size: New batch size (optional).
            max_concurrent_tasks: New concurrent tasks limit (optional).
            
        Returns:
            Updated UserSettings.
            
        Raises:
            ValueError: If validation fails.
        """
        # Ensure settings exist
        current = await self.get_user_settings(user_id)
        
        # Validate and build updates
        updates = {}
        
        if default_model_id is not None:
            # Validate model ID
            is_valid = await self.global_config_service.is_model_valid(default_model_id)
            if not is_valid:
                raise ValueError(f"Invalid model ID: {default_model_id}")
            updates["default_model_id"] = default_model_id
        
        if ui_language is not None:
            # Validate UI language
            valid_languages = [lang.value for lang in UILanguage]
            if ui_language not in valid_languages:
                raise ValueError(
                    f"UI language must be one of: {', '.join(valid_languages)}"
                )
            updates["ui_language"] = ui_language
        
        if translation_batch_size is not None:
            # Validate batch size
            if not 1 <= translation_batch_size <= 100:
                raise ValueError("Translation batch size must be between 1 and 100")
            updates["translation_batch_size"] = translation_batch_size
        
        if max_concurrent_tasks is not None:
            # Validate concurrent tasks
            if not 1 <= max_concurrent_tasks <= 10:
                raise ValueError("Max concurrent tasks must be between 1 and 10")
            updates["max_concurrent_tasks"] = max_concurrent_tasks
        
        if not updates:
            return current
        
        data = await self.repository.update_user_settings(user_id, **updates)
        
        if data:
            self._logger.info(f"Updated settings for user {user_id}")
            return UserSettings.from_dict(data)
        
        # Should not happen since we ensured settings exist
        return current
    
    async def reset_user_settings(self, user_id: str) -> UserSettings:
        """
        Reset user settings to global defaults.
        
        Args:
            user_id: User ID.
            
        Returns:
            Reset UserSettings.
        """
        # Delete existing settings
        await self.repository.delete_user_settings(user_id)
        
        # Re-initialize from defaults
        self._logger.info(f"Reset settings for user {user_id}")
        return await self._initialize_user_settings(user_id)
    
    async def delete_user_settings(self, user_id: str) -> bool:
        """
        Delete user settings.
        
        Args:
            user_id: User ID.
            
        Returns:
            True if deleted, False if not found.
        """
        return await self.repository.delete_user_settings(user_id)
    
    async def _initialize_user_settings(self, user_id: str) -> UserSettings:
        """
        Initialize user settings from global defaults.
        
        Args:
            user_id: User ID.
            
        Returns:
            Initialized UserSettings.
        """
        # Get global defaults
        defaults = await self.global_config_service.get_default_settings()
        
        # Create user settings
        data = await self.repository.create_user_settings({
            "user_id": user_id,
            "default_model_id": defaults.get("default_model_id", "global.amazon.nova-2-lite-v1:0"),
            "ui_language": defaults.get("ui_language", "zh"),
            "translation_batch_size": defaults.get("translation_batch_size", 10),
            "max_concurrent_tasks": defaults.get("max_concurrent_tasks", 3),
        })
        
        return UserSettings.from_dict(data)


# Import for type hints (avoid circular import)
from src.services.global_config_service import GlobalConfigService
