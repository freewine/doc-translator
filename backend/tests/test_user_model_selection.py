"""
Tests for user model selection in translation job creation.

Verifies that the resolve_create_translation_job resolver uses the user's
preferred model ID from their settings, with proper fallback to global default
when settings are missing or the model is no longer valid.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from pathlib import Path

from src.graphql.resolvers import (
    ResolverContext,
    resolve_create_translation_job,
)
from src.models.job import TranslationJob, JobStatus, LanguagePair
from src.models.config import UserSettings


@pytest.fixture
def mock_auth_service():
    service = Mock()
    service.get_username_from_token = Mock(return_value="testuser")
    return service


@pytest.fixture
def mock_job_manager():
    manager = Mock()
    mock_job = TranslationJob(
        status=JobStatus.PENDING,
        files_total=1,
        language_pair=LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi",
        ),
        file_ids=["file-1"],
    )
    manager.create_job = AsyncMock(return_value=mock_job)
    manager.job_store = Mock()
    manager.job_store.set_user_context = Mock()
    return manager


@pytest.fixture
def mock_s3_file_storage():
    storage = Mock()
    storage.get_upload = AsyncMock(
        return_value=(b"file content", {"original_filename": "test.xlsx"})
    )
    return storage


@pytest.fixture
def mock_language_pair_service():
    from src.models.config import LanguagePair as ConfigLanguagePair

    service = AsyncMock()
    mock_lp = ConfigLanguagePair(
        id="lp-uuid-123",
        user_id="__global__",
        source_language="zh",
        target_language="vi",
        display_name="Chinese→Vietnamese",
    )
    service.get_language_pair = AsyncMock(return_value=mock_lp)
    return service


@pytest.fixture
def mock_global_config_service():
    service = AsyncMock()
    service.is_model_valid = AsyncMock(return_value=True)
    service.get_default_model_id = AsyncMock(return_value="global.amazon.nova-2-lite-v1:0")
    return service


@pytest.fixture
def mock_user_settings_service():
    service = AsyncMock()
    return service


@pytest.fixture
def mock_translation_orchestrator():
    orchestrator = Mock()
    orchestrator.process_job = AsyncMock()
    orchestrator.excel_processor = Mock()
    orchestrator.executor = Mock()
    orchestrator.thesaurus_service = Mock()
    orchestrator.s3_file_storage = Mock()
    orchestrator.translation_service = Mock()
    orchestrator.translation_service.batch_size = 10
    return orchestrator


def _make_info(resolver_context):
    """Create a mock Strawberry Info object."""
    from strawberry.types import Info

    info = Mock(spec=Info)
    mock_request = Mock()
    mock_request.headers = {"Authorization": "Bearer mock-jwt-token"}
    info.context = {
        "request": mock_request,
        "resolver_context": resolver_context,
    }
    return info


# Patches applied to source modules since the resolver uses local imports
PATCH_ORCHESTRATOR = "src.services.translation_orchestrator.TranslationOrchestrator"
PATCH_TRANSLATION_SERVICE = "src.services.translation_service.TranslationService"


@pytest.mark.asyncio
async def test_job_uses_user_preferred_model(
    mock_auth_service,
    mock_job_manager,
    mock_s3_file_storage,
    mock_language_pair_service,
    mock_global_config_service,
    mock_user_settings_service,
    mock_translation_orchestrator,
):
    """A job created by a user with a custom default_model_id uses that model."""
    custom_model_id = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

    mock_user_settings_service.get_user_settings = AsyncMock(
        return_value=UserSettings(
            user_id="testuser",
            default_model_id=custom_model_id,
        )
    )
    mock_global_config_service.is_model_valid = AsyncMock(return_value=True)

    context = ResolverContext(
        auth_service=mock_auth_service,
        job_manager=mock_job_manager,
        s3_file_storage=mock_s3_file_storage,
        translation_orchestrator=mock_translation_orchestrator,
        language_pair_service=mock_language_pair_service,
        global_config_service=mock_global_config_service,
        user_settings_service=mock_user_settings_service,
    )
    info = _make_info(context)

    mock_ts_instance = Mock()
    mock_ts_instance.model_id = custom_model_id

    with patch(PATCH_ORCHESTRATOR) as MockOrchestrator, \
         patch(PATCH_TRANSLATION_SERVICE, return_value=mock_ts_instance) as MockTS, \
         patch("asyncio.create_task"):
        MockOrchestrator.return_value = Mock(process_job=AsyncMock())

        await resolve_create_translation_job(
            info=info,
            file_ids=["file-1"],
            language_pair_id="lp-uuid-123",
            auto_append=True,
            interleaved_mode=False,
        )

        # Verify TranslationService was constructed with the user's preferred model
        MockTS.assert_called_once_with(
            model_id=custom_model_id,
            batch_size=10,
        )

        # Verify the per-job service was passed to the orchestrator
        call_kwargs = MockOrchestrator.call_args[1]
        assert call_kwargs["translation_service"] is mock_ts_instance


@pytest.mark.asyncio
async def test_job_falls_back_to_default_when_no_settings(
    mock_auth_service,
    mock_job_manager,
    mock_s3_file_storage,
    mock_language_pair_service,
    mock_global_config_service,
    mock_user_settings_service,
    mock_translation_orchestrator,
):
    """A job created by a user with no settings falls back to the global default model."""
    default_model_id = "global.amazon.nova-2-lite-v1:0"

    # Simulate get_user_settings returning default settings (auto-initialized)
    mock_user_settings_service.get_user_settings = AsyncMock(
        return_value=UserSettings(
            user_id="testuser",
            default_model_id=default_model_id,
        )
    )
    mock_global_config_service.is_model_valid = AsyncMock(return_value=True)

    context = ResolverContext(
        auth_service=mock_auth_service,
        job_manager=mock_job_manager,
        s3_file_storage=mock_s3_file_storage,
        translation_orchestrator=mock_translation_orchestrator,
        language_pair_service=mock_language_pair_service,
        global_config_service=mock_global_config_service,
        user_settings_service=mock_user_settings_service,
    )
    info = _make_info(context)

    mock_ts_instance = Mock()
    mock_ts_instance.model_id = default_model_id

    with patch(PATCH_ORCHESTRATOR) as MockOrchestrator, \
         patch(PATCH_TRANSLATION_SERVICE, return_value=mock_ts_instance) as MockTS, \
         patch("asyncio.create_task"):
        MockOrchestrator.return_value = Mock(process_job=AsyncMock())

        await resolve_create_translation_job(
            info=info,
            file_ids=["file-1"],
            language_pair_id="lp-uuid-123",
            auto_append=True,
            interleaved_mode=False,
        )

        # The default model was still valid, so TranslationService is created with it
        MockTS.assert_called_once_with(
            model_id=default_model_id,
            batch_size=10,
        )


@pytest.mark.asyncio
async def test_job_falls_back_when_model_invalid(
    mock_auth_service,
    mock_job_manager,
    mock_s3_file_storage,
    mock_language_pair_service,
    mock_global_config_service,
    mock_user_settings_service,
    mock_translation_orchestrator,
):
    """A job created by a user with an invalid/removed model ID falls back to the global default."""
    invalid_model_id = "some.removed-model-v1:0"
    fallback_model_id = "global.amazon.nova-2-lite-v1:0"

    mock_user_settings_service.get_user_settings = AsyncMock(
        return_value=UserSettings(
            user_id="testuser",
            default_model_id=invalid_model_id,
        )
    )
    mock_global_config_service.is_model_valid = AsyncMock(return_value=False)
    mock_global_config_service.get_default_model_id = AsyncMock(
        return_value=fallback_model_id
    )

    context = ResolverContext(
        auth_service=mock_auth_service,
        job_manager=mock_job_manager,
        s3_file_storage=mock_s3_file_storage,
        translation_orchestrator=mock_translation_orchestrator,
        language_pair_service=mock_language_pair_service,
        global_config_service=mock_global_config_service,
        user_settings_service=mock_user_settings_service,
    )
    info = _make_info(context)

    mock_ts_instance = Mock()
    mock_ts_instance.model_id = fallback_model_id

    with patch(PATCH_ORCHESTRATOR) as MockOrchestrator, \
         patch(PATCH_TRANSLATION_SERVICE, return_value=mock_ts_instance) as MockTS, \
         patch("asyncio.create_task"):
        MockOrchestrator.return_value = Mock(process_job=AsyncMock())

        await resolve_create_translation_job(
            info=info,
            file_ids=["file-1"],
            language_pair_id="lp-uuid-123",
            auto_append=True,
            interleaved_mode=False,
        )

        # Verify TranslationService was created with the fallback model
        MockTS.assert_called_once_with(
            model_id=fallback_model_id,
            batch_size=10,
        )

        # Verify is_model_valid was called with the invalid model
        mock_global_config_service.is_model_valid.assert_called_with(invalid_model_id)
        # Verify get_default_model_id was called as fallback
        mock_global_config_service.get_default_model_id.assert_called_once()


@pytest.mark.asyncio
async def test_job_uses_shared_service_when_settings_service_unavailable(
    mock_auth_service,
    mock_job_manager,
    mock_s3_file_storage,
    mock_language_pair_service,
    mock_translation_orchestrator,
):
    """When user_settings_service is None, falls back to shared translation service."""
    context = ResolverContext(
        auth_service=mock_auth_service,
        job_manager=mock_job_manager,
        s3_file_storage=mock_s3_file_storage,
        translation_orchestrator=mock_translation_orchestrator,
        language_pair_service=mock_language_pair_service,
        user_settings_service=None,
        global_config_service=None,
    )
    info = _make_info(context)

    with patch(PATCH_ORCHESTRATOR) as MockOrchestrator, \
         patch(PATCH_TRANSLATION_SERVICE) as MockTS, \
         patch("asyncio.create_task"):
        MockOrchestrator.return_value = Mock(process_job=AsyncMock())

        await resolve_create_translation_job(
            info=info,
            file_ids=["file-1"],
            language_pair_id="lp-uuid-123",
            auto_append=True,
            interleaved_mode=False,
        )

        # TranslationService should NOT have been constructed (no per-job instance)
        MockTS.assert_not_called()

        # The shared translation_service from the orchestrator should be used
        call_kwargs = MockOrchestrator.call_args[1]
        assert (
            call_kwargs["translation_service"]
            is mock_translation_orchestrator.translation_service
        )
