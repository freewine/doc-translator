"""
Data models for the translation system.
"""
from .job import (
    FileError,
    FileProgress,
    JobStatus,
    LanguagePair,
    TranslationJob,
)
from .user import (
    AuthErrorCode,
    AuthResult,
    TokenPayload,
    User,
    UserRole,
    UserStatus,
    validate_role,
    validate_username,
)
from .config import (
    ConfigErrorCode,
    ConfigKey,
    GlobalConfig,
    LanguagePair as ConfigLanguagePair,
    ModelConfig,
    UILanguage,
    UserSettings,
    DEFAULT_LANGUAGE_PAIR,
    DEFAULT_USER_SETTINGS,
    READONLY_CONFIG_KEYS,
)

__all__ = [
    # Job models
    "FileError",
    "FileProgress",
    "JobStatus",
    "LanguagePair",
    "TranslationJob",
    # User models
    "AuthErrorCode",
    "AuthResult",
    "TokenPayload",
    "User",
    "UserRole",
    "UserStatus",
    "validate_role",
    "validate_username",
    # Config models (Unit-2)
    "ConfigErrorCode",
    "ConfigKey",
    "ConfigLanguagePair",
    "GlobalConfig",
    "ModelConfig",
    "UILanguage",
    "UserSettings",
    "DEFAULT_LANGUAGE_PAIR",
    "DEFAULT_USER_SETTINGS",
    "READONLY_CONFIG_KEYS",
]
