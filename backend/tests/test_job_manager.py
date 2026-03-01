"""
Unit tests for the job management system.
"""
import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.models import (
    FileError,
    FileProgress,
    JobStatus,
    LanguagePair,
    TranslationJob,
)
from src.storage import JobStore
from src.storage.job_repository import JobRepository
from src.services import JobManager


class TestTranslationJob:
    """Test the TranslationJob dataclass and its methods."""

    def test_job_creation(self):
        """Test that a job is created with correct default values."""
        job = TranslationJob()

        assert job.id is not None
        assert job.status == JobStatus.PENDING
        assert job.progress == 0.0
        assert job.files_total == 0
        assert job.files_completed == 0
        assert len(job.files_processing) == 0
        assert len(job.files_failed) == 0
        assert job.created_at is not None
        assert job.completed_at is None

    def test_job_with_custom_values(self):
        """Test creating a job with custom values."""
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )

        job = TranslationJob(
            files_total=5,
            language_pair=language_pair,
            file_ids=["file1", "file2", "file3", "file4", "file5"]
        )

        assert job.files_total == 5
        assert job.language_pair == language_pair
        assert len(job.file_ids) == 5

    def test_mark_file_processing(self):
        """Test marking a file as processing."""
        job = TranslationJob(files_total=2)

        job.mark_file_processing("test.xlsx", cells_total=100, worksheets_total=3)

        assert len(job.files_processing) == 1
        assert job.files_processing[0].filename == "test.xlsx"
        assert job.files_processing[0].cells_total == 100
        assert job.files_processing[0].worksheets_total == 3
        assert job.files_processing[0].progress == 0.0

    def test_update_file_progress(self):
        """Test updating progress for a file."""
        job = TranslationJob(files_total=1)
        job.mark_file_processing("test.xlsx", cells_total=100, worksheets_total=2)

        job.update_file_progress("test.xlsx", cells_translated=50, worksheets_completed=1)

        assert job.files_processing[0].cells_translated == 50
        assert job.files_processing[0].worksheets_completed == 1
        assert job.files_processing[0].progress == 0.5
        assert job.progress == 0.5  # Overall progress should be updated

    def test_mark_file_completed(self):
        """Test marking a file as completed."""
        job = TranslationJob(files_total=2)
        job.mark_file_processing("test.xlsx", cells_total=100)

        job.mark_file_completed("test.xlsx")

        assert len(job.files_processing) == 0
        assert job.files_completed == 1
        assert job.progress == 0.5  # 1 out of 2 files completed
        assert job.status == JobStatus.PENDING  # Not all files done yet

    def test_mark_file_failed(self):
        """Test marking a file as failed."""
        job = TranslationJob(files_total=2)
        job.mark_file_processing("test.xlsx", cells_total=100)

        job.mark_file_failed("test.xlsx", "Test error", "TestError")

        assert len(job.files_processing) == 0
        assert len(job.files_failed) == 1
        assert job.files_failed[0].filename == "test.xlsx"
        assert job.files_failed[0].error == "Test error"
        assert job.files_failed[0].error_type == "TestError"
        assert job.progress == 0.5  # 1 out of 2 files processed (failed)

    def test_job_completion_all_success(self):
        """Test job completion when all files succeed."""
        job = TranslationJob(files_total=2)

        job.mark_file_processing("file1.xlsx", cells_total=100)
        job.mark_file_completed("file1.xlsx")

        job.mark_file_processing("file2.xlsx", cells_total=100)
        job.mark_file_completed("file2.xlsx")

        assert job.status == JobStatus.COMPLETED
        assert job.progress == 1.0
        assert job.completed_at is not None

    def test_job_completion_all_failed(self):
        """Test job completion when all files fail."""
        job = TranslationJob(files_total=2)

        job.mark_file_processing("file1.xlsx", cells_total=100)
        job.mark_file_failed("file1.xlsx", "Error 1")

        job.mark_file_processing("file2.xlsx", cells_total=100)
        job.mark_file_failed("file2.xlsx", "Error 2")

        assert job.status == JobStatus.FAILED
        assert job.progress == 1.0
        assert job.completed_at is not None

    def test_job_completion_partial_success(self):
        """Test job completion with some successes and some failures."""
        job = TranslationJob(files_total=3)

        job.mark_file_processing("file1.xlsx", cells_total=100)
        job.mark_file_completed("file1.xlsx")

        job.mark_file_processing("file2.xlsx", cells_total=100)
        job.mark_file_failed("file2.xlsx", "Error")

        job.mark_file_processing("file3.xlsx", cells_total=100)
        job.mark_file_completed("file3.xlsx")

        assert job.status == JobStatus.PARTIAL_SUCCESS
        assert job.progress == 1.0
        assert job.completed_at is not None
        assert job.files_completed == 2
        assert len(job.files_failed) == 1

    def test_progress_calculation_with_multiple_files(self):
        """Test progress calculation with multiple files at different stages."""
        job = TranslationJob(files_total=4)

        # File 1: completed
        job.mark_file_processing("file1.xlsx", cells_total=100)
        job.mark_file_completed("file1.xlsx")

        # File 2: 50% done
        job.mark_file_processing("file2.xlsx", cells_total=100)
        job.update_file_progress("file2.xlsx", cells_translated=50)

        # File 3: 25% done
        job.mark_file_processing("file3.xlsx", cells_total=100)
        job.update_file_progress("file3.xlsx", cells_translated=25)

        # File 4: not started

        # Progress should be: (1 + 0.5 + 0.25 + 0) / 4 = 0.4375
        assert abs(job.progress - 0.4375) < 0.001


