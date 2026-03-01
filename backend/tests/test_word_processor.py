"""
Tests for Word Document Processor

Tests the WordProcessor class for text extraction, format preservation,
and file validation.
"""

import pytest
import tempfile
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from src.services.document_processor import (
    DocumentType,
    TextSegment,
)
from src.services.word_processor import WordProcessor


class TestWordProcessor:
    """Tests for WordProcessor."""
    
    def test_supported_extensions(self):
        """Test supported extensions."""
        processor = WordProcessor()
        assert processor.supported_extensions == ['.docx']
    
    def test_document_type(self):
        """Test document type."""
        processor = WordProcessor()
        assert processor.document_type == DocumentType.WORD
    
    def test_generate_output_filename(self):
        """Test output filename generation."""
        processor = WordProcessor()
        
        filename = processor.generate_output_filename(Path("document.docx"))
        assert filename == "document_vi.docx"
        
        filename = processor.generate_output_filename(Path("report.docx"), "en")
        assert filename == "report_en.docx"


class TestWordProcessorExtraction:
    """Tests for WordProcessor text extraction."""
    
    @pytest.mark.asyncio
    async def test_extract_text_from_paragraphs(self):
        """Test extracting text from paragraphs."""
        processor = WordProcessor()
        
        # Create a test Word file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            doc.add_paragraph("Hello World")
            doc.add_paragraph("This is a test")
            doc.save(f.name)
            file_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(file_path)
            
            assert len(segments) == 2
            texts = [s.text for s in segments]
            assert "Hello World" in texts
            assert "This is a test" in texts
            
            # Check metadata
            for segment in segments:
                assert segment.metadata.get("type") == "paragraph"
                assert "paragraph_idx" in segment.metadata
        finally:
            file_path.unlink()

    @pytest.mark.asyncio
    async def test_extract_text_from_tables(self):
        """Test extracting text from tables."""
        processor = WordProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            table = doc.add_table(rows=2, cols=2)
            table.cell(0, 0).text = "Cell A1"
            table.cell(0, 1).text = "Cell B1"
            table.cell(1, 0).text = "Cell A2"
            table.cell(1, 1).text = "Cell B2"
            doc.save(f.name)
            file_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(file_path)
            
            # Should have 4 table cell segments
            table_segments = [s for s in segments if s.metadata.get("type") == "table_cell"]
            assert len(table_segments) == 4
            
            texts = [s.text for s in table_segments]
            assert "Cell A1" in texts
            assert "Cell B1" in texts
            assert "Cell A2" in texts
            assert "Cell B2" in texts
        finally:
            file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_extract_text_preserves_formatting_metadata(self):
        """Test that extraction preserves formatting metadata."""
        processor = WordProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            para = doc.add_paragraph()
            run = para.add_run("Bold Text")
            run.bold = True
            run.font.size = Pt(14)
            doc.save(f.name)
            file_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(file_path)
            
            assert len(segments) == 1
            segment = segments[0]
            
            # Check runs metadata
            runs = segment.metadata.get("runs", [])
            assert len(runs) == 1
            assert runs[0]["bold"] is True
            assert runs[0]["font_size"] == 14.0
        finally:
            file_path.unlink()


class TestWordProcessorValidation:
    """Tests for WordProcessor file validation."""
    
    @pytest.mark.asyncio
    async def test_validate_file_success(self):
        """Test validating a valid Word file."""
        processor = WordProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            doc.add_paragraph("Test content")
            doc.save(f.name)
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
        processor = WordProcessor()
        
        is_valid, error = await processor.validate_file(Path("/nonexistent/file.docx"))
        
        assert is_valid is False
        assert "not found" in error.lower()
    
    @pytest.mark.asyncio
    async def test_validate_file_wrong_extension(self):
        """Test validating a file with wrong extension."""
        processor = WordProcessor()
        
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
        processor = WordProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            f.write(b"not a valid docx file")
            file_path = Path(f.name)
        
        try:
            is_valid, error = await processor.validate_file(file_path)
            assert is_valid is False
            assert "corrupted" in error.lower() or "cannot be read" in error.lower()
        finally:
            file_path.unlink()


