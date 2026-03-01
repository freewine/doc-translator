"""
DynamoDB-backed storage for translation jobs via JobRepository.
"""
from datetime import datetime
from typing import List, Optional, Tuple

from ..models import TranslationJob
from ..models.job import JobStatus
from .job_repository import JobRepository


class JobStore:
    """
    Storage for translation jobs backed by DynamoDB via JobRepository.

    This class provides a facade over JobRepository with user context management.
    All operations require a user context to be set via set_user_context().

    Usage:
        store = JobStore()
        store.set_user_context("user-123")
        await store.save_job(job)
        job = await store.get_job("job-456")
    """

    def __init__(self, repository: Optional[JobRepository] = None):
        """
        Initialize the job store.

        Args:
            repository: Optional JobRepository instance. If not provided, a default
                       one will be created.
        """
        self._repository = repository or JobRepository()
        self._user_id: Optional[str] = None

    def set_user_context(self, user_id: str) -> None:
        """
        Set the current user context for all operations.

        Args:
            user_id: The user ID to use for job operations.
        """
        self._user_id = user_id

    def _require_user_context(self) -> str:
        """
        Get the current user ID, raising ValueError if not set.

        Returns:
            The current user ID.

        Raises:
            ValueError: If user context has not been set.
        """
        if self._user_id is None:
            raise ValueError(
                "User context not set. Call set_user_context() before performing "
                "job operations."
            )
        return self._user_id

    async def save_job(self, job: TranslationJob) -> None:
        """
        Save a new job to the store.

        Args:
            job: The translation job to save.

        Raises:
            ValueError: If user context is not set.
        """
        user_id = self._require_user_context()
        await self._repository.create_job(job, user_id)

    async def get_job(self, job_id: str) -> Optional[TranslationJob]:
        """
        Retrieve a job by its ID.

        Args:
            job_id: The unique identifier of the job.

        Returns:
            The translation job if found, None otherwise.

        Raises:
            ValueError: If user context is not set.
        """
        user_id = self._require_user_context()
        return await self._repository.get_job(user_id, job_id)

    async def update_job(self, job: TranslationJob) -> None:
        """
        Update an existing job in the store.

        Args:
            job: The translation job with updated data.

        Raises:
            ValueError: If user context is not set.
            JobNotFoundError: If the job doesn't exist.
        """
        user_id = self._require_user_context()
        await self._repository.update_job(job, user_id)

    async def list_jobs(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
        status_filter: Optional[JobStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[List[TranslationJob], Optional[str]]:
        """
        List jobs for the current user with optional filtering and pagination.

        Args:
            limit: Maximum number of jobs to return (default 50).
            cursor: Pagination cursor from previous query.
            status_filter: Optional status to filter by.
            date_from: Optional start date for filtering.
            date_to: Optional end date for filtering.

        Returns:
            Tuple of (list of jobs, next cursor or None).

        Raises:
            ValueError: If user context is not set.
        """
        user_id = self._require_user_context()
        return await self._repository.list_jobs(
            user_id,
            status=status_filter,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            cursor=cursor,
        )

    async def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from the store.

        Args:
            job_id: The unique identifier of the job to delete.

        Returns:
            True if the job was deleted, False if it didn't exist.

        Raises:
            ValueError: If user context is not set.
        """
        user_id = self._require_user_context()
        return await self._repository.delete_job(user_id, job_id)

    async def clear(self) -> None:
        """
        Clear all jobs from the store.

        Raises:
            NotImplementedError: This operation is not supported with DynamoDB backend.
        """
        raise NotImplementedError(
            "clear() is not supported with DynamoDB backend. "
            "Use delete_job() to remove individual jobs."
        )

    # =========================================================================
    # Progress Tracking Methods
    # =========================================================================

    async def update_job_progress(
        self,
        job_id: str,
        filename: str,
        cells_translated: int,
        worksheets_completed: int = 0
    ) -> None:
        """
        Update progress for a specific file in a job.

        Args:
            job_id: The unique identifier of the job.
            filename: Name of the file being processed.
            cells_translated: Number of cells translated so far.
            worksheets_completed: Number of worksheets completed.
        """
        user_id = self._require_user_context()
        job = await self._repository.get_job(user_id, job_id)
        if job:
            job.update_file_progress(filename, cells_translated, worksheets_completed)
            await self._repository.update_job(job, user_id)

    async def mark_file_processing(
        self,
        job_id: str,
        filename: str,
        cells_total: int = 0,
        worksheets_total: int = 0
    ) -> None:
        """
        Mark a file as currently being processed.

        Args:
            job_id: The unique identifier of the job.
            filename: Name of the file being processed.
            cells_total: Total number of cells to translate.
            worksheets_total: Total number of worksheets.
        """
        user_id = self._require_user_context()
        job = await self._repository.get_job(user_id, job_id)
        if job:
            job.mark_file_processing(filename, cells_total, worksheets_total)
            await self._repository.update_job(job, user_id)

    async def mark_file_completed(
        self,
        job_id: str,
        filename: str,
        output_filename: Optional[str] = None,
        cells_translated: int = 0
    ) -> None:
        """
        Mark a file as successfully completed.

        Args:
            job_id: The unique identifier of the job.
            filename: Name of the completed file.
            output_filename: Name of the output file (with language suffix).
            cells_translated: Number of cells translated.
        """
        user_id = self._require_user_context()
        job = await self._repository.get_job(user_id, job_id)
        if job:
            job.mark_file_completed(filename, output_filename, cells_translated)
            await self._repository.update_job(job, user_id)

    async def mark_file_failed(
        self,
        job_id: str,
        filename: str,
        error: str,
        error_type: str = "ProcessingError"
    ) -> None:
        """
        Mark a file as failed.

        Args:
            job_id: The unique identifier of the job.
            filename: Name of the failed file.
            error: Error message.
            error_type: Type of error that occurred.
        """
        user_id = self._require_user_context()
        job = await self._repository.get_job(user_id, job_id)
        if job:
            job.mark_file_failed(filename, error, error_type)
            await self._repository.update_job(job, user_id)
