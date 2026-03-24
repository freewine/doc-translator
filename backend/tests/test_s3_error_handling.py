"""Property-based tests for S3 error handling.

This module tests that S3 operation failures result in appropriate error
responses rather than crashes or generic errors, as part of the local
storage cleanup feature.

**Property 6: S3 Errors Result in Appropriate Error Responses**
**Validates: Requirements 4.3, 5.3, 6.3**
"""

import io
import sys
import uuid
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from starlette.testclient import TestClient
from botocore.exceptions import ClientError

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# S3 error codes that can occur during operations
S3_ERROR_CODES = [
    "NoSuchKey",
    "NoSuchBucket",
    "AccessDenied",
    "InvalidAccessKeyId",
    "SignatureDoesNotMatch",
    "ExpiredToken",
    "InvalidBucketName",
    "BucketNotEmpty",
    "ServiceUnavailable",
    "InternalError",
    "SlowDown",
    "RequestTimeout",
    "RequestTimeTooSkewed",
]

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = [".xlsx", ".docx", ".pptx", ".pdf"]


def create_client_error(error_code: str, message: str = None) -> ClientError:
    """
    Create a botocore ClientError with the specified error code.
    
    Args:
        error_code: S3 error code (e.g., "NoSuchKey", "AccessDenied")
        message: Optional error message
        
    Returns:
        ClientError instance
    """
    if message is None:
        message = f"An error occurred ({error_code})"
    
    error_response = {
        "Error": {
            "Code": error_code,
            "Message": message,
        }
    }
    return ClientError(error_response, "S3Operation")


# Strategies for generating test data

@st.composite
def s3_error_code_strategy(draw):
    """
    Generate random S3 error codes.
    """
    return draw(st.sampled_from(S3_ERROR_CODES))


