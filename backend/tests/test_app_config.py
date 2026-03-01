"""Tests for AppConfig environment variable loading."""
import pytest


class TestAppConfigFromEnv:
    """Tests for AppConfig.from_env() method."""

    def test_from_env_requires_jwt_secret(self, monkeypatch):
        """Test that missing JWT_SECRET raises ConfigurationError."""
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.setenv("S3_BUCKET", "test-bucket")

        from src.core.app_config import AppConfig, ConfigurationError

        with pytest.raises(ConfigurationError, match="JWT_SECRET"):
            AppConfig.from_env()

    def test_from_env_requires_s3_bucket(self, monkeypatch):
        """Test that missing S3_BUCKET raises ConfigurationError."""
        monkeypatch.setenv("JWT_SECRET", "test-secret")
        monkeypatch.delenv("S3_BUCKET", raising=False)

        from src.core.app_config import AppConfig, ConfigurationError

        with pytest.raises(ConfigurationError, match="S3_BUCKET"):
            AppConfig.from_env()

    def test_from_env_uses_defaults(self, monkeypatch):
        """Test that optional vars use defaults when not set."""
        monkeypatch.setenv("JWT_SECRET", "test-secret")
        monkeypatch.setenv("S3_BUCKET", "test-bucket")
        monkeypatch.delenv("MAX_CONCURRENT_FILES", raising=False)
        monkeypatch.delenv("TRANSLATION_BATCH_SIZE", raising=False)
        monkeypatch.delenv("MAX_FILE_SIZE", raising=False)

        from src.core.app_config import AppConfig

        config = AppConfig.from_env()

        assert config.jwt_secret == "test-secret"
        assert config.s3_bucket == "test-bucket"
        assert config.max_concurrent_files == 5
        assert config.translation_batch_size == 10
        assert config.max_file_size == 52428800

    def test_from_env_accepts_custom_values(self, monkeypatch):
        """Test that custom env values are used."""
        monkeypatch.setenv("JWT_SECRET", "my-secret")
        monkeypatch.setenv("S3_BUCKET", "my-bucket")
        monkeypatch.setenv("MAX_CONCURRENT_FILES", "10")
        monkeypatch.setenv("TRANSLATION_BATCH_SIZE", "20")
        monkeypatch.setenv("MAX_FILE_SIZE", "104857600")

        from src.core.app_config import AppConfig

        config = AppConfig.from_env()

        assert config.jwt_secret == "my-secret"
        assert config.s3_bucket == "my-bucket"
        assert config.max_concurrent_files == 10
        assert config.translation_batch_size == 20
        assert config.max_file_size == 104857600

    def test_from_env_validates_positive_integers(self, monkeypatch):
        """Test that invalid integer values raise ConfigurationError."""
        monkeypatch.setenv("JWT_SECRET", "test")
        monkeypatch.setenv("S3_BUCKET", "test-bucket")
        monkeypatch.setenv("MAX_CONCURRENT_FILES", "invalid")

        from src.core.app_config import AppConfig, ConfigurationError

        with pytest.raises(ConfigurationError, match="MAX_CONCURRENT_FILES"):
            AppConfig.from_env()

    def test_from_env_validates_zero_not_allowed(self, monkeypatch):
        """Test that zero is rejected for positive integer fields."""
        monkeypatch.setenv("JWT_SECRET", "test")
        monkeypatch.setenv("S3_BUCKET", "test-bucket")
        monkeypatch.setenv("MAX_CONCURRENT_FILES", "0")

        from src.core.app_config import AppConfig, ConfigurationError

        with pytest.raises(ConfigurationError, match="positive integer"):
            AppConfig.from_env()
