"""
Unit tests for S3FileStorage - S3 storage for uploaded and output files.
"""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
from io import BytesIO

from botocore.exceptions import ClientError

from src.storage.s3_file_storage import S3FileStorage


class TestS3FileStorageInitialization:
    """Tests for S3FileStorage initialization."""

    def test_init_with_bucket_env_var(self):
        """Test initialization with S3_BUCKET environment variable."""
        with patch.dict("os.environ", {"S3_BUCKET": "test-bucket"}):
            storage = S3FileStorage()
            assert storage._bucket_name == "test-bucket"

    def test_init_without_bucket_raises_error(self):
        """Test initialization without S3_BUCKET raises ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove S3_BUCKET if it exists
            import os
            if "S3_BUCKET" in os.environ:
                del os.environ["S3_BUCKET"]

            with pytest.raises(ValueError) as exc_info:
                S3FileStorage()

            assert "S3_BUCKET" in str(exc_info.value)

    def test_init_with_explicit_bucket(self):
        """Test initialization with explicit bucket name."""
        storage = S3FileStorage(bucket_name="explicit-bucket")
        assert storage._bucket_name == "explicit-bucket"

    def test_init_with_explicit_bucket_and_logger(self):
        """Test initialization with explicit bucket and custom logger."""
        import logging
        logger = logging.getLogger("test")
        storage = S3FileStorage(
            bucket_name="test-bucket",
            logger_instance=logger,
        )
        assert storage._bucket_name == "test-bucket"


class TestS3FileStorageUpload:
    """Tests for file upload operations."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def storage(self, mock_s3_client):
        """Create S3FileStorage with mocked S3 client."""
        with patch.dict("os.environ", {"S3_BUCKET": "test-bucket"}):
            storage = S3FileStorage()
            storage._client = mock_s3_client
            return storage

    @pytest.mark.asyncio
    async def test_upload_file_success(self, storage, mock_s3_client):
        """Test successful file upload."""
        user_id = "user-123"
        file_id = "file-456"
        file_content = b"Excel file content"
        original_filename = "test_document.xlsx"

        s3_key = await storage.upload_file(
            user_id=user_id,
            file_id=file_id,
            file_content=file_content,
            original_filename=original_filename
        )

        # Verify S3 key format
        assert s3_key == f"{user_id}/uploads/{file_id}.xlsx"

        # Verify put_object was called for the file
        mock_s3_client.put_object.assert_any_call(
            Bucket="test-bucket",
            Key=f"{user_id}/uploads/{file_id}.xlsx",
            Body=file_content,
            ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Verify metadata was also uploaded
        calls = mock_s3_client.put_object.call_args_list
        metadata_call = [c for c in calls if ".metadata.json" in str(c)]
        assert len(metadata_call) == 1

    @pytest.mark.asyncio
    async def test_upload_file_stores_metadata(self, storage, mock_s3_client):
        """Test that upload stores correct metadata."""
        user_id = "user-123"
        file_id = "file-456"
        file_content = b"Test content"
        original_filename = "report.docx"

        with patch("src.storage.s3_file_storage.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            await storage.upload_file(
                user_id=user_id,
                file_id=file_id,
                file_content=file_content,
                original_filename=original_filename
            )

        # Find the metadata call
        calls = mock_s3_client.put_object.call_args_list
        metadata_call = None
        for call in calls:
            if ".metadata.json" in str(call):
                metadata_call = call
                break

        assert metadata_call is not None
        metadata_body = metadata_call[1]["Body"]
        metadata = json.loads(metadata_body)

        assert metadata["original_filename"] == "report.docx"
        assert metadata["content_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert metadata["document_type"] == "word"
        assert metadata["size_bytes"] == len(file_content)

    @pytest.mark.asyncio
    async def test_upload_file_content_types(self, storage, mock_s3_client):
        """Test correct content types for different file extensions."""
        test_cases = [
            ("file.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("file.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("file.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
            ("file.pdf", "application/pdf"),
        ]

        for filename, expected_content_type in test_cases:
            mock_s3_client.reset_mock()

            await storage.upload_file(
                user_id="user-123",
                file_id="file-456",
                file_content=b"content",
                original_filename=filename
            )

            # Find the file upload call (not metadata)
            file_call = None
            for call in mock_s3_client.put_object.call_args_list:
                if ".metadata.json" not in str(call):
                    file_call = call
                    break

            assert file_call is not None, f"No file call found for {filename}"
            assert file_call[1]["ContentType"] == expected_content_type, \
                f"Wrong content type for {filename}"


class TestS3FileStorageGetUpload:
    """Tests for getting uploaded files."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def storage(self, mock_s3_client):
        """Create S3FileStorage with mocked S3 client."""
        with patch.dict("os.environ", {"S3_BUCKET": "test-bucket"}):
            storage = S3FileStorage()
            storage._client = mock_s3_client
            return storage

    @pytest.mark.asyncio
    async def test_get_upload_success(self, storage, mock_s3_client):
        """Test successful retrieval of uploaded file."""
        user_id = "user-123"
        file_id = "file-456"
        file_content = b"Excel file content"
        metadata = {
            "original_filename": "test.xlsx",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "document_type": "excel",
            "uploaded_at": "2026-01-15T10:00:00+00:00",
            "size_bytes": len(file_content)
        }

        # Mock get_object responses
        def mock_get_object(Bucket, Key):
            if ".metadata.json" in Key:
                body = MagicMock()
                body.read.return_value = json.dumps(metadata).encode()
                return {"Body": body}
            else:
                body = MagicMock()
                body.read.return_value = file_content
                return {"Body": body}

        mock_s3_client.get_object.side_effect = mock_get_object

        content, returned_metadata = await storage.get_upload(user_id, file_id)

        assert content == file_content
        assert returned_metadata["original_filename"] == "test.xlsx"
        assert returned_metadata["document_type"] == "excel"

    @pytest.mark.asyncio
    async def test_get_upload_not_found(self, storage, mock_s3_client):
        """Test getting non-existent upload returns None."""
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject"
        )

        result = await storage.get_upload("user-123", "nonexistent")

        assert result is None


class TestS3FileStorageOutput:
    """Tests for output file operations."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def storage(self, mock_s3_client):
        """Create S3FileStorage with mocked S3 client."""
        with patch.dict("os.environ", {"S3_BUCKET": "test-bucket"}):
            storage = S3FileStorage()
            storage._client = mock_s3_client
            return storage

    @pytest.mark.asyncio
    async def test_save_output_success(self, storage, mock_s3_client):
        """Test successful output file save."""
        user_id = "user-123"
        job_id = "job-789"
        filename = "translated_vi.xlsx"
        content = b"Translated content"

        s3_key = await storage.save_output(
            user_id=user_id,
            job_id=job_id,
            filename=filename,
            content=content
        )

        assert s3_key == f"{user_id}/outputs/{job_id}/{filename}"
        mock_s3_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key=f"{user_id}/outputs/{job_id}/{filename}",
            Body=content,
            ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    @pytest.mark.asyncio
    async def test_get_output_success(self, storage, mock_s3_client):
        """Test successful output file retrieval."""
        user_id = "user-123"
        job_id = "job-789"
        filename = "translated_vi.xlsx"
        content = b"Translated content"

        body_mock = MagicMock()
        body_mock.read.return_value = content
        mock_s3_client.get_object.return_value = {"Body": body_mock}

        result = await storage.get_output(user_id, job_id, filename)

        assert result == content
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key=f"{user_id}/outputs/{job_id}/{filename}"
        )

    @pytest.mark.asyncio
    async def test_get_output_not_found(self, storage, mock_s3_client):
        """Test getting non-existent output returns None."""
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject"
        )

        result = await storage.get_output("user-123", "job-789", "missing.xlsx")

        assert result is None


class TestS3FileStorageStreamOutput:
    """Tests for streaming output file retrieval."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def storage(self, mock_s3_client):
        """Create S3FileStorage with mocked S3 client."""
        with patch.dict("os.environ", {"S3_BUCKET": "test-bucket"}):
            storage = S3FileStorage()
            storage._client = mock_s3_client
            return storage

    @pytest.mark.asyncio
    async def test_stream_output_success(self, storage, mock_s3_client):
        """Test successful streaming retrieval returns content_length and chunks."""
        content = b"A" * 1000
        body_mock = MagicMock()
        body_mock.read.side_effect = [content[:500], content[500:], b""]
        mock_s3_client.get_object.return_value = {
            "Body": body_mock,
            "ContentLength": 1000,
        }

        result = await storage.stream_output("user-123", "job-789", "file.xlsx")
        assert result is not None

        content_length, generator = result
        assert content_length == 1000

        chunks = []
        async for chunk in generator:
            chunks.append(chunk)
        assert b"".join(chunks) == content

    @pytest.mark.asyncio
    async def test_stream_output_not_found(self, storage, mock_s3_client):
        """Test streaming non-existent file returns None."""
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject",
        )

        result = await storage.stream_output("user-123", "job-789", "missing.xlsx")
        assert result is None

    @pytest.mark.asyncio
    async def test_stream_output_closes_body(self, storage, mock_s3_client):
        """Test that the S3 body is closed after iteration completes."""
        body_mock = MagicMock()
        body_mock.read.side_effect = [b"data", b""]
        mock_s3_client.get_object.return_value = {
            "Body": body_mock,
            "ContentLength": 4,
        }

        _, generator = await storage.stream_output("user-123", "job-789", "f.xlsx")
        async for _ in generator:
            pass

        body_mock.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_output_closes_body_on_error(self, storage, mock_s3_client):
        """Test that S3 body is closed even if read raises an exception."""
        body_mock = MagicMock()
        body_mock.read.side_effect = [b"first chunk", IOError("connection lost")]
        mock_s3_client.get_object.return_value = {
            "Body": body_mock,
            "ContentLength": 1000,
        }

        _, generator = await storage.stream_output("user-123", "job-789", "f.xlsx")
        with pytest.raises(IOError):
            async for _ in generator:
                pass

        body_mock.close.assert_called_once()


class TestS3FileStoragePresignedUrl:
    """Tests for presigned URL generation."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def storage(self, mock_s3_client):
        """Create S3FileStorage with mocked S3 client."""
        with patch.dict("os.environ", {"S3_BUCKET": "test-bucket"}):
            storage = S3FileStorage()
            storage._client = mock_s3_client
            return storage

    @pytest.mark.asyncio
    async def test_generate_download_url(self, storage, mock_s3_client):
        """Test presigned URL generation."""
        s3_key = "user-123/outputs/job-789/translated.xlsx"
        expected_url = "https://test-bucket.s3.amazonaws.com/user-123/outputs/job-789/translated.xlsx?signature=xxx"

        mock_s3_client.generate_presigned_url.return_value = expected_url

        url = await storage.generate_download_url(s3_key)

        assert url == expected_url
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": s3_key},
            ExpiresIn=900
        )

    @pytest.mark.asyncio
    async def test_generate_download_url_custom_expiry(self, storage, mock_s3_client):
        """Test presigned URL with custom expiry."""
        s3_key = "user-123/outputs/job-789/translated.xlsx"
        mock_s3_client.generate_presigned_url.return_value = "https://example.com/..."

        await storage.generate_download_url(s3_key, expiry=7200)

        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": s3_key},
            ExpiresIn=7200
        )

    @pytest.mark.asyncio
    async def test_generate_download_url_with_filename(self, storage, mock_s3_client):
        """Test presigned URL includes Content-Disposition when filename is provided."""
        s3_key = "user-123/outputs/job-789/translated.xlsx"
        mock_s3_client.generate_presigned_url.return_value = "https://example.com/..."

        url = await storage.generate_download_url(s3_key, filename="report.xlsx")

        assert url == "https://example.com/..."
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={
                "Bucket": "test-bucket",
                "Key": s3_key,
                "ResponseContentDisposition": "attachment; filename*=UTF-8''report.xlsx",
            },
            ExpiresIn=900
        )

    @pytest.mark.asyncio
    async def test_generate_output_download_url(self, storage, mock_s3_client):
        """Test generate_output_download_url builds correct key and includes filename."""
        mock_s3_client.generate_presigned_url.return_value = "https://example.com/..."

        url = await storage.generate_output_download_url(
            "user-123", "job-789", "translated.xlsx"
        )

        assert url == "https://example.com/..."
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={
                "Bucket": "test-bucket",
                "Key": "user-123/outputs/job-789/translated.xlsx",
                "ResponseContentDisposition": "attachment; filename*=UTF-8''translated.xlsx",
            },
            ExpiresIn=900
        )


