"""
Configuration-related data models for the config storage system.

This module defines the data structures for:
- LanguagePair: User-level language pair configuration
- UserSettings: User preference settings
- GlobalConfig: System-level global configuration
- ModelConfig: Model configuration value object
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class UILanguage(str, Enum):
    """Supported UI languages."""
    CHINESE = "zh"
    VIETNAMESE = "vi"
    ENGLISH = "en"


class ConfigKey(str, Enum):
    """Global configuration keys."""
    AVAILABLE_MODELS = "AVAILABLE_MODELS"
    DEFAULT_SETTINGS = "DEFAULT_SETTINGS"
    DEFAULT_LANGUAGE_PAIRS = "DEFAULT_LANGUAGE_PAIRS"
    AWS_CONFIG = "AWS_CONFIG"
    STORAGE_CONFIG = "STORAGE_CONFIG"


class ConfigErrorCode(str, Enum):
    """Configuration error codes."""
    LANGUAGE_PAIR_NOT_FOUND = "LANGUAGE_PAIR_NOT_FOUND"
    LANGUAGE_PAIR_DUPLICATE = "LANGUAGE_PAIR_DUPLICATE"
    INVALID_LANGUAGE_PAIR = "INVALID_LANGUAGE_PAIR"
    USER_SETTINGS_NOT_FOUND = "USER_SETTINGS_NOT_FOUND"
    INVALID_MODEL_ID = "INVALID_MODEL_ID"
    INVALID_UI_LANGUAGE = "INVALID_UI_LANGUAGE"
    INVALID_BATCH_SIZE = "INVALID_BATCH_SIZE"
    INVALID_CONCURRENT_TASKS = "INVALID_CONCURRENT_TASKS"
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
    CONFIG_READONLY = "CONFIG_READONLY"


@dataclass
class LanguagePair:
    """
    User-level language pair configuration.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Owner user ID
        source_language: Source language code (e.g., "zh")
        target_language: Target language code (e.g., "vi")
        display_name: Human-readable name (e.g., "Chinese→Vietnamese")
        is_enabled: Whether this pair is active
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """
    id: str
    user_id: str
    source_language: str
    target_language: str
    display_name: str
    is_enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "display_name": self.display_name,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LanguagePair":
        """Create LanguagePair from dictionary."""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            source_language=data["source_language"],
            target_language=data["target_language"],
            display_name=data["display_name"],
            is_enabled=data.get("is_enabled", True),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
        )
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate language pair data.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.source_language == self.target_language:
            return False, "Source and target languages cannot be the same"
        
        if not self.display_name or len(self.display_name) > 100:
            return False, "Display name must be 1-100 characters"
        
        return True, None


@dataclass
class UserSettings:
    """
    User preference settings.
    
    Attributes:
        user_id: User ID (primary key)
        default_model_id: Default translation model ID
        ui_language: Interface language ("zh", "vi", "en")
        translation_batch_size: Translation batch size (1-100)
        max_concurrent_tasks: Maximum concurrent tasks (1-10)
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """
    user_id: str
    default_model_id: str
    ui_language: str = "zh"
    translation_batch_size: int = 10
    max_concurrent_tasks: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "default_model_id": self.default_model_id,
            "ui_language": self.ui_language,
            "translation_batch_size": self.translation_batch_size,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSettings":
        """Create UserSettings from dictionary."""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        
        return cls(
            user_id=data["user_id"],
            default_model_id=data["default_model_id"],
            ui_language=data.get("ui_language", "zh"),
            translation_batch_size=data.get("translation_batch_size", 10),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 3),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
        )
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate user settings.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_languages = [lang.value for lang in UILanguage]
        if self.ui_language not in valid_languages:
            return False, f"UI language must be one of: {', '.join(valid_languages)}"
        
        if not 1 <= self.translation_batch_size <= 100:
            return False, "Translation batch size must be between 1 and 100"
        
        if not 1 <= self.max_concurrent_tasks <= 10:
            return False, "Max concurrent tasks must be between 1 and 10"
        
        return True, None


@dataclass
class GlobalConfig:
    """
    System-level global configuration.

    Attributes:
        config_key: Configuration key (primary key)
        config_value: Configuration value (JSON)
        description: Configuration description
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """
    config_key: str
    config_value: Dict[str, Any]
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "config_key": self.config_key,
            "config_value": self.config_value,
            "description": self.description,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlobalConfig":
        """Create GlobalConfig from dictionary."""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return cls(
            config_key=data["config_key"],
            config_value=data.get("config_value", {}),
            description=data.get("description", ""),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
        )


@dataclass(frozen=True)
class ModelConfig:
    """
    Model configuration value object.
    
    Attributes:
        model_id: Model ID (e.g., "global.amazon.nova-2-lite-v1:0")
        display_name: Display name (e.g., "Nova Pro")
        provider: Provider name (e.g., "amazon", "anthropic")
        is_default: Whether this is the system default model
    """
    model_id: str
    display_name: str
    provider: str
    is_default: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model_id": self.model_id,
            "display_name": self.display_name,
            "provider": self.provider,
            "is_default": self.is_default,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        """Create ModelConfig from dictionary."""
        return cls(
            model_id=data["model_id"],
            display_name=data["display_name"],
            provider=data.get("provider", "unknown"),
            is_default=data.get("is_default", False),
        )


# Default language pair for new users
DEFAULT_LANGUAGE_PAIR = {
    "source_language": "zh",
    "target_language": "vi",
    "display_name": "Chinese→Vietnamese",
}

# Default user settings
DEFAULT_USER_SETTINGS = {
    "default_model_id": "global.amazon.nova-2-lite-v1:0",
    "ui_language": "zh",
    "translation_batch_size": 10,
    "max_concurrent_tasks": 3,
}

# Read-only configuration keys (cannot be modified via API)
READONLY_CONFIG_KEYS = {ConfigKey.AWS_CONFIG.value, ConfigKey.STORAGE_CONFIG.value}
