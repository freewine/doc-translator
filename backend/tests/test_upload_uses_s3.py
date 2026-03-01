"""Property-based tests for upload endpoint S3 usage.

This module tests that the upload endpoint always uses S3 storage
for file uploads, as part of the local storage cleanup feature.

**Property 2: Upload Endpoint Uses S3 Storage**
**Validates: Requirements 4.1**
"""

import io
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from starlette.testclient import TestClient

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# Strategies for generating test data

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = [".xlsx", ".docx", ".pptx", ".pdf"]


@st.composite
def valid_filename_strategy(draw):
    """
    Generate valid filenames with allowed extensions.
    
    Filenames consist of:
    - A base name (alphanumeric + underscores, 1-50 chars)
    - An allowed extension
    """
    # Generate base name with safe characters
    base_name = draw(st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-'
        )
    ))
    # Ensure base name is not empty after filtering
    assume(len(base_name.strip()) > 0)
    assume(not base_name.startswith('-'))
    
    # Pick a random allowed extension
    extension = draw(st.sampled_from(ALLOWED_EXTENSIONS))
    
    return f"{base_name}{extension}"


@st.composite
def valid_file_content_strategy(draw):
    """
    Generate valid file content of various sizes.
    
    Sizes range from 1 byte to 10KB (to keep tests fast and avoid entropy issues).
    Content is random bytes.
    """
    # Generate file size (1 byte to 10KB - small enough for fast property tests)
    size = draw(st.integers(min_value=1, max_value=10 * 1024))
    
    # Generate random bytes
    content = draw(st.binary(min_size=size, max_size=size))
    
    return content


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
def valid_upload_request_strategy(draw):
    """
    Generate a complete valid upload request.
    
    Returns a dict with:
    - filename: Valid filename with allowed extension
    - content: File content bytes
    - username: Authenticated username
    """
    return {
        "filename": draw(valid_filename_strategy()),
        "content": draw(valid_file_content_strategy()),
        "username": draw(valid_username_strategy()),
    }