class TestS3FileStorageDeletion:
    """Tests for file deletion operations."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def storage(self, mock_s3_client):
        """Create S3FileStorage with mocked S3 client."""
        with patch.dict("os.environ", {"S3_BUCKET": "test-bucket"}):
            storage = S3FileStorage()
            storage._client = mock_s3_client
            return storage

    @pytest.mark.asyncio
    async def test_delete_user_data(self, storage, mock_s3_client):
        """Test deleting all data for a user."""
        user_id = "user-123"

        # Mock list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": f"{user_id}/uploads/file1.xlsx"},
                {"Key": f"{user_id}/uploads/file1.metadata.json"},
                {"Key": f"{user_id}/uploads/file2.docx"},
                {"Key": f"{user_id}/uploads/file2.metadata.json"},
                {"Key": f"{user_id}/outputs/job1/output.xlsx"},
            ],
            "IsTruncated": False
        }

        count = await storage.delete_user_data(user_id)

        assert count == 5
        mock_s3_client.list_objects_v2.assert_called_with(
            Bucket="test-bucket",
            Prefix=f"{user_id}/"
        )
        mock_s3_client.delete_objects.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_data_empty(self, storage, mock_s3_client):
        """Test deleting data for user with no files."""
        mock_s3_client.list_objects_v2.return_value = {"IsTruncated": False}

        count = await storage.delete_user_data("user-123")

        assert count == 0
        mock_s3_client.delete_objects.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_user_data_pagination(self, storage, mock_s3_client):
        """Test deleting user data with pagination."""
        user_id = "user-123"

        # Mock paginated responses
        mock_s3_client.list_objects_v2.side_effect = [
            {
                "Contents": [{"Key": f"{user_id}/uploads/file{i}.xlsx"} for i in range(1000)],
                "IsTruncated": True,
                "NextContinuationToken": "token123"
            },
            {
                "Contents": [{"Key": f"{user_id}/uploads/file{i}.xlsx"} for i in range(1000, 1500)],
                "IsTruncated": False
            }
        ]

        count = await storage.delete_user_data(user_id)

        assert count == 1500
        assert mock_s3_client.list_objects_v2.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_job_outputs(self, storage, mock_s3_client):
        """Test deleting all outputs for a job."""
        user_id = "user-123"
        job_id = "job-789"

        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": f"{user_id}/outputs/{job_id}/output1.xlsx"},
                {"Key": f"{user_id}/outputs/{job_id}/output2.docx"},
            ],
            "IsTruncated": False
        }

        count = await storage.delete_job_outputs(user_id, job_id)

        assert count == 2
        mock_s3_client.list_objects_v2.assert_called_with(
            Bucket="test-bucket",
            Prefix=f"{user_id}/outputs/{job_id}/"
        )

    @pytest.mark.asyncio
    async def test_delete_job_outputs_empty(self, storage, mock_s3_client):
        """Test deleting outputs for job with no files."""
        mock_s3_client.list_objects_v2.return_value = {"IsTruncated": False}

        count = await storage.delete_job_outputs("user-123", "job-789")

        assert count == 0


class TestS3FileStorageDocumentTypes:
    """Tests for document type detection."""

    @pytest.fixture
    def storage(self):
        """Create S3FileStorage."""
        with patch.dict("os.environ", {"S3_BUCKET": "test-bucket"}):
            storage = S3FileStorage()
            storage._client = MagicMock()
            return storage

    def test_detect_document_type_excel(self, storage):
        """Test Excel document type detection."""
        assert storage._detect_document_type("file.xlsx") == "excel"
        assert storage._detect_document_type("file.xls") == "excel"

    def test_detect_document_type_word(self, storage):
        """Test Word document type detection."""
        assert storage._detect_document_type("file.docx") == "word"
        assert storage._detect_document_type("file.doc") == "word"

    def test_detect_document_type_powerpoint(self, storage):
        """Test PowerPoint document type detection."""
        assert storage._detect_document_type("file.pptx") == "powerpoint"
        assert storage._detect_document_type("file.ppt") == "powerpoint"

    def test_detect_document_type_pdf(self, storage):
        """Test PDF document type detection."""
        assert storage._detect_document_type("file.pdf") == "pdf"

    def test_detect_document_type_text(self, storage):
        """Test text document type detection."""
        assert storage._detect_document_type("file.txt") == "text"

    def test_detect_document_type_markdown(self, storage):
        """Test markdown document type detection."""
        assert storage._detect_document_type("file.md") == "markdown"

    def test_detect_document_type_unknown(self, storage):
        """Test unknown document type."""
        assert storage._detect_document_type("file.csv") is None
        assert storage._detect_document_type("file.xyz") is None

    def test_get_content_type_for_extension(self, storage):
        """Test content type mapping."""
        assert storage._get_content_type(".xlsx") == \
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert storage._get_content_type(".docx") == \
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert storage._get_content_type(".pptx") == \
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert storage._get_content_type(".pdf") == "application/pdf"
        assert storage._get_content_type(".unknown") == "application/octet-stream"


class TestS3FileStorageAsyncWrapper:
    """Tests for async wrapper functionality."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def storage(self, mock_s3_client):
        """Create S3FileStorage with mocked S3 client."""
        with patch.dict("os.environ", {"S3_BUCKET": "test-bucket"}):
            storage = S3FileStorage()
            storage._client = mock_s3_client
            return storage

    @pytest.mark.asyncio
    async def test_run_sync_executes_in_executor(self, storage, mock_s3_client):
        """Test that _run_sync properly executes synchronous functions."""
        def sync_operation():
            return "result"

        result = await storage._run_sync(sync_operation)

        assert result == "result"

    @pytest.mark.asyncio
    async def test_run_sync_propagates_exceptions(self, storage):
        """Test that _run_sync properly propagates exceptions."""
        def failing_operation():
            raise ValueError("Test error")

        with pytest.raises(ValueError) as exc_info:
            await storage._run_sync(failing_operation)

        assert "Test error" in str(exc_info.value)
