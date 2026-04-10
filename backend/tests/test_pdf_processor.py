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
        """Test output filename generation with datetime stamp."""
        import re
        processor = PDFProcessor()

        filename = processor.generate_output_filename(Path("document.pdf"))
        assert re.match(r"^document_\d{8}_\d{6}_vi\.pdf$", filename)

        filename = processor.generate_output_filename(Path("report.pdf"), "en")
        assert re.match(r"^report_\d{8}_\d{6}_en\.pdf$", filename)


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
                output_mode="replace"
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
                output_mode="append"
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
                output_mode="interleave"
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
                output_mode="append"
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


class TestPDFProcessorFontResolution:
    """Tests for font family and style resolution."""

    def test_resolve_font_sans_serif_default(self):
        """Default font should be Helvetica (sans-serif)."""
        processor = PDFProcessor()
        font, css_family, css_extra = processor._resolve_font("ArialMT", 0, {})
        assert css_family == "sans-serif"
        assert "bold" not in css_extra
        assert "italic" not in css_extra

    def test_resolve_font_serif(self):
        """Font with serif keyword should resolve to serif family."""
        processor = PDFProcessor()
        font, css_family, _ = processor._resolve_font("TimesNewRomanPSMT", 0, {})
        assert css_family == "serif"

    def test_resolve_font_serif_via_flag(self):
        """Font with serif flag (bit 2) should resolve to serif."""
        processor = PDFProcessor()
        font, css_family, _ = processor._resolve_font("SomeFont", 1 << 2, {})
        assert css_family == "serif"

    def test_resolve_font_monospace(self):
        """Font with monospace keyword should resolve to monospace family."""
        processor = PDFProcessor()
        font, css_family, _ = processor._resolve_font("CourierNew", 0, {})
        assert css_family == "monospace"

    def test_resolve_font_monospace_via_flag(self):
        """Font with monospace flag (bit 3) should resolve to monospace."""
        processor = PDFProcessor()
        font, css_family, _ = processor._resolve_font("SomeFont", 1 << 3, {})
        assert css_family == "monospace"

    def test_resolve_font_bold(self):
        """Bold flag (bit 4) should produce bold CSS."""
        processor = PDFProcessor()
        _, _, css_extra = processor._resolve_font("Helvetica-Bold", 1 << 4, {})
        assert "font-weight: bold" in css_extra

    def test_resolve_font_italic(self):
        """Italic flag (bit 1) should produce italic CSS."""
        processor = PDFProcessor()
        _, _, css_extra = processor._resolve_font("Helvetica-Oblique", 1 << 1, {})
        assert "font-style: italic" in css_extra

    def test_resolve_font_bold_italic(self):
        """Both bold and italic flags should produce both CSS."""
        processor = PDFProcessor()
        flags = (1 << 4) | (1 << 1)
        _, _, css_extra = processor._resolve_font("Helvetica-BoldOblique", flags, {})
        assert "font-weight: bold" in css_extra
        assert "font-style: italic" in css_extra


class TestPDFProcessorBackgroundDetection:
    """Tests for adaptive background color detection."""

    @pytest.mark.asyncio
    async def test_detect_background_white_page(self):
        """White page should detect white background."""
        processor = PDFProcessor()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Test", fontsize=12)
            doc.save(f.name)
            doc.close()
            file_path = Path(f.name)

        try:
            doc = fitz.open(str(file_path))
            page = doc[0]
            bg = processor._detect_background_color(page, 0, {})
            doc.close()
            # White page should give near-white values
            assert bg[0] >= 0.95
            assert bg[1] >= 0.95
            assert bg[2] >= 0.95
        finally:
            file_path.unlink()

    @pytest.mark.asyncio
    async def test_detect_background_colored_page(self):
        """Page with colored rectangle should detect that color."""
        processor = PDFProcessor()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            # Fill page with a light blue background
            page.draw_rect(page.rect, color=None, fill=(0.8, 0.9, 1.0))
            page.insert_text((100, 100), "Test", fontsize=12)
            doc.save(f.name)
            doc.close()
            file_path = Path(f.name)

        try:
            doc = fitz.open(str(file_path))
            page = doc[0]
            bg = processor._detect_background_color(page, 0, {})
            doc.close()
            # Should detect the blue-ish background, not white
            assert bg[2] > bg[0]  # Blue component should be higher than red
        finally:
            file_path.unlink()

    def test_background_color_caching(self):
        """Background color should be cached per page."""
        processor = PDFProcessor()
        page_bg_cache = {0: (0.5, 0.5, 0.5)}
        doc = fitz.open()
        page = doc.new_page()
        bg = processor._detect_background_color(page, 0, page_bg_cache)
        doc.close()
        assert bg == (0.5, 0.5, 0.5)


