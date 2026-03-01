"""
Tests for GraphQL resolvers.

This module tests the resolver implementations for queries and mutations.
"""
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from strawberry.types import Info

from src.graphql.resolvers import (
    ResolverContext,
    AuthenticationError,
    ValidationError,
    resolve_me,
    resolve_job,
    resolve_jobs,
    resolve_job_history,
    resolve_language_pairs,
    resolve_login,
    resolve_logout,
    resolve_add_language_pair,
    resolve_remove_language_pair,
    require_auth,
    get_auth_token,
)
from src.models.job import LanguagePair
from src.models.job import TranslationJob, JobStatus


@pytest.fixture
def mock_auth_service():
    """Create a mock authentication service."""
    from src.services.auth_service import AuthResult
    service = Mock()
    service.authenticate = Mock(return_value="mock-jwt-token")
    service.get_username_from_token = Mock(return_value="testuser")
    # Mock authenticate_user for DynamoDB-based auth
    service.authenticate_user = AsyncMock(return_value=AuthResult(
        success=True,
        token="mock-jwt-token"
    ))
    return service


@pytest.fixture
def mock_language_pair_service():
    """Create a mock language pair service."""
    from src.models.config import LanguagePair as ConfigLanguagePair
    from datetime import datetime, timezone
    service = AsyncMock()

    # Create mock config.LanguagePair (different from job.LanguagePair)
    mock_lp = ConfigLanguagePair(
        id="lp-uuid-123",
        user_id="testuser",
        source_language="zh",
        target_language="vi",
        display_name="Chinese→Vietnamese",
    )

    service.get_language_pairs = AsyncMock(return_value=[mock_lp])
    service.get_language_pair = AsyncMock(return_value=mock_lp)
    service.create_language_pair = AsyncMock(return_value=ConfigLanguagePair(
        id="lp-uuid-456",
        user_id="testuser",
        source_language="ja",
        target_language="en",
        display_name="Japanese→English",
    ))
    service.delete_language_pair = AsyncMock()
    return service


@pytest.fixture
def mock_global_config_service():
    """Create a mock global config service."""
    from src.models.config import ModelConfig
    service = AsyncMock()
    service.get_available_models = AsyncMock(return_value=[
        ModelConfig(
            model_id="global.amazon.nova-2-lite-v1:0",
            display_name="Nova 2 Lite",
            provider="amazon",
            is_default=True,
        )
    ])
    service.get_default_model_id = AsyncMock(return_value="global.amazon.nova-2-lite-v1:0")
    service.is_model_valid = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_user_settings_service():
    """Create a mock user settings service."""
    service = AsyncMock()
    service.update_settings = AsyncMock()
    return service


@pytest.fixture
def mock_job_manager():
    """Create a mock job manager."""
    manager = Mock()
    
    # Create a mock job
    mock_job = TranslationJob(
        status=JobStatus.PENDING,
        files_total=1,
        language_pair=LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        ),
        file_ids=["file-1"]
    )
    
    manager.get_job = AsyncMock(return_value=mock_job)
    manager.list_jobs = AsyncMock(return_value=[mock_job])
    manager.create_job = AsyncMock(return_value=mock_job)
    return manager


@pytest.fixture
def mock_s3_file_storage():
    """Create a mock S3 file storage."""
    storage = Mock()
    storage.get_file_path = Mock(return_value=Path("/tmp/test.xlsx"))
    storage.save_uploaded_file = AsyncMock(return_value=("file-id-123", "file-id-123.xlsx"))
    storage.upload_file = AsyncMock(return_value="testuser/uploads/file-id-123.xlsx")
    storage.get_upload = AsyncMock(return_value=(b"file content", {"original_filename": "test.xlsx"}))
    return storage


@pytest.fixture
def mock_translation_orchestrator():
    """Create a mock translation orchestrator."""
    orchestrator = Mock()
    orchestrator.process_job = AsyncMock()
    return orchestrator


