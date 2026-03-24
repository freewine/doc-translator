"""
Tests for PDF Document Processor

Tests the PDFProcessor class for text extraction, format preservation,
and file validation including scanned document detection.
"""

import pytest
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

from src.services.document_processor import (
    DocumentType,
    TextSegment,
)
from src.services.pdf_processor import PDFProcessor


class TestPDFProcessor:
    """Tests for PDFProcessor."""
    
    def test_supported_extensions(self):
        """Test supported extensions."""
        processor = PDFProcessor()
        assert processor.supported_extensions == ['.pdf']
    
    def test_document_type(self):
        """Test document type."""
        processor = PDFProcessor()
        assert processor.document_type == DocumentType.PDF
    
    def test_generate_output_filename(self):
        """Test output filename generation."""
        processor = PDFProcessor()
        
        filename = processor.generate_output_filename(Path("document.pdf"))
        assert filename == "document_vi.pdf"
        
        filename = processor.generate_output_filename(Path("report.pdf"), "en")
        assert filename == "report_en.pdf"


class TestPDFProcessorExtraction:
    """Tests for PDFProcessor text extraction."""
    
    @pytest.mark.asyncio
    async def test_extract_text_from_simple_pdf(self):
        """Test extracting text from a simple PDF."""
        processor = PDFProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Hello World", fontsize=12)
            doc.save(f.name)
            doc.close()
            file_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(file_path)
            
            assert len(segments) >= 1
            texts = [s.text for s in segments]
            assert any("Hello World" in t for t in texts)
            
            # Check metadata
            for segment in segments:
                assert segment.metadata.get("type") == "text_line"
                assert "page_idx" in segment.metadata
                assert "spans" in segment.metadata
        finally:
            file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_extract_text_from_multipage_pdf(self):
        """Test extracting text from a multi-page PDF."""
        processor = PDFProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            
            # Page 1
            page1 = doc.new_page()
            page1.insert_text((100, 100), "Page One Content", fontsize=12)
            
            # Page 2
            page2 = doc.new_page()
            page2.insert_text((100, 100), "Page Two Content", fontsize=12)
            
            doc.save(f.name)
            doc.close()
            file_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(file_path)
            
            texts = [s.text for s in segments]
            assert any("Page One Content" in t for t in texts)
            assert any("Page Two Content" in t for t in texts)
            
            # Check page indices
            page_indices = set(s.metadata.get("page_idx") for s in segments)
            assert 0 in page_indices
            assert 1 in page_indices
        finally:
            file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_extract_text_preserves_font_metadata(self):
        """Test that extraction preserves font metadata."""
        processor = PDFProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Large Text", fontsize=24)
            doc.save(f.name)
            doc.close()
            file_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(file_path)
            
            assert len(segments) >= 1
            segment = [s for s in segments if "Large Text" in s.text][0]
            
            # Check spans metadata
            spans = segment.metadata.get("spans", [])
            assert len(spans) >= 1
            # Font size should be approximately 24
            assert spans[0]["size"] >= 20
        finally:
            file_path.unlink()


class TestPDFProcessorValidation:
    """Tests for PDFProcessor file validation."""
    
    @pytest.mark.asyncio
    async def test_validate_file_success(self):
        """Test validating a valid PDF file."""
        processor = PDFProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Test content", fontsize=12)
            doc.save(f.name)
            doc.close()
            file_path = Path(f.name)
        
        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is True
            assert error is None
        finally:
            file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_validate_file_not_found(self):
        """Test validating a non-existent file."""
        processor = PDFProcessor()
        
        is_valid, error = await processor.validate_file(Path("/nonexistent/file.pdf"))
        
        assert is_valid is False
        assert "not found" in error.lower()
    
    @pytest.mark.asyncio
    async def test_validate_file_wrong_extension(self):
        """Test validating a file with wrong extension."""
        processor = PDFProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test")
            file_path = Path(f.name)
        
        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is False
            assert "unsupported" in error.lower()
        finally:
            file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_validate_file_corrupted(self):
        """Test validating a corrupted file."""
        processor = PDFProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b"not a valid pdf file")
            file_path = Path(f.name)
        
        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is False
            assert "corrupted" in error.lower() or "cannot be read" in error.lower()
        finally:
            file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_validate_file_empty_pdf(self):
        """Test validating a PDF with no text content."""
        processor = PDFProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            doc.new_page()  # Empty page
            doc.save(f.name)
            doc.close()
            file_path = Path(f.name)
        
        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is False
            assert "no translatable text" in error.lower() or "no pages" in error.lower()
        finally:
            file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_validate_file_scanned_pdf(self):
        """Test validating a scanned PDF (image-only)."""
        processor = PDFProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            
            # Create a simple image (1x1 pixel)
            import io
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='white')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Insert image to simulate scanned PDF
            rect = fitz.Rect(0, 0, 595, 842)  # Full page
            page.insert_image(rect, stream=img_bytes.read())
            
            doc.save(f.name)
            doc.close()
            file_path = Path(f.name)
        
        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is False
            assert "scanned" in error.lower() or "no translatable text" in error.lower()
        finally:
            file_path.unlink()


