"""
Unit tests for JobRepository - DynamoDB storage for translation jobs.
"""
import base64
import json
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.storage.job_repository import (
    JobRepository,
    JOBS_TABLE,
    JobNotFoundError,
)
from src.models.job import (
    TranslationJob,
    JobStatus,
    FileProgress,
    CompletedFile,
    FileError,
    LanguagePair,
    DocumentType,
)


class TestJobRepository:
    """Tests for JobRepository."""

    @pytest.fixture
    def mock_dynamodb_resource(self):
        """Create a mock DynamoDB resource."""
        resource = MagicMock()
        table = MagicMock()
        resource.Table.return_value = table
        return resource, table

    @pytest.fixture
    def mock_dynamodb_client(self):
        """Create a mock DynamoDB client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def repository(self, mock_dynamodb_resource, mock_dynamodb_client):
        """Create JobRepository with mocked DynamoDB."""
        repo = JobRepository()
        resource, table = mock_dynamodb_resource
        repo._resource = resource
        repo._client = mock_dynamodb_client
        return repo

    @pytest.fixture
    def sample_job(self):
        """Create a sample translation job."""
        return TranslationJob(
            id="job-123",
            status=JobStatus.PENDING,
            progress=0.0,
            files_total=2,
            files_completed=0,
            created_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            file_ids=["file-1", "file-2"],
            auto_append=True,
            language_pair=LanguagePair(
                id="lp-1",
                source_language="Chinese",
                target_language="Vietnamese",
                source_language_code="zh",
                target_language_code="vi",
            ),
        )

    @pytest.fixture
    def sample_job_with_progress(self, sample_job):
        """Create a sample job with progress data."""
        sample_job.status = JobStatus.PROCESSING
        sample_job.progress = 0.5
        sample_job.files_processing = [
            FileProgress(
                filename="test.xlsx",
                progress=0.5,
                segments_total=100,
                segments_translated=50,
                document_type=DocumentType.EXCEL,
            )
        ]
        return sample_job

    @pytest.fixture
    def sample_completed_job(self, sample_job):
        """Create a sample completed job."""
        sample_job.status = JobStatus.COMPLETED
        sample_job.progress = 1.0
        sample_job.files_completed = 2
        sample_job.completed_at = datetime(2026, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
        sample_job.completed_files = [
            CompletedFile(
                original_filename="test.xlsx",
                output_filename="test_vi.xlsx",
                segments_translated=100,
                document_type=DocumentType.EXCEL,
            ),
            CompletedFile(
                original_filename="doc.docx",
                output_filename="doc_vi.docx",
                segments_translated=50,
                document_type=DocumentType.WORD,
            ),
        ]
        return sample_job

    @pytest.fixture
    def sample_dynamodb_item(self):
        """Create a sample DynamoDB item."""
        return {
            "user_id": "user-456",
            "job_id": "job-123",
            "status": "pending",
            "status_created": "pending#2026-01-15T10:00:00+00:00",
            "progress": Decimal("0.0"),
            "files_total": Decimal("2"),
            "files_completed": Decimal("0"),
            "files_processing": [],
            "files_failed": [],
            "completed_files": [],
            "created_at": "2026-01-15T10:00:00+00:00",
            "completed_at": None,
            "file_ids": ["file-1", "file-2"],
            "auto_append": True,
            "language_pair": {
                "id": "lp-1",
                "source_language": "Chinese",
                "target_language": "Vietnamese",
                "source_language_code": "zh",
                "target_language_code": "vi",
            },
        }

    # =========================================================================
    # Serialization Tests
    # =========================================================================

    def test_serialize_job(self, repository, sample_job):
        """Test job serialization to DynamoDB format."""
        user_id = "user-456"
        item = repository._serialize_job(sample_job, user_id)

        assert item["user_id"] == user_id
        assert item["job_id"] == sample_job.id
        assert item["status"] == "pending"
        assert item["status_created"] == "pending#2026-01-15T10:00:00+00:00"
        assert item["progress"] == Decimal("0.0")
        assert item["files_total"] == 2
        assert item["files_completed"] == 0
        assert item["files_processing"] == []
        assert item["files_failed"] == []
        assert item["completed_files"] == []
        assert item["file_ids"] == ["file-1", "file-2"]
        assert item["auto_append"] is True
        assert item["language_pair"]["id"] == "lp-1"

    def test_serialize_job_with_progress(self, repository, sample_job_with_progress):
        """Test serialization of job with file progress."""
        item = repository._serialize_job(sample_job_with_progress, "user-456")

        assert len(item["files_processing"]) == 1
        fp = item["files_processing"][0]
        assert fp["filename"] == "test.xlsx"
        assert fp["progress"] == Decimal("0.5")
        assert fp["segments_total"] == 100
        assert fp["segments_translated"] == 50
        assert fp["document_type"] == "excel"

    def test_serialize_job_with_completed_files(self, repository, sample_completed_job):
        """Test serialization of completed job."""
        item = repository._serialize_job(sample_completed_job, "user-456")

        assert item["status"] == "completed"
        assert len(item["completed_files"]) == 2
        cf = item["completed_files"][0]
        assert cf["original_filename"] == "test.xlsx"
        assert cf["output_filename"] == "test_vi.xlsx"
        assert cf["segments_translated"] == 100

    def test_deserialize_job(self, repository, sample_dynamodb_item):
        """Test job deserialization from DynamoDB format."""
        job = repository._deserialize_job(sample_dynamodb_item)

        assert job.id == "job-123"
        assert job.status == JobStatus.PENDING
        assert job.progress == 0.0
        assert job.files_total == 2
        assert job.files_completed == 0
        assert job.language_pair.id == "lp-1"
        assert job.language_pair.source_language == "Chinese"

    def test_deserialize_job_with_decimals(self, repository):
        """Test deserialization handles Decimal conversion."""
        item = {
            "user_id": "user-456",
            "job_id": "job-123",
            "status": "processing",
            "progress": Decimal("0.75"),
            "files_total": Decimal("4"),
            "files_completed": Decimal("3"),
            "files_processing": [{
                "filename": "test.xlsx",
                "progress": Decimal("0.5"),
                "segments_total": Decimal("100"),
                "segments_translated": Decimal("50"),
            }],
            "files_failed": [],
            "completed_files": [],
            "created_at": "2026-01-15T10:00:00+00:00",
            "file_ids": [],
            "auto_append": True,
        }

        job = repository._deserialize_job(item)

        assert job.progress == 0.75
        assert job.files_total == 4
        assert job.files_completed == 3
        assert job.files_processing[0].progress == 0.5

    # =========================================================================
    # Create Job Tests
    # =========================================================================

    async def test_create_job(self, repository, sample_job, mock_dynamodb_resource):
        """Test creating a new job."""
        resource, table = mock_dynamodb_resource
        user_id = "user-456"

        result = await repository.create_job(sample_job, user_id)

        assert result.id == sample_job.id
        table.put_item.assert_called_once()
        call_kwargs = table.put_item.call_args[1]
        assert call_kwargs["Item"]["user_id"] == user_id
        assert call_kwargs["Item"]["job_id"] == sample_job.id

    async def test_create_job_with_condition(self, repository, sample_job, mock_dynamodb_resource):
        """Test that create_job uses condition to prevent overwrites."""
        resource, table = mock_dynamodb_resource

        await repository.create_job(sample_job, "user-456")

        call_kwargs = table.put_item.call_args[1]
        assert "ConditionExpression" in call_kwargs
        assert "attribute_not_exists" in call_kwargs["ConditionExpression"]

    # =========================================================================
    # Get Job Tests
    # =========================================================================

    async def test_get_job_found(self, repository, sample_dynamodb_item, mock_dynamodb_resource):
        """Test getting an existing job."""
        resource, table = mock_dynamodb_resource
        table.get_item.return_value = {"Item": sample_dynamodb_item}

        job = await repository.get_job("user-456", "job-123")

        assert job is not None
        assert job.id == "job-123"
        table.get_item.assert_called_once_with(
            Key={"user_id": "user-456", "job_id": "job-123"}
        )

    async def test_get_job_not_found(self, repository, mock_dynamodb_resource):
        """Test getting a non-existent job."""
        resource, table = mock_dynamodb_resource
        table.get_item.return_value = {}

        job = await repository.get_job("user-456", "nonexistent")

        assert job is None

    # =========================================================================
    # Update Job Tests
    # =========================================================================

    async def test_update_job(self, repository, sample_job, mock_dynamodb_resource):
        """Test updating an existing job."""
        resource, table = mock_dynamodb_resource
        table.get_item.return_value = {"Item": {"user_id": "user-456", "job_id": "job-123"}}

        sample_job.status = JobStatus.PROCESSING
        sample_job.progress = 0.5

        result = await repository.update_job(sample_job, "user-456")

        assert result is not None
        table.put_item.assert_called_once()

    async def test_update_job_not_found(self, repository, sample_job, mock_dynamodb_resource):
        """Test updating a non-existent job raises error."""
        resource, table = mock_dynamodb_resource
        table.get_item.return_value = {}

        with pytest.raises(JobNotFoundError):
            await repository.update_job(sample_job, "user-456")

    # =========================================================================
    # Delete Job Tests
    # =========================================================================

    async def test_delete_job_success(self, repository, mock_dynamodb_resource):
        """Test successful job deletion."""
        resource, table = mock_dynamodb_resource
        table.delete_item.return_value = {"Attributes": {"job_id": "job-123"}}

        result = await repository.delete_job("user-456", "job-123")

        assert result is True
        table.delete_item.assert_called_once()

    async def test_delete_job_not_found(self, repository, mock_dynamodb_resource):
        """Test deleting a non-existent job."""
        resource, table = mock_dynamodb_resource
        table.delete_item.return_value = {}

        result = await repository.delete_job("user-456", "nonexistent")

        assert result is False

    # =========================================================================
    # List Jobs Tests
    # =========================================================================

    async def test_list_jobs_basic(self, repository, sample_dynamodb_item, mock_dynamodb_resource):
        """Test listing jobs for a user."""
        resource, table = mock_dynamodb_resource
        table.query.return_value = {
            "Items": [sample_dynamodb_item],
            "LastEvaluatedKey": None,
        }

        jobs, cursor = await repository.list_jobs("user-456")

        assert len(jobs) == 1
        assert jobs[0].id == "job-123"
        assert cursor is None

    async def test_list_jobs_with_pagination(self, repository, sample_dynamodb_item, mock_dynamodb_resource):
        """Test listing jobs with pagination."""
        resource, table = mock_dynamodb_resource
        last_key = {"user_id": "user-456", "job_id": "job-123"}
        table.query.return_value = {
            "Items": [sample_dynamodb_item],
            "LastEvaluatedKey": last_key,
        }

        jobs, cursor = await repository.list_jobs("user-456", limit=10)

        assert len(jobs) == 1
        assert cursor is not None
        # Cursor should be base64 encoded JSON
        decoded = json.loads(base64.b64decode(cursor).decode("utf-8"))
        assert decoded == last_key

    async def test_list_jobs_with_cursor(self, repository, sample_dynamodb_item, mock_dynamodb_resource):
        """Test listing jobs starting from cursor."""
        resource, table = mock_dynamodb_resource
        table.query.return_value = {"Items": [sample_dynamodb_item]}

        # Create a valid cursor
        cursor_data = {"user_id": "user-456", "job_id": "job-100"}
        cursor = base64.b64encode(json.dumps(cursor_data).encode("utf-8")).decode("utf-8")

        jobs, _ = await repository.list_jobs("user-456", cursor=cursor)

        call_kwargs = table.query.call_args[1]
        assert "ExclusiveStartKey" in call_kwargs
        assert call_kwargs["ExclusiveStartKey"] == cursor_data

    async def test_list_jobs_filter_by_status(self, repository, sample_dynamodb_item, mock_dynamodb_resource):
        """Test listing jobs filtered by status."""
        resource, table = mock_dynamodb_resource
        table.query.return_value = {"Items": [sample_dynamodb_item]}

        jobs, _ = await repository.list_jobs("user-456", status=JobStatus.PENDING)

        call_kwargs = table.query.call_args[1]
        assert "FilterExpression" in call_kwargs or "IndexName" in call_kwargs

    async def test_list_jobs_filter_by_date_range(self, repository, sample_dynamodb_item, mock_dynamodb_resource):
        """Test listing jobs filtered by date range."""
        resource, table = mock_dynamodb_resource
        table.query.return_value = {"Items": [sample_dynamodb_item]}

        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 1, 31, tzinfo=timezone.utc)

        jobs, _ = await repository.list_jobs(
            "user-456",
            date_from=date_from,
            date_to=date_to,
        )

        call_kwargs = table.query.call_args[1]
        # Should have filter for date range
        assert "FilterExpression" in call_kwargs

    async def test_list_jobs_empty_result(self, repository, mock_dynamodb_resource):
        """Test listing jobs when none exist."""
        resource, table = mock_dynamodb_resource
        table.query.return_value = {"Items": []}

        jobs, cursor = await repository.list_jobs("user-456")

        assert jobs == []
        assert cursor is None

    # =========================================================================
    # Table Initialization Tests
    # =========================================================================

    async def test_initialize_table_creates_table(self, repository, mock_dynamodb_client):
        """Test table initialization creates table if not exists."""
        mock_dynamodb_client.describe_table.side_effect = Exception("ResourceNotFoundException")
        mock_dynamodb_client.create_table.return_value = {}
        mock_dynamodb_client.get_waiter.return_value.wait.return_value = None

        await repository.initialize_table()

        mock_dynamodb_client.create_table.assert_called_once()
        call_kwargs = mock_dynamodb_client.create_table.call_args[1]
        assert call_kwargs["TableName"] == JOBS_TABLE

    async def test_initialize_table_skips_existing(self, repository, mock_dynamodb_client):
        """Test table initialization skips if table exists."""
        mock_dynamodb_client.describe_table.return_value = {"Table": {"TableName": JOBS_TABLE}}

        await repository.initialize_table()

        mock_dynamodb_client.create_table.assert_not_called()

    # =========================================================================
    # GSI Tests
    # =========================================================================

    async def test_table_has_user_status_index(self, repository, mock_dynamodb_client):
        """Test that table creation includes user_status_index GSI."""
        mock_dynamodb_client.describe_table.side_effect = Exception("ResourceNotFoundException")
        mock_dynamodb_client.create_table.return_value = {}
        mock_dynamodb_client.get_waiter.return_value.wait.return_value = None

        await repository.initialize_table()

        call_kwargs = mock_dynamodb_client.create_table.call_args[1]
        gsi_names = [gsi["IndexName"] for gsi in call_kwargs["GlobalSecondaryIndexes"]]
        assert "user_status_index" in gsi_names

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    async def test_create_job_handles_dynamodb_error(self, repository, sample_job, mock_dynamodb_resource):
        """Test that DynamoDB errors are properly propagated."""
        from botocore.exceptions import ClientError

        resource, table = mock_dynamodb_resource
        table.put_item.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "DynamoDB error"}},
            "PutItem"
        )

        with pytest.raises(ClientError):
            await repository.create_job(sample_job, "user-456")


class TestJobRepositoryDecimalConversion:
    """Tests for Decimal conversion utilities."""

    def test_convert_floats_to_decimal(self):
        """Test float to Decimal conversion."""
        repo = JobRepository()

        data = {
            "progress": 0.5,
            "nested": {
                "value": 0.75,
            },
            "list": [{"item": 0.25}],
        }

        result = repo._convert_floats_to_decimal(data)

        assert isinstance(result["progress"], Decimal)
        assert result["progress"] == Decimal("0.5")
        assert isinstance(result["nested"]["value"], Decimal)
        assert isinstance(result["list"][0]["item"], Decimal)

    def test_convert_decimals_to_float(self):
        """Test Decimal to float conversion."""
        repo = JobRepository()

        data = {
            "progress": Decimal("0.5"),
            "nested": {
                "value": Decimal("0.75"),
            },
            "list": [{"item": Decimal("0.25")}],
            "int_value": Decimal("10"),
        }

        result = repo._convert_decimals_to_native(data)

        assert isinstance(result["progress"], float)
        assert result["progress"] == 0.5
        assert isinstance(result["nested"]["value"], float)
        assert isinstance(result["int_value"], int)
