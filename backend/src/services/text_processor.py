"""
Text Document Processor Module

Provides document processing for plain text (.txt) files.
Extracts text by splitting into paragraphs (double-newline separated)
and writes translations back preserving the paragraph structure.
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


class TextProcessor(DocumentProcessor):
    """
    Document processor for plain text files (.txt).

    Extracts text by splitting content into paragraphs separated by
    double newlines. Each paragraph becomes a translatable TextSegment.

    Preserves paragraph structure during translation writing.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the text processor.

        Args:
            logger: Logger instance for logging operations
        """
        self.logger = logger or logging.getLogger(__name__)

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return ['.txt']

    @property
    def document_type(self) -> DocumentType:
        """Return the document type this processor handles."""
        return DocumentType.TEXT

    async def extract_text(self, file_path: Path) -> List[TextSegment]:
        """
        Extract all translatable text segments from a plain text file.

        Splits content by double newlines into paragraphs. Each non-empty
        paragraph becomes a TextSegment.

        Args:
            file_path: Path to the text file

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
            raise ValueError(f"Failed to read text file: {file_path}. Error: {str(e)}")

        paragraphs = content.split("\n\n")
        segments: List[TextSegment] = []

        for idx, paragraph in enumerate(paragraphs):
            text = paragraph.strip()
            if text:
                segment = TextSegment(
                    id=str(idx),
                    text=text,
                    location=f"Paragraph {idx + 1}",
                    metadata={
                        "type": "paragraph",
                        "paragraph_idx": idx,
                    }
                )
                segments.append(segment)

        self.logger.info(
            f"Extracted {len(segments)} text segments from {file_path.name}"
        )
        return segments

    async def write_translated(
        self,
        file_path: Path,
        segments: List[TextSegment],
        translations: List[str],
        output_path: Path,
        output_mode: str = "replace"
    ) -> bool:
        """
        Write translated text back to a plain text file.

        Args:
            file_path: Path to the original text file
            segments: List of original text segments
            translations: List of translated texts (same order as segments)
            output_path: Path where the translated file should be saved
            output_mode: One of "replace", "append", "prepend", "interleave", "interleave_reverse" (default: "replace")

        Returns:
            True if writing succeeded, False otherwise
        """
        try:
            output_parts = []
            for seg, trans in zip(segments, translations):
                final_text = apply_output_mode(
                    seg.text, trans, output_mode
                )
                output_parts.append(final_text)

            output_content = "\n\n".join(output_parts)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(
                output_path.write_text, output_content, encoding="utf-8"
            )

            self.logger.info(f"Saved translated text file to: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to write translated text file: {e}")
            return False

    async def validate_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate that the text file can be processed.

        Checks for:
        - File existence
        - Correct extension
        - File is readable as text
        - File has non-whitespace content

        Args:
            file_path: Path to the text file to validate

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
            return False, f"Failed to read text file: {str(e)}"

        if not content.strip():
            return False, "Text file contains no content."

        return True, None