class TestUploadEndpointUsesS3:
    """Property-based tests for upload endpoint S3 usage."""
    
    @pytest.fixture
    def mock_app_context(self):
        """Create a mock app context with S3 storage."""
        import main
        
        # Create mock S3 file storage
        mock_s3_storage = AsyncMock()
        mock_s3_storage.upload_file = AsyncMock(return_value="test-user/uploads/test-id.xlsx")
        
        # Create mock auth service
        mock_auth_service = Mock()
        
        # Create mock app config
        mock_app_config = Mock()
        mock_app_config.allowed_extensions = ALLOWED_EXTENSIONS
        mock_app_config.max_file_size = 50 * 1024 * 1024  # 50MB
        mock_app_config.s3_bucket = "test-bucket"
        mock_app_config.jwt_secret = "test-secret"
        mock_app_config.max_concurrent_files = 5
        mock_app_config.translation_batch_size = 10
        
        # Create mock app context
        mock_context = Mock()
        mock_context.s3_file_storage = mock_s3_storage
        mock_context.auth_service = mock_auth_service
        mock_context.app_config = mock_app_config
        
        return mock_context
    
    @given(upload_request=valid_upload_request_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.data_too_large],
        deadline=None  # Disable deadline for async operations
    )
    def test_property_2_upload_endpoint_uses_s3_storage(self, upload_request, mock_app_context):
        """
        **Validates: Requirements 4.1**
        
        Property 2: Upload Endpoint Uses S3 Storage
        
        For any valid file upload request with proper authentication,
        the uploaded file content should be stored in S3 under the
        user's upload path ({user_id}/uploads/{file_id}.{ext}).
        
        This property ensures that:
        1. S3 upload_file is always called for valid uploads
        2. The correct user_id is passed to S3
        3. The file content is passed correctly
        4. The original filename is preserved in metadata
        """
        import main
        from main import app
        
        filename = upload_request["filename"]
        content = upload_request["content"]
        username = upload_request["username"]
        
        # Configure mock auth to return the username
        mock_app_context.auth_service.get_username_from_token = Mock(return_value=username)
        
        # Reset the mock to track calls
        mock_app_context.s3_file_storage.upload_file.reset_mock()
        
        # Set the global app_context
        original_context = main.app_context
        main.app_context = mock_app_context
        
        try:
            # Create test client
            client = TestClient(app, raise_server_exceptions=False)
            
            # Create file-like object for upload
            files = {
                "file": (filename, io.BytesIO(content), "application/octet-stream")
            }
            
            # Make upload request with auth header
            response = client.post(
                "/api/upload",
                files=files,
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Verify the response is successful
            assert response.status_code == 200, f"Upload failed: {response.json()}"
            
            # Verify S3 upload_file was called
            assert mock_app_context.s3_file_storage.upload_file.called, (
                "S3 upload_file should be called for valid uploads"
            )
            
            # Get the call arguments
            call_args = mock_app_context.s3_file_storage.upload_file.call_args
            
            # Verify user_id matches the authenticated user
            assert call_args.kwargs.get("user_id") == username, (
                f"S3 upload should use user_id '{username}', "
                f"got '{call_args.kwargs.get('user_id')}'"
            )
            
            # Verify file content was passed
            assert call_args.kwargs.get("file_content") == content, (
                "S3 upload should receive the exact file content"
            )
            
            # Verify original filename was passed
            assert call_args.kwargs.get("original_filename") == filename, (
                f"S3 upload should preserve original filename '{filename}', "
                f"got '{call_args.kwargs.get('original_filename')}'"
            )
            
            # Verify file_id was generated (UUID format)
            file_id = call_args.kwargs.get("file_id")
            assert file_id is not None, "S3 upload should receive a file_id"
            assert len(file_id) == 36, f"file_id should be UUID format, got '{file_id}'"
            
        finally:
            # Restore original context
            main.app_context = original_context
    
    @given(
        filename=valid_filename_strategy(),
        content=st.binary(min_size=1, max_size=10000),
        username=valid_username_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    def test_property_2_s3_key_structure(self, filename, content, username, mock_app_context):
        """
        **Validates: Requirements 4.1**
        
        Property 2: Upload Endpoint Uses S3 Storage (key structure variant)
        
        Verifies that the S3 key follows the expected structure:
        {user_id}/uploads/{file_id}.{ext}
        
        The file extension in the S3 key should match the original file extension.
        """
        import main
        from main import app
        
        # Configure mock auth
        mock_app_context.auth_service.get_username_from_token = Mock(return_value=username)
        mock_app_context.s3_file_storage.upload_file.reset_mock()
        
        # Set the global app_context
        original_context = main.app_context
        main.app_context = mock_app_context
        
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
            
            assert response.status_code == 200, f"Upload failed: {response.json()}"
            
            # Verify S3 was called
            assert mock_app_context.s3_file_storage.upload_file.called
            
            # The S3FileStorage.upload_file method constructs the key internally
            # We verify the parameters passed would result in correct key structure
            call_args = mock_app_context.s3_file_storage.upload_file.call_args
            
            passed_user_id = call_args.kwargs.get("user_id")
            passed_file_id = call_args.kwargs.get("file_id")
            passed_filename = call_args.kwargs.get("original_filename")
            
            # Verify user_id is the authenticated user
            assert passed_user_id == username
            
            # Verify file_id is a valid UUID
            import uuid
            try:
                uuid.UUID(passed_file_id)
            except ValueError:
                pytest.fail(f"file_id should be a valid UUID, got '{passed_file_id}'")
            
            # Verify original filename preserves extension
            original_ext = Path(filename).suffix.lower()
            passed_ext = Path(passed_filename).suffix.lower()
            assert original_ext == passed_ext, (
                f"Extension should be preserved: expected '{original_ext}', got '{passed_ext}'"
            )
            
        finally:
            main.app_context = original_context
    
    @given(upload_request=valid_upload_request_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.data_too_large],
        deadline=None
    )
    def test_property_2_response_contains_file_metadata(self, upload_request, mock_app_context):
        """
        **Validates: Requirements 4.1**
        
        Property 2: Upload Endpoint Uses S3 Storage (response variant)
        
        Verifies that successful uploads return proper metadata:
        - id: The generated file ID
        - filename: The original filename
        - size: The file size in bytes
        - documentType: The detected document type
        """
        import main
        from main import app
        
        filename = upload_request["filename"]
        content = upload_request["content"]
        username = upload_request["username"]
        
        mock_app_context.auth_service.get_username_from_token = Mock(return_value=username)
        mock_app_context.s3_file_storage.upload_file.reset_mock()
        
        original_context = main.app_context
        main.app_context = mock_app_context
        
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
            
            assert response.status_code == 200
            
            data = response.json()
            
            # Verify response contains required fields
            assert "id" in data, "Response should contain 'id'"
            assert "filename" in data, "Response should contain 'filename'"
            assert "size" in data, "Response should contain 'size'"
            assert "documentType" in data, "Response should contain 'documentType'"
            
            # Verify values are correct
            assert data["filename"] == filename
            assert data["size"] == len(content)
            
            # Verify document type matches extension
            ext = Path(filename).suffix.lower()
            expected_types = {
                ".xlsx": "excel",
                ".docx": "word",
                ".pptx": "powerpoint",
                ".pdf": "pdf"
            }
            assert data["documentType"] == expected_types.get(ext), (
                f"Document type for {ext} should be {expected_types.get(ext)}, "
                f"got {data['documentType']}"
            )
            
        finally:
            main.app_context = original_context
    
    @given(
        filename=valid_filename_strategy(),
        username=valid_username_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    def test_property_2_no_local_storage_fallback(self, filename, username, mock_app_context):
        """
        **Validates: Requirements 4.1, 4.2**
        
        Property 2: Upload Endpoint Uses S3 Storage (no fallback variant)
        
        Verifies that the upload endpoint does NOT use local file storage
        as a fallback. Only S3 storage should be used.
        
        This ensures the local storage cleanup is complete.
        """
        import main
        from main import app
        
        content = b"test content"
        
        mock_app_context.auth_service.get_username_from_token = Mock(return_value=username)
        mock_app_context.s3_file_storage.upload_file.reset_mock()
        
        # Ensure file_storage is None (local storage removed)
        mock_app_context.file_storage = None
        
        original_context = main.app_context
        main.app_context = mock_app_context
        
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
            
            # Upload should succeed using S3
            assert response.status_code == 200, f"Upload failed: {response.json()}"
            
            # S3 should be called
            assert mock_app_context.s3_file_storage.upload_file.called, (
                "S3 upload_file should be called even when file_storage is None"
            )
            
        finally:
            main.app_context = original_context


class TestUploadEndpointS3Errors:
    """Tests for S3 error handling in upload endpoint."""
    
    @pytest.fixture
    def mock_app_context_with_s3_error(self):
        """Create a mock app context where S3 upload fails."""
        import main
        
        # Create mock S3 file storage that raises an error
        mock_s3_storage = AsyncMock()
        mock_s3_storage.upload_file = AsyncMock(
            side_effect=Exception("S3 upload failed: Access Denied")
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
    
    @given(filename=valid_filename_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    def test_s3_upload_error_returns_500(self, filename, mock_app_context_with_s3_error):
        """
        **Validates: Requirements 4.3**
        
        When S3 upload fails, the endpoint should return HTTP 500
        with an appropriate error message.
        """
        import main
        from main import app
        
        content = b"test content"
        
        original_context = main.app_context
        main.app_context = mock_app_context_with_s3_error
        
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
            
            # Should return 500 for S3 errors
            assert response.status_code == 500, (
                f"S3 error should return 500, got {response.status_code}"
            )
            
            # Should have error message
            data = response.json()
            assert "error" in data
            assert "storage" in data["error"].lower() or "upload" in data["error"].lower(), (
                f"Error message should mention storage/upload issue: {data['error']}"
            )
            
        finally:
            main.app_context = original_context