class TestPDFProcessorSpanDistribution:
    """Tests for text distribution across spans."""

    def test_single_span(self):
        """Single span should return all text."""
        processor = PDFProcessor()
        spans = [{"text": "Hello"}]
        result = processor._distribute_text_to_spans(spans, "Bonjour")
        assert result == ["Bonjour"]

    def test_two_equal_spans(self):
        """Two equal-length spans should split roughly in half."""
        processor = PDFProcessor()
        spans = [{"text": "Hello"}, {"text": "World"}]
        result = processor._distribute_text_to_spans(spans, "Bonjour le Monde")
        assert len(result) == 2
        # All words should be present across the two portions
        full = " ".join(result)
        assert "Bonjour" in full
        assert "Monde" in full

    def test_last_span_gets_remainder(self):
        """Last span should get all remaining words."""
        processor = PDFProcessor()
        spans = [{"text": "A"}, {"text": "BBBBB"}]
        result = processor._distribute_text_to_spans(spans, "one two three four")
        assert len(result) == 2
        # Second span (longer original) should get more words
        assert " ".join(result) == "one two three four"


class TestPDFProcessorBuildSpanHtml:
    """Tests for HTML generation with per-span formatting."""

    def test_build_span_html_single_span(self):
        """Single span should produce one HTML span element."""
        processor = PDFProcessor()
        spans = [{"text": "Hello", "font": "Helvetica", "flags": 0, "size": 12, "color": 0}]
        html = processor._build_span_html(spans, "Bonjour", {})
        assert "<span style=" in html
        assert "Bonjour" in html

    def test_build_span_html_bold_italic(self):
        """Bold+italic span should have corresponding CSS."""
        processor = PDFProcessor()
        flags = (1 << 4) | (1 << 1)  # bold + italic
        spans = [{"text": "Hello", "font": "Helvetica", "flags": flags, "size": 14, "color": 0}]
        html = processor._build_span_html(spans, "Bonjour", {})
        assert "font-weight: bold" in html
        assert "font-style: italic" in html

    def test_build_span_html_multi_span(self):
        """Multi-span line should produce multiple HTML spans."""
        processor = PDFProcessor()
        spans = [
            {"text": "Bold", "font": "Helvetica-Bold", "flags": (1 << 4), "size": 12, "color": 0},
            {"text": " Normal", "font": "Helvetica", "flags": 0, "size": 12, "color": 0},
        ]
        html = processor._build_span_html(spans, "Gras Normal", {})
        assert html.count("<span style=") == 2
        assert "font-weight: bold" in html

    def test_build_span_html_escapes_special_chars(self):
        """Special HTML characters should be escaped."""
        processor = PDFProcessor()
        spans = [{"text": "test", "font": "Helvetica", "flags": 0, "size": 12, "color": 0}]
        html = processor._build_span_html(spans, "a < b & c > d", {})
        assert "&lt;" in html
        assert "&amp;" in html
        assert "&gt;" in html


class TestPDFProcessorWriteWithFormatPreservation:
    """Tests for end-to-end write with format preservation."""

    @pytest.mark.asyncio
    async def test_write_translated_preserves_bold(self):
        """Bold text should remain bold after translation."""
        processor = PDFProcessor()

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            # Insert bold text using a bold font
            page.insert_text(
                (100, 100), "Bold Text", fontsize=14,
                fontname="hebo",  # Helvetica Bold
            )
            doc.save(f.name)
            doc.close()
            input_path = Path(f.name)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            output_path = Path(f.name)

        try:
            segments = await processor.extract_text(input_path)
            translations = ["Texte Gras" for _ in segments]

            success = await processor.write_translated(
                input_path, segments, translations, output_path
            )

            assert success is True
            doc = fitz.open(str(output_path))
            text = doc[0].get_text("text")
            doc.close()
            assert "Texte Gras" in text
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()


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