class TestWordProcessorWriteTranslated:
    """Tests for WordProcessor write_translated method."""
    
    @pytest.mark.asyncio
    async def test_write_translated_paragraphs(self):
        """Test writing translated text to paragraphs."""
        processor = WordProcessor()
        
        # Create a test Word file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            doc.add_paragraph("Hello")
            doc.add_paragraph("World")
            doc.save(f.name)
            input_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            # Extract text
            segments = await processor.extract_text(input_path)
            
            # Create translations
            translations = ["Xin chào", "Thế giới"]
            
            # Write translated (with auto_append=False to replace original text)
            success = await processor.write_translated(
                input_path, segments, translations, output_path, auto_append=False
            )
            
            assert success is True
            assert output_path.exists()
            
            # Verify the translated content
            doc = Document(str(output_path))
            texts = [p.text for p in doc.paragraphs if p.text.strip()]
            assert "Xin chào" in texts
            assert "Thế giới" in texts
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()
    
    @pytest.mark.asyncio
    async def test_write_translated_preserves_bold(self):
        """Test that writing preserves bold formatting."""
        processor = WordProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            para = doc.add_paragraph()
            run = para.add_run("Bold Text")
            run.bold = True
            doc.save(f.name)
            input_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(input_path)
            translations = ["Văn bản đậm"]
            
            # Write translated (with auto_append=False to replace original text)
            success = await processor.write_translated(
                input_path, segments, translations, output_path, auto_append=False
            )
            
            assert success is True
            
            # Verify bold is preserved
            doc = Document(str(output_path))
            para = doc.paragraphs[0]
            assert para.runs[0].bold is True
            assert para.runs[0].text == "Văn bản đậm"
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()
    
    @pytest.mark.asyncio
    async def test_write_translated_table_cells(self):
        """Test writing translated text to table cells."""
        processor = WordProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            table = doc.add_table(rows=1, cols=2)
            table.cell(0, 0).text = "Hello"
            table.cell(0, 1).text = "World"
            doc.save(f.name)
            input_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(input_path)
            table_segments = [s for s in segments if s.metadata.get("type") == "table_cell"]
            
            translations = ["Xin chào", "Thế giới"]
            
            # Write translated (with auto_append=False to replace original text)
            success = await processor.write_translated(
                input_path, table_segments, translations, output_path, auto_append=False
            )
            
            assert success is True
            
            # Verify table content
            doc = Document(str(output_path))
            table = doc.tables[0]
            assert table.cell(0, 0).text == "Xin chào"
            assert table.cell(0, 1).text == "Thế giới"
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()


class TestWordProcessorMergedCells:
    """Tests for WordProcessor handling of merged cells."""
    
    @pytest.mark.asyncio
    async def test_extract_merged_cells_horizontal(self):
        """Test that horizontally merged cells are extracted only once."""
        processor = WordProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            table = doc.add_table(rows=2, cols=3)
            
            # Merge cells A1 and B1 (horizontal merge)
            a1 = table.cell(0, 0)
            b1 = table.cell(0, 1)
            a1.merge(b1)
            a1.text = "Merged A1-B1"
            
            table.cell(0, 2).text = "C1"
            table.cell(1, 0).text = "A2"
            table.cell(1, 1).text = "B2"
            table.cell(1, 2).text = "C2"
            doc.save(f.name)
            file_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(file_path)
            table_segments = [s for s in segments if s.metadata.get("type") == "table_cell"]
            
            # Should have 5 segments (merged cell counts as 1, plus 4 other cells)
            assert len(table_segments) == 5
            
            texts = [s.text for s in table_segments]
            assert "Merged A1-B1" in texts
            assert texts.count("Merged A1-B1") == 1  # Should appear only once
            assert "C1" in texts
            assert "A2" in texts
            assert "B2" in texts
            assert "C2" in texts
        finally:
            file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_write_translated_merged_cells(self):
        """Test writing translations to merged cells."""
        processor = WordProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            table = doc.add_table(rows=1, cols=3)
            
            # Merge cells A1 and B1
            a1 = table.cell(0, 0)
            b1 = table.cell(0, 1)
            a1.merge(b1)
            a1.text = "Merged"
            table.cell(0, 2).text = "Single"
            doc.save(f.name)
            input_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(input_path)
            table_segments = [s for s in segments if s.metadata.get("type") == "table_cell"]
            
            # Create translations for each segment
            translations = []
            for seg in table_segments:
                if seg.text == "Merged":
                    translations.append("Đã hợp nhất")
                elif seg.text == "Single":
                    translations.append("Đơn lẻ")
            
            # Write translated (with auto_append=False to replace original text)
            success = await processor.write_translated(
                input_path, table_segments, translations, output_path, auto_append=False
            )
            
            assert success is True
            
            # Verify content
            doc = Document(str(output_path))
            table = doc.tables[0]
            # Merged cell should have translated text
            assert "Đã hợp nhất" in table.cell(0, 0).text
            assert table.cell(0, 2).text == "Đơn lẻ"
        finally:
            input_path.unlink()
            if output_path.exists():
                output_path.unlink()


