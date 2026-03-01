"""Property-based tests for translation orchestrator S3 uploads.

This module tests that the translation orchestrator always uploads output files
to S3 when processing is complete, as part of the local storage cleanup feature.

**Property 4: Translation Orchestrator Uploads Outputs to S3**
**Validates: Requirements 6.2**
"""

import asyncio
import sys
import uuid
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from src.models.job import TranslationJob, JobStatus, LanguagePair, DocumentType
from src.services.translation_orchestrator import TranslationOrchestrator, FileProcessingResult


# Strategies for generating test data

ALLOWED_EXTENSIONS = [".xlsx", ".docx", ".pptx", ".pdf"]


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


def valid_job_id_strategy():
    """
    Generate valid job IDs (UUID format).
    """
    return st.builds(lambda: str(uuid.uuid4()))


@st.composite
def valid_filename_strategy(draw):
    """
    Generate valid filenames with allowed extensions.
    """
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
    
    extension = draw(st.sampled_from(ALLOWED_EXTENSIONS))
    return f"{base_name}{extension}"


@st.composite
def valid_file_content_strategy(draw):
    """
    Generate valid file content of various sizes.
    """
    size = draw(st.integers(min_value=10, max_value=1024))
    content = draw(st.binary(min_size=size, max_size=size))
    return content


@st.composite
def valid_translation_result_strategy(draw):
    """
    Generate a complete valid translation result scenario.
    
    Returns a dict with:
    - user_id: User ID for S3 path
    - job_id: Job ID for S3 path
    - filename: Original filename
    - output_filename: Output filename with _vi suffix
    - content: File content bytes
    - segments: Number of text segments
    """
    filename = draw(valid_filename_strategy())
    extension = Path(filename).suffix
    base_name = Path(filename).stem
    output_filename = f"{base_name}_vi{extension}"
    
    return {
        "user_id": draw(valid_username_strategy()),
        "job_id": draw(valid_job_id_strategy()),
        "filename": filename,
        "output_filename": output_filename,
        "content": draw(valid_file_content_strategy()),
        "segments": draw(st.integers(min_value=1, max_value=100)),
    }


# Mock classes for testing

@dataclass
class MockTextSegment:
    """Mock text segment for testing."""
    text: str
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MockDocumentProcessor:
    """Mock document processor for testing."""
    
    def __init__(self, document_type: DocumentType, segments: list):
        self.document_type = document_type
        self._segments = segments
        self._write_success = True
    
    async def validate_file(self, file_path: Path):
        return True, None
    
    async def extract_text(self, file_path: Path):
        return self._segments
    
    def generate_output_filename(self, original_path: Path, target_lang_code: str):
        return f"{original_path.stem}_{target_lang_code}{original_path.suffix}"
    
    async def write_translated(self, file_path, segments, translations, output_path, auto_append=False, interleaved_mode=False):
        # Write some content to the output file
        output_path.write_bytes(b"translated content")
        return self._write_success


