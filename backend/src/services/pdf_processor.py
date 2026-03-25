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

    # Built-in font mapping: (family, bold, italic) -> PyMuPDF font code
    _FONT_MAP = {
        ("sans", False, False): "helv",
        ("sans", True, False): "hebo",
        ("sans", False, True): "heit",
        ("sans", True, True): "hebi",
        ("serif", False, False): "tiro",
        ("serif", True, False): "tibo",
        ("serif", False, True): "tiit",
        ("serif", True, True): "tibi",
        ("mono", False, False): "cour",
        ("mono", True, False): "cobo",
        ("mono", False, True): "coit",
        ("mono", True, True): "cobi",
    }

    # Keywords for font family detection from font name
    _MONO_KEYWORDS = ("courier", "mono", "consolas", "menlo", "firacode", "inconsolata")
    _SERIF_KEYWORDS = ("times", "serif", "garamond", "georgia", "palatino", "cambria", "book")

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the PDF document processor.

        Args:
            logger: Logger instance for logging operations
        """
        self.logger = logger or logging.getLogger(__name__)
        self._current_document: Optional[fitz.Document] = None
        self._font_cache: dict[str, fitz.Font] = {}
        self._page_bg_cache: dict[int, tuple[float, float, float]] = {}

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
        self._extract_document_fonts(document)
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


    def _build_span_html(self, spans: list[dict], translated_text: str) -> str:
        """
        Build HTML with per-span formatting for multi-span lines.

        Distributes translated text proportionally across original span
        boundaries and wraps each portion in a <span> with the original
        span's CSS styling.
        """
        portions = self._distribute_text_to_spans(spans, translated_text)
        html_parts = []
        for span, text_portion in zip(spans, portions):
            css = self._get_css_for_span(span)
            escaped = text_portion.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            escaped = escaped.replace("\n", "<br/>")
            html_parts.append(f'<span style="{css}">{escaped}</span>')
        return "".join(html_parts)

    def _distribute_text_to_spans(
        self, spans: list[dict], translated_text: str
    ) -> list[str]:
        """
        Distribute translated text proportionally across spans.

        Uses original span character ratios, splitting at word boundaries
        when possible.
        """
        if len(spans) <= 1:
            return [translated_text]

        # Calculate character ratios from original spans
        original_lengths = [max(len(s.get("text", "")), 1) for s in spans]
        total_original = sum(original_lengths)
        ratios = [length / total_original for length in original_lengths]

        words = translated_text.split(" ")
        total_words = len(words)
        portions: list[str] = []
        word_idx = 0

        for i, ratio in enumerate(ratios):
            if i == len(ratios) - 1:
                # Last span gets remaining words
                portions.append(" ".join(words[word_idx:]))
            else:
                # Allocate words proportionally
                target_words = max(1, round(ratio * total_words))
                end_idx = min(word_idx + target_words, total_words)
                portions.append(" ".join(words[word_idx:end_idx]))
                word_idx = end_idx

        return portions

    def _detect_background_color(
        self, page: fitz.Page, page_idx: int
    ) -> tuple[float, float, float]:
        """
        Detect the background color of a page by sampling edge pixels.

        Caches result per page index since most pages have uniform backgrounds.
        Returns RGB tuple in 0-1 range.
        """
        if page_idx in self._page_bg_cache:
            return self._page_bg_cache[page_idx]

        bg_color = (1.0, 1.0, 1.0)  # default white
        try:
            # Render a small strip from the top-left corner
            clip = fitz.Rect(0, 0, min(50, page.rect.width), min(50, page.rect.height))
            pix = page.get_pixmap(clip=clip, dpi=36)
            # Sample corner pixels (likely background)
            samples: list[tuple[int, ...]] = []
            for sx, sy in [(0, 0), (pix.width - 1, 0), (0, pix.height - 1)]:
                sx = max(0, min(sx, pix.width - 1))
                sy = max(0, min(sy, pix.height - 1))
                pixel = pix.pixel(sx, sy)
                samples.append(pixel[:3])

            # Use the most common sampled color
            from collections import Counter
            most_common = Counter(samples).most_common(1)[0][0]
            bg_color = (most_common[0] / 255.0, most_common[1] / 255.0, most_common[2] / 255.0)
        except Exception as e:
            self.logger.debug(f"Background color detection failed for page {page_idx}: {e}")

        self._page_bg_cache[page_idx] = bg_color
        return bg_color

    def _extract_document_fonts(self, document: fitz.Document) -> None:
        """
        Extract embedded fonts from the document and cache them for reuse.

        Fonts that are fully embedded can be reused for rendering translated text.
        Subsetted or protected fonts are silently skipped.
        """
        self._font_cache.clear()
        seen_xrefs: set[int] = set()

        try:
            for page_idx in range(len(document)):
                page = document[page_idx]
                for font_info in page.get_fonts(full=True):
                    xref = font_info[0]
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)

                    try:
                        basename, _ext, _, content = document.extract_font(xref)
                        if content and basename:
                            font = fitz.Font(fontbuffer=content)
                            self._font_cache[basename] = font
                    except Exception:
                        continue
        except Exception as e:
            self.logger.debug(f"Font extraction failed: {e}")

    async def write_translated(
        self,
        file_path: Path,
        segments: List[TextSegment],
        translations: List[str],
        output_path: Path,
        output_mode: str = "replace"
    ) -> bool:
        """
        Write translated text back to PDF document, preserving formatting.

        Args:
            file_path: Path to the original PDF file
            segments: List of original text segments
            translations: List of translated texts (same order as segments)
            output_path: Path where the translated document should be saved
            output_mode: One of "replace", "append", "interleaved" (default: "replace")
            
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
                final_text = apply_output_mode(seg.text, trans, output_mode)
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
            
            # Close and clear cached state
            document.close()
            self._current_document = None
            self._font_cache.clear()
            self._page_bg_cache.clear()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write translated PDF document: {e}")
            return False

    def _calculate_output_rect(
        self,
        line_bbox: tuple,
        num_lines: int,
        font_size: float,
        page_height: float,
        next_segment_top: float | None,
    ) -> tuple[fitz.Rect, float]:
        """
        Calculate expanded rect and adjusted font size for multi-line output.

        For append/interleaved modes, the output text has more lines than the
        original. This method expands the rect downward and reduces font size
        if needed to avoid overlapping with the next segment.

        Returns:
            Tuple of (expanded_rect, adjusted_font_size)
        """
        original_rect = fitz.Rect(line_bbox)

        if num_lines <= 1:
            return original_rect, font_size

        original_height = original_rect.height
        line_spacing = 1.3
        needed_height = font_size * line_spacing * num_lines

        # Determine max available vertical space
        bottom_margin = 20
        max_bottom = page_height - bottom_margin
        if next_segment_top is not None:
            max_bottom = min(max_bottom, next_segment_top)

        available_height = max_bottom - original_rect.y0
        available_height = max(available_height, original_height)

        adjusted_font_size = font_size
        if needed_height > available_height:
            # Scale font down to fit, with a floor of 6pt
            adjusted_font_size = max(font_size * available_height / needed_height, 6.0)
            needed_height = available_height

        expanded_rect = fitz.Rect(
            original_rect.x0,
            original_rect.y0,
            original_rect.x1,
            original_rect.y0 + needed_height,
        )

        return expanded_rect, adjusted_font_size

    async def _write_page_translations(
        self,
        page: fitz.Page,
        page_segments: List[tuple[TextSegment, str]]
    ) -> None:
        """
        Write translations to a single PDF page.

        For each segment:
        1. Redact the original text area with detected background color
        2. Insert translated text at the same position with preserved formatting
        """
        # Pre-compute vertical ordering for next-segment-top lookup
        sorted_segments = sorted(
            page_segments,
            key=lambda ps: ps[0].metadata.get("line_bbox", (0, 0, 0, 0))[1]
        )
        next_top_map: dict[str, float] = {}
        for i, (seg, _) in enumerate(sorted_segments):
            if i + 1 < len(sorted_segments):
                next_bbox = sorted_segments[i + 1][0].metadata.get("line_bbox", (0, 0, 0, 0))
                next_top_map[seg.id] = next_bbox[1]

        # Detect background color for this page
        page_idx = page_segments[0][0].metadata.get("page_idx", 0) if page_segments else 0
        bg_color = self._detect_background_color(page, page_idx)

        # First pass: add redaction annotations for all original text areas
        for segment, translation in page_segments:
            spans = segment.metadata.get("spans", [])
            if not spans:
                continue

            # Get the bounding box for the entire line
            line_bbox = segment.metadata.get("line_bbox")
            if line_bbox:
                num_lines = translation.count('\n') + 1
                font_size = spans[0].get("size", 12)

                if num_lines > 1:
                    # Expand redaction area for multi-line output
                    expanded_rect, _ = self._calculate_output_rect(
                        line_bbox, num_lines, font_size,
                        page.rect.height, next_top_map.get(segment.id)
                    )
                    rect = expanded_rect + (-1, -1, 1, 1)
                else:
                    rect = fitz.Rect(line_bbox) + (-1, -1, 1, 1)

                page.add_redact_annot(rect, fill=bg_color)

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
                num_lines = translation.count('\n') + 1

                # Calculate available width to prevent text overflow
                page_width = page.rect.width
                right_margin = 20  # Small margin from page edge
                x = line_bbox[0]
                available_width = page_width - x - right_margin
                original_width = line_bbox[2] - line_bbox[0]
                text_width = min(max(original_width, 100), available_width)

                if num_lines > 1:
                    # Multi-line: use expanded rect with htmlbox rendering
                    expanded_rect, adjusted_font_size = self._calculate_output_rect(
                        line_bbox, num_lines, font_size,
                        page.rect.height, next_top_map.get(segment.id)
                    )
                    # Ensure rect uses full available width
                    output_rect = fitz.Rect(
                        expanded_rect.x0, expanded_rect.y0,
                        expanded_rect.x0 + text_width, expanded_rect.y1,
                    )
                    self._insert_unicode_text(
                        page, x, 0, translation, adjusted_font_size,
                        font_color, text_width, output_rect=output_rect,
                        spans_metadata=spans,
                    )
                else:
                    # Single line
                    y = line_bbox[3] - 2  # Small offset for baseline
                    self._insert_unicode_text(
                        page, x, y, translation, font_size, font_color,
                        text_width, spans_metadata=spans,
                    )

    def _insert_unicode_text(
        self,
        page: fitz.Page,
        x: float,
        y: float,
        text: str,
        font_size: float,
        color: tuple[float, float, float],
        max_width: float,
        output_rect: Optional[fitz.Rect] = None,
        spans_metadata: Optional[list[dict]] = None,
    ) -> None:
        """
        Insert text with full Unicode support and format preservation.

        For multi-span text, builds per-span HTML with individual styling.
        For single-line text, uses TextWriter with resolved font.
        For multi-line text (append/interleaved modes), uses insert_htmlbox.

        Args:
            page: The PDF page to insert text into
            x: X coordinate for text insertion (used for single-line)
            y: Y coordinate for text insertion (used for single-line)
            text: The text to insert
            font_size: Font size in points
            color: RGB color tuple (0-1 range)
            max_width: Maximum width available for text
            output_rect: Pre-calculated rect for multi-line rendering
            spans_metadata: Original span metadata list for per-span formatting
        """
        # Resolve font from first span metadata if available
        font_name = ""
        flags = 0
        if spans_metadata:
            font_name = spans_metadata[0].get("font", "")
            flags = spans_metadata[0].get("flags", 0)

        resolved_font, css_family, css_extra = self._resolve_font(font_name, flags)
        css = (
            f"* {{font-size: {font_size}pt; "
            f"color: rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)}); "
            f"font-family: {css_family}; {css_extra}}}"
        )

        # Multi-span path: build rich HTML with per-span formatting
        if spans_metadata and len(spans_metadata) > 1:
            html_content = self._build_span_html(spans_metadata, text)
            rect = output_rect or fitz.Rect(
                x, y - font_size, x + max_width, y + font_size * 2
            )
            try:
                page.insert_htmlbox(rect, html_content)
                return
            except Exception as e:
                self.logger.warning(f"Failed multi-span htmlbox insert: {e}")
                # Fall through to single-format rendering

        if output_rect is not None:
            # Multi-line path: use insert_htmlbox with expanded rect
            try:
                html_text = text.replace('\n', '<br/>')
                page.insert_htmlbox(output_rect, html_text, css=css)
                return
            except Exception as e:
                self.logger.warning(f"Failed to insert multi-line text via htmlbox: {e}")

        # Single-line path: use TextWriter with resolved font
        try:
            tw = fitz.TextWriter(page.rect)
            try:
                tw.append((x, y), text, font=resolved_font, fontsize=font_size)
                tw.write_text(page, color=color)
                return
            except Exception:
                # Fallback: try Helvetica for broad glyph coverage
                try:
                    tw2 = fitz.TextWriter(page.rect)
                    tw2.append((x, y), text, font=fitz.Font("helv"), fontsize=font_size)
                    tw2.write_text(page, color=color)
                    return
                except Exception:
                    pass
                # Fallback: use insert_htmlbox which handles Unicode/CJK better
                rect = fitz.Rect(x, y - font_size, x + max_width, y + font_size * 2)
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

    def _resolve_font(
        self, font_name: str, flags: int
    ) -> tuple[fitz.Font, str, str]:
        """
        Resolve original font metadata to the best available font.

        Args:
            font_name: Original font name from PDF span metadata
            flags: Font flags from PDF span metadata

        Returns:
            Tuple of (fitz.Font, css_family, css_extra_styles)
            css_extra_styles contains font-weight and font-style declarations.
        """
        is_bold = bool(flags & (1 << 4))
        is_italic = bool(flags & (1 << 1))

        # Try embedded font cache first
        if font_name and font_name in self._font_cache:
            try:
                font = self._font_cache[font_name]
                css_family = "sans-serif"
                css_extra = self._css_weight_style(is_bold, is_italic)
                return font, css_family, css_extra
            except Exception:
                pass

        # Determine family category
        name_lower = font_name.lower() if font_name else ""
        if any(kw in name_lower for kw in self._MONO_KEYWORDS) or (flags & (1 << 3)):
            family = "mono"
            css_family = "monospace"
        elif any(kw in name_lower for kw in self._SERIF_KEYWORDS) or (flags & (1 << 2)):
            family = "serif"
            css_family = "serif"
        else:
            family = "sans"
            css_family = "sans-serif"

        font_code = self._FONT_MAP.get((family, is_bold, is_italic), "helv")
        css_extra = self._css_weight_style(is_bold, is_italic)
        return fitz.Font(font_code), css_family, css_extra

    @staticmethod
    def _css_weight_style(is_bold: bool, is_italic: bool) -> str:
        parts = []
        if is_bold:
            parts.append("font-weight: bold;")
        if is_italic:
            parts.append("font-style: italic;")
        return " ".join(parts)

    def _get_css_for_span(self, span: dict) -> str:
        """Build inline CSS string from span metadata."""
        font_name = span.get("font", "")
        flags = span.get("flags", 0)
        size = span.get("size", 12)
        color = self._int_to_rgb(span.get("color", 0))
        _, css_family, css_extra = self._resolve_font(font_name, flags)
        return (
            f"font-size: {size}pt; "
            f"font-family: {css_family}; "
            f"color: rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)}); "
            f"{css_extra}"
        )

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
