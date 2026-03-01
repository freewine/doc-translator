"""
PDF Document Processor Module

Provides document processing for PDF (.pdf) files.
Extracts text with position and styling information while preserving
layout, images, and vector graphics during translation writing.
"""

import logging
from pathlib import Path
from typing import List, Optional, Any
import asyncio

import fitz  # PyMuPDF

from .document_processor import (
    DocumentProcessor,
    DocumentType,
    TextSegment,
    apply_output_mode,
)


class PDFProcessor(DocumentProcessor):
    """
    Document processor for PDF files (.pdf).
    
    Extracts text from:
    - Text blocks with bounding boxes
    - Font information where available
    - Reading order preservation
    
    Preserves formatting during translation writing:
    - Original layout and page structure
    - Font size and color where possible
    - Embedded images and vector graphics
    
    Note: This processor only works with text-based PDFs.
    Scanned/image-only PDFs are detected and rejected with an appropriate error.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the PDF document processor.
        
        Args:
            logger: Logger instance for logging operations
        """
        self.logger = logger or logging.getLogger(__name__)
        self._current_document: Optional[fitz.Document] = None

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return ['.pdf']
    
    @property
    def document_type(self) -> DocumentType:
        """Return the document type this processor handles."""
        return DocumentType.PDF

    async def extract_text(self, file_path: Path) -> List[TextSegment]:
        """
        Extract all translatable text segments from the PDF document.
        
        Extracts text blocks with position information for reconstruction.
        Each text block becomes a segment with metadata about its position,
        font, and styling.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of TextSegment objects containing text and metadata
            
        Raises:
            ValueError: If the file cannot be loaded or is scanned/image-only
        """
        try:
            document = await asyncio.to_thread(fitz.open, str(file_path))
        except Exception as e:
            raise ValueError(f"Failed to load PDF file: {file_path}. Error: {str(e)}")
        
        self._current_document = document
        segments: List[TextSegment] = []
        segment_id = 0
        
        for page_idx in range(len(document)):
            page = document[page_idx]
            page_segments = self._extract_page_segments(page, page_idx, segment_id)
            segments.extend(page_segments)
            segment_id += len(page_segments)
        
        self.logger.info(f"Extracted {len(segments)} text segments from {file_path.name}")
        return segments
    
    def _extract_page_segments(
        self,
        page: fitz.Page,
        page_idx: int,
        start_segment_id: int
    ) -> List[TextSegment]:
        """
        Extract text segments from a single PDF page.
        
        Uses PyMuPDF's text extraction with detailed block information
        to capture position and styling data.
        """
        segments = []
        segment_id = start_segment_id
        
        # Get text blocks with detailed information
        # dict format gives us blocks with spans containing font info
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        
        for block_idx, block in enumerate(text_dict.get("blocks", [])):
            # Skip image blocks
            if block.get("type") != 0:  # type 0 is text, type 1 is image
                continue
            
            block_segments = self._extract_block_segments(
                block, page_idx, block_idx, segment_id
            )
            segments.extend(block_segments)
            segment_id += len(block_segments)
        
        return segments
    
    def _extract_block_segments(
        self,
        block: dict,
        page_idx: int,
        block_idx: int,
        start_segment_id: int
    ) -> List[TextSegment]:
        """
        Extract text segments from a text block.
        
        A block contains lines, and each line contains spans with text and font info.
        We create one segment per line to maintain reading order and allow
        proper reconstruction.
        """
        segments = []
        segment_id = start_segment_id
        
        bbox = block.get("bbox", (0, 0, 0, 0))
        
        for line_idx, line in enumerate(block.get("lines", [])):
            line_text_parts = []
            spans_metadata = []
            line_bbox = line.get("bbox", bbox)
            
            for span_idx, span in enumerate(line.get("spans", [])):
                span_text = span.get("text", "")
                if span_text:
                    line_text_parts.append(span_text)
                    
                    # Capture span metadata for format preservation
                    span_meta = {
                        "span_idx": span_idx,
                        "text": span_text,
                        "font": span.get("font", ""),
                        "size": span.get("size", 12),
                        "color": span.get("color", 0),  # Color as integer
                        "flags": span.get("flags", 0),  # Font flags (bold, italic, etc.)
                        "bbox": span.get("bbox", line_bbox),
                        "origin": span.get("origin", (line_bbox[0], line_bbox[1])),
                    }
                    spans_metadata.append(span_meta)
            
            line_text = "".join(line_text_parts).strip()
            
            if line_text:
                segment = TextSegment(
                    id=str(segment_id),
                    text=line_text,
                    location=f"Page {page_idx + 1}, Block {block_idx + 1}, Line {line_idx + 1}",
                    metadata={
                        "type": "text_line",
                        "page_idx": page_idx,
                        "block_idx": block_idx,
                        "line_idx": line_idx,
                        "block_bbox": bbox,
                        "line_bbox": line_bbox,
                        "spans": spans_metadata,
                    }
                )
                segments.append(segment)
                segment_id += 1
        
        return segments


    async def write_translated(
        self,
        file_path: Path,
        segments: List[TextSegment],
        translations: List[str],
        output_path: Path,
        auto_append: bool = False,
        interleaved_mode: bool = False
    ) -> bool:
        """
        Write translated text back to PDF document, preserving formatting.
        
        Output modes (mutually exclusive):
        - Replace: translated text replaces original (default)
        - Append: translated text appended after original (auto_append=True)
        - Interleaved: original and translated lines interleaved (interleaved_mode=True)
        
        Strategy:
        1. For each text segment, redact (white out) the original text area
        2. Insert the translated text at the same position
        3. Match font size and color where possible
        4. Preserve all images and vector graphics
        
        Args:
            file_path: Path to the original PDF file
            segments: List of original text segments
            translations: List of translated texts (same order as segments)
            output_path: Path where the translated document should be saved
            auto_append: Whether to append translation to original text (default: False)
            interleaved_mode: Whether to interleave original and translated lines (default: False)
            
        Returns:
            True if writing succeeded, False otherwise
        """
        try:
            # Load document if not already loaded
            document = self._current_document
            if document is None:
                document = await asyncio.to_thread(fitz.open, str(file_path))
            
            # Create translation map with output mode applied
            translation_map = {}
            for seg, trans in zip(segments, translations):
                final_text = apply_output_mode(seg.text, trans, auto_append, interleaved_mode)
                translation_map[seg.id] = final_text
            
            # Group segments by page for efficient processing
            segments_by_page: dict[int, List[tuple[TextSegment, str]]] = {}
            for segment in segments:
                translation = translation_map.get(segment.id)
                if translation is None:
                    continue
                page_idx = segment.metadata.get("page_idx", 0)
                if page_idx not in segments_by_page:
                    segments_by_page[page_idx] = []
                segments_by_page[page_idx].append((segment, translation))
            
            # Process each page
            for page_idx, page_segments in segments_by_page.items():
                if page_idx >= len(document):
                    self.logger.warning(f"Page index {page_idx} out of range")
                    continue
                
                page = document[page_idx]
                await self._write_page_translations(page, page_segments)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the document
            await asyncio.to_thread(document.save, str(output_path))
            
            self.logger.info(f"Saved translated PDF document to: {output_path}")
            
            # Close and clear the cached document
            document.close()
            self._current_document = None
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write translated PDF document: {e}")
            return False

    async def _write_page_translations(
        self,
        page: fitz.Page,
        page_segments: List[tuple[TextSegment, str]]
    ) -> None:
        """
        Write translations to a single PDF page.
        
        For each segment:
        1. Redact the original text area with white fill
        2. Insert translated text at the same position
        """
        # First pass: add redaction annotations for all original text areas
        for segment, translation in page_segments:
            spans = segment.metadata.get("spans", [])
            if not spans:
                continue
            
            # Get the bounding box for the entire line
            line_bbox = segment.metadata.get("line_bbox")
            if line_bbox:
                # Add redaction annotation (white rectangle over original text)
                rect = fitz.Rect(line_bbox)
                # Expand rect slightly to ensure complete coverage
                rect = rect + (-1, -1, 1, 1)
                page.add_redact_annot(rect, fill=(1, 1, 1))  # White fill
        
        # Apply all redactions at once
        page.apply_redactions()
        
        # Second pass: insert translated text
        for segment, translation in page_segments:
            spans = segment.metadata.get("spans", [])
            if not spans:
                continue
            
            # Get font info from first span
            first_span = spans[0]
            font_size = first_span.get("size", 12)
            font_color = self._int_to_rgb(first_span.get("color", 0))
            
            # Get position from line bbox or span origin
            line_bbox = segment.metadata.get("line_bbox")
            if line_bbox:
                # Position text at the start of the line
                x = line_bbox[0]
                # Adjust y position (PDF coordinates have origin at bottom-left)
                # The bbox y values are from top, so we use the bottom of the bbox
                y = line_bbox[3] - 2  # Small offset for baseline
                
                # Calculate available width to prevent text overflow
                page_width = page.rect.width
                right_margin = 20  # Small margin from page edge
                available_width = page_width - x - right_margin
                
                # Use original line width as reference, but cap at available space
                original_width = line_bbox[2] - line_bbox[0]
                text_width = min(max(original_width, 100), available_width)
                
                # Insert translated text using text writer for better Unicode support
                self._insert_unicode_text(page, x, y, translation, font_size, font_color, text_width)

    def _insert_unicode_text(
        self,
        page: fitz.Page,
        x: float,
        y: float,
        text: str,
        font_size: float,
        color: tuple[float, float, float],
        max_width: float
    ) -> None:
        """
        Insert text with full Unicode support using TextWriter.
        
        PyMuPDF's built-in fonts have limited Unicode support.
        Using TextWriter with a proper font allows Vietnamese and other
        Unicode characters to be rendered correctly.
        
        Args:
            page: The PDF page to insert text into
            x: X coordinate for text insertion
            y: Y coordinate for text insertion
            text: The text to insert
            font_size: Font size in points
            color: RGB color tuple (0-1 range)
            max_width: Maximum width available for text (prevents overflow)
        """
        try:
            # Create a text writer for the page
            tw = fitz.TextWriter(page.rect)
            
            # Use a font with good Unicode support
            # fitz.Font() without arguments uses a built-in font with Unicode support
            font = fitz.Font("helv")  # Start with Helvetica
            
            # Try to append text - if it fails due to missing glyphs,
            # fall back to a different approach
            try:
                tw.append((x, y), text, font=font, fontsize=font_size)
                tw.write_text(page, color=color)
            except Exception:
                # Fallback: use insert_htmlbox which handles Unicode better
                # Use calculated max_width to prevent text overflow
                rect = fitz.Rect(x, y - font_size, x + max_width, y + font_size * 2)
                css = f"* {{font-size: {font_size}pt; color: rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)}); font-family: sans-serif;}}"
                page.insert_htmlbox(rect, text, css=css)
        except Exception as e:
            self.logger.warning(f"Failed to insert Unicode text: {e}")
            # Last resort: simple insert_text
            try:
                page.insert_text(
                    point=(x, y),
                    text=text,
                    fontsize=font_size,
                    color=color,
                )
            except Exception as e2:
                self.logger.error(f"All text insertion methods failed: {e2}")

    def _int_to_rgb(self, color_int: int) -> tuple[float, float, float]:
        """
        Convert integer color value to RGB tuple (0-1 range).
        
        PyMuPDF stores colors as integers in BGR format.
        """
        if color_int == 0:
            return (0, 0, 0)  # Black
        
        # Extract RGB components
        b = (color_int >> 16) & 0xFF
        g = (color_int >> 8) & 0xFF
        r = color_int & 0xFF
        
        return (r / 255.0, g / 255.0, b / 255.0)


    async def validate_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate that the PDF file can be processed.
        
        Checks for:
        - File existence
        - Password protection
        - File corruption
        - Scanned/image-only PDFs (no extractable text)
        
        Args:
            file_path: Path to the PDF file to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        
        if file_path.suffix.lower() not in self.supported_extensions:
            return False, f"Unsupported file format: {file_path.suffix}"
        
        try:
            # Try to open the document
            document = await asyncio.to_thread(fitz.open, str(file_path))
        except Exception as e:
            error_msg = str(e).lower()
            if "password" in error_msg or "encrypted" in error_msg:
                return False, "This file is password protected. Please remove the password and try again."
            return False, f"This file appears to be corrupted and cannot be read."
        
        try:
            # Check if document is encrypted/password protected
            if document.is_encrypted:
                document.close()
                return False, "This file is password protected. Please remove the password and try again."
            
            # Check if document has any pages
            if len(document) == 0:
                document.close()
                return False, "PDF document contains no pages."
            
            # Check for extractable text content
            total_text_length = 0
            total_images = 0
            
            for page_idx in range(len(document)):
                page = document[page_idx]
                
                # Get text content
                text = page.get_text("text").strip()
                total_text_length += len(text)
                
                # Count images on the page
                image_list = page.get_images()
                total_images += len(image_list)
            
            document.close()
            
            # Determine if this is a scanned PDF
            # A scanned PDF typically has images but little to no extractable text
            if total_text_length < 10:  # Less than 10 characters of text
                if total_images > 0:
                    return False, "This PDF contains only scanned images. Please use OCR software to convert it first."
                else:
                    return False, "PDF document contains no translatable text content."
            
            return True, None
            
        except Exception as e:
            try:
                document.close()
            except Exception:
                pass
            error_msg = str(e).lower()
            if "password" in error_msg or "encrypted" in error_msg:
                return False, "This file is password protected. Please remove the password and try again."
            return False, f"Failed to read PDF file: {str(e)}"

    def _is_scanned_pdf(self, document: fitz.Document) -> bool:
        """
        Detect if a PDF is scanned (image-only) without extractable text.
        
        A scanned PDF typically:
        - Has one large image per page
        - Has little to no extractable text
        - May have OCR text layer (which we can use)
        
        Returns:
            True if the PDF appears to be scanned without usable text
        """
        total_text_chars = 0
        total_pages = len(document)
        pages_with_large_images = 0
        
        for page_idx in range(total_pages):
            page = document[page_idx]
            
            # Get text content
            text = page.get_text("text").strip()
            total_text_chars += len(text)
            
            # Check for large images (typical of scanned pages)
            images = page.get_images()
            page_rect = page.rect
            page_area = page_rect.width * page_rect.height
            
            for img in images:
                # Get image dimensions
                xref = img[0]
                try:
                    img_info = document.extract_image(xref)
                    if img_info:
                        img_width = img_info.get("width", 0)
                        img_height = img_info.get("height", 0)
                        img_area = img_width * img_height
                        
                        # If image covers most of the page, it's likely a scan
                        if img_area > page_area * 0.5:
                            pages_with_large_images += 1
                            break
                except Exception:
                    pass
        
        # Consider it scanned if:
        # - Most pages have large images AND
        # - Very little text is extractable
        avg_chars_per_page = total_text_chars / max(total_pages, 1)
        scanned_page_ratio = pages_with_large_images / max(total_pages, 1)
        
        return scanned_page_ratio > 0.5 and avg_chars_per_page < 50