@st.composite
def s3_error_message_strategy(draw):
    """
    Generate random S3 error messages.
    """
    base_messages = [
        "The specified key does not exist",
        "Access Denied",
        "The specified bucket does not exist",
        "The request signature we calculated does not match",
        "The security token included in the request is expired",
        "Service is temporarily unavailable",
        "Internal server error",
        "Please reduce your request rate",
        "Request has expired",
    ]
    return draw(st.sampled_from(base_messages))


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
def valid_username_strategy(draw):
    """
    Generate valid usernames.
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
def valid_job_id_strategy(draw):
    """
    Generate valid job IDs.
    """
    job_id = draw(st.text(
        min_size=8,
        max_size=36,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_'
        )
    ))
    assume(len(job_id.strip()) >= 8)
    assume(not job_id.startswith('-'))
    assume(not job_id.startswith('_'))
    return job_id


@st.composite
def valid_file_content_strategy(draw):
    """
    Generate valid file content of various sizes.
    """
    size = draw(st.integers(min_value=10, max_value=1024))
    content = draw(st.binary(min_size=size, max_size=size))
    return content


class TestUploadEndpointS3ErrorHandling:
    """Property-based tests for S3 error handling in upload endpoint."""
    
    @pytest.fixture
    def mock_app_context_factory(self):
        """Factory to create mock app context with configurable S3 error."""
        def create_context(error_code: str, error_message: str = None):
            import main
            
            # Create mock S3 file storage that raises ClientError
            mock_s3_storage = AsyncMock()
            mock_s3_storage.upload_file = AsyncMock(
                side_effect=create_client_error(error_code, error_message)
            )
            
            mock_auth_service = Mock()
            mock_auth_service.get_username_from_token = Mock(return_value="testuser")
            
            mock_app_config = Mock()
            mock_app_config.allowed_extensions = ALLOWED_EXTENSIONS
            mock_app_config.max_file_size = 50 * 1024 * 1024
            mock_app_config.s3_bucket = "test-bucket"
            mock_app_config.jwt_secret = "test-secret"
            
            mock_context = Mock()
            mock_context.s3_file_storage = mock_s3_storage
            mock_context.auth_service = mock_auth_service
            mock_context.app_config = mock_app_config
            
            return mock_context
        
        return create_context
    
    @given(
        error_code=s3_error_code_strategy(),
        filename=valid_filename_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    def test_property_6_upload_s3_errors_return_appropriate_response(
        self, error_code, filename, mock_app_context_factory
    ):
        """
        **Validates: Requirements 4.3**
        
        Property 6: S3 Errors Result in Appropriate Error Responses
        
        For any S3 upload failure (ClientError with various codes),
        the upload endpoint should return an appropriate error response
        (HTTP 500) with a meaningful error message rather than crashing.
        
        This property ensures that:
        1. The system doesn't crash on S3 errors
        2. HTTP 500 is returned for upload failures
        3. Error message mentions storage/upload issue
        """
        import main
        from main import app
        
        content = b"test file content"
        mock_context = mock_app_context_factory(error_code)
        
        original_context = main.app_context
        main.app_context = mock_context
        
        try:
            client = TestClient(app, raise_server_exceptions=False)
            
            files = {
                "file": (filename, io.BytesIO(content), "application/octet-stream")
            }
            
            response = client.post(
                "/api/upload",
                files=files,
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should return 500 for S3 errors (not crash)
            assert response.status_code == 500, (
                f"S3 error '{error_code}' should return 500, got {response.status_code}"
            )
            
            # Should return JSON response
            data = response.json()
            assert "error" in data, (
                f"Response should contain 'error' field for S3 error '{error_code}'"
            )
            
            # Error message should mention storage/upload issue
            error_msg = data["error"].lower()
            assert "storage" in error_msg or "upload" in error_msg, (
                f"Error message should mention storage/upload issue for '{error_code}': {data['error']}"
            )
            
        finally:
            main.app_context = original_context
    
    @given(
        error_code=s3_error_code_strategy(),
        error_message=s3_error_message_strategy(),
        filename=valid_filename_strategy(),
        content=valid_file_content_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.data_too_large],
        deadline=None
    )
    def test_property_6_upload_s3_errors_do_not_crash(
        self, error_code, error_message, filename, content, mock_app_context_factory
    ):
        """
        **Validates: Requirements 4.3**
        
        Property 6: S3 Errors Result in Appropriate Error Responses (no crash variant)
        
        For any combination of S3 error code and message, the upload endpoint
        should handle the error gracefully without crashing.
        """
        import main
        from main import app
        
        mock_context = mock_app_context_factory(error_code, error_message)
        
        original_context = main.app_context
        main.app_context = mock_context
        
        try:
            client = TestClient(app, raise_server_exceptions=False)
            
            files = {
                "file": (filename, io.BytesIO(content), "application/octet-stream")
            }
            
            # This should NOT raise an exception
            response = client.post(
                "/api/upload",
                files=files,
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should return a valid HTTP response (not crash)
            assert response.status_code in [400, 401, 403, 404, 500], (
                f"Should return valid HTTP error code, got {response.status_code}"
            )
            
            # Should return valid JSON
            try:
                data = response.json()
                assert isinstance(data, dict), "Response should be a JSON object"
            except Exception as e:
                pytest.fail(f"Response should be valid JSON: {e}")
            
        finally:
            main.app_context = original_context


class TestDownloadEndpointS3ErrorHandling:
    """Property-based tests for S3 error handling in download endpoint."""
    
    @pytest.fixture
    def mock_app_context_factory(self):
        """Factory to create mock app context with configurable S3 error."""
        def create_context(error_code: str, error_message: str = None):
            import main
            
            # Create mock S3 file storage that raises ClientError
            mock_s3_storage = AsyncMock()
            mock_s3_storage.generate_download_url = AsyncMock(
                side_effect=create_client_error(error_code, error_message)
            )
            
            mock_auth_service = Mock()
            mock_auth_service.verify_token = Mock(
                return_value={"sub": "testuser", "username": "testuser"}
            )
            
            mock_app_config = Mock()
            mock_app_config.s3_bucket = "test-bucket"
            mock_app_config.jwt_secret = "test-secret"
            
            mock_context = Mock()
            mock_context.s3_file_storage = mock_s3_storage
            mock_context.auth_service = mock_auth_service
            mock_context.app_config = mock_app_config
            
            return mock_context
        
        return create_context
    
    @given(
        error_code=s3_error_code_strategy(),
        job_id=valid_job_id_strategy(),
        filename=valid_filename_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    def test_property_6_download_s3_errors_return_appropriate_response(
        self, error_code, job_id, filename, mock_app_context_factory
    ):
        """
        **Validates: Requirements 5.3**
        
        Property 6: S3 Errors Result in Appropriate Error Responses
        
        For any S3 download/presigned URL generation failure (ClientError with
        various codes), the download endpoint should return an appropriate error
        response (HTTP 404) with a meaningful error message rather than crashing.
        
        This property ensures that:
        1. The system doesn't crash on S3 errors
        2. HTTP 404 is returned for download failures
        3. Error message mentions file not found or access denied
        """
        import main
        from main import app
        
        mock_context = mock_app_context_factory(error_code)
        
        original_context = main.app_context
        main.app_context = mock_context
        
        try:
            client = TestClient(app, raise_server_exceptions=False)
            
            response = client.get(
                f"/api/download?job_id={job_id}&filename={filename}",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should return 404 for S3 errors (not crash)
            assert response.status_code == 404, (
                f"S3 error '{error_code}' should return 404, got {response.status_code}"
            )
            
            # Should return JSON response
            data = response.json()
            assert "error" in data, (
                f"Response should contain 'error' field for S3 error '{error_code}'"
            )
            
            # Error message should mention file not found or access denied
            error_msg = data["error"].lower()
            assert "not found" in error_msg or "access denied" in error_msg, (
                f"Error message should mention 'not found' or 'access denied' for '{error_code}': {data['error']}"
            )
            
        finally:
            main.app_context = original_context
    
    @given(
        error_code=s3_error_code_strategy(),
        error_message=s3_error_message_strategy(),
        job_id=valid_job_id_strategy(),
        filename=valid_filename_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    def test_property_6_download_s3_errors_do_not_crash(
        self, error_code, error_message, job_id, filename, mock_app_context_factory
    ):
        """
        **Validates: Requirements 5.3**
        
        Property 6: S3 Errors Result in Appropriate Error Responses (no crash variant)
        
        For any combination of S3 error code and message, the download endpoint
        should handle the error gracefully without crashing.
        """
        import main
        from main import app
        
        mock_context = mock_app_context_factory(error_code, error_message)
        
        original_context = main.app_context
        main.app_context = mock_context
        
        try:
            client = TestClient(app, raise_server_exceptions=False)
            
            # This should NOT raise an exception
            response = client.get(
                f"/api/download?job_id={job_id}&filename={filename}",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should return a valid HTTP response (not crash)
            assert response.status_code in [400, 401, 403, 404, 500], (
                f"Should return valid HTTP error code, got {response.status_code}"
            )
            
            # Should return valid JSON
            try:
                data = response.json()
                assert isinstance(data, dict), "Response should be a JSON object"
            except Exception as e:
                pytest.fail(f"Response should be valid JSON: {e}")
            
        finally:
            main.app_context = original_context


class TestJobCreationS3ErrorHandling:
    """Property-based tests for S3 error handling in job creation."""
    
    @given(
        error_code=s3_error_code_strategy(),
        username=valid_username_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None
    )
    def test_property_6_job_creation_s3_errors_return_validation_error(
        self, error_code, username
    ):
        """
        **Validates: Requirements 6.3**
        
        Property 6: S3 Errors Result in Appropriate Error Responses
        
        For any S3 file retrieval failure during job creation, the resolver
        should return a ValidationError with a meaningful error message
        rather than crashing.
        
        This property ensures that:
        1. The system doesn't crash on S3 errors during job creation
        2. ValidationError is raised with appropriate message
        3. Error message mentions file not found
        """
        from src.graphql.resolvers import resolve_create_translation_job, ResolverContext, ValidationError
        from src.models.job import TranslationJob, JobStatus
        
        file_id = str(uuid.uuid4())
        language_pair_id = "zh-vi"
        
        # Create mock S3 file storage that raises ClientError
        mock_s3_storage = AsyncMock()
        mock_s3_storage.get_upload = AsyncMock(
            side_effect=create_client_error(error_code)
        )
        
        # Create mock language pair service
        @dataclass
        class MockConfigLanguagePair:
            id: str
            source_language: str
            target_language: str
            display_name: str
        
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
                    # Should raise ValidationError, not crash
                    with pytest.raises(ValidationError) as exc_info:
                        loop.run_until_complete(
                            resolve_create_translation_job(
                                info=mock_info,
                                file_ids=[file_id],
                                language_pair_id=language_pair_id,
                            )
                        )
                    
                    # Verify error message mentions storage/retrieval failure
                    error_message = str(exc_info.value)
                    assert (
                        "not found" in error_message.lower() or 
                        "storage" in error_message.lower() or
                        "retrieve" in error_message.lower() or
                        file_id in error_message
                    ), (
                        f"ValidationError should mention storage/retrieval failure for '{error_code}': {error_message}"
                    )
                finally:
                    loop.close()


class TestOrchestratorS3ErrorHandling:
    """Property-based tests for S3 error handling in translation orchestrator."""
    
    @given(
        error_code=s3_error_code_strategy(),
        username=valid_username_strategy(),
        filename=valid_filename_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None
    )
    def test_property_6_orchestrator_s3_upload_errors_mark_file_failed(
        self, error_code, username, filename
    ):
        """
        **Validates: Requirements 6.3**
        
        Property 6: S3 Errors Result in Appropriate Error Responses
        
        For any S3 upload failure during translation processing, the orchestrator
        should mark the file as failed with "S3UploadError" error type rather
        than crashing.
        
        This property ensures that:
        1. The system doesn't crash on S3 upload errors
        2. File is marked as failed with S3UploadError error type
        3. Error message mentions S3 or upload failure
        """
        from src.models.job import TranslationJob, JobStatus, LanguagePair, DocumentType
        from src.services.translation_orchestrator import TranslationOrchestrator
        
        job_id = str(uuid.uuid4())
        
        # Create mock S3 file storage that fails on save_output
        mock_s3_storage = AsyncMock()
        mock_s3_storage.save_output = AsyncMock(
            side_effect=create_client_error(error_code)
        )
        
        # Create mock translation service
        mock_translation_service = Mock()
        mock_translation_service.batch_size = 10
        from src.services.translation_service import TranslationResult
        mock_translation_service.batch_translate_async = AsyncMock(
            side_effect=lambda texts, lp, tp: [TranslationResult(text="translated")] * len(texts)
        )
        
        # Create mock concurrent executor
        mock_executor = Mock()
        
        # Create mock excel processor (legacy)
        mock_excel_processor = Mock()
        
        # Create mock text segments
        @dataclass
        class MockTextSegment:
            text: str
            metadata: dict = None
            
            def __post_init__(self):
                if self.metadata is None:
                    self.metadata = {}
        
        segments = [MockTextSegment(text="test text")]
        
        # Determine document type from extension
        ext = Path(filename).suffix.lower()
        doc_type_map = {
            ".xlsx": DocumentType.EXCEL,
            ".docx": DocumentType.WORD,
            ".pptx": DocumentType.POWERPOINT,
            ".pdf": DocumentType.PDF,
        }
        document_type = doc_type_map.get(ext, DocumentType.EXCEL)
        
        # Create mock processor
        class MockDocumentProcessor:
            def __init__(self, doc_type, segs):
                self.document_type = doc_type
                self._segments = segs
            
            async def validate_file(self, file_path):
                return True, None
            
            async def extract_text(self, file_path):
                return self._segments
            
            def generate_output_filename(self, original_path, target_lang_code):
                return f"{original_path.stem}_{target_lang_code}{original_path.suffix}"
            
            async def write_translated(self, file_path, segments, translations, output_path, auto_append=False, interleaved_mode=False):
                output_path.write_bytes(b"translated content")
                return True
        
        mock_processor = MockDocumentProcessor(document_type, segments)
        
        # Create mock processor factory
        mock_factory = Mock()
        mock_factory.get_processor = Mock(return_value=mock_processor)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            orchestrator = TranslationOrchestrator(
                excel_processor=mock_excel_processor,
                translation_service=mock_translation_service,
                concurrent_executor=mock_executor,
                output_dir=output_dir,
                processor_factory=mock_factory,
                s3_file_storage=mock_s3_storage,
            )
            
            job = TranslationJob(id=job_id, status=JobStatus.PENDING, files_total=1)
            
            language_pair = LanguagePair(
                id="zh-vi",
                source_language="Chinese",
                target_language="Vietnamese",
                source_language_code="zh",
                target_language_code="vi",
            )
            
            input_file = output_dir / f"input_{uuid.uuid4()}{ext}"
            input_file.write_bytes(b"test content")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                file_result = loop.run_until_complete(
                    orchestrator.process_file(
                        file_path=input_file,
                        original_filename=filename,
                        language_pair=language_pair,
                        job=job,
                        user_id=username,
                    )
                )
            finally:
                loop.close()
            
            # Verify the result indicates failure (not crash)
            assert not file_result.success, (
                f"File processing should fail when S3 upload fails with '{error_code}'"
            )
            
            # Verify error type is S3UploadError
            assert file_result.error_type == "S3UploadError", (
                f"Error type should be 'S3UploadError' for '{error_code}', got '{file_result.error_type}'"
            )
            
            # Verify error message mentions S3 or upload
            assert "S3" in file_result.error or "upload" in file_result.error.lower(), (
                f"Error message should mention S3 or upload for '{error_code}': {file_result.error}"
            )