@pytest.fixture
def resolver_context(
    mock_auth_service,
    mock_language_pair_service,
    mock_global_config_service,
    mock_user_settings_service,
    mock_job_manager,
    mock_s3_file_storage,
    mock_translation_orchestrator
):
    """Create a resolver context with mocked services."""
    return ResolverContext(
        auth_service=mock_auth_service,
        job_manager=mock_job_manager,
        s3_file_storage=mock_s3_file_storage,
        translation_orchestrator=mock_translation_orchestrator,
        language_pair_service=mock_language_pair_service,
        global_config_service=mock_global_config_service,
        user_settings_service=mock_user_settings_service,
    )


@pytest.fixture
def mock_info(resolver_context):
    """Create a mock Strawberry Info object."""
    info = Mock(spec=Info)
    
    # Mock request with Authorization header
    mock_request = Mock()
    mock_request.headers = {"Authorization": "Bearer mock-jwt-token"}
    
    info.context = {
        "request": mock_request,
        "resolver_context": resolver_context
    }
    return info


@pytest.fixture
def mock_info_no_auth(resolver_context):
    """Create a mock Info object without authentication."""
    info = Mock(spec=Info)
    
    # Mock request without Authorization header
    mock_request = Mock()
    mock_request.headers = {}
    
    info.context = {
        "request": mock_request,
        "resolver_context": resolver_context
    }
    return info


# Test helper functions

def test_get_auth_token_with_bearer(mock_info):
    """Test extracting token from Bearer authorization header."""
    token = get_auth_token(mock_info)
    assert token == "mock-jwt-token"


def test_get_auth_token_without_bearer(mock_info_no_auth):
    """Test extracting token when no authorization header present."""
    token = get_auth_token(mock_info_no_auth)
    assert token is None


def test_require_auth_success(mock_info):
    """Test require_auth with valid token."""
    username = require_auth(mock_info)
    assert username == "testuser"


def test_require_auth_no_token(mock_info_no_auth):
    """Test require_auth without token raises AuthenticationError."""
    with pytest.raises(AuthenticationError, match="Authentication required"):
        require_auth(mock_info_no_auth)


def test_require_auth_invalid_token(mock_info, mock_auth_service):
    """Test require_auth with invalid token raises AuthenticationError."""
    mock_auth_service.get_username_from_token.return_value = None
    
    with pytest.raises(AuthenticationError, match="Invalid or expired token"):
        require_auth(mock_info)


# Test query resolvers

@pytest.mark.asyncio
async def test_resolve_me(mock_info):
    """Test resolve_me returns authenticated user."""
    user = await resolve_me(mock_info)
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_resolve_me_with_user_service(mock_info, mock_auth_service):
    """Test resolve_me returns full user data including role when user_service is available."""
    from src.models.user import User as UserModel, UserRole

    # Create mock user with admin role
    mock_user = UserModel(
        username="testuser",
        password_hash="hashed",
        role=UserRole.ADMIN,
        must_change_password=True
    )

    # Create mock user_service
    mock_user_service = AsyncMock()
    mock_user_service.get_user = AsyncMock(return_value=mock_user)

    # Add user_service to context
    mock_info.context["user_service"] = mock_user_service

    user = await resolve_me(mock_info)

    assert user.username == "testuser"
    assert user.role == "admin"
    assert user.mustChangePassword is True
    mock_user_service.get_user.assert_called_once_with("testuser")


@pytest.mark.asyncio
async def test_resolve_me_no_auth(mock_info_no_auth):
    """Test resolve_me without authentication raises error."""
    with pytest.raises(AuthenticationError):
        await resolve_me(mock_info_no_auth)


@pytest.mark.asyncio
async def test_resolve_job(mock_info, mock_job_manager):
    """Test resolve_job returns job by ID."""
    job = await resolve_job(mock_info, "job-123")
    
    assert job is not None
    assert job.id is not None
    assert job.status is not None
    mock_job_manager.get_job.assert_called_once_with("job-123")


