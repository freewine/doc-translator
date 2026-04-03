"""Property-based tests for download endpoint file streaming.

This module tests that the download endpoint streams file content
directly from S3 through the backend.

**Property 3: Download Endpoint Streams File Content**
**Validates: Requirements 5.1**
"""

import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from starlette.testclient import TestClient

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# Strategies for generating test data

@st.composite
def valid_job_id_strategy(draw):
    """
    Generate valid job IDs.

    Job IDs are UUIDs or alphanumeric strings.
    """
    # Generate UUID-like strings or simple alphanumeric IDs
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
def valid_filename_strategy(draw):
    """
    Generate valid output filenames with _vi suffix.

    Filenames consist of:
    - A base name (alphanumeric + underscores, 1-30 chars)
    - The _vi suffix (indicating Vietnamese translation)
    - An allowed extension
    """
    # Allowed extensions for translated files
    allowed_extensions = [".xlsx", ".docx", ".pptx", ".pdf"]

    # Generate base name with safe characters
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

    # Pick a random allowed extension
    extension = draw(st.sampled_from(allowed_extensions))

    # Add _vi suffix for translated files
    return f"{base_name}_vi{extension}"


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
def valid_download_request_strategy(draw):
    """
    Generate a complete valid download request.

    Returns a dict with:
    - job_id: Valid job ID
    - filename: Valid output filename with _vi suffix
    - username: Authenticated username
    """
    return {
        "job_id": draw(valid_job_id_strategy()),
        "filename": draw(valid_filename_strategy()),
        "username": draw(valid_username_strategy()),
    }


