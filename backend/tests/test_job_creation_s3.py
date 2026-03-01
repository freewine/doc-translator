"""Property-based tests for job creation S3 retrieval.

This module tests that the create_translation_job resolver retrieves
file content from S3 storage, as part of the local storage cleanup feature.

**Property 5: Job Creation Retrieves Files from S3**
**Validates: Requirements 7.2**
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from src.models.job import TranslationJob, JobStatus, LanguagePair


# Strategies for generating test data

ALLOWED_EXTENSIONS = [".xlsx", ".docx", ".pptx", ".pdf"]


def valid_file_id_strategy():
    """
    Generate valid file IDs (UUID format).
    
    File IDs are UUIDs generated during upload.
    """
    return st.builds(lambda: str(uuid.uuid4()))


@st.composite
def valid_username_strategy(draw):
    """
    Generate valid usernames.
    
    Usernames are alphanumeric with underscores, 3-30 chars.
    """
    username = draw(st.text(
        min_size=3,
        max_size=30,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_'
        )
    ))
    assume(len(username.strip()) >= 3)
    return username


@st.composite
def valid_filename_strategy(draw):
    """
    Generate valid filenames with allowed extensions.
    """
    base_name = draw(st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        )
    ))
    assume(len(base_name.strip()) > 0)
    assume(not base_name.startswith('-'))
    
    extension = draw(st.sampled_from(ALLOWED_EXTENSIONS))
    return f"{base_name}{extension}"


@st.composite
def valid_language_pair_id_strategy(draw):
    """
    Generate valid language pair IDs.
    """
    lp_id = draw(st.text(
        min_size=3,
        max_size=36,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_'
        )
    ))
    assume(len(lp_id.strip()) >= 3)
    return lp_id


@st.composite
def valid_file_content_strategy(draw):
    """
    Generate valid file content of various sizes.
    """
    size = draw(st.integers(min_value=10, max_value=1024))
    content = draw(st.binary(min_size=size, max_size=size))
    return content


@st.composite
def valid_job_creation_request_strategy(draw):
    """
    Generate a complete valid job creation request.
    
    Returns a dict with:
    - file_ids: List of file IDs to translate
    - language_pair_id: ID of language pair to use
    - username: Authenticated username
    - file_contents: Dict mapping file_id to (content, metadata)
    """
    # Generate 1-3 file IDs
    num_files = draw(st.integers(min_value=1, max_value=3))
    file_ids = [str(uuid.uuid4()) for _ in range(num_files)]
    
    # Generate file contents and metadata for each file
    file_contents = {}
    for file_id in file_ids:
        content = draw(valid_file_content_strategy())
        filename = draw(valid_filename_strategy())
        metadata = {
            "original_filename": filename,
            "content_type": "application/octet-stream",
            "document_type": "excel",
            "size_bytes": len(content),
        }
        file_contents[file_id] = (content, metadata)
    
    return {
        "file_ids": file_ids,
        "language_pair_id": draw(valid_language_pair_id_strategy()),
        "username": draw(valid_username_strategy()),
        "file_contents": file_contents,
    }


# Mock classes for testing

@dataclass
class MockConfigLanguagePair:
    """Mock config language pair for testing (from language_pair_service)."""
    id: str
    source_language: str
    target_language: str
    display_name: str


class TestJobCreationS3Retrieval:
    """Property-based tests for job creation S3 retrieval."""
    
    @given(request=valid_job_creation_request_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None
    )
    def test_property_5_job_creation_retrieves_files_from_s3(self, request):
        """
        **Validates: Requirements 7.2**
        
        Property 5: Job Creation Retrieves Files from S3
        
        For any translation job creation request, the file content should be
        retrieved from S3 storage using the user's upload path, not from
        local filesystem.
        
        This property ensures that:
        1. S3 get_upload is called for each file_id
        2. The correct user_id is passed to S3
        3. File content is retrieved from S3, not local storage
        """
        import asyncio
        from src.graphql.resolvers import resolve_create_translation_job, ResolverContext
        
        file_ids = request["file_ids"]
        language_pair_id = request["language_pair_id"]
        username = request["username"]
        file_contents = request["file_contents"]
        
        # Create mock S3 file storage
        mock_s3_storage = AsyncMock()
        
        # Configure get_upload to return file content for each file_id
        async def mock_get_upload(user_id, file_id):
            if file_id in file_contents:
                return file_contents[file_id]
            return None
        
        mock_s3_storage.get_upload = AsyncMock(side_effect=mock_get_upload)
        
        # Create mock language pair service
        mock_lp_service = AsyncMock()
        mock_lp = MockConfigLanguagePair(
            id=language_pair_id,
            source_language="zh",
            target_language="vi",
            display_name="中文→越南语"
        )
        mock_lp_service.get_language_pair = AsyncMock(return_value=mock_lp)
        
        # Create mock job manager
        mock_job_manager = Mock()
        mock_job_store = Mock()
        mock_job_store.set_user_context = Mock()
        mock_job_manager.job_store = mock_job_store
        
        # Create a real TranslationJob with proper JobStatus enum
        mock_job = TranslationJob(
            id="test-job-id",
            status=JobStatus.PENDING,
            files_total=len(file_ids),
        )
        mock_job_manager.create_job = AsyncMock(return_value=mock_job)
        
        # Create mock translation orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.excel_processor = Mock()
        mock_orchestrator.translation_service = Mock()
        mock_orchestrator.executor = Mock()
        mock_orchestrator.thesaurus_service = None
        mock_orchestrator.s3_file_storage = mock_s3_storage
        
        # Create mock auth service
        mock_auth_service = Mock()
        
        # Create resolver context
        context = ResolverContext(
            auth_service=mock_auth_service,
            job_manager=mock_job_manager,
            s3_file_storage=mock_s3_storage,
            translation_orchestrator=mock_orchestrator,
            language_pair_service=mock_lp_service,
        )
        
        # Create mock info object
        mock_info = Mock()
        mock_info.context = {
            "resolver_context": context,
            "request": Mock(headers={"Authorization": "Bearer test-token"})
        }
        
        # Patch require_auth to return the username
        with patch('src.graphql.resolvers.require_auth', return_value=username):
            # Patch asyncio.create_task to prevent background task execution
            with patch('asyncio.create_task'):
                # Run the resolver
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        resolve_create_translation_job(
                            info=mock_info,
                            file_ids=file_ids,
                            language_pair_id=language_pair_id,
                        )
                    )
                finally:
                    loop.close()
        
        # Verify S3 get_upload was called for each file_id
        assert mock_s3_storage.get_upload.call_count == len(file_ids), (
            f"S3 get_upload should be called {len(file_ids)} times, "
            f"got {mock_s3_storage.get_upload.call_count}"
        )
        
        # Verify each call used the correct user_id and file_id
        for call in mock_s3_storage.get_upload.call_args_list:
            call_user_id = call[0][0]  # First positional arg
            call_file_id = call[0][1]  # Second positional arg
            
            assert call_user_id == username, (
                f"S3 get_upload should use user_id '{username}', got '{call_user_id}'"
            )
            assert call_file_id in file_ids, (
                f"S3 get_upload should be called with file_id in {file_ids}, got '{call_file_id}'"
            )
    
    @given(
        file_id=valid_file_id_strategy(),
        username=valid_username_strategy(),
        language_pair_id=valid_language_pair_id_strategy(),
        filename=valid_filename_strategy(),
        content=valid_file_content_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None
    )
    def test_property_5_s3_retrieval_uses_user_path(
        self, file_id, username, language_pair_id, filename, content
    ):
        """
        **Validates: Requirements 7.2**
        
        Property 5: Job Creation Retrieves Files from S3 (user path variant)
        
        Verifies that S3 get_upload is called with the authenticated user's ID,
        ensuring user isolation for file retrieval.
        """
        import asyncio
        from src.graphql.resolvers import resolve_create_translation_job, ResolverContext
        
        # Create mock S3 file storage
        mock_s3_storage = AsyncMock()
        metadata = {
            "original_filename": filename,
            "content_type": "application/octet-stream",
            "document_type": "excel",
            "size_bytes": len(content),
        }
        mock_s3_storage.get_upload = AsyncMock(return_value=(content, metadata))
        
        # Create mock language pair service
        mock_lp_service = AsyncMock()
        mock_lp = MockConfigLanguagePair(
            id=language_pair_id,
            source_language="zh",
            target_language="vi",
            display_name="中文→越南语"
        )
        mock_lp_service.get_language_pair = AsyncMock(return_value=mock_lp)
        
        # Create mock job manager
        mock_job_manager = Mock()
        mock_job_store = Mock()
        mock_job_store.set_user_context = Mock()
        mock_job_manager.job_store = mock_job_store
        
        # Create a real TranslationJob
        mock_job = TranslationJob(id="test-job-id", files_total=1)
        mock_job_manager.create_job = AsyncMock(return_value=mock_job)
        
        # Create mock translation orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.excel_processor = Mock()
        mock_orchestrator.translation_service = Mock()
        mock_orchestrator.executor = Mock()
        mock_orchestrator.thesaurus_service = None
        mock_orchestrator.s3_file_storage = mock_s3_storage
        
        # Create resolver context
        context = ResolverContext(
            auth_service=Mock(),
            job_manager=mock_job_manager,
            s3_file_storage=mock_s3_storage,
            translation_orchestrator=mock_orchestrator,
            language_pair_service=mock_lp_service,
        )
        
        # Create mock info object
        mock_info = Mock()
        mock_info.context = {
            "resolver_context": context,
            "request": Mock(headers={"Authorization": "Bearer test-token"})
        }
        
        # Patch require_auth to return the username
        with patch('src.graphql.resolvers.require_auth', return_value=username):
            with patch('asyncio.create_task'):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        resolve_create_translation_job(
                            info=mock_info,
                            file_ids=[file_id],
                            language_pair_id=language_pair_id,
                        )
                    )
                finally:
                    loop.close()
        
        # Verify S3 get_upload was called with correct user_id
        mock_s3_storage.get_upload.assert_called_once()
        call_args = mock_s3_storage.get_upload.call_args
        
        assert call_args[0][0] == username, (
            f"S3 get_upload should use authenticated user '{username}', "
            f"got '{call_args[0][0]}'"
        )
        assert call_args[0][1] == file_id, (
            f"S3 get_upload should use file_id '{file_id}', "
            f"got '{call_args[0][1]}'"
        )
    
    @given(
        file_id=valid_file_id_strategy(),
        username=valid_username_strategy(),
        language_pair_id=valid_language_pair_id_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None
    )
    def test_property_5_file_not_found_raises_validation_error(
        self, file_id, username, language_pair_id
    ):
        """
        **Validates: Requirements 7.2**
        
        Property 5: Job Creation Retrieves Files from S3 (error handling variant)
        
        When S3 get_upload returns None (file not found), the resolver should
        raise a ValidationError with an appropriate message.
        """
        import asyncio
        from src.graphql.resolvers import resolve_create_translation_job, ResolverContext, ValidationError
        
        # Create mock S3 file storage that returns None (file not found)
        mock_s3_storage = AsyncMock()
        mock_s3_storage.get_upload = AsyncMock(return_value=None)
        
        # Create mock language pair service
        mock_lp_service = AsyncMock()
        mock_lp = MockConfigLanguagePair(
            id=language_pair_id,
            source_language="zh",
            target_language="vi",
            display_name="中文→越南语"
        )
        mock_lp_service.get_language_pair = AsyncMock(return_value=mock_lp)
        
        # Create mock job manager
        mock_job_manager = Mock()
        mock_job_store = Mock()
        mock_job_store.set_user_context = Mock()
        mock_job_manager.job_store = mock_job_store
        
        # Create mock translation orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.excel_processor = Mock()
        mock_orchestrator.translation_service = Mock()
        mock_orchestrator.executor = Mock()
        mock_orchestrator.thesaurus_service = None
        mock_orchestrator.s3_file_storage = mock_s3_storage
        
        # Create resolver context
        context = ResolverContext(
            auth_service=Mock(),
            job_manager=mock_job_manager,
            s3_file_storage=mock_s3_storage,
            translation_orchestrator=mock_orchestrator,
            language_pair_service=mock_lp_service,
        )
        
        # Create mock info object
        mock_info = Mock()
        mock_info.context = {
            "resolver_context": context,
            "request": Mock(headers={"Authorization": "Bearer test-token"})
        }
        
        # Patch require_auth to return the username
        with patch('src.graphql.resolvers.require_auth', return_value=username):
            with patch('asyncio.create_task'):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    with pytest.raises(ValidationError) as exc_info:
                        loop.run_until_complete(
                            resolve_create_translation_job(
                                info=mock_info,
                                file_ids=[file_id],
                                language_pair_id=language_pair_id,
                            )
                        )
                    
                    # Verify error message mentions file not found
                    error_message = str(exc_info.value)
                    assert "not found" in error_message.lower() or file_id in error_message, (
                        f"ValidationError should mention file not found or file_id, got: {error_message}"
                    )
                finally:
                    loop.close()
    
    @given(request=valid_job_creation_request_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None
    )
    def test_property_5_no_local_filesystem_access(self, request):
        """
        **Validates: Requirements 7.2**
        
        Property 5: Job Creation Retrieves Files from S3 (no local access variant)
        
        Verifies that job creation does NOT access local filesystem for file
        retrieval. Only S3 storage should be used.
        
        This ensures the local storage cleanup is complete.
        """
        import asyncio
        from src.graphql.resolvers import resolve_create_translation_job, ResolverContext
        
        file_ids = request["file_ids"]
        language_pair_id = request["language_pair_id"]
        username = request["username"]
        file_contents = request["file_contents"]
        
        # Create mock S3 file storage
        mock_s3_storage = AsyncMock()
        
        async def mock_get_upload(user_id, file_id):
            if file_id in file_contents:
                return file_contents[file_id]
            return None
        
        mock_s3_storage.get_upload = AsyncMock(side_effect=mock_get_upload)
        
        # Create mock language pair service
        mock_lp_service = AsyncMock()
        mock_lp = MockConfigLanguagePair(
            id=language_pair_id,
            source_language="zh",
            target_language="vi",
            display_name="中文→越南语"
        )
        mock_lp_service.get_language_pair = AsyncMock(return_value=mock_lp)
        
        # Create mock job manager
        mock_job_manager = Mock()
        mock_job_store = Mock()
        mock_job_store.set_user_context = Mock()
        mock_job_manager.job_store = mock_job_store
        
        # Create a real TranslationJob
        mock_job = TranslationJob(id="test-job-id", files_total=len(file_ids))
        mock_job_manager.create_job = AsyncMock(return_value=mock_job)
        
        # Create mock translation orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.excel_processor = Mock()
        mock_orchestrator.translation_service = Mock()
        mock_orchestrator.executor = Mock()
        mock_orchestrator.thesaurus_service = None
        mock_orchestrator.s3_file_storage = mock_s3_storage
        
        # Create resolver context WITHOUT file_storage (local storage removed)
        context = ResolverContext(
            auth_service=Mock(),
            job_manager=mock_job_manager,
            s3_file_storage=mock_s3_storage,
            translation_orchestrator=mock_orchestrator,
            language_pair_service=mock_lp_service,
        )
        
        # Verify context does not have file_storage attribute
        assert not hasattr(context, 'file_storage') or context.file_storage is None, (
            "ResolverContext should not have file_storage attribute (local storage removed)"
        )
        
        # Create mock info object
        mock_info = Mock()
        mock_info.context = {
            "resolver_context": context,
            "request": Mock(headers={"Authorization": "Bearer test-token"})
        }
        
        # Patch require_auth to return the username
        with patch('src.graphql.resolvers.require_auth', return_value=username):
            with patch('asyncio.create_task'):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        resolve_create_translation_job(
                            info=mock_info,
                            file_ids=file_ids,
                            language_pair_id=language_pair_id,
                        )
                    )
                finally:
                    loop.close()
        
        # Verify S3 was used (not local storage)
        assert mock_s3_storage.get_upload.called, (
            "S3 get_upload should be called for file retrieval"
        )
        
        # Verify job was created successfully
        assert result is not None, "Job should be created successfully using S3 storage"
