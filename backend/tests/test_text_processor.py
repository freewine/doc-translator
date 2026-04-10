"""
Tests for TextProcessor

Tests the plain text (.txt) document processor for text extraction,
translation writing, and file validation.
"""

import pytest
import tempfile
from pathlib import Path

from src.services.text_processor import TextProcessor
from src.services.document_processor import DocumentType


class TestTextProcessorProperties:
    """Tests for TextProcessor properties."""

    def test_supported_extensions(self):
        """Test supported extensions returns ['.txt']."""
        processor = TextProcessor()
        assert processor.supported_extensions == ['.txt']

    def test_document_type(self):
        """Test document type is TEXT."""
        processor = TextProcessor()
        assert processor.document_type == DocumentType.TEXT


class TestTextProcessorExtractText:
    """Tests for TextProcessor.extract_text."""

    async def test_extract_text_single_paragraph(self):
        """Test extracting a single paragraph."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("Hello World")
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            assert len(segments) == 1
            assert segments[0].text == "Hello World"
            assert segments[0].id == "0"
            assert segments[0].location == "Paragraph 1"
            assert segments[0].metadata["type"] == "paragraph"
            assert segments[0].metadata["paragraph_idx"] == 0
        finally:
            file_path.unlink()

    async def test_extract_text_multiple_paragraphs(self):
        """Test extracting multiple paragraphs separated by double newlines."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("First paragraph.\n\nSecond paragraph.\n\nThird paragraph.")
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            assert len(segments) == 3
            assert segments[0].text == "First paragraph."
            assert segments[1].text == "Second paragraph."
            assert segments[2].text == "Third paragraph."
            assert segments[0].location == "Paragraph 1"
            assert segments[1].location == "Paragraph 2"
            assert segments[2].location == "Paragraph 3"
        finally:
            file_path.unlink()

    async def test_extract_text_skips_empty_paragraphs(self):
        """Test that empty paragraphs (multiple blank lines) are skipped."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("First paragraph.\n\n\n\nSecond paragraph.")
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            assert len(segments) == 2
            assert segments[0].text == "First paragraph."
            assert segments[1].text == "Second paragraph."
        finally:
            file_path.unlink()

    async def test_extract_text_unicode(self):
        """Test extracting text with unicode characters."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("Hello World\n\nXin chao\n\n")
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            assert len(segments) == 2
            assert segments[0].text == "Hello World"
            assert segments[1].text == "Xin chao"
        finally:
            file_path.unlink()

    async def test_extract_text_file_not_found(self):
        """Test that extracting from non-existent file raises ValueError."""
        processor = TextProcessor()

        with pytest.raises(ValueError, match="Failed to read text file"):
            await processor.extract_text(Path("/nonexistent/file.txt"))


class TestTextProcessorValidateFile:
    """Tests for TextProcessor.validate_file."""

    async def test_validate_file_success(self):
        """Test validating a valid text file."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("Some content here.")
            file_path = Path(f.name)

        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is True
            assert error is None
        finally:
            file_path.unlink()

    async def test_validate_file_not_found(self):
        """Test validating a non-existent file."""
        processor = TextProcessor()

        is_valid, error = await processor.validate_file(Path("/nonexistent/file.txt"))
        assert is_valid is False
        assert "not found" in error.lower()

    async def test_validate_file_wrong_extension(self):
        """Test validating a file with wrong extension."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.docx', delete=False, mode='w'
        ) as f:
            f.write("test")
            file_path = Path(f.name)

        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is False
            assert "unsupported" in error.lower()
        finally:
            file_path.unlink()

    async def test_validate_file_empty(self):
        """Test validating an empty text file."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("")
            file_path = Path(f.name)

        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is False
            assert "no content" in error.lower()
        finally:
            file_path.unlink()

    async def test_validate_file_whitespace_only(self):
        """Test validating a file with only whitespace."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("   \n\n   \n")
            file_path = Path(f.name)

        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is False
            assert "no content" in error.lower()
        finally:
            file_path.unlink()


class TestTextProcessorWriteTranslated:
    """Tests for TextProcessor.write_translated."""

    async def test_write_translated_replace_mode(self):
        """Test writing translations in replace mode (default)."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("Hello World\n\nGoodbye World")
            input_path = Path(f.name)

        output_path = Path(tempfile.mktemp(suffix='.txt'))

        try:
            segments = await processor.extract_text(input_path)
            translations = ["Xin chao", "Tam biet"]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                output_mode="replace"
            )

            assert success is True
            assert output_path.exists()

            content = output_path.read_text(encoding='utf-8')
            assert content == "Xin chao\n\nTam biet"
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    async def test_write_translated_append_mode(self):
        """Test writing translations in append mode."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("Hello World\n\nGoodbye World")
            input_path = Path(f.name)

        output_path = Path(tempfile.mktemp(suffix='.txt'))

        try:
            segments = await processor.extract_text(input_path)
            translations = ["Xin chao", "Tam biet"]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                output_mode="append"
            )

            assert success is True
            content = output_path.read_text(encoding='utf-8')
            # Each paragraph should have original + newline + translation
            assert "Hello World\nXin chao" in content
            assert "Goodbye World\nTam biet" in content
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    async def test_write_translated_interleaved_mode(self):
        """Test writing translations in interleaved mode."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("Hello World\n\nGoodbye World")
            input_path = Path(f.name)

        output_path = Path(tempfile.mktemp(suffix='.txt'))

        try:
            segments = await processor.extract_text(input_path)
            translations = ["Xin chao", "Tam biet"]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                output_mode="interleave"
            )

            assert success is True
            content = output_path.read_text(encoding='utf-8')
            # Each paragraph should have original + newline + translation (interleaved)
            assert "Hello World\nXin chao" in content
            assert "Goodbye World\nTam biet" in content
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    async def test_write_translated_creates_output_directory(self):
        """Test that write_translated creates output directory if needed."""
        processor = TextProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("Hello")
            input_path = Path(f.name)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "output.txt"

            try:
                segments = await processor.extract_text(input_path)
                translations = ["Xin chao"]

                success = await processor.write_translated(
                    input_path, segments, translations, output_path
                )

                assert success is True
                assert output_path.exists()
            finally:
                input_path.unlink()

    async def test_generate_output_filename(self):
        """Test output filename generation with datetime stamp."""
        import re
        processor = TextProcessor()

        filename = processor.generate_output_filename(Path("document.txt"))
        assert re.match(r"^document_\d{8}_\d{6}_vi\.txt$", filename)

        filename = processor.generate_output_filename(Path("readme.txt"), "en")
        assert re.match(r"^readme_\d{8}_\d{6}_en\.txt$", filename)
