"""
Tests for config GraphQL resolvers.

Tests cover:
- Language pair queries and mutations
- User settings queries and mutations
- Available models query
- Authentication requirements
- Admin-only access for language pair mutations
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.graphql.config_resolvers import (
    ConfigLanguagePair,
    ConfigUserSettings,
    ConfigModelInfo,
    convert_language_pair,
    convert_user_settings,
    convert_model_config,
    resolve_config_language_pairs,
    resolve_config_user_settings,
    resolve_available_models,
    resolve_create_config_language_pair,
    resolve_update_config_language_pair,
    resolve_delete_config_language_pair,
    resolve_update_config_user_settings,
    resolve_reset_config_user_settings,
)
from src.graphql.decorators import PermissionError as AuthPermissionError
from src.models.config import (
    LanguagePair,
    UserSettings,
    ModelConfig,
)
from src.models.user import User as UserModel, UserRole, UserStatus


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_language_pair():
    """Create a sample LanguagePair for testing."""
    return LanguagePair(
        id="lp-123",
        user_id="testuser",
        source_language="zh",
        target_language="vi",
        display_name="Chinese→Vietnamese",
        is_enabled=True,
        created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_user_settings():
    """Create sample UserSettings for testing."""
    return UserSettings(
        user_id="testuser",
        default_model_id="global.amazon.nova-2-lite-v1:0",
        ui_language="zh",
        translation_batch_size=10,
        max_concurrent_tasks=3,
        created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_model_config():
    """Create a sample ModelConfig for testing."""
    return ModelConfig(
        model_id="global.amazon.nova-2-lite-v1:0",
        display_name="Nova 2 Lite",
        provider="amazon",
        is_default=True,
    )


@pytest.fixture
def mock_info():
    """Create a mock Strawberry Info object."""
    info = MagicMock()
    info.context = {}
    return info


@pytest.fixture
def mock_resolver_context():
    """Create a mock ResolverContext with config services."""
    context = MagicMock()
    context.language_pair_service = AsyncMock()
    context.user_settings_service = AsyncMock()
    context.global_config_service = AsyncMock()
    return context


@pytest.fixture
def mock_auth_service():
    """Create a mock AuthService."""
    auth_service = MagicMock()
    auth_service.get_username_from_token.return_value = "testuser"
    return auth_service


@pytest.fixture
def admin_user():
    """Create an admin user for testing."""
    return UserModel(
        username="testuser",
        password_hash="hashed",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )


@pytest.fixture
def regular_user():
    """Create a regular user for testing."""
    return UserModel(
        username="regularuser",
        password_hash="hashed",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )


# =============================================================================
# Conversion Function Tests
# =============================================================================

class TestConversionFunctions:
    """Tests for type conversion functions."""
    
    def test_convert_language_pair(self, sample_language_pair):
        """Test converting domain LanguagePair to GraphQL type."""
        result = convert_language_pair(sample_language_pair)
        
        assert isinstance(result, ConfigLanguagePair)
        assert result.id == "lp-123"
        assert result.user_id == "testuser"
        assert result.source_language == "zh"
        assert result.target_language == "vi"
        assert result.display_name == "Chinese→Vietnamese"
        assert result.is_enabled is True
        assert "2025-01-01" in result.created_at
    
    def test_convert_user_settings(self, sample_user_settings):
        """Test converting domain UserSettings to GraphQL type."""
        result = convert_user_settings(sample_user_settings)
        
        assert isinstance(result, ConfigUserSettings)
        assert result.user_id == "testuser"
        assert result.default_model_id == "global.amazon.nova-2-lite-v1:0"
        assert result.ui_language == "zh"
        assert result.translation_batch_size == 10
        assert result.max_concurrent_tasks == 3
    
    def test_convert_model_config(self, sample_model_config):
        """Test converting domain ModelConfig to GraphQL type."""
        result = convert_model_config(sample_model_config)
        
        assert isinstance(result, ConfigModelInfo)
        assert result.model_id == "global.amazon.nova-2-lite-v1:0"
        assert result.display_name == "Nova 2 Lite"
        assert result.provider == "amazon"
        assert result.is_default is True


# =============================================================================
# Query Resolver Tests
# =============================================================================

class TestQueryResolvers:
    """Tests for query resolvers."""
    
    @pytest.mark.asyncio
    async def test_resolve_config_language_pairs_success(
        self, mock_info, mock_resolver_context, mock_auth_service, sample_language_pair
    ):
        """Test successful language pairs query."""
        # Setup
        mock_resolver_context.auth_service = mock_auth_service
        mock_resolver_context.language_pair_service.get_language_pairs.return_value = [
            sample_language_pair
        ]
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"})
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            result = await resolve_config_language_pairs(mock_info, include_disabled=False)
        
        assert len(result) == 1
        assert result[0].id == "lp-123"
        mock_resolver_context.language_pair_service.get_language_pairs.assert_called_once_with(
            "__global__", False
        )
    
    @pytest.mark.asyncio
    async def test_resolve_config_language_pairs_empty(
        self, mock_info, mock_resolver_context, mock_auth_service
    ):
        """Test language pairs query with no service available."""
        mock_resolver_context.language_pair_service = None
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"})
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            result = await resolve_config_language_pairs(mock_info)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_resolve_config_user_settings_success(
        self, mock_info, mock_resolver_context, mock_auth_service, sample_user_settings
    ):
        """Test successful user settings query."""
        mock_resolver_context.auth_service = mock_auth_service
        mock_resolver_context.user_settings_service.get_user_settings.return_value = sample_user_settings
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"})
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            result = await resolve_config_user_settings(mock_info)
        
        assert result.user_id == "testuser"
        assert result.default_model_id == "global.amazon.nova-2-lite-v1:0"
    
    @pytest.mark.asyncio
    async def test_resolve_available_models_success(
        self, mock_info, mock_resolver_context, mock_auth_service, sample_model_config
    ):
        """Test successful available models query."""
        mock_resolver_context.auth_service = mock_auth_service
        mock_resolver_context.global_config_service.get_available_models.return_value = [
            sample_model_config
        ]
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"})
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            result = await resolve_available_models(mock_info)
        
        assert len(result) == 1
        assert result[0].model_id == "global.amazon.nova-2-lite-v1:0"
        assert result[0].display_name == "Nova 2 Lite"


# =============================================================================
# Mutation Resolver Tests
# =============================================================================

class TestMutationResolvers:
    """Tests for mutation resolvers."""
    
    @pytest.mark.asyncio
    async def test_resolve_create_config_language_pair_success(
        self, mock_info, mock_resolver_context, mock_auth_service, sample_language_pair, admin_user
    ):
        """Test successful language pair creation by admin."""
        mock_resolver_context.auth_service = mock_auth_service
        mock_resolver_context.language_pair_service.create_language_pair.return_value = sample_language_pair
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"}),
            "current_user": admin_user,
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            result = await resolve_create_config_language_pair(
                mock_info,
                source_language="zh",
                target_language="vi",
                display_name="Chinese→Vietnamese",
                is_enabled=True
            )
        
        assert result.id == "lp-123"
        assert result.source_language == "zh"
        mock_resolver_context.language_pair_service.create_language_pair.assert_called_once_with(
            user_id="__global__",
            source_language="zh",
            target_language="vi",
            display_name="Chinese→Vietnamese",
            is_enabled=True,
        )
    
    @pytest.mark.asyncio
    async def test_resolve_create_config_language_pair_validation_error(
        self, mock_info, mock_resolver_context, mock_auth_service, admin_user
    ):
        """Test language pair creation with validation error."""
        mock_resolver_context.auth_service = mock_auth_service
        mock_resolver_context.language_pair_service.create_language_pair.side_effect = ValueError(
            "Source and target languages cannot be the same"
        )
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"}),
            "current_user": admin_user,
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            with pytest.raises(Exception) as exc_info:
                await resolve_create_config_language_pair(
                    mock_info,
                    source_language="zh",
                    target_language="zh",
                    display_name="Invalid",
                    is_enabled=True
                )
        
        assert "Source and target languages cannot be the same" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_resolve_update_config_language_pair_success(
        self, mock_info, mock_resolver_context, mock_auth_service, sample_language_pair, admin_user
    ):
        """Test successful language pair update by admin."""
        updated_pair = LanguagePair(
            id="lp-123",
            user_id="__global__",
            source_language="zh",
            target_language="vi",
            display_name="Updated Name",
            is_enabled=True,
            created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        )
        mock_resolver_context.auth_service = mock_auth_service
        mock_resolver_context.language_pair_service.update_language_pair.return_value = updated_pair
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"}),
            "current_user": admin_user,
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            result = await resolve_update_config_language_pair(
                mock_info,
                language_pair_id="lp-123",
                display_name="Updated Name"
            )
        
        assert result.display_name == "Updated Name"
        mock_resolver_context.language_pair_service.update_language_pair.assert_called_once_with(
            user_id="__global__",
            language_pair_id="lp-123",
            display_name="Updated Name",
            is_enabled=None,
        )
    
    @pytest.mark.asyncio
    async def test_resolve_update_config_language_pair_not_found(
        self, mock_info, mock_resolver_context, mock_auth_service, admin_user
    ):
        """Test language pair update when not found."""
        mock_resolver_context.auth_service = mock_auth_service
        mock_resolver_context.language_pair_service.update_language_pair.return_value = None
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"}),
            "current_user": admin_user,
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            result = await resolve_update_config_language_pair(
                mock_info,
                language_pair_id="nonexistent",
                display_name="Updated Name"
            )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_resolve_delete_config_language_pair_success(
        self, mock_info, mock_resolver_context, mock_auth_service, admin_user
    ):
        """Test successful language pair deletion by admin."""
        mock_resolver_context.auth_service = mock_auth_service
        mock_resolver_context.language_pair_service.delete_language_pair.return_value = True
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"}),
            "current_user": admin_user,
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            result = await resolve_delete_config_language_pair(mock_info, "lp-123")
        
        assert result is True
        mock_resolver_context.language_pair_service.delete_language_pair.assert_called_once_with(
            "__global__", "lp-123"
        )
    
    @pytest.mark.asyncio
    async def test_resolve_update_config_user_settings_success(
        self, mock_info, mock_resolver_context, mock_auth_service, sample_user_settings
    ):
        """Test successful user settings update."""
        updated_settings = UserSettings(
            user_id="testuser",
            default_model_id="global.amazon.nova-2-lite-v1:0",
            ui_language="en",
            translation_batch_size=20,
            max_concurrent_tasks=5,
            created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        )
        mock_resolver_context.auth_service = mock_auth_service
        mock_resolver_context.user_settings_service.update_user_settings.return_value = updated_settings
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"})
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            result = await resolve_update_config_user_settings(
                mock_info,
                default_model_id="global.amazon.nova-2-lite-v1:0",
                ui_language="en",
                translation_batch_size=20,
                max_concurrent_tasks=5
            )
        
        assert result.default_model_id == "global.amazon.nova-2-lite-v1:0"
        assert result.ui_language == "en"
        assert result.translation_batch_size == 20
    
    @pytest.mark.asyncio
    async def test_resolve_update_config_user_settings_validation_error(
        self, mock_info, mock_resolver_context, mock_auth_service
    ):
        """Test user settings update with validation error."""
        mock_resolver_context.auth_service = mock_auth_service
        mock_resolver_context.user_settings_service.update_user_settings.side_effect = ValueError(
            "Invalid model ID: invalid-model"
        )
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"})
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            with pytest.raises(Exception) as exc_info:
                await resolve_update_config_user_settings(
                    mock_info,
                    default_model_id="invalid-model"
                )
        
        assert "Invalid model ID" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_resolve_reset_config_user_settings_success(
        self, mock_info, mock_resolver_context, mock_auth_service, sample_user_settings
    ):
        """Test successful user settings reset."""
        mock_resolver_context.auth_service = mock_auth_service
        mock_resolver_context.user_settings_service.reset_user_settings.return_value = sample_user_settings
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"})
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="testuser"):
            result = await resolve_reset_config_user_settings(mock_info)
        
        assert result.user_id == "testuser"
        assert result.default_model_id == "global.amazon.nova-2-lite-v1:0"
        mock_resolver_context.user_settings_service.reset_user_settings.assert_called_once_with(
            "testuser"
        )


# =============================================================================
# Admin Permission Tests
# =============================================================================

class TestAdminPermissions:
    """Tests for admin-only access to language pair mutations."""
    
    @pytest.mark.asyncio
    async def test_regular_user_rejected_from_create_language_pair(
        self, mock_info, mock_resolver_context, mock_auth_service, regular_user
    ):
        """Test that regular user is rejected from creating language pairs."""
        mock_resolver_context.auth_service = mock_auth_service
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"}),
            "current_user": regular_user,
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="regularuser"):
            with pytest.raises(AuthPermissionError, match="Admin access required"):
                await resolve_create_config_language_pair(
                    mock_info,
                    source_language="zh",
                    target_language="vi",
                    display_name="Chinese→Vietnamese",
                    is_enabled=True
                )
    
    @pytest.mark.asyncio
    async def test_regular_user_rejected_from_update_language_pair(
        self, mock_info, mock_resolver_context, mock_auth_service, regular_user
    ):
        """Test that regular user is rejected from updating language pairs."""
        mock_resolver_context.auth_service = mock_auth_service
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"}),
            "current_user": regular_user,
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="regularuser"):
            with pytest.raises(AuthPermissionError, match="Admin access required"):
                await resolve_update_config_language_pair(
                    mock_info,
                    language_pair_id="lp-123",
                    display_name="Updated Name"
                )
    
    @pytest.mark.asyncio
    async def test_regular_user_rejected_from_delete_language_pair(
        self, mock_info, mock_resolver_context, mock_auth_service, regular_user
    ):
        """Test that regular user is rejected from deleting language pairs."""
        mock_resolver_context.auth_service = mock_auth_service
        mock_info.context = {
            "resolver_context": mock_resolver_context,
            "request": MagicMock(headers={"Authorization": "Bearer valid_token"}),
            "current_user": regular_user,
        }
        
        with patch('src.graphql.config_resolvers.require_auth', return_value="regularuser"):
            with pytest.raises(AuthPermissionError, match="Admin access required"):
                await resolve_delete_config_language_pair(mock_info, "lp-123")


# =============================================================================
# Authentication Tests
# =============================================================================

class TestAuthentication:
    """Tests for authentication requirements."""
    
    @pytest.mark.asyncio
    async def test_query_requires_authentication(self, mock_info):
        """Test that queries require authentication."""
        mock_info.context = {"resolver_context": None}
        
        from src.graphql.resolvers import AuthenticationError
        
        with pytest.raises(AuthenticationError):
            await resolve_config_language_pairs(mock_info)
    
    @pytest.mark.asyncio
    async def test_mutation_requires_authentication(self, mock_info):
        """Test that mutations require authentication."""
        mock_info.context = {"resolver_context": None}
        
        from src.graphql.resolvers import AuthenticationError
        
        with pytest.raises(AuthenticationError):
            await resolve_create_config_language_pair(
                mock_info, "zh", "vi", "Test", True
            )
