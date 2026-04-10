"""
Excel Document Processor Module

Adapter that wraps the existing ExcelProcessor to implement the DocumentProcessor interface.
Provides unified text extraction and translation writing for Excel files.
"""

import logging
from pathlib import Path
from typing import List, Optional
import asyncio

from .document_processor import (
    DocumentProcessor,
    DocumentType,
    TextSegment,
    apply_output_mode,
)
from .excel_processor import ExcelProcessor, CellData


class ExcelDocumentProcessor(DocumentProcessor):
    """
    Document processor for Microsoft Excel files (.xlsx).
    
    Wraps the existing ExcelProcessor to provide the unified DocumentProcessor interface
    while preserving all Excel-specific functionality like format preservation.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the Excel document processor.
        
        Args:
            logger: Logger instance for logging operations
        """
        self.logger = logger or logging.getLogger(__name__)
        self._excel_processor = ExcelProcessor(logger=self.logger)
    
    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return ['.xlsx']
    
    @property
    def document_type(self) -> DocumentType:
        """Return the document type this processor handles."""
        return DocumentType.EXCEL
    
    async def extract_text(self, file_path: Path) -> List[TextSegment]:
        """
        Extract all translatable text segments from the Excel document.
        
        Extracts text from all cells across all worksheets, excluding formulas.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            List of TextSegment objects containing cell text and metadata
            
        Raises:
            ValueError: If the file cannot be loaded
        """
        workbook = await self._excel_processor.load_workbook(file_path)
        if workbook is None:
            raise ValueError(f"Failed to load Excel file: {file_path}")
        
        segments: List[TextSegment] = []
        segment_id = 0
        
        for worksheet in workbook.worksheets:
            cells = await self._excel_processor.iterate_cells_in_worksheet(worksheet)
            
            for cell_data in cells:
                segment = TextSegment(
                    id=str(segment_id),
                    text=str(cell_data.value),
                    location=f"{cell_data.worksheet_name}!{cell_data.cell.coordinate}",
                    metadata={
                        "worksheet_name": cell_data.worksheet_name,
                        "row": cell_data.row,
                        "column": cell_data.column,
                        "cell_coordinate": cell_data.cell.coordinate,
                    }
                )
                segments.append(segment)
                segment_id += 1
        
        self.logger.info(f"Extracted {len(segments)} text segments from {file_path.name}")
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
        Write translated text back to Excel document, preserving formatting.

        Args:
            file_path: Path to the original Excel file
            segments: List of original text segments
            translations: List of translated texts (same order as segments)
            output_path: Path where the translated document should be saved
            output_mode: One of "replace", "append", "prepend", "interleave", "interleave_reverse" (default: "replace")
            
        Returns:
            True if writing succeeded, False otherwise
        """
        try:
            # Always load fresh from file to avoid shared state issues
            # during concurrent processing of multiple files
            workbook = await self._excel_processor.load_workbook(file_path)
            if workbook is None:
                self.logger.error(f"Failed to load workbook for writing: {file_path}")
                return False
            
            # Create a mapping of segment locations to (original_text, translation)
            translation_map = {}
            for segment, translation in zip(segments, translations):
                ws_name = segment.metadata.get("worksheet_name")
                row = segment.metadata.get("row")
                col = segment.metadata.get("column")
                if ws_name and row and col:
                    translation_map[(ws_name, row, col)] = (segment.text, translation)
            
            # Update cells with translations (applying output mode logic)
            for worksheet in workbook.worksheets:
                for row in worksheet.iter_rows():
                    for cell in row:
                        key = (worksheet.title, cell.row, cell.column)
                        if key in translation_map:
                            original_text, translated_text = translation_map[key]
                            final_text = apply_output_mode(original_text, translated_text, output_mode)
                            await self._excel_processor.update_cell(
                                cell, 
                                final_text
                            )
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the workbook
            await asyncio.to_thread(workbook.save, str(output_path))
            
            self.logger.info(f"Saved translated Excel to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write translated Excel: {e}")
            return False
    
    async def validate_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate that the Excel file can be processed.
        
        Checks for:
        - File existence
        - File readability (not password protected or corrupted)
        
        Args:
            file_path: Path to the Excel file to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        
        if not file_path.suffix.lower() in self.supported_extensions:
            return False, f"Unsupported file format: {file_path.suffix}"
        
        try:
            # Try to load the workbook to check for corruption/password protection
            workbook = await self._excel_processor.load_workbook(file_path)
            if workbook is None:
                return False, "Failed to open Excel file. The file may be corrupted or password protected."
            
            # Check if there are any worksheets
            if len(workbook.worksheets) == 0:
                return False, "Excel file contains no worksheets."
            
            return True, None
            
        except Exception as e:
            error_msg = str(e).lower()
            if "password" in error_msg or "encrypted" in error_msg:
                return False, "This file is password protected. Please remove the password and try again."
            return False, f"Failed to read Excel file: {str(e)}"