@pytest.mark.asyncio
async def test_resolve_job_not_found(mock_info, mock_job_manager):
    """Test resolve_job returns None when job not found."""
    mock_job_manager.get_job.return_value = None
    
    job = await resolve_job(mock_info, "nonexistent")
    assert job is None


@pytest.mark.asyncio
async def test_resolve_jobs(mock_info, mock_job_manager):
    """Test resolve_jobs returns list of jobs."""
    jobs = await resolve_jobs(mock_info)

    assert isinstance(jobs, list)
    assert len(jobs) == 1
    mock_job_manager.list_jobs.assert_called_once()


# Test job_history resolver

@pytest.mark.asyncio
async def test_resolve_job_history_basic(mock_info, mock_job_manager):
    """Test resolve_job_history returns paginated results."""
    # Setup mock job_store on job_manager
    mock_job_store = Mock()
    mock_job = TranslationJob(
        status=JobStatus.COMPLETED,
        files_total=1,
        language_pair=LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        ),
        file_ids=["file-1"]
    )
    mock_job_store.list_jobs = AsyncMock(return_value=([mock_job], None))
    mock_job_store.set_user_context = Mock()
    mock_job_manager.job_store = mock_job_store

    result = await resolve_job_history(mock_info)

    assert result.jobs is not None
    assert len(result.jobs) == 1
    assert result.next_cursor is None
    assert result.has_more is False
    mock_job_store.set_user_context.assert_called_once_with("testuser")


@pytest.mark.asyncio
async def test_resolve_job_history_with_pagination(mock_info, mock_job_manager):
    """Test resolve_job_history with pagination cursor."""
    mock_job_store = Mock()
    mock_job = TranslationJob(
        status=JobStatus.COMPLETED,
        files_total=1,
        language_pair=LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        ),
        file_ids=["file-1"]
    )
    mock_job_store.list_jobs = AsyncMock(return_value=([mock_job], "next-cursor-token"))
    mock_job_store.set_user_context = Mock()
    mock_job_manager.job_store = mock_job_store

    result = await resolve_job_history(mock_info, limit=10, cursor="prev-cursor")

    assert result.next_cursor == "next-cursor-token"
    assert result.has_more is True
    mock_job_store.list_jobs.assert_called_once()
    call_kwargs = mock_job_store.list_jobs.call_args[1]
    assert call_kwargs["limit"] == 10
    assert call_kwargs["cursor"] == "prev-cursor"


@pytest.mark.asyncio
async def test_resolve_job_history_clamps_limit(mock_info, mock_job_manager):
    """Test resolve_job_history clamps limit to valid range."""
    mock_job_store = Mock()
    mock_job_store.list_jobs = AsyncMock(return_value=([], None))
    mock_job_store.set_user_context = Mock()
    mock_job_manager.job_store = mock_job_store

    # Test limit too high (should clamp to 100)
    await resolve_job_history(mock_info, limit=200)
    call_kwargs = mock_job_store.list_jobs.call_args[1]
    assert call_kwargs["limit"] == 100

    # Test limit too low (should clamp to 1)
    await resolve_job_history(mock_info, limit=-5)
    call_kwargs = mock_job_store.list_jobs.call_args[1]
    assert call_kwargs["limit"] == 1


