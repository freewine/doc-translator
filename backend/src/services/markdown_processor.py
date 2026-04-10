"""
Markdown Document Processor Module

Provides document processing for Markdown (.md) files.
Extracts translatable text lines (headings, paragraphs, list items,
blockquotes) while preserving code blocks, front matter, and blank lines.
Writes translations back preserving the original document structure.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from .document_processor import (
    DocumentProcessor,
    DocumentType,
    TextSegment,
    apply_output_mode,
)


class MarkdownProcessor(DocumentProcessor):
    """
    Document processor for Markdown files (.md).

    Extracts translatable content line-by-line, skipping:
    - Fenced code blocks (``` delimited)
    - Front matter (--- delimited at file start)
    - Blank lines

    Translatable content includes headings, paragraphs, list items,
    and blockquotes. The full line (including markdown syntax like #, -, >)
    is sent to the LLM so it can preserve markdown formatting.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the markdown processor.

        Args:
            logger: Logger instance for logging operations
        """
        self.logger = logger or logging.getLogger(__name__)

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return ['.md']

    @property
    def document_type(self) -> DocumentType:
        """Return the document type this processor handles."""
        return DocumentType.MARKDOWN

    async def extract_text(self, file_path: Path) -> List[TextSegment]:
        """
        Extract all translatable text segments from a Markdown file.

        Parses line-by-line, skipping code blocks, front matter, and blank
        lines. Each translatable line becomes a TextSegment with metadata
        indicating its type and line index.

        Args:
            file_path: Path to the Markdown file

        Returns:
            List of TextSegment objects containing text and metadata

        Raises:
            ValueError: If the file cannot be read
        """
        try:
            content = await asyncio.to_thread(
                file_path.read_text, encoding="utf-8", errors="replace"
            )
        except Exception as e:
            raise ValueError(
                f"Failed to read Markdown file: {file_path}. Error: {str(e)}"
            )

        lines = content.split("\n")
        segments: List[TextSegment] = []
        segment_id = 0

        in_code_block = False
        in_front_matter = False
        front_matter_possible = True

        for line_idx, line in enumerate(lines):
            stripped = line.strip()

            # Handle front matter (--- at file start)
            if front_matter_possible and line_idx == 0 and stripped == "---":
                in_front_matter = True
                continue
            if in_front_matter:
                if stripped == "---":
                    in_front_matter = False
                continue
            front_matter_possible = False

            # Handle fenced code blocks
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            # Skip blank lines
            if not stripped:
                continue

            # Classify and extract translatable lines
            line_type = self._classify_line(stripped)
            segment = TextSegment(
                id=str(segment_id),
                text=line,
                location=f"Line {line_idx + 1}",
                metadata={
                    "type": line_type,
                    "line_idx": line_idx,
                }
            )
            segments.append(segment)
            segment_id += 1

        self.logger.info(
            f"Extracted {len(segments)} text segments from {file_path.name}"
        )
        return segments

    def _classify_line(self, stripped: str) -> str:
        """
        Classify a markdown line by its type.

        Args:
            stripped: The stripped line text

        Returns:
            Line type string: "heading", "list_item", "blockquote", or "paragraph"
        """
        if stripped.startswith("#"):
            return "heading"
        if (
            stripped.startswith("- ")
            or stripped.startswith("* ")
            or stripped.startswith("+ ")
            or (len(stripped) > 2 and stripped[0].isdigit() and ". " in stripped[:5])
        ):
            return "list_item"
        if stripped.startswith(">"):
            return "blockquote"
        return "paragraph"

    async def write_translated(
        self,
        file_path: Path,
        segments: List[TextSegment],
        translations: List[str],
        output_path: Path,
        output_mode: str = "replace"
    ) -> bool:
        """
        Write translated text back to a Markdown file, preserving structure.

        Args:
            file_path: Path to the original Markdown file
            segments: List of original text segments
            translations: List of translated texts (same order as segments)
            output_path: Path where the translated file should be saved
            output_mode: One of "replace", "append", "prepend", "interleave", "interleave_reverse" (default: "replace")

        Returns:
            True if writing succeeded, False otherwise
        """
        try:
            content = await asyncio.to_thread(
                file_path.read_text, encoding="utf-8", errors="replace"
            )
            lines = content.split("\n")

            # Build a map from line_idx to translated text
            translation_map: dict[int, str] = {}
            for seg, trans in zip(segments, translations):
                line_idx = seg.metadata.get("line_idx")
                if line_idx is not None:
                    final_text = apply_output_mode(
                        seg.text, trans, output_mode
                    )
                    translation_map[line_idx] = final_text

            # Replace translated lines, keep everything else as-is
            output_lines = []
            for line_idx, line in enumerate(lines):
                if line_idx in translation_map:
                    output_lines.append(translation_map[line_idx])
                else:
                    output_lines.append(line)

            output_content = "\n".join(output_lines)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(
                output_path.write_text, output_content, encoding="utf-8"
            )

            self.logger.info(f"Saved translated Markdown file to: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to write translated Markdown file: {e}")
            return False

    async def validate_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate that the Markdown file can be processed.

        Checks for:
        - File existence
        - Correct extension
        - File is readable as text
        - File has translatable content (not all code blocks)

        Args:
            file_path: Path to the Markdown file to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_path.exists():
            return False, f"File not found: {file_path}"

        if file_path.suffix.lower() not in self.supported_extensions:
            return False, f"Unsupported file format: {file_path.suffix}"

        try:
            content = await asyncio.to_thread(
                file_path.read_text, encoding="utf-8", errors="replace"
            )
        except Exception as e:
            return False, f"Failed to read Markdown file: {str(e)}"

        if not content.strip():
            return False, "Markdown file contains no content."

        # Check if there is any translatable content (not all code blocks)
        lines = content.split("\n")
        in_code_block = False
        in_front_matter = False
        has_translatable = False

        for line_idx, line in enumerate(lines):
            stripped = line.strip()

            if line_idx == 0 and stripped == "---":
                in_front_matter = True
                continue
            if in_front_matter:
                if stripped == "---":
                    in_front_matter = False
                continue

            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            if stripped:
                has_translatable = True
                break

        if not has_translatable:
            return False, "Markdown file contains no translatable content."

        return True, None