class TestWordProcessorNestedTables:
    """Tests for WordProcessor handling of nested tables."""
    
    @pytest.mark.asyncio
    async def test_extract_nested_tables(self):
        """Test extracting text from nested tables."""
        processor = WordProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            
            # Create outer table
            outer_table = doc.add_table(rows=1, cols=2)
            outer_table.cell(0, 0).text = "Outer Cell"
            
            # Add nested table in second cell
            inner_cell = outer_table.cell(0, 1)
            # Clear default paragraph and add nested table
            inner_cell.paragraphs[0].clear()
            nested_table = inner_cell.add_table(rows=1, cols=2)
            nested_table.cell(0, 0).text = "Nested A"
            nested_table.cell(0, 1).text = "Nested B"
            
            doc.save(f.name)
            file_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(file_path)
            table_segments = [s for s in segments if s.metadata.get("type") == "table_cell"]
            
            texts = [s.text for s in table_segments]
            
            # Should extract from both outer and nested tables
            assert "Outer Cell" in texts
            assert "Nested A" in texts
            assert "Nested B" in texts
            
            # Check that nested table segments have correct location prefix
            nested_segments = [s for s in table_segments if "nested" in s.location]
            assert len(nested_segments) == 2
        finally:
            file_path.unlink()


class TestWordProcessorHeaderFooterTables:
    """Tests for WordProcessor handling of tables in headers/footers."""
    
    @pytest.mark.asyncio
    async def test_extract_table_in_header(self):
        """Test extracting text from tables in document header."""
        from docx.shared import Inches
        processor = WordProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            
            # Add content to body
            doc.add_paragraph("Body content")
            
            # Add table to header (requires width parameter)
            section = doc.sections[0]
            header = section.header
            header_table = header.add_table(rows=1, cols=2, width=Inches(6))
            header_table.cell(0, 0).text = "Header Cell 1"
            header_table.cell(0, 1).text = "Header Cell 2"
            
            doc.save(f.name)
            file_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(file_path)
            
            # Check for header table segments
            header_table_segments = [
                s for s in segments 
                if s.metadata.get("type") == "table_cell" 
                and s.metadata.get("header_footer") == "header"
            ]
            
            assert len(header_table_segments) == 2
            texts = [s.text for s in header_table_segments]
            assert "Header Cell 1" in texts
            assert "Header Cell 2" in texts
        finally:
            file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_extract_table_in_footer(self):
        """Test extracting text from tables in document footer."""
        from docx.shared import Inches
        processor = WordProcessor()
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            doc = Document()
            
            # Add content to body
            doc.add_paragraph("Body content")
            
            # Add table to footer (requires width parameter)
            section = doc.sections[0]
            footer = section.footer
            footer_table = footer.add_table(rows=1, cols=2, width=Inches(6))
            footer_table.cell(0, 0).text = "Footer Cell 1"
            footer_table.cell(0, 1).text = "Footer Cell 2"
            
            doc.save(f.name)
            file_path = Path(f.name)
        
        try:
            segments = await processor.extract_text(file_path)
            
            # Check for footer table segments
            footer_table_segments = [
                s for s in segments 
                if s.metadata.get("type") == "table_cell" 
                and s.metadata.get("header_footer") == "footer"
            ]
            
            assert len(footer_table_segments) == 2
            texts = [s.text for s in footer_table_segments]
            assert "Footer Cell 1" in texts
            assert "Footer Cell 2" in texts
        finally:
            file_path.unlink()