@pytest.mark.asyncio
async def test_resolve_job_history_with_status_filter(mock_info, mock_job_manager):
    """Test resolve_job_history with status filter."""
    from src.graphql.schema import JobStatus as GQLJobStatus

    mock_job_store = Mock()
    mock_job_store.list_jobs = AsyncMock(return_value=([], None))
    mock_job_store.set_user_context = Mock()
    mock_job_manager.job_store = mock_job_store

    await resolve_job_history(mock_info, status=GQLJobStatus.COMPLETED)

    call_kwargs = mock_job_store.list_jobs.call_args[1]
    assert call_kwargs["status_filter"] == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_resolve_job_history_with_date_filters(mock_info, mock_job_manager):
    """Test resolve_job_history with date range filters."""
    mock_job_store = Mock()
    mock_job_store.list_jobs = AsyncMock(return_value=([], None))
    mock_job_store.set_user_context = Mock()
    mock_job_manager.job_store = mock_job_store

    await resolve_job_history(
        mock_info,
        date_from="2024-01-01T00:00:00Z",
        date_to="2024-12-31T23:59:59Z"
    )

    call_kwargs = mock_job_store.list_jobs.call_args[1]
    assert call_kwargs["date_from"] is not None
    assert call_kwargs["date_to"] is not None
    assert call_kwargs["date_from"].year == 2024
    assert call_kwargs["date_from"].month == 1
    assert call_kwargs["date_to"].year == 2024
    assert call_kwargs["date_to"].month == 12


@pytest.mark.asyncio
async def test_resolve_job_history_invalid_date_ignored(mock_info, mock_job_manager):
    """Test resolve_job_history ignores invalid date formats."""
    mock_job_store = Mock()
    mock_job_store.list_jobs = AsyncMock(return_value=([], None))
    mock_job_store.set_user_context = Mock()
    mock_job_manager.job_store = mock_job_store

    # Should not raise error, just ignore invalid dates
    await resolve_job_history(
        mock_info,
        date_from="not-a-date",
        date_to="also-not-a-date"
    )

    call_kwargs = mock_job_store.list_jobs.call_args[1]
    assert call_kwargs["date_from"] is None
    assert call_kwargs["date_to"] is None


@pytest.mark.asyncio
async def test_resolve_job_history_no_auth(mock_info_no_auth):
    """Test resolve_job_history requires authentication."""
    with pytest.raises(AuthenticationError):
        await resolve_job_history(mock_info_no_auth)


@pytest.mark.asyncio
async def test_resolve_language_pairs(mock_info, mock_language_pair_service):
    """Test resolve_language_pairs returns configured pairs."""
    pairs = await resolve_language_pairs(mock_info)

    assert isinstance(pairs, list)
    assert len(pairs) == 1
    assert pairs[0].id == "lp-uuid-123"
    mock_language_pair_service.get_language_pairs.assert_called_once_with("__global__")


# Test mutation resolvers

@pytest.mark.asyncio
async def test_resolve_login_success(mock_info, mock_auth_service):
    """Test resolve_login with valid credentials."""
    payload = await resolve_login("admin", "password", mock_info)

    assert payload.token == "mock-jwt-token"
    assert payload.user.username == "admin"
    mock_auth_service.authenticate_user.assert_called_once_with("admin", "password")


@pytest.mark.asyncio
async def test_resolve_login_invalid_credentials(mock_info, mock_auth_service):
    """Test resolve_login with invalid credentials raises error."""
    from src.services.auth_service import AuthResult
    mock_auth_service.authenticate_user.return_value = AuthResult(
        success=False,
        error="Invalid username or password"
    )

    with pytest.raises(AuthenticationError, match="Invalid username or password"):
        await resolve_login("admin", "wrong", mock_info)


@pytest.mark.asyncio
async def test_resolve_logout(mock_info):
    """Test resolve_logout returns True when authenticated."""
    result = await resolve_logout(mock_info)
    assert result is True


@pytest.mark.asyncio
async def test_resolve_logout_no_auth(mock_info_no_auth):
    """Test resolve_logout without authentication raises error."""
    with pytest.raises(AuthenticationError):
        await resolve_logout(mock_info_no_auth)


@pytest.fixture
def mock_admin_info(mock_info):
    """Create a mock Info object with an admin user in context for admin-only resolvers."""
    from src.models.user import User as UserModel, UserRole
    admin_user = UserModel(
        username="testuser",
        password_hash="hashed",
        role=UserRole.ADMIN,
    )
    mock_info.context["current_user"] = admin_user
    return mock_info


