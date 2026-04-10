"""
Job management service for coordinating translation jobs.
"""
import asyncio
from typing import List, Optional

from ..models import JobStatus, LanguagePair, TranslationJob
from ..storage import JobStore


class JobManager:
    """
    Manages the lifecycle of translation jobs.
    
    This class provides high-level operations for creating, tracking, and managing
    translation jobs. It coordinates with the JobStore for persistence and provides
    methods for job lifecycle management.
    """
    
    def __init__(self, job_store: Optional[JobStore] = None):
        """
        Initialize the job manager.
        
        Args:
            job_store: Optional JobStore instance. If not provided, creates a new one.
        """
        self.job_store = job_store or JobStore()
    
    async def create_job(
        self,
        file_ids: List[str],
        language_pair: LanguagePair,
        output_mode: str = "replace"
    ) -> TranslationJob:
        """
        Create a new translation job.

        Args:
            file_ids: List of file IDs to be processed
            language_pair: Language pair to use for translation
            output_mode: One of "replace", "append", "prepend", "interleave", "interleave_reverse" (default: "replace")

        Returns:
            The newly created translation job
        """
        job = TranslationJob(
            status=JobStatus.PENDING,
            files_total=len(file_ids),
            language_pair=language_pair,
            file_ids=file_ids,
            output_mode=output_mode
        )
        
        await self.job_store.save_job(job)
        return job
    
    async def get_job(self, job_id: str) -> Optional[TranslationJob]:
        """
        Retrieve a job by its ID.
        
        Args:
            job_id: The unique identifier of the job
            
        Returns:
            The translation job if found, None otherwise
        """
        return await self.job_store.get_job(job_id)
    
    async def list_jobs(self) -> List[TranslationJob]:
        """
        List all jobs.

        Returns:
            A list of all translation jobs, sorted by creation time (newest first)
        """
        jobs, _ = await self.job_store.list_jobs()
        return jobs
    
    async def start_job(self, job_id: str) -> bool:
        """
        Mark a job as started (status changes to PROCESSING).
        
        Args:
            job_id: The unique identifier of the job
            
        Returns:
            True if the job was started, False if not found or already started
        """
        job = await self.job_store.get_job(job_id)
        if job and job.status == JobStatus.PENDING:
            job.status = JobStatus.PROCESSING
            await self.job_store.save_job(job)
            return True
        return False
    
    async def update_file_progress(
        self,
        job_id: str,
        filename: str,
        cells_translated: int,
        worksheets_completed: int = 0
    ) -> None:
        """
        Update progress for a specific file in a job.
        
        Args:
            job_id: The unique identifier of the job
            filename: Name of the file being processed
            cells_translated: Number of cells translated so far
            worksheets_completed: Number of worksheets completed
        """
        await self.job_store.update_job_progress(
            job_id,
            filename,
            cells_translated,
            worksheets_completed
        )
    
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
            job_id: The unique identifier of the job
            filename: Name of the file being processed
            cells_total: Total number of cells to translate
            worksheets_total: Total number of worksheets
        """
        await self.job_store.mark_file_processing(
            job_id,
            filename,
            cells_total,
            worksheets_total
        )
    
    async def mark_file_completed(self, job_id: str, filename: str, output_filename: Optional[str] = None, cells_translated: int = 0) -> None:
        """
        Mark a file as successfully completed.
        
        Args:
            job_id: The unique identifier of the job
            filename: Name of the completed file
            output_filename: Name of the output file (with language suffix)
            cells_translated: Number of cells translated
        """
        await self.job_store.mark_file_completed(job_id, filename, output_filename, cells_translated)
    
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
            job_id: The unique identifier of the job
            filename: Name of the failed file
            error: Error message
            error_type: Type of error that occurred
        """
        await self.job_store.mark_file_failed(job_id, filename, error, error_type)
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job (mark as failed).
        
        Args:
            job_id: The unique identifier of the job
            
        Returns:
            True if the job was cancelled, False if not found
        """
        job = await self.job_store.get_job(job_id)
        if job and job.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
            job.status = JobStatus.FAILED
            await self.job_store.save_job(job)
            return True
        return False
    
    async def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from the store.
        
        Args:
            job_id: The unique identifier of the job to delete
            
        Returns:
            True if the job was deleted, False if it didn't exist
        """
        return await self.job_store.delete_job(job_id)
    
    async def get_active_jobs(self) -> List[TranslationJob]:
        """
        Get all active jobs (pending or processing).

        Returns:
            A list of active translation jobs
        """
        all_jobs, _ = await self.job_store.list_jobs()
        return [
            job for job in all_jobs
            if job.status in [JobStatus.PENDING, JobStatus.PROCESSING]
        ]

    async def get_completed_jobs(self) -> List[TranslationJob]:
        """
        Get all completed jobs (completed, failed, or partial success).

        Returns:
            A list of completed translation jobs
        """
        all_jobs, _ = await self.job_store.list_jobs()
        return [
            job for job in all_jobs
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PARTIAL_SUCCESS]
        ]
