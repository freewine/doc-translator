"""
Tests for MarkdownProcessor

Tests the Markdown (.md) document processor for text extraction,
translation writing, and file validation.
"""

import pytest
import tempfile
from pathlib import Path

from src.services.markdown_processor import MarkdownProcessor
from src.services.document_processor import DocumentType


class TestMarkdownProcessorProperties:
    """Tests for MarkdownProcessor properties."""

    def test_supported_extensions(self):
        """Test supported extensions returns ['.md']."""
        processor = MarkdownProcessor()
        assert processor.supported_extensions == ['.md']

    def test_document_type(self):
        """Test document type is MARKDOWN."""
        processor = MarkdownProcessor()
        assert processor.document_type == DocumentType.MARKDOWN


class TestMarkdownProcessorExtractText:
    """Tests for MarkdownProcessor.extract_text."""

    async def test_extract_headings(self):
        """Test extracting heading lines."""
        processor = MarkdownProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("# Title\n\n## Subtitle\n\n### Section")
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            assert len(segments) == 3
            assert segments[0].text == "# Title"
            assert segments[0].metadata["type"] == "heading"
            assert segments[1].text == "## Subtitle"
            assert segments[1].metadata["type"] == "heading"
            assert segments[2].text == "### Section"
            assert segments[2].metadata["type"] == "heading"
        finally:
            file_path.unlink()

    async def test_extract_paragraphs(self):
        """Test extracting paragraph text."""
        processor = MarkdownProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("This is a paragraph.\n\nThis is another paragraph.")
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            assert len(segments) == 2
            assert segments[0].text == "This is a paragraph."
            assert segments[0].metadata["type"] == "paragraph"
            assert segments[1].text == "This is another paragraph."
            assert segments[1].metadata["type"] == "paragraph"
        finally:
            file_path.unlink()

    async def test_extract_list_items(self):
        """Test extracting list items."""
        processor = MarkdownProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("- Item one\n- Item two\n* Item three\n1. Numbered item")
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            assert len(segments) == 4
            for seg in segments:
                assert seg.metadata["type"] == "list_item"
            assert segments[0].text == "- Item one"
            assert segments[1].text == "- Item two"
            assert segments[2].text == "* Item three"
            assert segments[3].text == "1. Numbered item"
        finally:
            file_path.unlink()

    async def test_extract_blockquotes(self):
        """Test extracting blockquotes."""
        processor = MarkdownProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("> This is a quote\n> Another quote line")
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            assert len(segments) == 2
            assert segments[0].metadata["type"] == "blockquote"
            assert segments[1].metadata["type"] == "blockquote"
        finally:
            file_path.unlink()

    async def test_skip_fenced_code_blocks(self):
        """Test that fenced code blocks are skipped."""
        processor = MarkdownProcessor()

        content = "# Title\n\n```python\ndef hello():\n    pass\n```\n\nParagraph after code."
        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(content)
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            texts = [s.text for s in segments]
            assert "# Title" in texts
            assert "Paragraph after code." in texts
            # Code block contents should not be extracted
            assert not any("def hello" in t for t in texts)
            assert not any("pass" in t for t in texts)
            assert len(segments) == 2
        finally:
            file_path.unlink()

    async def test_skip_front_matter(self):
        """Test that YAML front matter is skipped."""
        processor = MarkdownProcessor()

        content = "---\ntitle: Test\ndate: 2024-01-01\n---\n\n# Title\n\nContent here."
        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(content)
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            texts = [s.text for s in segments]
            assert "# Title" in texts
            assert "Content here." in texts
            # Front matter should not be extracted
            assert not any("title: Test" in t for t in texts)
            assert len(segments) == 2
        finally:
            file_path.unlink()

    async def test_skip_blank_lines(self):
        """Test that blank lines are skipped."""
        processor = MarkdownProcessor()

        content = "Line one.\n\n\n\nLine two."
        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(content)
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            assert len(segments) == 2
            assert segments[0].text == "Line one."
            assert segments[1].text == "Line two."
        finally:
            file_path.unlink()

    async def test_line_idx_metadata(self):
        """Test that line_idx metadata is correctly set."""
        processor = MarkdownProcessor()

        content = "# Title\n\nParagraph"
        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(content)
            file_path = Path(f.name)

        try:
            segments = await processor.extract_text(file_path)

            assert segments[0].metadata["line_idx"] == 0  # "# Title" is line 0
            assert segments[1].metadata["line_idx"] == 2  # "Paragraph" is line 2
        finally:
            file_path.unlink()

    async def test_extract_text_file_not_found(self):
        """Test that extracting from non-existent file raises ValueError."""
        processor = MarkdownProcessor()

        with pytest.raises(ValueError, match="Failed to read Markdown file"):
            await processor.extract_text(Path("/nonexistent/file.md"))


class TestMarkdownProcessorValidateFile:
    """Tests for MarkdownProcessor.validate_file."""

    async def test_validate_file_success(self):
        """Test validating a valid markdown file."""
        processor = MarkdownProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("# Hello\n\nSome content.")
            file_path = Path(f.name)

        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is True
            assert error is None
        finally:
            file_path.unlink()

    async def test_validate_file_not_found(self):
        """Test validating a non-existent file."""
        processor = MarkdownProcessor()

        is_valid, error = await processor.validate_file(Path("/nonexistent/file.md"))
        assert is_valid is False
        assert "not found" in error.lower()

    async def test_validate_file_wrong_extension(self):
        """Test validating a file with wrong extension."""
        processor = MarkdownProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w'
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
        """Test validating an empty markdown file."""
        processor = MarkdownProcessor()

        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write("")
            file_path = Path(f.name)

        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is False
            assert "no content" in error.lower()
        finally:
            file_path.unlink()

    async def test_validate_file_only_code_blocks(self):
        """Test validating a file with only code blocks (no translatable content)."""
        processor = MarkdownProcessor()

        content = "```python\ndef hello():\n    pass\n```"
        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(content)
            file_path = Path(f.name)

        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is False
            assert "no translatable content" in error.lower()
        finally:
            file_path.unlink()


