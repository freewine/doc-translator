"""
Unit tests for JobStore with DynamoDB backend via JobRepository.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, List, Tuple

from src.storage.job_store import JobStore
from src.storage.job_repository import JobRepository, JobNotFoundError
from src.models.job import (
    TranslationJob,
    JobStatus,
    FileProgress,
    CompletedFile,
    FileError,
    LanguagePair,
    DocumentType,
)


class TestJobStoreInitialization:
    """Tests for JobStore initialization."""

    def test_init_creates_default_repository(self):
        """Test JobStore creates a JobRepository if not provided."""
        store = JobStore()
        assert store._repository is not None
        assert isinstance(store._repository, JobRepository)

    def test_init_accepts_custom_repository(self):
        """Test JobStore accepts a custom JobRepository."""
        custom_repo = JobRepository(endpoint_url="http://localhost:8000")
        store = JobStore(repository=custom_repo)
        assert store._repository is custom_repo

    def test_init_no_user_context(self):
        """Test JobStore starts without user context."""
        store = JobStore()
        assert store._user_id is None


class TestJobStoreUserContext:
    """Tests for user context management."""

    def test_set_user_context(self):
        """Test setting user context."""
        store = JobStore()
        store.set_user_context("user-123")
        assert store._user_id == "user-123"

    def test_set_user_context_overwrites(self):
        """Test setting user context overwrites previous value."""
        store = JobStore()
        store.set_user_context("user-123")
        store.set_user_context("user-456")
        assert store._user_id == "user-456"

    def test_require_user_context_raises_without_context(self):
        """Test _require_user_context raises ValueError without user context."""
        store = JobStore()
        with pytest.raises(ValueError) as exc_info:
            store._require_user_context()
        assert "user context" in str(exc_info.value).lower()

    def test_require_user_context_returns_user_id(self):
        """Test _require_user_context returns user_id when set."""
        store = JobStore()
        store.set_user_context("user-123")
        user_id = store._require_user_context()
        assert user_id == "user-123"


class TestJobStoreSaveJob:
    """Tests for saving jobs."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock JobRepository."""
        repo = MagicMock(spec=JobRepository)
        repo.create_job = AsyncMock()
        repo.update_job = AsyncMock()
        repo.get_job = AsyncMock(return_value=None)
        repo.delete_job = AsyncMock(return_value=True)
        repo.list_jobs = AsyncMock(return_value=([], None))
        return repo

    @pytest.fixture
    def store(self, mock_repository):
        """Create JobStore with mock repository and user context."""
        store = JobStore(repository=mock_repository)
        store.set_user_context("user-123")
        return store

    @pytest.fixture
    def sample_job(self):
        """Create a sample translation job."""
        return TranslationJob(
            id="job-456",
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

    @pytest.mark.asyncio
    async def test_save_job_calls_repository_create(self, store, mock_repository, sample_job):
        """Test save_job calls repository.create_job."""
        mock_repository.create_job.return_value = sample_job

        await store.save_job(sample_job)

        mock_repository.create_job.assert_called_once_with(sample_job, "user-123")

    @pytest.mark.asyncio
    async def test_save_job_requires_user_context(self, mock_repository, sample_job):
        """Test save_job raises without user context."""
        store = JobStore(repository=mock_repository)

        with pytest.raises(ValueError) as exc_info:
            await store.save_job(sample_job)

        assert "user context" in str(exc_info.value).lower()


class TestJobStoreGetJob:
    """Tests for getting jobs."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock JobRepository."""
        repo = MagicMock(spec=JobRepository)
        repo.get_job = AsyncMock()
        return repo

    @pytest.fixture
    def store(self, mock_repository):
        """Create JobStore with mock repository and user context."""
        store = JobStore(repository=mock_repository)
        store.set_user_context("user-123")
        return store

    @pytest.fixture
    def sample_job(self):
        """Create a sample translation job."""
        return TranslationJob(
            id="job-456",
            status=JobStatus.PROCESSING,
            progress=0.5,
            files_total=2,
            files_completed=1,
            created_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_get_job_found(self, store, mock_repository, sample_job):
        """Test get_job returns job when found."""
        mock_repository.get_job.return_value = sample_job

        result = await store.get_job("job-456")

        assert result is not None
        assert result.id == "job-456"
        mock_repository.get_job.assert_called_once_with("user-123", "job-456")

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, store, mock_repository):
        """Test get_job returns None when not found."""
        mock_repository.get_job.return_value = None

        result = await store.get_job("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_job_requires_user_context(self, mock_repository):
        """Test get_job raises without user context."""
        store = JobStore(repository=mock_repository)

        with pytest.raises(ValueError):
            await store.get_job("job-456")


class TestJobStoreUpdateJob:
    """Tests for updating jobs."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock JobRepository."""
        repo = MagicMock(spec=JobRepository)
        repo.update_job = AsyncMock()
        return repo

    @pytest.fixture
    def store(self, mock_repository):
        """Create JobStore with mock repository and user context."""
        store = JobStore(repository=mock_repository)
        store.set_user_context("user-123")
        return store

    @pytest.fixture
    def sample_job(self):
        """Create a sample translation job."""
        return TranslationJob(
            id="job-456",
            status=JobStatus.PROCESSING,
            progress=0.5,
            files_total=2,
            files_completed=1,
            created_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_update_job_calls_repository(self, store, mock_repository, sample_job):
        """Test update_job calls repository.update_job."""
        mock_repository.update_job.return_value = sample_job

        await store.update_job(sample_job)

        mock_repository.update_job.assert_called_once_with(sample_job, "user-123")

    @pytest.mark.asyncio
    async def test_update_job_requires_user_context(self, mock_repository, sample_job):
        """Test update_job raises without user context."""
        store = JobStore(repository=mock_repository)

        with pytest.raises(ValueError):
            await store.update_job(sample_job)


class TestJobStoreListJobs:
    """Tests for listing jobs."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock JobRepository."""
        repo = MagicMock(spec=JobRepository)
        repo.list_jobs = AsyncMock()
        return repo

    @pytest.fixture
    def store(self, mock_repository):
        """Create JobStore with mock repository and user context."""
        store = JobStore(repository=mock_repository)
        store.set_user_context("user-123")
        return store

    @pytest.fixture
    def sample_jobs(self):
        """Create sample jobs for listing."""
        return [
            TranslationJob(
                id="job-1",
                status=JobStatus.COMPLETED,
                progress=1.0,
                created_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            ),
            TranslationJob(
                id="job-2",
                status=JobStatus.PENDING,
                progress=0.0,
                created_at=datetime(2026, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
            ),
        ]

    @pytest.mark.asyncio
    async def test_list_jobs_basic(self, store, mock_repository, sample_jobs):
        """Test list_jobs returns jobs from repository."""
        mock_repository.list_jobs.return_value = (sample_jobs, None)

        jobs, cursor = await store.list_jobs()

        assert len(jobs) == 2
        assert cursor is None
        mock_repository.list_jobs.assert_called_once_with(
            "user-123",
            status=None,
            date_from=None,
            date_to=None,
            limit=50,
            cursor=None,
        )

    @pytest.mark.asyncio
    async def test_list_jobs_with_limit(self, store, mock_repository, sample_jobs):
        """Test list_jobs with limit parameter."""
        mock_repository.list_jobs.return_value = (sample_jobs[:1], "cursor123")

        jobs, cursor = await store.list_jobs(limit=1)

        assert len(jobs) == 1
        assert cursor == "cursor123"
        call_kwargs = mock_repository.list_jobs.call_args[1]
        assert call_kwargs["limit"] == 1

    @pytest.mark.asyncio
    async def test_list_jobs_with_cursor(self, store, mock_repository, sample_jobs):
        """Test list_jobs with pagination cursor."""
        mock_repository.list_jobs.return_value = (sample_jobs, None)

        await store.list_jobs(cursor="cursor123")

        call_kwargs = mock_repository.list_jobs.call_args[1]
        assert call_kwargs["cursor"] == "cursor123"

    @pytest.mark.asyncio
    async def test_list_jobs_with_status_filter(self, store, mock_repository, sample_jobs):
        """Test list_jobs with status filter."""
        mock_repository.list_jobs.return_value = ([sample_jobs[0]], None)

        await store.list_jobs(status_filter=JobStatus.COMPLETED)

        call_kwargs = mock_repository.list_jobs.call_args[1]
        assert call_kwargs["status"] == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_list_jobs_with_date_range(self, store, mock_repository, sample_jobs):
        """Test list_jobs with date range filter."""
        mock_repository.list_jobs.return_value = (sample_jobs, None)
        date_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(2026, 1, 31, tzinfo=timezone.utc)

        await store.list_jobs(date_from=date_from, date_to=date_to)

        call_kwargs = mock_repository.list_jobs.call_args[1]
        assert call_kwargs["date_from"] == date_from
        assert call_kwargs["date_to"] == date_to

    @pytest.mark.asyncio
    async def test_list_jobs_requires_user_context(self, mock_repository):
        """Test list_jobs raises without user context."""
        store = JobStore(repository=mock_repository)

        with pytest.raises(ValueError):
            await store.list_jobs()


class TestJobStoreDeleteJob:
    """Tests for deleting jobs."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock JobRepository."""
        repo = MagicMock(spec=JobRepository)
        repo.delete_job = AsyncMock()
        return repo

    @pytest.fixture
    def store(self, mock_repository):
        """Create JobStore with mock repository and user context."""
        store = JobStore(repository=mock_repository)
        store.set_user_context("user-123")
        return store

    @pytest.mark.asyncio
    async def test_delete_job_success(self, store, mock_repository):
        """Test delete_job returns True on success."""
        mock_repository.delete_job.return_value = True

        result = await store.delete_job("job-456")

        assert result is True
        mock_repository.delete_job.assert_called_once_with("user-123", "job-456")

    @pytest.mark.asyncio
    async def test_delete_job_not_found(self, store, mock_repository):
        """Test delete_job returns False when not found."""
        mock_repository.delete_job.return_value = False

        result = await store.delete_job("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_job_requires_user_context(self, mock_repository):
        """Test delete_job raises without user context."""
        store = JobStore(repository=mock_repository)

        with pytest.raises(ValueError):
            await store.delete_job("job-456")


class TestJobStoreClear:
    """Tests for clear operation."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock JobRepository."""
        return MagicMock(spec=JobRepository)

    @pytest.fixture
    def store(self, mock_repository):
        """Create JobStore with mock repository."""
        store = JobStore(repository=mock_repository)
        store.set_user_context("user-123")
        return store

    @pytest.mark.asyncio
    async def test_clear_raises_not_implemented(self, store):
        """Test clear raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await store.clear()


class TestJobStoreProgressMethods:
    """Tests for progress tracking methods."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock JobRepository."""
        repo = MagicMock(spec=JobRepository)
        repo.get_job = AsyncMock()
        repo.update_job = AsyncMock()
        return repo

    @pytest.fixture
    def store(self, mock_repository):
        """Create JobStore with mock repository and user context."""
        store = JobStore(repository=mock_repository)
        store.set_user_context("user-123")
        return store

    @pytest.fixture
    def sample_job(self):
        """Create a sample job for progress tracking."""
        job = TranslationJob(
            id="job-456",
            status=JobStatus.PROCESSING,
            progress=0.0,
            files_total=2,
            files_completed=0,
            created_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        )
        return job

    @pytest.mark.asyncio
    async def test_update_job_progress(self, store, mock_repository, sample_job):
        """Test update_job_progress fetches, updates, and saves job."""
        mock_repository.get_job.return_value = sample_job
        mock_repository.update_job.return_value = sample_job

        await store.update_job_progress("job-456", "test.xlsx", 50, 1)

        # Verify job was fetched
        mock_repository.get_job.assert_called_once_with("user-123", "job-456")
        # Verify job was updated
        mock_repository.update_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_job_progress_job_not_found(self, store, mock_repository):
        """Test update_job_progress does nothing if job not found."""
        mock_repository.get_job.return_value = None

        await store.update_job_progress("nonexistent", "test.xlsx", 50, 1)

        mock_repository.update_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_mark_file_processing(self, store, mock_repository, sample_job):
        """Test mark_file_processing fetches, updates, and saves job."""
        mock_repository.get_job.return_value = sample_job
        mock_repository.update_job.return_value = sample_job

        await store.mark_file_processing("job-456", "test.xlsx", 100, 5)

        mock_repository.get_job.assert_called_once()
        mock_repository.update_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_file_completed(self, store, mock_repository, sample_job):
        """Test mark_file_completed fetches, updates, and saves job."""
        # Add a file to processing list first
        sample_job.mark_file_processing("test.xlsx", segments_total=100)
        mock_repository.get_job.return_value = sample_job
        mock_repository.update_job.return_value = sample_job

        await store.mark_file_completed("job-456", "test.xlsx", "test_vi.xlsx", 100)

        mock_repository.get_job.assert_called_once()
        mock_repository.update_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_file_failed(self, store, mock_repository, sample_job):
        """Test mark_file_failed fetches, updates, and saves job."""
        sample_job.mark_file_processing("test.xlsx", segments_total=100)
        mock_repository.get_job.return_value = sample_job
        mock_repository.update_job.return_value = sample_job

        await store.mark_file_failed("job-456", "test.xlsx", "Translation error", "TranslationError")

        mock_repository.get_job.assert_called_once()
        mock_repository.update_job.assert_called_once()


class TestJobStoreBackwardCompatibility:
    """Tests for backward compatibility with old interface."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock JobRepository."""
        repo = MagicMock(spec=JobRepository)
        repo.get_job = AsyncMock()
        repo.create_job = AsyncMock()
        repo.update_job = AsyncMock()
        repo.list_jobs = AsyncMock(return_value=([], None))
        repo.delete_job = AsyncMock(return_value=True)
        return repo

    @pytest.fixture
    def store(self, mock_repository):
        """Create JobStore with mock repository and user context."""
        store = JobStore(repository=mock_repository)
        store.set_user_context("user-123")
        return store

    @pytest.mark.asyncio
    async def test_all_methods_are_async(self, store, mock_repository):
        """Test that all public methods are async."""
        job = TranslationJob(id="job-1")
        mock_repository.get_job.return_value = job
        mock_repository.create_job.return_value = job
        mock_repository.update_job.return_value = job

        # All these should be awaitable
        await store.save_job(job)
        await store.get_job("job-1")
        await store.update_job(job)
        await store.list_jobs()
        await store.delete_job("job-1")
        await store.update_job_progress("job-1", "test.xlsx", 10, 1)
        await store.mark_file_processing("job-1", "test.xlsx", 100, 5)
        await store.mark_file_completed("job-1", "test.xlsx", "test_vi.xlsx", 100)
        await store.mark_file_failed("job-1", "test.xlsx", "Error", "ErrorType")