class TestJobStore:
    """Test the JobStore class with mocked repository."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock JobRepository."""
        repo = MagicMock(spec=JobRepository)
        repo.create_job = AsyncMock()
        repo.get_job = AsyncMock()
        repo.update_job = AsyncMock()
        repo.delete_job = AsyncMock()
        repo.list_jobs = AsyncMock()
        return repo

    @pytest.fixture
    def store(self, mock_repository):
        """Create JobStore with mocked repository and user context."""
        store = JobStore(repository=mock_repository)
        store.set_user_context("test-user")
        return store

    @pytest.mark.asyncio
    async def test_save_and_get_job(self, store, mock_repository):
        """Test saving and retrieving a job."""
        job = TranslationJob(files_total=1)
        mock_repository.create_job.return_value = job
        mock_repository.get_job.return_value = job

        await store.save_job(job)
        retrieved = await store.get_job(job.id)

        assert retrieved is not None
        assert retrieved.id == job.id
        assert retrieved.files_total == 1

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, store, mock_repository):
        """Test retrieving a job that doesn't exist."""
        mock_repository.get_job.return_value = None

        retrieved = await store.get_job("nonexistent-id")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_jobs(self, store, mock_repository):
        """Test listing all jobs."""
        job1 = TranslationJob(files_total=1)
        job2 = TranslationJob(files_total=2)
        job3 = TranslationJob(files_total=3)

        # Mock list_jobs to return jobs in reverse order (newest first)
        mock_repository.list_jobs.return_value = ([job3, job2, job1], None)

        jobs, cursor = await store.list_jobs()

        assert len(jobs) == 3
        # Should be sorted by creation time, newest first
        assert jobs[0].id == job3.id
        assert jobs[1].id == job2.id
        assert jobs[2].id == job1.id

    @pytest.mark.asyncio
    async def test_update_job_progress(self, store, mock_repository):
        """Test updating job progress through the store."""
        job = TranslationJob(files_total=1)
        job.mark_file_processing("test.xlsx", cells_total=100)
        mock_repository.get_job.return_value = job
        mock_repository.update_job.return_value = job

        await store.update_job_progress(job.id, "test.xlsx", cells_translated=50)

        mock_repository.update_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_file_completed_through_store(self, store, mock_repository):
        """Test marking a file as completed through the store."""
        job = TranslationJob(files_total=1)
        job.mark_file_processing("test.xlsx", cells_total=100)
        mock_repository.get_job.return_value = job
        mock_repository.update_job.return_value = job

        await store.mark_file_completed(job.id, "test.xlsx")

        mock_repository.update_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_file_failed_through_store(self, store, mock_repository):
        """Test marking a file as failed through the store."""
        job = TranslationJob(files_total=1)
        job.mark_file_processing("test.xlsx", cells_total=100)
        mock_repository.get_job.return_value = job
        mock_repository.update_job.return_value = job

        await store.mark_file_failed(job.id, "test.xlsx", "Test error", "TestError")

        mock_repository.update_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_job(self, store, mock_repository):
        """Test deleting a job."""
        job = TranslationJob(files_total=1)
        mock_repository.delete_job.return_value = True
        mock_repository.get_job.return_value = None

        deleted = await store.delete_job(job.id)

        assert deleted is True
        retrieved = await store.get_job(job.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_job(self, store, mock_repository):
        """Test deleting a job that doesn't exist."""
        mock_repository.delete_job.return_value = False

        deleted = await store.delete_job("nonexistent-id")

        assert deleted is False

    @pytest.mark.asyncio
    async def test_clear_store(self, store):
        """Test clearing all jobs from the store raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await store.clear()

    @pytest.mark.asyncio
    async def test_concurrent_access(self, store, mock_repository):
        """Test that concurrent access to the store works with mocked repository."""
        job = TranslationJob(files_total=100)
        mock_repository.get_job.return_value = job
        mock_repository.update_job.return_value = job

        # Simulate concurrent updates
        async def update_progress(filename: str, cells: int):
            await store.mark_file_processing(job.id, filename, cells_total=100)
            for i in range(10):
                await store.update_job_progress(job.id, filename, cells_translated=i * 10)
                await asyncio.sleep(0.001)
            await store.mark_file_completed(job.id, filename)

        # Run multiple concurrent updates
        tasks = [
            update_progress(f"file{i}.xlsx", 100)
            for i in range(10)
        ]
        await asyncio.gather(*tasks)

        # Verify update_job was called multiple times
        assert mock_repository.update_job.call_count > 0


class TestJobManager:
    """Test the JobManager class with mocked repository."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock JobRepository."""
        repo = MagicMock(spec=JobRepository)
        repo.create_job = AsyncMock()
        repo.get_job = AsyncMock()
        repo.update_job = AsyncMock()
        repo.delete_job = AsyncMock()
        repo.list_jobs = AsyncMock(return_value=([], None))
        return repo

    @pytest.fixture
    def store(self, mock_repository):
        """Create JobStore with mocked repository."""
        store = JobStore(repository=mock_repository)
        store.set_user_context("test-user")
        return store

    @pytest.fixture
    def manager(self, store):
        """Create JobManager with mocked store."""
        return JobManager(job_store=store)

    @pytest.mark.asyncio
    async def test_create_job(self, manager, mock_repository):
        """Test creating a job through the manager."""
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )

        job = await manager.create_job(
            file_ids=["file1", "file2", "file3"],
            language_pair=language_pair
        )

        assert job.id is not None
        assert job.status == JobStatus.PENDING
        assert job.files_total == 3
        assert len(job.file_ids) == 3
        assert job.language_pair == language_pair
        mock_repository.create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job(self, manager, mock_repository):
        """Test retrieving a job through the manager."""
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )

        created_job = await manager.create_job(
            file_ids=["file1"],
            language_pair=language_pair
        )

        mock_repository.get_job.return_value = created_job

        retrieved_job = await manager.get_job(created_job.id)

        assert retrieved_job is not None
        assert retrieved_job.id == created_job.id

    @pytest.mark.asyncio
    async def test_list_jobs(self, manager, mock_repository):
        """Test listing all jobs through the manager."""
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )

        job1 = await manager.create_job(file_ids=["file1"], language_pair=language_pair)
        job2 = await manager.create_job(file_ids=["file2"], language_pair=language_pair)
        job3 = await manager.create_job(file_ids=["file3"], language_pair=language_pair)

        mock_repository.list_jobs.return_value = ([job1, job2, job3], None)

        jobs = await manager.list_jobs()

        assert len(jobs) == 3

    @pytest.mark.asyncio
    async def test_start_job(self, manager, mock_repository):
        """Test starting a job."""
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )

        job = await manager.create_job(file_ids=["file1"], language_pair=language_pair)
        mock_repository.get_job.return_value = job

        started = await manager.start_job(job.id)

        assert started is True
        # The job should have been updated with PROCESSING status
        mock_repository.create_job.assert_called()  # save_job calls create_job

    @pytest.mark.asyncio
    async def test_start_already_started_job(self, manager, mock_repository):
        """Test that starting an already started job returns False."""
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )

        job = await manager.create_job(file_ids=["file1"], language_pair=language_pair)
        job.status = JobStatus.PROCESSING
        mock_repository.get_job.return_value = job

        started_again = await manager.start_job(job.id)

        assert started_again is False

    @pytest.mark.asyncio
    async def test_update_file_progress(self, manager, mock_repository):
        """Test updating file progress through the manager."""
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )

        job = await manager.create_job(file_ids=["file1"], language_pair=language_pair)
        job.mark_file_processing("test.xlsx", cells_total=100)
        mock_repository.get_job.return_value = job
        mock_repository.update_job.return_value = job

        await manager.update_file_progress(job.id, "test.xlsx", cells_translated=75)

        mock_repository.update_job.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_job(self, manager, mock_repository):
        """Test cancelling a job."""
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )

        job = await manager.create_job(file_ids=["file1"], language_pair=language_pair)
        job.status = JobStatus.PROCESSING
        mock_repository.get_job.return_value = job

        cancelled = await manager.cancel_job(job.id)

        assert cancelled is True

    @pytest.mark.asyncio
    async def test_get_active_jobs(self, manager, mock_repository):
        """Test getting active jobs."""
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )

        job1 = await manager.create_job(file_ids=["file1"], language_pair=language_pair)
        job2 = await manager.create_job(file_ids=["file2"], language_pair=language_pair)
        job3 = await manager.create_job(file_ids=["file3"], language_pair=language_pair)

        job2.status = JobStatus.PROCESSING
        job3.status = JobStatus.COMPLETED

        mock_repository.list_jobs.return_value = ([job1, job2, job3], None)

        active_jobs = await manager.get_active_jobs()

        assert len(active_jobs) == 2
        active_ids = [job.id for job in active_jobs]
        assert job1.id in active_ids
        assert job2.id in active_ids
        assert job3.id not in active_ids

    @pytest.mark.asyncio
    async def test_get_completed_jobs(self, manager, mock_repository):
        """Test getting completed jobs."""
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )

        job1 = await manager.create_job(file_ids=["file1"], language_pair=language_pair)
        job2 = await manager.create_job(file_ids=["file2"], language_pair=language_pair)
        job3 = await manager.create_job(file_ids=["file3"], language_pair=language_pair)

        job1.status = JobStatus.COMPLETED
        job2.status = JobStatus.FAILED
        # job3 remains PENDING

        mock_repository.list_jobs.return_value = ([job1, job2, job3], None)

        completed_jobs = await manager.get_completed_jobs()

        assert len(completed_jobs) == 2
        completed_ids = [job.id for job in completed_jobs]
        assert job1.id in completed_ids
        assert job2.id in completed_ids
        assert job3.id not in completed_ids
