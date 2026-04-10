"""
Job-related data models for the translation system.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4


def sync_legacy_cell_fields(
    segments_total: int,
    segments_translated: int,
    cells_total: int,
    cells_translated: int
) -> tuple[int, int, int, int]:
    """
    Synchronize legacy cell fields with segment fields for backward compatibility.

    Args:
        segments_total: Total segments count
        segments_translated: Translated segments count
        cells_total: Legacy total cells count
        cells_translated: Legacy translated cells count

    Returns:
        Tuple of (segments_total, segments_translated, cells_total, cells_translated)
        with synchronized values
    """
    if segments_total > 0 and cells_total == 0:
        cells_total = segments_total
    if segments_translated > 0 and cells_translated == 0:
        cells_translated = segments_translated
    if cells_total > 0 and segments_total == 0:
        segments_total = cells_total
    if cells_translated > 0 and segments_translated == 0:
        segments_translated = cells_translated

    return segments_total, segments_translated, cells_total, cells_translated


class JobStatus(Enum):
    """Status of a translation job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"


class DocumentType(str, Enum):
    """Enumeration of supported document types."""
    EXCEL = "excel"
    WORD = "word"
    POWERPOINT = "powerpoint"
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"


@dataclass
class FileProgress:
    """Progress information for a single file in a translation job."""
    filename: str
    progress: float  # 0.0 to 1.0
    segments_total: int
    segments_translated: int
    document_type: Optional[DocumentType] = None
    # Legacy fields for backward compatibility with Excel-specific code
    cells_total: int = 0
    cells_translated: int = 0
    worksheets_completed: int = 0
    worksheets_total: int = 0

    def __post_init__(self):
        """Sync legacy cell fields with segment fields for backward compatibility."""
        (
            self.segments_total,
            self.segments_translated,
            self.cells_total,
            self.cells_translated
        ) = sync_legacy_cell_fields(
            self.segments_total,
            self.segments_translated,
            self.cells_total,
            self.cells_translated
        )


@dataclass
class CompletedFile:
    """Information about a completed file in a translation job."""
    original_filename: str
    output_filename: str
    segments_translated: int
    document_type: Optional[DocumentType] = None
    # Legacy field for backward compatibility
    cells_translated: int = 0
    segments_failed: int = 0
    translation_warning: Optional[str] = None

    def __post_init__(self):
        """Sync legacy cell field with segment field for backward compatibility."""
        _, self.segments_translated, _, self.cells_translated = sync_legacy_cell_fields(
            0, self.segments_translated, 0, self.cells_translated
        )


@dataclass
class FileError:
    """Error information for a failed file in a translation job."""
    filename: str
    error: str
    error_type: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LanguagePair:
    """Language pair configuration for translation.
    
    Language detection is handled by the model's system prompt.
    """
    id: str
    source_language: str
    target_language: str
    source_language_code: str
    target_language_code: str