@pytest.fixture
def mock_regular_user_info(mock_info):
    """Create a mock Info object with a regular user in context."""
    from src.models.user import User as UserModel, UserRole
    regular_user = UserModel(
        username="testuser",
        password_hash="hashed",
        role=UserRole.USER,
    )
    mock_info.context["current_user"] = regular_user
    return mock_info


@pytest.mark.asyncio
async def test_resolve_add_language_pair(mock_admin_info, mock_language_pair_service):
    """Test resolve_add_language_pair creates new pair for admin user."""
    pair = await resolve_add_language_pair(
        mock_admin_info,
        "Japanese",
        "English",
        "ja",
        "en"
    )

    assert pair.id == "lp-uuid-456"
    assert pair.source_language_code == "ja"
    assert pair.target_language_code == "en"
    mock_language_pair_service.create_language_pair.assert_called_once_with(
        user_id="__global__",
        source_language="ja",
        target_language="en",
        display_name="Japanese→English"
    )


@pytest.mark.asyncio
async def test_resolve_add_language_pair_duplicate(mock_admin_info, mock_language_pair_service):
    """Test resolve_add_language_pair with duplicate raises error."""
    mock_language_pair_service.create_language_pair.side_effect = ValueError("Already exists")

    with pytest.raises(ValidationError, match="Already exists"):
        await resolve_add_language_pair(
            mock_admin_info,
            "Chinese",
            "Vietnamese",
            "zh",
            "vi"
        )


@pytest.mark.asyncio
async def test_resolve_add_language_pair_regular_user_rejected(mock_regular_user_info):
    """Test resolve_add_language_pair rejects non-admin users."""
    from src.graphql.decorators import PermissionError as AuthPermissionError
    with pytest.raises(AuthPermissionError, match="Admin access required"):
        await resolve_add_language_pair(
            mock_regular_user_info,
            "Japanese",
            "English",
            "ja",
            "en"
        )


@pytest.mark.asyncio
async def test_resolve_remove_language_pair(mock_admin_info, mock_language_pair_service):
    """Test resolve_remove_language_pair removes pair for admin user."""
    result = await resolve_remove_language_pair(mock_admin_info, "lp-uuid-123")

    assert result is True
    mock_language_pair_service.delete_language_pair.assert_called_once_with("__global__", "lp-uuid-123")


@pytest.mark.asyncio
async def test_resolve_remove_language_pair_not_found(mock_admin_info, mock_language_pair_service):
    """Test resolve_remove_language_pair with nonexistent pair raises error."""
    mock_language_pair_service.delete_language_pair.side_effect = ValueError("Language pair not found")

    with pytest.raises(ValidationError, match="Language pair not found"):
        await resolve_remove_language_pair(mock_admin_info, "nonexistent")


@pytest.mark.asyncio
async def test_resolve_remove_language_pair_regular_user_rejected(mock_regular_user_info):
    """Test resolve_remove_language_pair rejects non-admin users."""
    from src.graphql.decorators import PermissionError as AuthPermissionError
    with pytest.raises(AuthPermissionError, match="Admin access required"):
        await resolve_remove_language_pair(mock_regular_user_info, "lp-uuid-123")


# Test error handling

@pytest.mark.asyncio
async def test_authentication_required_for_protected_resolvers(mock_info_no_auth):
    """Test that protected resolvers require authentication."""
    with pytest.raises(AuthenticationError):
        await resolve_me(mock_info_no_auth)
    
    with pytest.raises(AuthenticationError):
        await resolve_job(mock_info_no_auth, "job-123")
    
    with pytest.raises(AuthenticationError):
        await resolve_jobs(mock_info_no_auth)
    
    with pytest.raises(AuthenticationError):
        await resolve_language_pairs(mock_info_no_auth)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
