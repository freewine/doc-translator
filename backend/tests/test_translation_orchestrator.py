"""
Tests for TranslationOrchestrator.

Tests the orchestration of translation jobs with concurrent processing,
error isolation, and progress tracking.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from backend.src.services.translation_orchestrator import (
    TranslationOrchestrator,
    FileProcessingResult
)
from backend.src.models.job import TranslationJob, JobStatus, LanguagePair, DocumentType
from backend.src.services.excel_processor import ExcelProcessor, CellData
from backend.src.services.translation_service import TranslationService, TranslationResult
from backend.src.services.concurrent_executor import ConcurrentExecutor
from backend.src.services.document_processor import (
    DocumentProcessorFactory,
    DocumentProcessor,
    TextSegment
)


@pytest.fixture
def language_pair():
    """Create a test language pair."""
    return LanguagePair(
        id="zh-vi",
        source_language="Chinese",
        target_language="Vietnamese",
        source_language_code="zh",
        target_language_code="vi"
    )


@pytest.fixture
def mock_excel_processor():
    """Create a mock Excel processor."""
    processor = Mock(spec=ExcelProcessor)
    processor.load_workbook = AsyncMock()
    processor.iterate_cells_in_worksheet = AsyncMock()
    processor.process_worksheets_concurrently = AsyncMock()
    processor.update_cell = AsyncMock()
    processor.save_workbook = AsyncMock()
    return processor


@pytest.fixture
def mock_translation_service():
    """Create a mock translation service."""
    service = Mock(spec=TranslationService)
    service.translate_text_async = AsyncMock()
    service.batch_translate_async = AsyncMock()
    service.batch_size = 10  # Default batch size for testing
    return service


@pytest.fixture
def mock_concurrent_executor():
    """Create a mock concurrent executor."""
    executor = Mock(spec=ConcurrentExecutor)
    executor.process_files_concurrently = AsyncMock()
    executor.process_worksheets_concurrently = AsyncMock()
    return executor


@pytest.fixture
def mock_document_processor():
    """Create a mock document processor."""
    processor = Mock(spec=DocumentProcessor)
    processor.supported_extensions = ['.xlsx']
    processor.document_type = DocumentType.EXCEL
    processor.validate_file = AsyncMock(return_value=(True, None))
    processor.extract_text = AsyncMock(return_value=[])
    processor.write_translated = AsyncMock(return_value=True)
    processor.generate_output_filename = Mock(return_value="test_vi.xlsx")
    return processor


@pytest.fixture
def mock_processor_factory(mock_document_processor):
    """Create a mock document processor factory."""
    factory = Mock(spec=DocumentProcessorFactory)
    factory.get_processor = Mock(return_value=mock_document_processor)
    factory.get_supported_extensions = Mock(return_value=['.xlsx', '.docx', '.pptx', '.pdf'])
    factory.is_supported = Mock(return_value=True)
    factory.get_document_type = Mock(return_value=DocumentType.EXCEL)
    return factory


@pytest.fixture
def orchestrator(mock_excel_processor, mock_translation_service, mock_concurrent_executor, mock_processor_factory, tmp_path):
    """Create a TranslationOrchestrator instance with mocked processor factory."""
    output_dir = tmp_path / "output"
    return TranslationOrchestrator(
        excel_processor=mock_excel_processor,
        translation_service=mock_translation_service,
        concurrent_executor=mock_concurrent_executor,
        output_dir=output_dir,
        processor_factory=mock_processor_factory
    )


@pytest.mark.asyncio
async def test_orchestrator_initialization(tmp_path):
    """Test that orchestrator initializes correctly."""
    output_dir = tmp_path / "output"
    excel_processor = Mock(spec=ExcelProcessor)
    translation_service = Mock(spec=TranslationService)
    executor = Mock(spec=ConcurrentExecutor)
    
    orchestrator = TranslationOrchestrator(
        excel_processor=excel_processor,
        translation_service=translation_service,
        concurrent_executor=executor,
        output_dir=output_dir
    )
    
    assert orchestrator.excel_processor == excel_processor
    assert orchestrator.translation_service == translation_service
    assert orchestrator.executor == executor
    assert orchestrator.output_dir == output_dir
    assert output_dir.exists()


@pytest.mark.asyncio
async def test_process_file_success(orchestrator, mock_document_processor, mock_translation_service, language_pair, tmp_path):
    """Test successful file processing."""
    # Setup
    file_path = tmp_path / "test.xlsx"
    file_path.touch()
    
    job = TranslationJob(files_total=1)
    
    # Mock text segments
    segments = [
        TextSegment(id="0", text="你好", location="Sheet1!A1", metadata={}),
    ]
    
    mock_document_processor.validate_file.return_value = (True, None)
    mock_document_processor.extract_text.return_value = segments
    mock_document_processor.write_translated.return_value = True
    mock_document_processor.generate_output_filename.return_value = "test_vi.xlsx"
    
    mock_translation_service.batch_translate_async.return_value = [TranslationResult(text="Xin chào")]

    # Execute
    result = await orchestrator.process_file(file_path, "test.xlsx", language_pair, job)

    # Verify
    assert result.success is True
    assert result.filename == "test.xlsx"
    assert result.segments_translated == 1
    assert result.segments_total == 1
    assert result.segments_failed == 0
    assert result.translation_warning is None
    assert result.output_path is not None
    assert result.error is None
    assert result.document_type == DocumentType.EXCEL


@pytest.mark.asyncio
async def test_process_file_load_failure(orchestrator, mock_document_processor, language_pair, tmp_path):
    """Test file processing when file validation fails."""
    # Setup
    file_path = tmp_path / "test.xlsx"
    file_path.touch()
    
    job = TranslationJob(files_total=1)
    
    # Mock validation failure
    mock_document_processor.validate_file.return_value = (False, "Failed to open file. The file may be corrupted.")
    
    # Execute
    result = await orchestrator.process_file(file_path, "test.xlsx", language_pair, job)
    
    # Verify
    assert result.success is False
    assert result.filename == "test.xlsx"
    assert result.error is not None
    assert "corrupted" in result.error.lower()


@pytest.mark.asyncio
async def test_process_file_save_failure(orchestrator, mock_document_processor, mock_translation_service, language_pair, tmp_path):
    """Test file processing when saving fails."""
    # Setup
    file_path = tmp_path / "test.xlsx"
    file_path.touch()
    
    job = TranslationJob(files_total=1)
    
    # Mock text segments
    segments = [
        TextSegment(id="0", text="你好", location="Sheet1!A1", metadata={}),
    ]
    
    mock_document_processor.validate_file.return_value = (True, None)
    mock_document_processor.extract_text.return_value = segments
    mock_document_processor.write_translated.return_value = False  # Save fails
    mock_document_processor.generate_output_filename.return_value = "test_vi.xlsx"

    mock_translation_service.batch_translate_async.return_value = [TranslationResult(text="Xin chào")]

    # Execute
    result = await orchestrator.process_file(file_path, "test.xlsx", language_pair, job)
    
    # Verify
    assert result.success is False
    assert result.filename == "test.xlsx"
    assert result.error is not None
    assert "Failed to write" in result.error


@pytest.mark.asyncio
async def test_process_file_with_progress_callback(orchestrator, mock_document_processor, mock_translation_service, language_pair, tmp_path):
    """Test file processing with progress callbacks."""
    # Setup
    file_path = tmp_path / "test.xlsx"
    file_path.touch()
    
    job = TranslationJob(files_total=1)
    
    # Mock text segments
    segments = []
    for i in range(15):  # More than 10 to trigger progress updates
        segments.append(TextSegment(
            id=str(i),
            text=f"Text {i}",
            location=f"Sheet1!A{i+1}",
            metadata={}
        ))
    
    mock_document_processor.validate_file.return_value = (True, None)
    mock_document_processor.extract_text.return_value = segments
    mock_document_processor.write_translated.return_value = True
    mock_document_processor.generate_output_filename.return_value = "test_vi.xlsx"
    
    mock_translation_service.batch_translate_async.return_value = [TranslationResult(text="Translated")] * len(segments)
    
    # Track progress callbacks
    progress_calls = []
    
    async def progress_callback(event_type, data):
        progress_calls.append((event_type, data))
    
    # Execute
    result = await orchestrator.process_file(file_path, "test.xlsx", language_pair, job, progress_callback)
    
    # Verify
    assert result.success is True
    assert len(progress_calls) > 0
    
    # Check for file_started event
    started_events = [call for call in progress_calls if call[0] == "file_started"]
    assert len(started_events) > 0
    assert started_events[0][1]["filename"] == "test.xlsx"


@pytest.mark.asyncio
async def test_process_job_success(orchestrator, mock_concurrent_executor, language_pair, tmp_path):
    """Test successful job processing."""
    # Setup
    file_paths = [
        tmp_path / "file1.xlsx",
        tmp_path / "file2.xlsx"
    ]
    for fp in file_paths:
        fp.touch()
    
    job = TranslationJob()
    
    # Mock successful file processing
    from backend.src.services.concurrent_executor import ProcessingResult
    
    mock_results = [
        ProcessingResult(
            success=True,
            result=FileProcessingResult(
                filename="file1.xlsx",
                success=True,
                cells_translated=10,
                cells_total=10
            )
        ),
        ProcessingResult(
            success=True,
            result=FileProcessingResult(
                filename="file2.xlsx",
                success=True,
                cells_translated=20,
                cells_total=20
            )
        )
    ]
    
    mock_concurrent_executor.process_files_concurrently.return_value = mock_results
    
    # Execute
    await orchestrator.process_job(job, file_paths, language_pair)
    
    # Verify
    assert job.status in [JobStatus.COMPLETED, JobStatus.PROCESSING]
    assert job.files_total == 2
    assert job.files_completed == 2
    assert len(job.files_failed) == 0


@pytest.mark.asyncio
async def test_process_job_with_failures(orchestrator, mock_concurrent_executor, language_pair, tmp_path):
    """Test job processing with some file failures (error isolation)."""
    # Setup
    file_paths = [
        tmp_path / "file1.xlsx",
        tmp_path / "file2.xlsx",
        tmp_path / "file3.xlsx"
    ]
    for fp in file_paths:
        fp.touch()
    
    job = TranslationJob()
    
    # Mock mixed results
    from backend.src.services.concurrent_executor import ProcessingResult
    
    mock_results = [
        ProcessingResult(
            success=True,
            result=FileProcessingResult(
                filename="file1.xlsx",
                success=True,
                cells_translated=10,
                cells_total=10
            )
        ),
        ProcessingResult(
            success=True,
            result=FileProcessingResult(
                filename="file2.xlsx",
                success=False,
                error="Translation failed",
                error_type="TranslationError"
            )
        ),
        ProcessingResult(
            success=True,
            result=FileProcessingResult(
                filename="file3.xlsx",
                success=True,
                cells_translated=15,
                cells_total=15
            )
        )
    ]
    
    mock_concurrent_executor.process_files_concurrently.return_value = mock_results
    
    # Execute
    await orchestrator.process_job(job, file_paths, language_pair)
    
    # Verify error isolation - job continues despite failure
    assert job.files_total == 3
    assert job.files_completed == 2
    assert len(job.files_failed) == 1
    assert job.files_failed[0].filename == "file2.xlsx"
    assert job.status == JobStatus.PARTIAL_SUCCESS


@pytest.mark.asyncio
async def test_process_job_all_failures(orchestrator, mock_concurrent_executor, language_pair, tmp_path):
    """Test job processing when all files fail."""
    # Setup
    file_paths = [
        tmp_path / "file1.xlsx",
        tmp_path / "file2.xlsx"
    ]
    for fp in file_paths:
        fp.touch()
    
    job = TranslationJob()
    
    # Mock all failures
    from backend.src.services.concurrent_executor import ProcessingResult
    
    mock_results = [
        ProcessingResult(
            success=True,
            result=FileProcessingResult(
                filename="file1.xlsx",
                success=False,
                error="Load failed",
                error_type="LoadError"
            )
        ),
        ProcessingResult(
            success=True,
            result=FileProcessingResult(
                filename="file2.xlsx",
                success=False,
                error="Load failed",
                error_type="LoadError"
            )
        )
    ]
    
    mock_concurrent_executor.process_files_concurrently.return_value = mock_results
    
    # Execute
    await orchestrator.process_job(job, file_paths, language_pair)
    
    # Verify
    assert job.files_total == 2
    assert job.files_completed == 0
    assert len(job.files_failed) == 2
    assert job.status == JobStatus.FAILED


@pytest.mark.asyncio
async def test_process_job_with_progress_callback(orchestrator, mock_concurrent_executor, language_pair, tmp_path):
    """Test job processing with progress callbacks."""
    # Setup
    file_paths = [tmp_path / "file1.xlsx"]
    file_paths[0].touch()
    
    job = TranslationJob()
    
    # Mock result
    from backend.src.services.concurrent_executor import ProcessingResult
    
    mock_results = [
        ProcessingResult(
            success=True,
            result=FileProcessingResult(
                filename="file1.xlsx",
                success=True,
                cells_translated=10,
                cells_total=10
            )
        )
    ]
    
    mock_concurrent_executor.process_files_concurrently.return_value = mock_results
    
    # Track callbacks
    callback_events = []
    
    async def progress_callback(event_type, data):
        callback_events.append((event_type, data))
    
    # Execute
    await orchestrator.process_job(job, file_paths, language_pair, progress_callback)
    
    # Verify callbacks were called
    assert len(callback_events) > 0
    
    # Check for job_started event
    started_events = [e for e in callback_events if e[0] == "job_started"]
    assert len(started_events) > 0
    
    # Check for job_completed event
    completed_events = [e for e in callback_events if e[0] == "job_completed"]
    assert len(completed_events) > 0


@pytest.mark.asyncio
async def test_error_logging_on_file_failure(orchestrator, mock_document_processor, language_pair, tmp_path, caplog):
    """Test that errors are comprehensively logged when file processing fails."""
    import logging
    caplog.set_level(logging.ERROR)
    
    # Setup
    file_path = tmp_path / "test.xlsx"
    file_path.touch()
    
    job = TranslationJob(files_total=1)
    
    # Mock exception during text extraction
    mock_document_processor.validate_file.return_value = (True, None)
    mock_document_processor.extract_text.side_effect = Exception("Simulated error")
    
    # Execute
    result = await orchestrator.process_file(file_path, "test.xlsx", language_pair, job)
    
    # Verify error was logged
    assert result.success is False
    assert len(caplog.records) > 0
    assert any("Failed to process file" in record.message for record in caplog.records)
    assert any("test.xlsx" in record.message for record in caplog.records)
