"""
Unit tests for configuration models.
"""
import pytest
from datetime import datetime, timezone

from src.models.config import (
    ConfigErrorCode,
    ConfigKey,
    DEFAULT_LANGUAGE_PAIR,
    DEFAULT_USER_SETTINGS,
    GlobalConfig,
    LanguagePair,
    ModelConfig,
    READONLY_CONFIG_KEYS,
    UILanguage,
    UserSettings,
)


class TestLanguagePair:
    """Tests for LanguagePair model."""
    
    def test_create_language_pair(self):
        """Test creating a language pair."""
        lp = LanguagePair(
            id="lp-123",
            user_id="user-456",
            source_language="zh",
            target_language="vi",
            display_name="Chinese→Vietnamese",
        )
        
        assert lp.id == "lp-123"
        assert lp.user_id == "user-456"
        assert lp.source_language == "zh"
        assert lp.target_language == "vi"
        assert lp.display_name == "Chinese→Vietnamese"
        assert lp.is_enabled is True
    
    def test_language_pair_to_dict(self):
        """Test converting language pair to dictionary."""
        now = datetime.now(timezone.utc)
        lp = LanguagePair(
            id="lp-123",
            user_id="user-456",
            source_language="zh",
            target_language="vi",
            display_name="Chinese→Vietnamese",
            is_enabled=True,
            created_at=now,
            updated_at=now,
        )
        
        data = lp.to_dict()
        
        assert data["id"] == "lp-123"
        assert data["user_id"] == "user-456"
        assert data["source_language"] == "zh"
        assert data["target_language"] == "vi"
        assert data["display_name"] == "Chinese→Vietnamese"
        assert data["is_enabled"] is True
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_language_pair_from_dict(self):
        """Test creating language pair from dictionary."""
        data = {
            "id": "lp-123",
            "user_id": "user-456",
            "source_language": "zh",
            "target_language": "vi",
            "display_name": "Chinese→Vietnamese",
            "is_enabled": False,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        lp = LanguagePair.from_dict(data)
        
        assert lp.id == "lp-123"
        assert lp.user_id == "user-456"
        assert lp.source_language == "zh"
        assert lp.target_language == "vi"
        assert lp.is_enabled is False
    
    def test_language_pair_validate_success(self):
        """Test successful validation."""
        lp = LanguagePair(
            id="lp-123",
            user_id="user-456",
            source_language="zh",
            target_language="vi",
            display_name="Chinese→Vietnamese",
        )
        
        is_valid, error = lp.validate()
        
        assert is_valid is True
        assert error is None
    
    def test_language_pair_validate_same_language(self):
        """Test validation fails when source equals target."""
        lp = LanguagePair(
            id="lp-123",
            user_id="user-456",
            source_language="zh",
            target_language="zh",
            display_name="Chinese→Chinese",
        )
        
        is_valid, error = lp.validate()
        
        assert is_valid is False
        assert "same" in error.lower()
    
    def test_language_pair_validate_display_name_too_long(self):
        """Test validation fails when display name is too long."""
        lp = LanguagePair(
            id="lp-123",
            user_id="user-456",
            source_language="zh",
            target_language="vi",
            display_name="x" * 101,
        )
        
        is_valid, error = lp.validate()
        
        assert is_valid is False
        assert "100" in error


class TestUserSettings:
    """Tests for UserSettings model."""
    
    def test_create_user_settings(self):
        """Test creating user settings."""
        settings = UserSettings(
            user_id="user-123",
            default_model_id="global.amazon.nova-2-lite-v1:0",
        )
        
        assert settings.user_id == "user-123"
        assert settings.default_model_id == "global.amazon.nova-2-lite-v1:0"
        assert settings.ui_language == "zh"
        assert settings.translation_batch_size == 10
        assert settings.max_concurrent_tasks == 3
    
    def test_user_settings_to_dict(self):
        """Test converting user settings to dictionary."""
        settings = UserSettings(
            user_id="user-123",
            default_model_id="global.amazon.nova-2-lite-v1:0",
            ui_language="vi",
            translation_batch_size=20,
            max_concurrent_tasks=5,
        )
        
        data = settings.to_dict()
        
        assert data["user_id"] == "user-123"
        assert data["default_model_id"] == "global.amazon.nova-2-lite-v1:0"
        assert data["ui_language"] == "vi"
        assert data["translation_batch_size"] == 20
        assert data["max_concurrent_tasks"] == 5
    
    def test_user_settings_from_dict(self):
        """Test creating user settings from dictionary."""
        data = {
            "user_id": "user-123",
            "default_model_id": "global.amazon.nova-2-lite-v1:0",
            "ui_language": "en",
            "translation_batch_size": 50,
            "max_concurrent_tasks": 8,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        settings = UserSettings.from_dict(data)
        
        assert settings.user_id == "user-123"
        assert settings.ui_language == "en"
        assert settings.translation_batch_size == 50
        assert settings.max_concurrent_tasks == 8
    
    def test_user_settings_validate_success(self):
        """Test successful validation."""
        settings = UserSettings(
            user_id="user-123",
            default_model_id="global.amazon.nova-2-lite-v1:0",
            ui_language="zh",
            translation_batch_size=10,
            max_concurrent_tasks=3,
        )
        
        is_valid, error = settings.validate()
        
        assert is_valid is True
        assert error is None
    
    def test_user_settings_validate_invalid_language(self):
        """Test validation fails with invalid UI language."""
        settings = UserSettings(
            user_id="user-123",
            default_model_id="global.amazon.nova-2-lite-v1:0",
            ui_language="invalid",
        )
        
        is_valid, error = settings.validate()
        
        assert is_valid is False
        assert "language" in error.lower()
    
    def test_user_settings_validate_batch_size_too_low(self):
        """Test validation fails when batch size is too low."""
        settings = UserSettings(
            user_id="user-123",
            default_model_id="global.amazon.nova-2-lite-v1:0",
            translation_batch_size=0,
        )
        
        is_valid, error = settings.validate()
        
        assert is_valid is False
        assert "batch" in error.lower()
    
    def test_user_settings_validate_batch_size_too_high(self):
        """Test validation fails when batch size is too high."""
        settings = UserSettings(
            user_id="user-123",
            default_model_id="global.amazon.nova-2-lite-v1:0",
            translation_batch_size=101,
        )
        
        is_valid, error = settings.validate()
        
        assert is_valid is False
        assert "batch" in error.lower()
    
    def test_user_settings_validate_concurrent_tasks_too_low(self):
        """Test validation fails when concurrent tasks is too low."""
        settings = UserSettings(
            user_id="user-123",
            default_model_id="global.amazon.nova-2-lite-v1:0",
            max_concurrent_tasks=0,
        )
        
        is_valid, error = settings.validate()
        
        assert is_valid is False
        assert "concurrent" in error.lower()
    
    def test_user_settings_validate_concurrent_tasks_too_high(self):
        """Test validation fails when concurrent tasks is too high."""
        settings = UserSettings(
            user_id="user-123",
            default_model_id="global.amazon.nova-2-lite-v1:0",
            max_concurrent_tasks=11,
        )
        
        is_valid, error = settings.validate()
        
        assert is_valid is False
        assert "concurrent" in error.lower()


class TestGlobalConfig:
    """Tests for GlobalConfig model."""
    
    def test_create_global_config(self):
        """Test creating global config."""
        config = GlobalConfig(
            config_key="AVAILABLE_MODELS",
            config_value={"models": []},
            description="Available translation models",
        )
        
        assert config.config_key == "AVAILABLE_MODELS"
        assert config.config_value == {"models": []}
        assert config.description == "Available translation models"
    
    def test_global_config_to_dict(self):
        """Test converting global config to dictionary."""
        config = GlobalConfig(
            config_key="AVAILABLE_MODELS",
            config_value={"models": [{"id": "model-1"}]},
            description="Test",
        )
        
        data = config.to_dict()
        
        assert data["config_key"] == "AVAILABLE_MODELS"
        assert data["config_value"] == {"models": [{"id": "model-1"}]}
    
    def test_global_config_from_dict(self):
        """Test creating global config from dictionary."""
        data = {
            "config_key": "DEFAULT_SETTINGS",
            "config_value": {"ui_language": "zh"},
            "description": "Default user settings",
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        config = GlobalConfig.from_dict(data)
        
        assert config.config_key == "DEFAULT_SETTINGS"
        assert config.config_value == {"ui_language": "zh"}


class TestModelConfig:
    """Tests for ModelConfig value object."""
    
    def test_create_model_config(self):
        """Test creating model config."""
        model = ModelConfig(
            model_id="global.amazon.nova-2-lite-v1:0",
            display_name="Nova 2 Lite",
            provider="amazon",
            is_default=True,
        )
        
        assert model.model_id == "global.amazon.nova-2-lite-v1:0"
        assert model.display_name == "Nova 2 Lite"
        assert model.provider == "amazon"
        assert model.is_default is True
    
    def test_model_config_immutable(self):
        """Test that ModelConfig is immutable."""
        model = ModelConfig(
            model_id="global.amazon.nova-2-lite-v1:0",
            display_name="Nova 2 Lite",
            provider="amazon",
        )
        
        with pytest.raises(Exception):
            model.model_id = "changed"
    
    def test_model_config_to_dict(self):
        """Test converting model config to dictionary."""
        model = ModelConfig(
            model_id="global.amazon.nova-2-lite-v1:0",
            display_name="Nova 2 Lite",
            provider="amazon",
            is_default=True,
        )
        
        data = model.to_dict()
        
        assert data["model_id"] == "global.amazon.nova-2-lite-v1:0"
        assert data["display_name"] == "Nova 2 Lite"
        assert data["provider"] == "amazon"
        assert data["is_default"] is True
    
    def test_model_config_from_dict(self):
        """Test creating model config from dictionary."""
        data = {
            "model_id": "anthropic.claude-3-sonnet",
            "display_name": "Claude 3 Sonnet",
            "provider": "anthropic",
            "is_default": False,
        }
        
        model = ModelConfig.from_dict(data)
        
        assert model.model_id == "anthropic.claude-3-sonnet"
        assert model.display_name == "Claude 3 Sonnet"
        assert model.provider == "anthropic"


class TestEnums:
    """Tests for configuration enums."""
    
    def test_ui_language_values(self):
        """Test UILanguage enum values."""
        assert UILanguage.CHINESE.value == "zh"
        assert UILanguage.VIETNAMESE.value == "vi"
        assert UILanguage.ENGLISH.value == "en"
    
    def test_config_key_values(self):
        """Test ConfigKey enum values."""
        assert ConfigKey.AVAILABLE_MODELS.value == "AVAILABLE_MODELS"
        assert ConfigKey.DEFAULT_SETTINGS.value == "DEFAULT_SETTINGS"
        assert ConfigKey.DEFAULT_LANGUAGE_PAIRS.value == "DEFAULT_LANGUAGE_PAIRS"
        assert ConfigKey.AWS_CONFIG.value == "AWS_CONFIG"
        assert ConfigKey.STORAGE_CONFIG.value == "STORAGE_CONFIG"
    
    def test_config_error_code_values(self):
        """Test ConfigErrorCode enum values."""
        assert ConfigErrorCode.LANGUAGE_PAIR_NOT_FOUND.value == "LANGUAGE_PAIR_NOT_FOUND"
        assert ConfigErrorCode.INVALID_MODEL_ID.value == "INVALID_MODEL_ID"


class TestConstants:
    """Tests for configuration constants."""
    
    def test_default_language_pair(self):
        """Test default language pair constant."""
        assert DEFAULT_LANGUAGE_PAIR["source_language"] == "zh"
        assert DEFAULT_LANGUAGE_PAIR["target_language"] == "vi"
        assert "display_name" in DEFAULT_LANGUAGE_PAIR
    
    def test_default_user_settings(self):
        """Test default user settings constant."""
        assert "default_model_id" in DEFAULT_USER_SETTINGS
        assert DEFAULT_USER_SETTINGS["ui_language"] == "zh"
        assert DEFAULT_USER_SETTINGS["translation_batch_size"] == 10
        assert DEFAULT_USER_SETTINGS["max_concurrent_tasks"] == 3
    
    def test_readonly_config_keys(self):
        """Test readonly config keys constant."""
        assert "AWS_CONFIG" in READONLY_CONFIG_KEYS
        assert "STORAGE_CONFIG" in READONLY_CONFIG_KEYS
        assert "AVAILABLE_MODELS" not in READONLY_CONFIG_KEYS