class TestPDFProcessorWriteTranslated:
    """Tests for PDFProcessor write_translated method."""
    
    @pytest.mark.asyncio
    async def test_write_translated_simple(self):
        """Test writing translated text to a simple PDF."""
        processor = PDFProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Hello", fontsize=12)
            doc.save(f.name)
            doc.close()
            input_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            # Extract text
            segments = await processor.extract_text(input_path)
            
            # Create translations
            translations = ["Xin chào" for _ in segments]
            
            # Write translated
            success = await processor.write_translated(
                input_path, segments, translations, output_path
            )
            
            assert success is True
            assert output_path.exists()
            
            # Verify the translated content
            doc = fitz.open(str(output_path))
            page = doc[0]
            text = page.get_text("text")
            doc.close()
            
            # The translated text should be present
            assert "Xin chào" in text
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()
    
    @pytest.mark.asyncio
    async def test_write_translated_multipage(self):
        """Test writing translated text to a multi-page PDF."""
        processor = PDFProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page1 = doc.new_page()
            page1.insert_text((100, 100), "Page One", fontsize=12)
            page2 = doc.new_page()
            page2.insert_text((100, 100), "Page Two", fontsize=12)
            doc.save(f.name)
            doc.close()
            input_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(input_path)
            
            # Create translations based on content
            translations = []
            for seg in segments:
                if "Page One" in seg.text:
                    translations.append("Trang Một")
                elif "Page Two" in seg.text:
                    translations.append("Trang Hai")
                else:
                    translations.append(seg.text)
            
            success = await processor.write_translated(
                input_path, segments, translations, output_path
            )
            
            assert success is True
            
            # Verify content on both pages
            doc = fitz.open(str(output_path))
            page1_text = doc[0].get_text("text")
            page2_text = doc[1].get_text("text")
            doc.close()
            
            assert "Trang Một" in page1_text
            assert "Trang Hai" in page2_text
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()
    
    @pytest.mark.asyncio
    async def test_write_translated_preserves_images(self):
        """Test that writing preserves embedded images."""
        processor = PDFProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            
            # Add text
            page.insert_text((100, 100), "Text with image", fontsize=12)
            
            # Add an image
            import io
            from PIL import Image
            img = Image.new('RGB', (50, 50), color='red')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            rect = fitz.Rect(200, 200, 250, 250)
            page.insert_image(rect, stream=img_bytes.read())
            
            doc.save(f.name)
            doc.close()
            input_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(input_path)
            translations = ["Văn bản với hình ảnh" for _ in segments]
            
            success = await processor.write_translated(
                input_path, segments, translations, output_path
            )
            
            assert success is True
            
            # Verify image is preserved
            doc = fitz.open(str(output_path))
            page = doc[0]
            images = page.get_images()
            doc.close()
            
            # Should still have the image
            assert len(images) >= 1
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()