class TestOrchestratorS3Uploads:
    """Property-based tests for orchestrator S3 uploads."""
    
    @given(result=valid_translation_result_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None
    )
    def test_property_4_orchestrator_uploads_outputs_to_s3(self, result):
        """
        **Validates: Requirements 6.2**
        
        Property 4: Translation Orchestrator Uploads Outputs to S3
        
        For any successfully completed file translation, the output file should
        be uploaded to S3 under the user's output path
        ({user_id}/outputs/{job_id}/{filename}).
        
        This property ensures that:
        1. S3 save_output is called for successful translations
        2. The correct user_id, job_id, and filename are passed
        3. The output content is uploaded to S3
        """
        user_id = result["user_id"]
        job_id = result["job_id"]
        filename = result["filename"]
        output_filename = result["output_filename"]
        segments_count = result["segments"]
        
        # Create mock S3 file storage
        mock_s3_storage = AsyncMock()
        expected_s3_key = f"{user_id}/outputs/{job_id}/{output_filename}"
        mock_s3_storage.save_output = AsyncMock(return_value=expected_s3_key)
        
        # Create mock translation service
        mock_translation_service = Mock()
        mock_translation_service.batch_size = 10
        mock_translation_service.batch_translate_async = AsyncMock(
            side_effect=lambda texts, lp, tp: ["translated"] * len(texts)
        )
        
        # Create mock concurrent executor
        mock_executor = Mock()
        
        # Create mock excel processor (legacy)
        mock_excel_processor = Mock()
        
        # Create text segments for the mock processor
        segments = [MockTextSegment(text=f"text_{i}") for i in range(segments_count)]
        
        # Determine document type from extension
        ext = Path(filename).suffix.lower()
        doc_type_map = {
            ".xlsx": DocumentType.EXCEL,
            ".docx": DocumentType.WORD,
            ".pptx": DocumentType.POWERPOINT,
            ".pdf": DocumentType.PDF,
        }
        document_type = doc_type_map.get(ext, DocumentType.EXCEL)
        
        # Create mock processor
        mock_processor = MockDocumentProcessor(document_type, segments)
        
        # Create mock processor factory
        mock_factory = Mock()
        mock_factory.get_processor = Mock(return_value=mock_processor)
        
        # Create temp directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create orchestrator with S3 storage
            orchestrator = TranslationOrchestrator(
                excel_processor=mock_excel_processor,
                translation_service=mock_translation_service,
                concurrent_executor=mock_executor,
                output_dir=output_dir,
                processor_factory=mock_factory,
                s3_file_storage=mock_s3_storage,
            )
            
            # Create a translation job
            job = TranslationJob(
                id=job_id,
                status=JobStatus.PENDING,
                files_total=1,
            )
            
            # Create language pair
            language_pair = LanguagePair(
                id="zh-vi",
                source_language="Chinese",
                target_language="Vietnamese",
                source_language_code="zh",
                target_language_code="vi",
            )
            
            # Create temp input file
            input_file = output_dir / f"input_{uuid.uuid4()}{ext}"
            input_file.write_bytes(b"test content")
            
            # Run the process_file method
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                file_result = loop.run_until_complete(
                    orchestrator.process_file(
                        file_path=input_file,
                        original_filename=filename,
                        language_pair=language_pair,
                        job=job,
                        progress_callback=None,
                        term_pairs=None,
                        user_id=user_id,
                    )
                )
            finally:
                loop.close()
            
            # Verify the result is successful
            assert file_result.success, f"File processing should succeed, got error: {file_result.error}"
            
            # Verify S3 save_output was called
            assert mock_s3_storage.save_output.called, (
                "S3 save_output should be called for successful translations"
            )
            
            # Get the call arguments
            call_args = mock_s3_storage.save_output.call_args
            
            # Verify user_id matches
            assert call_args.kwargs.get("user_id") == user_id, (
                f"S3 save_output should use user_id '{user_id}', "
                f"got '{call_args.kwargs.get('user_id')}'"
            )
            
            # Verify job_id matches
            assert call_args.kwargs.get("job_id") == job_id, (
                f"S3 save_output should use job_id '{job_id}', "
                f"got '{call_args.kwargs.get('job_id')}'"
            )
            
            # Verify filename matches expected output filename
            assert call_args.kwargs.get("filename") == output_filename, (
                f"S3 save_output should use filename '{output_filename}', "
                f"got '{call_args.kwargs.get('filename')}'"
            )
            
            # Verify content was passed
            assert call_args.kwargs.get("content") is not None, (
                "S3 save_output should receive file content"
            )
            
            # Verify s3_key is set in result
            assert file_result.s3_key == expected_s3_key, (
                f"FileProcessingResult should have s3_key '{expected_s3_key}', "
                f"got '{file_result.s3_key}'"
            )
    
    @given(result=valid_translation_result_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None
    )
    def test_property_4_s3_key_structure(self, result):
        """
        **Validates: Requirements 6.2**
        
        Property 4: Translation Orchestrator Uploads Outputs to S3 (key structure variant)
        
        Verifies that the S3 key follows the expected structure:
        {user_id}/outputs/{job_id}/{filename}
        """
        user_id = result["user_id"]
        job_id = result["job_id"]
        filename = result["filename"]
        output_filename = result["output_filename"]
        segments_count = result["segments"]
        
        # Create mock S3 file storage that captures the key
        mock_s3_storage = AsyncMock()
        captured_key = None
        
        async def capture_save_output(user_id, job_id, filename, content):
            nonlocal captured_key
            captured_key = f"{user_id}/outputs/{job_id}/{filename}"
            return captured_key
        
        mock_s3_storage.save_output = AsyncMock(side_effect=capture_save_output)
        
        # Create mock translation service
        mock_translation_service = Mock()
        mock_translation_service.batch_size = 10
        mock_translation_service.batch_translate_async = AsyncMock(
            side_effect=lambda texts, lp, tp: ["translated"] * len(texts)
        )
        
        # Create mock concurrent executor
        mock_executor = Mock()
        
        # Create mock excel processor (legacy)
        mock_excel_processor = Mock()
        
        # Create text segments
        segments = [MockTextSegment(text=f"text_{i}") for i in range(segments_count)]
        
        # Determine document type
        ext = Path(filename).suffix.lower()
        doc_type_map = {
            ".xlsx": DocumentType.EXCEL,
            ".docx": DocumentType.WORD,
            ".pptx": DocumentType.POWERPOINT,
            ".pdf": DocumentType.PDF,
        }
        document_type = doc_type_map.get(ext, DocumentType.EXCEL)
        
        # Create mock processor
        mock_processor = MockDocumentProcessor(document_type, segments)
        
        # Create mock processor factory
        mock_factory = Mock()
        mock_factory.get_processor = Mock(return_value=mock_processor)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            orchestrator = TranslationOrchestrator(
                excel_processor=mock_excel_processor,
                translation_service=mock_translation_service,
                concurrent_executor=mock_executor,
                output_dir=output_dir,
                processor_factory=mock_factory,
                s3_file_storage=mock_s3_storage,
            )
            
            job = TranslationJob(id=job_id, status=JobStatus.PENDING, files_total=1)
            
            language_pair = LanguagePair(
                id="zh-vi",
                source_language="Chinese",
                target_language="Vietnamese",
                source_language_code="zh",
                target_language_code="vi",
            )
            
            input_file = output_dir / f"input_{uuid.uuid4()}{ext}"
            input_file.write_bytes(b"test content")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                file_result = loop.run_until_complete(
                    orchestrator.process_file(
                        file_path=input_file,
                        original_filename=filename,
                        language_pair=language_pair,
                        job=job,
                        user_id=user_id,
                    )
                )
            finally:
                loop.close()
            
            assert file_result.success
            
            # Verify the S3 key structure
            expected_key = f"{user_id}/outputs/{job_id}/{output_filename}"
            assert captured_key == expected_key, (
                f"S3 key should be '{expected_key}', got '{captured_key}'"
            )
            
            # Verify key components
            assert captured_key.startswith(f"{user_id}/"), (
                f"S3 key should start with user_id '{user_id}/'"
            )
            assert "/outputs/" in captured_key, (
                "S3 key should contain '/outputs/'"
            )
            assert f"/{job_id}/" in captured_key, (
                f"S3 key should contain job_id '/{job_id}/'"
            )
            assert captured_key.endswith(output_filename), (
                f"S3 key should end with output filename '{output_filename}'"
            )
    
    @given(result=valid_translation_result_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None
    )
    def test_property_4_s3_upload_failure_marks_file_failed(self, result):
        """
        **Validates: Requirements 6.2, 6.3**
        
        Property 4: Translation Orchestrator Uploads Outputs to S3 (error handling variant)
        
        When S3 upload fails, the file should be marked as failed with
        "S3UploadError" error type.
        """
        user_id = result["user_id"]
        job_id = result["job_id"]
        filename = result["filename"]
        segments_count = result["segments"]
        
        # Create mock S3 file storage that fails
        mock_s3_storage = AsyncMock()
        mock_s3_storage.save_output = AsyncMock(
            side_effect=Exception("S3 upload failed: Access Denied")
        )
        
        # Create mock translation service
        mock_translation_service = Mock()
        mock_translation_service.batch_size = 10
        mock_translation_service.batch_translate_async = AsyncMock(
            side_effect=lambda texts, lp, tp: ["translated"] * len(texts)
        )
        
        # Create mock concurrent executor
        mock_executor = Mock()
        
        # Create mock excel processor (legacy)
        mock_excel_processor = Mock()
        
        # Create text segments
        segments = [MockTextSegment(text=f"text_{i}") for i in range(segments_count)]
        
        # Determine document type
        ext = Path(filename).suffix.lower()
        doc_type_map = {
            ".xlsx": DocumentType.EXCEL,
            ".docx": DocumentType.WORD,
            ".pptx": DocumentType.POWERPOINT,
            ".pdf": DocumentType.PDF,
        }
        document_type = doc_type_map.get(ext, DocumentType.EXCEL)
        
        # Create mock processor
        mock_processor = MockDocumentProcessor(document_type, segments)
        
        # Create mock processor factory
        mock_factory = Mock()
        mock_factory.get_processor = Mock(return_value=mock_processor)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            orchestrator = TranslationOrchestrator(
                excel_processor=mock_excel_processor,
                translation_service=mock_translation_service,
                concurrent_executor=mock_executor,
                output_dir=output_dir,
                processor_factory=mock_factory,
                s3_file_storage=mock_s3_storage,
            )
            
            job = TranslationJob(id=job_id, status=JobStatus.PENDING, files_total=1)
            
            language_pair = LanguagePair(
                id="zh-vi",
                source_language="Chinese",
                target_language="Vietnamese",
                source_language_code="zh",
                target_language_code="vi",
            )
            
            input_file = output_dir / f"input_{uuid.uuid4()}{ext}"
            input_file.write_bytes(b"test content")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                file_result = loop.run_until_complete(
                    orchestrator.process_file(
                        file_path=input_file,
                        original_filename=filename,
                        language_pair=language_pair,
                        job=job,
                        user_id=user_id,
                    )
                )
            finally:
                loop.close()
            
            # Verify the result indicates failure
            assert not file_result.success, (
                "File processing should fail when S3 upload fails"
            )
            
            # Verify error type is S3UploadError
            assert file_result.error_type == "S3UploadError", (
                f"Error type should be 'S3UploadError', got '{file_result.error_type}'"
            )
            
            # Verify error message mentions S3
            assert "S3" in file_result.error or "upload" in file_result.error.lower(), (
                f"Error message should mention S3 upload failure: {file_result.error}"
            )
    
    @given(result=valid_translation_result_strategy())
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
        deadline=None
    )
    def test_property_4_no_s3_upload_without_user_id(self, result):
        """
        **Validates: Requirements 6.2**
        
        Property 4: Translation Orchestrator Uploads Outputs to S3 (user_id required variant)
        
        When user_id is not provided, S3 upload should not be attempted.
        This ensures backward compatibility and proper user isolation.
        """
        job_id = result["job_id"]
        filename = result["filename"]
        segments_count = result["segments"]
        
        # Create mock S3 file storage
        mock_s3_storage = AsyncMock()
        mock_s3_storage.save_output = AsyncMock(return_value="some/key")
        
        # Create mock translation service
        mock_translation_service = Mock()
        mock_translation_service.batch_size = 10
        mock_translation_service.batch_translate_async = AsyncMock(
            side_effect=lambda texts, lp, tp: ["translated"] * len(texts)
        )
        
        # Create mock concurrent executor
        mock_executor = Mock()
        
        # Create mock excel processor (legacy)
        mock_excel_processor = Mock()
        
        # Create text segments
        segments = [MockTextSegment(text=f"text_{i}") for i in range(segments_count)]
        
        # Determine document type
        ext = Path(filename).suffix.lower()
        doc_type_map = {
            ".xlsx": DocumentType.EXCEL,
            ".docx": DocumentType.WORD,
            ".pptx": DocumentType.POWERPOINT,
            ".pdf": DocumentType.PDF,
        }
        document_type = doc_type_map.get(ext, DocumentType.EXCEL)
        
        # Create mock processor
        mock_processor = MockDocumentProcessor(document_type, segments)
        
        # Create mock processor factory
        mock_factory = Mock()
        mock_factory.get_processor = Mock(return_value=mock_processor)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            orchestrator = TranslationOrchestrator(
                excel_processor=mock_excel_processor,
                translation_service=mock_translation_service,
                concurrent_executor=mock_executor,
                output_dir=output_dir,
                processor_factory=mock_factory,
                s3_file_storage=mock_s3_storage,
            )
            
            job = TranslationJob(id=job_id, status=JobStatus.PENDING, files_total=1)
            
            language_pair = LanguagePair(
                id="zh-vi",
                source_language="Chinese",
                target_language="Vietnamese",
                source_language_code="zh",
                target_language_code="vi",
            )
            
            input_file = output_dir / f"input_{uuid.uuid4()}{ext}"
            input_file.write_bytes(b"test content")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                file_result = loop.run_until_complete(
                    orchestrator.process_file(
                        file_path=input_file,
                        original_filename=filename,
                        language_pair=language_pair,
                        job=job,
                        user_id=None,  # No user_id provided
                    )
                )
            finally:
                loop.close()
            
            # Verify the result is successful (local processing works)
            assert file_result.success, (
                f"File processing should succeed without user_id, got error: {file_result.error}"
            )
            
            # Verify S3 save_output was NOT called
            assert not mock_s3_storage.save_output.called, (
                "S3 save_output should NOT be called when user_id is not provided"
            )
            
            # Verify s3_key is None in result
            assert file_result.s3_key is None, (
                f"s3_key should be None when user_id is not provided, got '{file_result.s3_key}'"
            )
