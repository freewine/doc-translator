"""
Translation Orchestrator Module

Coordinates all components for translation job processing with concurrent execution,
error isolation, and real-time progress tracking.

Supports multiple document formats through the DocumentProcessorFactory:
- Excel (.xlsx)
- Word (.docx)
- PowerPoint (.pptx)
- PDF (.pdf)

Supports term pair injection for consistent terminology translation via ThesaurusService.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, TYPE_CHECKING
from dataclasses import dataclass, field

from ..models.job import (
    TranslationJob,
    JobStatus,
    FileProgress,
    FileError,
    LanguagePair,
    DocumentType,
    sync_legacy_cell_fields
)
from .document_processor import DocumentProcessorFactory, DocumentProcessor, TextSegment
from .excel_processor import ExcelProcessor
from .excel_document_processor import ExcelDocumentProcessor
from .word_processor import WordProcessor
from .powerpoint_processor import PowerPointProcessor
from .pdf_processor import PDFProcessor
from .text_processor import TextProcessor
from .markdown_processor import MarkdownProcessor
from .translation_service import TranslationService
from .concurrent_executor import ConcurrentExecutor, ProcessingResult

if TYPE_CHECKING:
    from .thesaurus_service import ThesaurusService
    from ..models.thesaurus import TermPair
    from ..storage.s3_file_storage import S3FileStorage
    from ..storage.job_store import JobStore


@dataclass
class FileProcessingResult:
    """Result of processing a single file."""
    filename: str
    success: bool
    output_path: Optional[Path] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    segments_translated: int = 0
    segments_total: int = 0
    document_type: Optional[DocumentType] = None
    # S3 storage key for the output file (if uploaded to S3)
    s3_key: Optional[str] = None
    # Legacy fields for backward compatibility
    cells_translated: int = 0
    cells_total: int = 0

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


class TranslationOrchestrator:
    """
    Orchestrates translation jobs by coordinating document processing, translation,
    and concurrent execution with comprehensive error handling and progress tracking.
    
    Supports multiple document formats through the DocumentProcessorFactory:
    - Excel (.xlsx)
    - Word (.docx)
    - PowerPoint (.pptx)
    - PDF (.pdf)
    """
    
    def __init__(
        self,
        excel_processor: ExcelProcessor,
        translation_service: TranslationService,
        concurrent_executor: ConcurrentExecutor,
        output_dir: Path,
        logger: Optional[logging.Logger] = None,
        processor_factory: Optional[DocumentProcessorFactory] = None,
        thesaurus_service: Optional["ThesaurusService"] = None,
        s3_file_storage: Optional["S3FileStorage"] = None,
        job_store: Optional["JobStore"] = None
    ):
        """
        Initialize the translation orchestrator.

        Args:
            excel_processor: ExcelProcessor instance for Excel operations (legacy)
            translation_service: TranslationService instance for translations
            concurrent_executor: ConcurrentExecutor for concurrent processing
            output_dir: Directory to save translated files (used for intermediate processing)
            logger: Logger instance for logging operations
            processor_factory: Optional DocumentProcessorFactory for multi-format support
            thesaurus_service: Optional ThesaurusService for term pair retrieval
            s3_file_storage: Optional S3FileStorage for uploading output files to S3
            job_store: Optional JobStore for persisting job progress to DynamoDB
        """
        self.excel_processor = excel_processor
        self.translation_service = translation_service
        self.executor = concurrent_executor
        self.output_dir = output_dir
        self.logger = logger or logging.getLogger(__name__)
        self.thesaurus_service = thesaurus_service
        self.s3_file_storage = s3_file_storage
        self.job_store = job_store

        # Initialize document processor factory with all supported processors
        self.processor_factory = processor_factory or self._create_default_factory()

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("TranslationOrchestrator initialized with multi-format support")

    async def _persist_job(self, job: TranslationJob) -> None:
        """
        Persist job state to storage if job_store is configured.

        Args:
            job: The translation job to persist.
        """
        if self.job_store is not None:
            try:
                await self.job_store.update_job(job)
            except Exception as e:
                self.logger.warning(f"Failed to persist job state: {e}")

    def _create_default_factory(self) -> DocumentProcessorFactory:
        """Create and configure the default document processor factory."""
        factory = DocumentProcessorFactory()
        
        # Register all supported document processors
        factory.register(ExcelDocumentProcessor(logger=self.logger))
        factory.register(WordProcessor(logger=self.logger))
        factory.register(PowerPointProcessor(logger=self.logger))
        factory.register(PDFProcessor(logger=self.logger))
        factory.register(TextProcessor(logger=self.logger))
        factory.register(MarkdownProcessor(logger=self.logger))

        self.logger.info(
            f"Registered document processors for: {factory.get_supported_extensions()}"
        )
        
        return factory
    
    async def process_job(
        self,
        job: TranslationJob,
        file_paths: List[tuple[Path, str]],
        language_pair: LanguagePair,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        catalog_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> None:
        """
        Process a translation job with concurrent file processing.

        Processes up to 10 files concurrently. Updates job status and progress
        in real-time. Implements error isolation - continues processing remaining
        files even if individual files fail.

        If s3_file_storage is configured and user_id is provided, output files
        will be uploaded to S3 after local processing.

        Args:
            job: TranslationJob to process
            file_paths: List of tuples (file_path, original_filename) to translate
            language_pair: LanguagePair for translation
            progress_callback: Optional callback for progress updates
            catalog_ids: Optional list of catalog IDs for term pair retrieval
            user_id: Optional user ID for S3 storage (required if using S3)
        """
        self.logger.info(
            f"Starting job {job.id} with {len(file_paths)} files "
            f"({language_pair.source_language} → {language_pair.target_language})"
        )
        
        # Update job status to processing
        job.status = JobStatus.PROCESSING
        job.files_total = len(file_paths)
        job.language_pair = language_pair

        # Persist initial processing state
        await self._persist_job(job)

        # Retrieve term pairs for translation if catalogs are selected
        term_pairs: Optional[List["TermPair"]] = None
        if catalog_ids and self.thesaurus_service:
            try:
                term_pairs = await self.thesaurus_service.get_terms_for_translation(
                    language_pair_id=language_pair.id,
                    catalog_ids=catalog_ids
                )
                self.logger.info(
                    f"Retrieved {len(term_pairs)} term pairs for translation from {len(catalog_ids)} catalogs"
                )
            except Exception as e:
                self.logger.warning(f"Failed to retrieve term pairs: {e}. Proceeding without term injection.")
                term_pairs = None
        
        # Notify progress callback of job start
        if progress_callback:
            try:
                await progress_callback("job_started", {
                    "job_id": job.id,
                    "files_total": job.files_total,
                    "language_pair": {
                        "source": language_pair.source_language,
                        "target": language_pair.target_language
                    },
                    "term_pairs_count": len(term_pairs) if term_pairs else 0
                })
            except Exception as e:
                self.logger.warning(f"Progress callback error: {e}")
        
        # Process files concurrently with error isolation
        async def _process_file_wrapper(file_info: tuple[Path, str], callback: Optional[Callable]) -> FileProcessingResult:
            """Wrapper to process a single file with error isolation."""
            file_path, original_filename = file_info
            try:
                return await self.process_file(
                    file_path, original_filename, language_pair, job, callback, term_pairs, user_id
                )
            except Exception as e:
                # Error isolation: log error and continue with other files
                self.logger.error(
                    f"Error processing file {original_filename}: {type(e).__name__} - {str(e)}",
                    exc_info=True
                )
                return FileProcessingResult(
                    filename=original_filename,
                    success=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        # Process files concurrently (up to 10 at a time)
        results = await self.executor.process_files_concurrently(
            items=file_paths,
            process_func=_process_file_wrapper,
            progress_callback=progress_callback
        )
        
        # Aggregate results and update job status
        for result in results:
            if isinstance(result, ProcessingResult):
                file_result = result.result
                if isinstance(file_result, FileProcessingResult):
                    if file_result.success:
                        # Extract just the filename from the output path
                        output_filename = file_result.output_path.name if file_result.output_path else None
                        job.mark_file_completed(
                            file_result.filename,
                            output_filename=output_filename,
                            segments_translated=file_result.segments_translated,
                            document_type=file_result.document_type
                        )
                        await self._persist_job(job)
                        self.logger.info(
                            f"File completed: {file_result.filename} -> {output_filename} "
                            f"({file_result.segments_translated}/{file_result.segments_total} segments)"
                        )
                    else:
                        job.mark_file_failed(
                            file_result.filename,
                            file_result.error or "Unknown error",
                            file_result.error_type or "ProcessingError"
                        )
                        await self._persist_job(job)
                        self.logger.error(
                            f"File failed: {file_result.filename} - {file_result.error}"
                        )
        
        # Log final job status
        self.logger.info(
            f"Job {job.id} completed: {job.files_completed} successful, "
            f"{len(job.files_failed)} failed, status: {job.status.value}"
        )
        
        # Notify progress callback of job completion
        if progress_callback:
            try:
                await progress_callback("job_completed", {
                    "job_id": job.id,
                    "status": job.status.value,
                    "files_completed": job.files_completed,
                    "files_failed": len(job.files_failed),
                    "progress": job.progress
                })
            except Exception as e:
                self.logger.warning(f"Progress callback error: {e}")
    
    async def process_file(
        self,
        file_path: Path,
        original_filename: str,
        language_pair: LanguagePair,
        job: TranslationJob,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        term_pairs: Optional[List["TermPair"]] = None,
        user_id: Optional[str] = None
    ) -> FileProcessingResult:
        """
        Process a single file using the appropriate document processor.

        Selects the correct processor based on file extension and processes
        the document using the unified DocumentProcessor interface.

        If s3_file_storage is configured and user_id is provided, the output
        file will be uploaded to S3 after local processing.

        Args:
            file_path: Path to the document file to translate
            original_filename: Original filename (not the UUID-based stored name)
            language_pair: LanguagePair for translation
            job: TranslationJob for progress tracking
            progress_callback: Optional callback for progress updates
            term_pairs: Optional list of TermPair objects for terminology injection
            user_id: Optional user ID for S3 storage

        Returns:
            FileProcessingResult with processing outcome (includes s3_key if uploaded)
        """
        self.logger.info(f"Processing file: {original_filename}")
        
        # Determine file extension from original filename
        original_path = Path(original_filename)
        
        # Get appropriate processor from factory
        processor = self.processor_factory.get_processor(original_path)
        
        if processor is None:
            # Unsupported file format
            supported = self.processor_factory.get_supported_extensions()
            error_msg = f"Unsupported file format: {original_path.suffix}. Supported formats: {', '.join(supported)}"
            self.logger.error(error_msg)
            return FileProcessingResult(
                filename=original_filename,
                success=False,
                error=error_msg,
                error_type="UnsupportedFormatError"
            )
        
        document_type = processor.document_type
        self.logger.info(f"Using {document_type.value} processor for {original_filename}")
        
        try:
            # Validate file before processing
            is_valid, validation_error = await processor.validate_file(file_path)
            if not is_valid:
                self.logger.error(f"File validation failed: {validation_error}")
                return FileProcessingResult(
                    filename=original_filename,
                    success=False,
                    error=validation_error,
                    error_type="ValidationError",
                    document_type=document_type
                )
            
            # Extract text segments from document
            segments = await processor.extract_text(file_path)
            total_segments = len(segments)
            
            if total_segments == 0:
                self.logger.warning(f"No translatable text found in {original_filename}")
                # Still create output file even if no text to translate
                output_filename = processor.generate_output_filename(
                    original_path, language_pair.target_language_code
                )
                output_path = self.output_dir / output_filename

                # Copy original file as output (no translation needed)
                import shutil
                await asyncio.to_thread(shutil.copy2, file_path, output_path)

                # Upload to S3 if storage is configured and user_id is provided
                s3_key: Optional[str] = None
                if self.s3_file_storage is not None and user_id is not None:
                    try:
                        output_content = await asyncio.to_thread(output_path.read_bytes)
                        s3_key = await self.s3_file_storage.save_output(
                            user_id=user_id,
                            job_id=job.id,
                            filename=output_filename,
                            content=output_content
                        )
                        self.logger.info(f"Uploaded output to S3: {s3_key}")
                    except Exception as e:
                        self.logger.error(
                            f"Failed to upload output to S3: {type(e).__name__} - {str(e)}",
                            exc_info=True
                        )
                        # Mark file as failed with S3UploadError
                        return FileProcessingResult(
                            filename=original_filename,
                            success=False,
                            error=f"Failed to upload output to S3: {str(e)}",
                            error_type="S3UploadError",
                            document_type=document_type
                        )

                return FileProcessingResult(
                    filename=original_filename,
                    success=True,
                    output_path=output_path,
                    segments_translated=0,
                    segments_total=0,
                    document_type=document_type,
                    s3_key=s3_key
                )
            
            # Mark file as processing in job
            job.mark_file_processing(
                filename=original_filename,
                segments_total=total_segments,
                document_type=document_type
            )
            await self._persist_job(job)

            # Notify progress callback
            if progress_callback:
                try:
                    await progress_callback("file_started", {
                        "filename": original_filename,
                        "segments_total": total_segments,
                        "document_type": document_type.value
                    })
                except Exception as e:
                    self.logger.warning(f"Progress callback error: {e}")
            
            # Extract text values for translation
            text_values = [segment.text for segment in segments]
            
            # Batch translate with incremental progress updates
            self.logger.info(f"Translating {total_segments} segments...")
            batch_size = self.translation_service.batch_size
            combined_translations = []
            segments_translated = 0
            
            # Process in batches with progress updates
            for i in range(0, len(text_values), batch_size):
                batch = text_values[i:i + batch_size]
                
                # Translate this batch with term pairs for consistent terminology
                batch_translations = await self.translation_service.batch_translate_async(
                    batch,
                    language_pair,
                    term_pairs
                )
                combined_translations.extend(batch_translations)
                
                # Update progress after each batch
                segments_translated += len(batch)
                job.update_file_progress(
                    filename=original_filename,
                    segments_translated=segments_translated
                )
                await self._persist_job(job)

                # Notify progress callback
                if progress_callback:
                    try:
                        current_progress = segments_translated / total_segments if total_segments > 0 else 0
                        await progress_callback("file_progress", {
                            "filename": original_filename,
                            "segments_translated": segments_translated,
                            "segments_total": total_segments,
                            "progress": current_progress
                        })
                    except Exception as e:
                        self.logger.warning(f"Progress callback error: {e}")
                
                self.logger.debug(f"Batch {i // batch_size + 1} completed: {segments_translated}/{total_segments} segments")
            
            # Generate output path
            output_filename = processor.generate_output_filename(
                original_path, language_pair.target_language_code
            )
            output_path = self.output_dir / output_filename
            
            # Write translated document
            self.logger.info(f"Writing translated document to {output_path}...")
            write_success = await processor.write_translated(
                file_path=file_path,
                segments=segments,
                translations=combined_translations,
                output_path=output_path,
                auto_append=job.auto_append,
                interleaved_mode=job.interleaved_mode
            )
            
            if not write_success:
                raise RuntimeError(f"Failed to write translated document: {original_filename}")

            # Upload to S3 if storage is configured and user_id is provided
            s3_key: Optional[str] = None
            if self.s3_file_storage is not None and user_id is not None:
                try:
                    # Read the local output file
                    output_content = await asyncio.to_thread(output_path.read_bytes)
                    # Upload to S3
                    s3_key = await self.s3_file_storage.save_output(
                        user_id=user_id,
                        job_id=job.id,
                        filename=output_filename,
                        content=output_content
                    )
                    self.logger.info(
                        f"Uploaded output to S3: {s3_key}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to upload output to S3: {type(e).__name__} - {str(e)}",
                        exc_info=True
                    )
                    # Mark file as failed with S3UploadError
                    return FileProcessingResult(
                        filename=original_filename,
                        success=False,
                        error=f"Failed to upload output to S3: {str(e)}",
                        error_type="S3UploadError",
                        document_type=document_type,
                        segments_translated=total_segments,
                        segments_total=total_segments
                    )

            self.logger.info(
                f"File processed successfully: {original_filename} "
                f"({total_segments} segments translated)"
            )

            return FileProcessingResult(
                filename=original_filename,
                success=True,
                output_path=output_path,
                segments_translated=total_segments,
                segments_total=total_segments,
                document_type=document_type,
                s3_key=s3_key
            )
        
        except Exception as e:
            # Comprehensive error logging
            self.logger.error(
                f"Failed to process file {original_filename}: {type(e).__name__} - {str(e)}",
                exc_info=True
            )
            
            return FileProcessingResult(
                filename=original_filename,
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                document_type=document_type
            )
    