class TestMarkdownProcessorWriteTranslated:
    """Tests for MarkdownProcessor.write_translated."""

    async def test_write_translated_replace_mode(self):
        """Test writing translations in replace mode (default)."""
        processor = MarkdownProcessor()

        content = "# Title\n\nSome paragraph.\n\n```python\ncode()\n```\n\nAnother paragraph."
        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(content)
            input_path = Path(f.name)

        output_path = Path(tempfile.mktemp(suffix='.md'))

        try:
            segments = await processor.extract_text(input_path)
            translations = ["# Tieu de", "Mot doan van.", "Doan van khac."]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                output_mode="replace"
            )

            assert success is True
            result = output_path.read_text(encoding='utf-8')

            # Translated lines should be replaced
            assert "# Tieu de" in result
            assert "Mot doan van." in result
            assert "Doan van khac." in result
            # Code block should be preserved
            assert "```python" in result
            assert "code()" in result
            # Original text should not be present
            assert "# Title" not in result
            assert "Some paragraph." not in result
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    async def test_write_translated_preserves_code_blocks(self):
        """Test that code blocks are preserved in translated output."""
        processor = MarkdownProcessor()

        content = "# Title\n\n```\ncode block\n```\n\nParagraph."
        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(content)
            input_path = Path(f.name)

        output_path = Path(tempfile.mktemp(suffix='.md'))

        try:
            segments = await processor.extract_text(input_path)
            translations = ["# Translated Title", "Translated Paragraph."]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                output_mode="replace"
            )

            assert success is True
            result = output_path.read_text(encoding='utf-8')

            assert "```" in result
            assert "code block" in result
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    async def test_write_translated_preserves_front_matter(self):
        """Test that front matter is preserved in translated output."""
        processor = MarkdownProcessor()

        content = "---\ntitle: Test\n---\n\n# Title\n\nContent."
        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(content)
            input_path = Path(f.name)

        output_path = Path(tempfile.mktemp(suffix='.md'))

        try:
            segments = await processor.extract_text(input_path)
            translations = ["# Tieu de", "Noi dung."]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                output_mode="replace"
            )

            assert success is True
            result = output_path.read_text(encoding='utf-8')

            # Front matter should be preserved
            assert "---" in result
            assert "title: Test" in result
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    async def test_write_translated_append_mode(self):
        """Test writing translations in append mode."""
        processor = MarkdownProcessor()

        content = "# Title\n\nParagraph."
        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(content)
            input_path = Path(f.name)

        output_path = Path(tempfile.mktemp(suffix='.md'))

        try:
            segments = await processor.extract_text(input_path)
            translations = ["# Tieu de", "Doan van."]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                output_mode="append"
            )

            assert success is True
            result = output_path.read_text(encoding='utf-8')

            # Append mode: original + newline + translation
            assert "# Title\n# Tieu de" in result
            assert "Paragraph.\nDoan van." in result
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    async def test_write_translated_interleaved_mode(self):
        """Test writing translations in interleaved mode."""
        processor = MarkdownProcessor()

        content = "# Title\n\nParagraph."
        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(content)
            input_path = Path(f.name)

        output_path = Path(tempfile.mktemp(suffix='.md'))

        try:
            segments = await processor.extract_text(input_path)
            translations = ["# Tieu de", "Doan van."]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                output_mode="interleave"
            )

            assert success is True
            result = output_path.read_text(encoding='utf-8')

            # Interleaved mode: original + newline + translation for each segment
            assert "# Title\n# Tieu de" in result
            assert "Paragraph.\nDoan van." in result
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    async def test_write_translated_preserves_blank_lines(self):
        """Test that blank lines between content are preserved."""
        processor = MarkdownProcessor()

        content = "# Title\n\n\n\nParagraph."
        with tempfile.NamedTemporaryFile(
            suffix='.md', delete=False, mode='w', encoding='utf-8'
        ) as f:
            f.write(content)
            input_path = Path(f.name)

        output_path = Path(tempfile.mktemp(suffix='.md'))

        try:
            segments = await processor.extract_text(input_path)
            translations = ["# Tieu de", "Doan van."]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                output_mode="replace"
            )

            assert success is True
            result = output_path.read_text(encoding='utf-8')
            lines = result.split("\n")

            # The blank lines between title and paragraph should be preserved
            assert lines[0] == "# Tieu de"
            assert lines[1] == ""
            assert lines[2] == ""
            assert lines[3] == ""
            assert lines[4] == "Doan van."
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    async def test_generate_output_filename(self):
        """Test output filename generation with datetime stamp."""
        import re
        processor = MarkdownProcessor()

        filename = processor.generate_output_filename(Path("document.md"))
        assert re.match(r"^document_\d{8}_\d{6}_vi\.md$", filename)

        filename = processor.generate_output_filename(Path("readme.md"), "en")
        assert re.match(r"^readme_\d{8}_\d{6}_en\.md$", filename)