class TestPDFProcessorOutputModes:
    """Tests for PDF output modes (Replace, Append, Interleaved)."""

    @pytest.mark.asyncio
    async def test_write_translated_replace_mode(self):
        """Test Replace mode: only translated text should appear."""
        processor = PDFProcessor()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Hello", fontsize=12)
            doc.save(f.name)
            doc.close()
            input_path = Path(f.name)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = Path(f.name)

        try:
            segments = await processor.extract_text(input_path)
            translations = ["Xin chào" for _ in segments]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                auto_append=False, interleaved_mode=False
            )

            assert success is True
            doc = fitz.open(str(output_path))
            text = doc[0].get_text("text")
            doc.close()
            assert "Xin chào" in text
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    @pytest.mark.asyncio
    async def test_write_translated_append_mode(self):
        """Test Append mode: both original and translated text should appear."""
        processor = PDFProcessor()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Hello", fontsize=12)
            doc.save(f.name)
            doc.close()
            input_path = Path(f.name)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = Path(f.name)

        try:
            segments = await processor.extract_text(input_path)
            translations = ["Xin chào" for _ in segments]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                auto_append=True, interleaved_mode=False
            )

            assert success is True
            doc = fitz.open(str(output_path))
            text = doc[0].get_text("text")
            doc.close()
            # Both original and translated should be present
            assert "Hello" in text
            assert "Xin chào" in text
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    @pytest.mark.asyncio
    async def test_write_translated_interleaved_mode(self):
        """Test Interleaved mode: original and translated lines interleaved."""
        processor = PDFProcessor()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Hello", fontsize=12)
            doc.save(f.name)
            doc.close()
            input_path = Path(f.name)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = Path(f.name)

        try:
            segments = await processor.extract_text(input_path)
            translations = ["Xin chào" for _ in segments]

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                auto_append=False, interleaved_mode=True
            )

            assert success is True
            doc = fitz.open(str(output_path))
            text = doc[0].get_text("text")
            doc.close()
            # Both original and translated should be present
            assert "Hello" in text
            assert "Xin chào" in text
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    @pytest.mark.asyncio
    async def test_write_translated_append_multiline_pdf(self):
        """Test Append mode with multiple text lines on a page."""
        processor = PDFProcessor()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Line one", fontsize=12)
            page.insert_text((100, 200), "Line two", fontsize=12)
            doc.save(f.name)
            doc.close()
            input_path = Path(f.name)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = Path(f.name)

        try:
            segments = await processor.extract_text(input_path)
            translations = []
            for seg in segments:
                if "one" in seg.text.lower():
                    translations.append("Dòng một")
                elif "two" in seg.text.lower():
                    translations.append("Dòng hai")
                else:
                    translations.append(seg.text)

            success = await processor.write_translated(
                input_path, segments, translations, output_path,
                auto_append=True, interleaved_mode=False
            )

            assert success is True
            doc = fitz.open(str(output_path))
            text = doc[0].get_text("text")
            doc.close()
            # All original and translated text should be present
            assert "Line one" in text
            assert "Dòng một" in text
            assert "Line two" in text
            assert "Dòng hai" in text
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()


class TestPDFProcessorCalculateOutputRect:
    """Tests for _calculate_output_rect helper."""

    def test_single_line_returns_original(self):
        """Single line should return original rect and font size unchanged."""
        processor = PDFProcessor()
        line_bbox = (100, 100, 300, 114)
        rect, font_size = processor._calculate_output_rect(
            line_bbox, num_lines=1, font_size=12, page_height=842,
            next_segment_top=None,
        )
        assert rect == fitz.Rect(line_bbox)
        assert font_size == 12

    def test_two_lines_with_ample_space(self):
        """Two lines with plenty of space should expand rect, keep font size."""
        processor = PDFProcessor()
        line_bbox = (100, 100, 300, 114)
        rect, font_size = processor._calculate_output_rect(
            line_bbox, num_lines=2, font_size=12, page_height=842,
            next_segment_top=None,
        )
        assert rect.y1 > 114  # Expanded downward
        assert font_size == 12  # Unchanged

    def test_two_lines_with_tight_space(self):
        """Two lines with tight space should reduce font size."""
        processor = PDFProcessor()
        line_bbox = (100, 100, 300, 114)
        # Next segment starts very close (only 5pt gap)
        rect, font_size = processor._calculate_output_rect(
            line_bbox, num_lines=2, font_size=12, page_height=842,
            next_segment_top=105,
        )
        assert font_size < 12  # Should be reduced
        assert font_size >= 6  # Should not go below floor

    def test_font_size_floor(self):
        """Font size should not drop below 6pt."""
        processor = PDFProcessor()
        line_bbox = (100, 100, 300, 114)
        # Extremely tight space
        rect, font_size = processor._calculate_output_rect(
            line_bbox, num_lines=4, font_size=12, page_height=842,
            next_segment_top=102,
        )
        assert font_size >= 6.0


class TestPDFProcessorColorConversion:
    """Tests for PDFProcessor color conversion utilities."""
    
    def test_int_to_rgb_black(self):
        """Test converting black color."""
        processor = PDFProcessor()
        rgb = processor._int_to_rgb(0)
        assert rgb == (0, 0, 0)
    
    def test_int_to_rgb_white(self):
        """Test converting white color."""
        processor = PDFProcessor()
        # White in BGR format: 0xFFFFFF
        rgb = processor._int_to_rgb(0xFFFFFF)
        assert rgb == (1.0, 1.0, 1.0)
    
    def test_int_to_rgb_red(self):
        """Test converting red color."""
        processor = PDFProcessor()
        # Red in BGR format: 0x0000FF
        rgb = processor._int_to_rgb(0x0000FF)
        assert rgb == (1.0, 0, 0)