@dataclass
class TranslationJob:
    """
    Represents a translation job with status tracking and progress information.
    
    Attributes:
        id: Unique identifier for the job
        status: Current status of the job
        progress: Overall progress (0.0 to 1.0)
        files_total: Total number of files in the job
        files_completed: Number of files successfully completed
        files_processing: List of files currently being processed
        files_failed: List of files that failed processing
        created_at: Timestamp when the job was created
        completed_at: Timestamp when the job completed (None if not completed)
        language_pair: Language pair used for translation
        file_ids: List of file IDs to be processed
        output_mode: Output mode for translations ("replace", "append", "prepend", "interleave", "interleave_reverse")
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    files_total: int = 0
    files_completed: int = 0
    files_processing: List[FileProgress] = field(default_factory=list)
    files_failed: List[FileError] = field(default_factory=list)
    completed_files: List[CompletedFile] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    language_pair: Optional[LanguagePair] = None
    file_ids: List[str] = field(default_factory=list)
    output_mode: str = "replace"
    
    def update_progress(self) -> None:
        """
        Calculate and update overall job progress based on file progress.
        Progress is calculated as: (completed + failed + sum of processing progress) / total
        """
        if self.files_total == 0:
            self.progress = 0.0
            return
        
        # Count completed and failed files as 1.0 progress each
        completed_progress = self.files_completed + len(self.files_failed)
        
        # Sum up progress of files currently being processed
        processing_progress = sum(fp.progress for fp in self.files_processing)
        
        # Calculate overall progress
        self.progress = (completed_progress + processing_progress) / self.files_total
        
        # Ensure progress is between 0.0 and 1.0
        self.progress = max(0.0, min(1.0, self.progress))
    
    def mark_file_processing(
        self,
        filename: str,
        segments_total: int = 0,
        worksheets_total: int = 0,
        document_type: Optional[DocumentType] = None,
        cells_total: int = 0  # Legacy parameter for backward compatibility
    ) -> None:
        """
        Mark a file as currently being processed.
        
        Args:
            filename: Name of the file being processed
            segments_total: Total number of segments to translate
            worksheets_total: Total number of worksheets/pages in the file
            document_type: Type of document being processed
            cells_total: Legacy parameter (use segments_total instead)
        """
        # Remove from processing list if already there
        self.files_processing = [fp for fp in self.files_processing if fp.filename != filename]
        
        # Support legacy cells_total parameter
        actual_segments_total = segments_total if segments_total > 0 else cells_total
        
        # Add new progress entry
        file_progress = FileProgress(
            filename=filename,
            progress=0.0,
            segments_total=actual_segments_total,
            segments_translated=0,
            document_type=document_type,
            worksheets_completed=0,
            worksheets_total=worksheets_total
        )
        self.files_processing.append(file_progress)
        self.update_progress()
    
    def update_file_progress(
        self,
        filename: str,
        segments_translated: int = 0,
        worksheets_completed: int = 0,
        cells_translated: int = 0  # Legacy parameter for backward compatibility
    ) -> None:
        """
        Update progress for a file currently being processed.
        
        Args:
            filename: Name of the file
            segments_translated: Number of segments translated so far
            worksheets_completed: Number of worksheets/pages completed
            cells_translated: Legacy parameter (use segments_translated instead)
        """
        # Support legacy cells_translated parameter
        actual_segments_translated = segments_translated if segments_translated > 0 else cells_translated
        
        for file_progress in self.files_processing:
            if file_progress.filename == filename:
                file_progress.segments_translated = actual_segments_translated
                # Sync legacy field
                file_progress.cells_translated = actual_segments_translated
                file_progress.worksheets_completed = worksheets_completed
                
                # Calculate file progress
                if file_progress.segments_total > 0:
                    file_progress.progress = file_progress.segments_translated / file_progress.segments_total
                else:
                    file_progress.progress = 0.0
                
                break
        
        self.update_progress()
    
    def mark_file_completed(
        self,
        filename: str,
        output_filename: Optional[str] = None,
        segments_translated: int = 0,
        document_type: Optional[DocumentType] = None,
        cells_translated: int = 0,  # Legacy parameter for backward compatibility
        segments_failed: int = 0,
        translation_warning: Optional[str] = None
    ) -> None:
        """
        Mark a file as successfully completed.

        Args:
            filename: Name of the original file
            output_filename: Name of the output file (with language suffix)
            segments_translated: Number of segments translated
            document_type: Type of document that was processed
            cells_translated: Legacy parameter (use segments_translated instead)
            segments_failed: Number of segments that failed translation (fell back to original)
            translation_warning: Warning message about translation failures
        """
        # Support legacy cells_translated parameter
        actual_segments_translated = segments_translated if segments_translated > 0 else cells_translated

        # Try to get document type from processing list if not provided
        if document_type is None:
            for fp in self.files_processing:
                if fp.filename == filename and fp.document_type:
                    document_type = fp.document_type
                    break

        # Remove from processing list
        self.files_processing = [fp for fp in self.files_processing if fp.filename != filename]

        # Add to completed files list
        if output_filename:
            completed_file = CompletedFile(
                original_filename=filename,
                output_filename=output_filename,
                segments_translated=actual_segments_translated,
                document_type=document_type,
                segments_failed=segments_failed,
                translation_warning=translation_warning
            )
            self.completed_files.append(completed_file)
        
        # Increment completed count
        self.files_completed += 1
        
        # Update overall progress
        self.update_progress()
        
        # Check if job is complete
        self._check_job_completion()
    
    def mark_file_failed(self, filename: str, error: str, error_type: str = "ProcessingError") -> None:
        """
        Mark a file as failed.
        
        Args:
            filename: Name of the failed file
            error: Error message
            error_type: Type of error that occurred
        """
        # Remove from processing list
        self.files_processing = [fp for fp in self.files_processing if fp.filename != filename]
        
        # Add to failed list
        file_error = FileError(
            filename=filename,
            error=error,
            error_type=error_type,
            timestamp=datetime.now()
        )
        self.files_failed.append(file_error)
        
        # Update overall progress
        self.update_progress()
        
        # Check if job is complete
        self._check_job_completion()
    
    def _check_job_completion(self) -> None:
        """
        Check if the job is complete and update status accordingly.
        A job is complete when all files are either completed or failed.
        """
        total_processed = self.files_completed + len(self.files_failed)
        
        if total_processed >= self.files_total and self.files_total > 0:
            # All files processed
            if len(self.files_failed) == 0:
                # All succeeded
                self.status = JobStatus.COMPLETED
            elif self.files_completed == 0:
                # All failed
                self.status = JobStatus.FAILED
            else:
                # Some succeeded, some failed
                self.status = JobStatus.PARTIAL_SUCCESS
            
            self.completed_at = datetime.now()
            self.progress = 1.0