class TestDownloadEndpointFileStreaming:
    """Property-based tests for download endpoint file streaming."""

    @pytest.fixture
    def mock_app_context(self):
        """Create a mock app context with S3 storage."""
        import main

        # Create mock S3 file storage
        mock_s3_storage = AsyncMock()
        def make_stream_result(data=b"test file content"):
            async def gen():
                yield data
            return (len(data), gen())

        mock_s3_storage.stream_output = AsyncMock(
            side_effect=lambda **kwargs: make_stream_result()
        )

        # Create mock auth service
        mock_auth_service = Mock()

        # Create mock app config
        mock_app_config = Mock()
        mock_app_config.s3_bucket = "test-bucket"
        mock_app_config.jwt_secret = "test-secret"

        # Create mock app context
        mock_context = Mock()
        mock_context.s3_file_storage = mock_s3_storage
        mock_context.auth_service = mock_auth_service
        mock_context.app_config = mock_app_config

        return mock_context

    @given(download_request=valid_download_request_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None  # Disable deadline for async operations
    )
    def test_property_3_download_streams_file_content(self, download_request, mock_app_context):
        """
        **Validates: Requirements 5.1**

        Property 3: Download Endpoint Streams File Content

        For any valid file download request with proper authentication,
        the endpoint should stream the file content directly.
        """
        import main
        from main import app

        job_id = download_request["job_id"]
        filename = download_request["filename"]
        username = download_request["username"]

        # Configure mock auth to return valid user
        mock_app_context.auth_service.verify_token = Mock(
            return_value={"sub": username, "username": username}
        )

        # Reset the mock to track calls
        mock_app_context.s3_file_storage.stream_output.reset_mock()

        # Set the global app_context
        original_context = main.app_context
        main.app_context = mock_app_context

        try:
            # Create test client
            client = TestClient(app, raise_server_exceptions=False)

            # Make download request with auth header
            response = client.get(
                f"/api/download?job_id={job_id}&filename={filename}",
                headers={"Authorization": "Bearer test-token"}
            )

            # Verify the response is successful
            assert response.status_code == 200, f"Download failed: {response.text}"

            # Verify response contains file content
            assert response.content == b"test file content"
            assert "attachment" in response.headers.get("content-disposition", "")

        finally:
            # Restore original context
            main.app_context = original_context

    @given(download_request=valid_download_request_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    def test_property_3_s3_called_with_correct_args(self, download_request, mock_app_context):
        """
        **Validates: Requirements 5.1**

        Property 3: Download Endpoint Streams File Content (S3 args variant)

        Verifies that S3 get_output is called with the correct
        user_id, job_id, and filename arguments.
        """
        import main
        from main import app

        job_id = download_request["job_id"]
        filename = download_request["filename"]
        username = download_request["username"]

        # Configure mock auth
        mock_app_context.auth_service.verify_token = Mock(
            return_value={"sub": username, "username": username}
        )
        mock_app_context.s3_file_storage.stream_output.reset_mock()

        original_context = main.app_context
        main.app_context = mock_app_context

        try:
            client = TestClient(app, raise_server_exceptions=False)

            response = client.get(
                f"/api/download?job_id={job_id}&filename={filename}",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200, f"Download failed: {response.text}"

            # Verify S3 get_output was called
            assert mock_app_context.s3_file_storage.stream_output.called, (
                "S3 get_output should be called for downloads"
            )

            # Get the call arguments
            call_args = mock_app_context.s3_file_storage.stream_output.call_args

            # Verify correct arguments
            assert call_args.kwargs.get("user_id") == username, (
                f"user_id should be '{username}', got '{call_args.kwargs.get('user_id')}'"
            )
            assert call_args.kwargs.get("job_id") == job_id, (
                f"job_id should be '{job_id}', got '{call_args.kwargs.get('job_id')}'"
            )
            assert call_args.kwargs.get("filename") == filename, (
                f"filename should be '{filename}', got '{call_args.kwargs.get('filename')}'"
            )

        finally:
            main.app_context = original_context

    @given(download_request=valid_download_request_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    def test_property_3_response_has_content_disposition(self, download_request, mock_app_context):
        """
        **Validates: Requirements 5.1, 5.2**

        Property 3: Download Endpoint Streams File Content (format variant)

        Verifies that the download endpoint returns a streaming response
        with Content-Disposition header for browser download.
        """
        import main
        from main import app

        job_id = download_request["job_id"]
        filename = download_request["filename"]
        username = download_request["username"]

        mock_app_context.auth_service.verify_token = Mock(
            return_value={"sub": username, "username": username}
        )
        mock_app_context.s3_file_storage.stream_output.reset_mock()

        original_context = main.app_context
        main.app_context = mock_app_context

        try:
            client = TestClient(app, raise_server_exceptions=False)

            response = client.get(
                f"/api/download?job_id={job_id}&filename={filename}",
                headers={"Authorization": "Bearer test-token"}
            )

            # Should return 200
            assert response.status_code == 200, f"Download failed: {response.text}"

            # Response should have Content-Disposition attachment header
            content_disposition = response.headers.get("content-disposition", "")
            assert "attachment" in content_disposition
            # Content type should not be JSON (we're streaming file content now)
            content_type = response.headers.get("content-type", "")
            assert "application/json" not in content_type

        finally:
            main.app_context = original_context

    @given(
        job_id=valid_job_id_strategy(),
        filename=valid_filename_strategy(),
        username=valid_username_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    def test_property_3_uses_username_from_token(self, job_id, filename, username, mock_app_context):
        """
        **Validates: Requirements 5.1**

        Property 3: Download Endpoint Streams File Content (auth variant)

        Verifies that the download endpoint uses the username from the
        JWT token to fetch the file, ensuring user isolation.
        """
        import main
        from main import app

        # Configure mock auth to return specific username
        mock_app_context.auth_service.verify_token = Mock(
            return_value={"sub": username, "username": username}
        )
        mock_app_context.s3_file_storage.stream_output.reset_mock()

        original_context = main.app_context
        main.app_context = mock_app_context

        try:
            client = TestClient(app, raise_server_exceptions=False)

            response = client.get(
                f"/api/download?job_id={job_id}&filename={filename}",
                headers={"Authorization": "Bearer test-token"}
            )

            assert response.status_code == 200

            # Verify get_output was called with the username from the token
            call_args = mock_app_context.s3_file_storage.stream_output.call_args
            assert call_args.kwargs.get("user_id") == username, (
                f"user_id should be '{username}', got '{call_args.kwargs.get('user_id')}'"
            )

        finally:
            main.app_context = original_context


class TestDownloadEndpointS3Errors:
    """Tests for S3 error handling in download endpoint."""

    @pytest.fixture
    def mock_app_context_with_s3_error(self):
        """Create a mock app context where S3 get_output fails."""
        import main

        # Create mock S3 file storage that raises an error
        mock_s3_storage = AsyncMock()
        mock_s3_storage.stream_output = AsyncMock(
            side_effect=Exception("NoSuchKey: The specified key does not exist")
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

    @given(
        job_id=valid_job_id_strategy(),
        filename=valid_filename_strategy()
    )
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None
    )
    def test_s3_download_error_returns_404(self, job_id, filename, mock_app_context_with_s3_error):
        """
        **Validates: Requirements 5.3**

        When S3 get_output fails, the endpoint should return
        HTTP 404 with an appropriate error message.
        """
        import main
        from main import app

        original_context = main.app_context
        main.app_context = mock_app_context_with_s3_error

        try:
            client = TestClient(app, raise_server_exceptions=False)

            response = client.get(
                f"/api/download?job_id={job_id}&filename={filename}",
                headers={"Authorization": "Bearer test-token"}
            )

            # Should return 404 for S3 errors (file not found)
            assert response.status_code == 404, (
                f"S3 error should return 404, got {response.status_code}"
            )

            # Should have error message
            data = response.json()
            assert "error" in data
            assert "not found" in data["error"].lower() or "access denied" in data["error"].lower(), (
                f"Error message should mention file not found or access denied: {data['error']}"
            )

        finally:
            main.app_context = original_context
