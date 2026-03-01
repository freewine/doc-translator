"""Property-based tests for S3 configuration requirement.

This module tests that the application correctly requires S3_BUCKET
environment variable at startup, as part of the local storage cleanup.
"""

import os
from contextlib import contextmanager
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck


# Environment variables that AppConfig reads
APP_CONFIG_ENV_VARS = [
    "JWT_SECRET", "S3_BUCKET", "MAX_CONCURRENT_FILES",
    "TRANSLATION_BATCH_SIZE", "MAX_FILE_SIZE"
]


@contextmanager
def isolated_env(env_vars: dict):
    """
    Context manager that temporarily sets environment variables and restores
    the original state on exit.
    
    Args:
        env_vars: Dictionary of environment variables to set
    """
    # Save original values
    original = {}
    for var in APP_CONFIG_ENV_VARS:
        original[var] = os.environ.get(var)
        # Clear the variable
        if var in os.environ:
            del os.environ[var]
    
    # Set new values
    for name, value in env_vars.items():
        os.environ[name] = value
    
    try:
        yield
    finally:
        # Restore original values
        for var in APP_CONFIG_ENV_VARS:
            if var in os.environ:
                del os.environ[var]
            if original[var] is not None:
                os.environ[var] = original[var]
        
        # Clean up any extra vars we added
        for name in env_vars:
            if name not in APP_CONFIG_ENV_VARS and name in os.environ:
                del os.environ[name]


# Strategy for generating random environment variable names
# Excludes S3_BUCKET to ensure we never accidentally set it
@st.composite
def env_var_name_strategy(draw):
    """Generate valid environment variable names that are NOT S3_BUCKET."""
    name = draw(st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_'
        )
    ))
    # Ensure we never generate S3_BUCKET or other AppConfig vars
    assume(name.upper() not in [v.upper() for v in APP_CONFIG_ENV_VARS])
    return name


@st.composite
def env_var_value_strategy(draw):
    """Generate valid environment variable values."""
    return draw(st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            min_codepoint=33,
            max_codepoint=126
        )
    ))


@st.composite
def random_env_config_without_s3_bucket(draw):
    """
    Generate a random environment configuration that does NOT include S3_BUCKET.
    
    This strategy generates:
    - A random JWT_SECRET (may or may not be present)
    - Random optional config values (MAX_CONCURRENT_FILES, etc.)
    - Never includes S3_BUCKET
    """
    config = {}
    
    # Randomly decide whether to include JWT_SECRET
    if draw(st.booleans()):
        config["JWT_SECRET"] = draw(st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(min_codepoint=33, max_codepoint=126)
        ))
    
    # Randomly include optional config values
    if draw(st.booleans()):
        config["MAX_CONCURRENT_FILES"] = str(draw(st.integers(min_value=1, max_value=100)))
    
    if draw(st.booleans()):
        config["TRANSLATION_BATCH_SIZE"] = str(draw(st.integers(min_value=1, max_value=100)))
    
    if draw(st.booleans()):
        config["MAX_FILE_SIZE"] = str(draw(st.integers(min_value=1, max_value=100000000)))
    
    # S3_BUCKET is never included
    return config


class TestS3ConfigurationRequired:
    """Property-based tests for S3 configuration requirement."""
    
    @given(env_config=random_env_config_without_s3_bucket())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_1_s3_configuration_required_at_startup(self, env_config):
        """
        **Validates: Requirements 3.1**
        
        Property 1: S3 Configuration Required at Startup
        
        For any application startup attempt without the `S3_BUCKET` environment
        variable set, the system should raise a `ConfigurationError` and fail to start.
        
        This property ensures that:
        1. The system fails fast when S3 is not configured
        2. No silent fallback to local storage occurs
        3. The error message clearly indicates S3_BUCKET is required
        """
        from src.core.app_config import AppConfig, ConfigurationError
        
        with isolated_env(env_config):
            # The system should raise ConfigurationError when S3_BUCKET is missing
            with pytest.raises(ConfigurationError) as exc_info:
                AppConfig.from_env()
            
            # Verify the error message mentions S3_BUCKET
            error_message = str(exc_info.value)
            assert "S3_BUCKET" in error_message, (
                f"ConfigurationError should mention S3_BUCKET, got: {error_message}"
            )
    
    @given(
        jwt_secret=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=33, max_codepoint=126)),
        max_files=st.integers(min_value=1, max_value=100),
        batch_size=st.integers(min_value=1, max_value=100),
        max_file_size=st.integers(min_value=1, max_value=100000000)
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_1_s3_required_even_with_all_other_config(
        self, jwt_secret, max_files, batch_size, max_file_size
    ):
        """
        **Validates: Requirements 3.1**
        
        Property 1: S3 Configuration Required at Startup (variant)
        
        Even when all other configuration values are valid and present,
        the system should still raise ConfigurationError if S3_BUCKET is missing.
        
        This ensures S3_BUCKET is truly mandatory and not just checked when
        other config is missing.
        """
        from src.core.app_config import AppConfig, ConfigurationError
        
        # Set all valid configuration EXCEPT S3_BUCKET
        env_config = {
            "JWT_SECRET": jwt_secret,
            "MAX_CONCURRENT_FILES": str(max_files),
            "TRANSLATION_BATCH_SIZE": str(batch_size),
            "MAX_FILE_SIZE": str(max_file_size),
        }
        
        with isolated_env(env_config):
            # Should still raise ConfigurationError for missing S3_BUCKET
            with pytest.raises(ConfigurationError) as exc_info:
                AppConfig.from_env()
            
            error_message = str(exc_info.value)
            assert "S3_BUCKET" in error_message, (
                f"ConfigurationError should mention S3_BUCKET, got: {error_message}"
            )
    
    @given(
        s3_bucket=st.text(min_size=1, max_size=63, alphabet=st.characters(
            whitelist_categories=('Ll', 'Nd'),
            whitelist_characters='-'
        )),
        jwt_secret=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=33, max_codepoint=126))
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_1_inverse_s3_bucket_present_allows_startup(
        self, s3_bucket, jwt_secret
    ):
        """
        **Validates: Requirements 3.1, 3.2**
        
        Inverse property test: When S3_BUCKET IS present (along with JWT_SECRET),
        the system should NOT raise ConfigurationError for S3_BUCKET.
        
        This confirms the property works both ways:
        - Missing S3_BUCKET -> ConfigurationError
        - Present S3_BUCKET -> No ConfigurationError (for S3_BUCKET)
        """
        from src.core.app_config import AppConfig, ConfigurationError
        
        # Ensure bucket name is valid (not empty after filtering)
        assume(len(s3_bucket.strip()) > 0)
        assume(not s3_bucket.startswith('-'))
        
        # Set required configuration including S3_BUCKET
        env_config = {
            "JWT_SECRET": jwt_secret,
            "S3_BUCKET": s3_bucket,
        }
        
        with isolated_env(env_config):
            # Should NOT raise ConfigurationError - config should load successfully
            try:
                config = AppConfig.from_env()
                # Verify S3_BUCKET was loaded correctly
                assert config.s3_bucket == s3_bucket, (
                    f"s3_bucket should be '{s3_bucket}', got '{config.s3_bucket}'"
                )
            except ConfigurationError as e:
                # If there's an error, it should NOT be about S3_BUCKET
                error_message = str(e)
                assert "S3_BUCKET" not in error_message, (
                    f"With S3_BUCKET set, should not get S3_BUCKET error: {error_message}"
                )
                raise  # Re-raise if it's a different config error
