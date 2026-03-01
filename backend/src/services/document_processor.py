"""
Document Processor Module

Provides abstract base class and data models for document processing.
Supports multiple document formats (Excel, Word, PowerPoint, PDF) through
a unified interface for text extraction and translation writing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Any


def apply_auto_append(
    original_text: str,
    translated_text: str,
    auto_append: bool
) -> str:
    """
    Apply auto-append logic to determine final output text.
    
    Args:
        original_text: Original text from document
        translated_text: Translated text
        auto_append: Whether to append or replace
        
    Returns:
        Final text to write to document
    """
    if not auto_append:
        return translated_text
    
    # If texts are equal (after stripping), no need to append (avoid duplication)
    if original_text.strip() == translated_text.strip():
        return translated_text
    
    # Append translated text to original
    return f"{original_text}\n{translated_text}"


def apply_interleaved_mode(
    original_text: str,
    translated_text: str
) -> str:
    """
    Apply interleaved mode logic to interleave original and translated lines.
    
    When interleaved mode is enabled, this function splits both original and
    translated text by newline characters and interleaves them line by line
    in the format: original_line_1, translated_line_1, original_line_2, etc.
    
    Args:
        original_text: Original text from document
        translated_text: Translated text
        
    Returns:
        Interleaved text with original and translated lines alternating
        
    Requirements:
        - 4.1: Split both original and translated text by newline characters
        - 4.2: Interleave lines in format {original_line_1}\\n{translated_line_1}\\n...
        - 4.3: Append remaining original lines if original has more lines
        - 4.4: Append remaining translated lines if translated has more lines
        - 4.5: Return original text only if texts are equal (no duplication)
    """
    # If texts are equal, no need to interleave (avoid duplication)
    # Requirement 4.5
    if original_text.strip() == translated_text.strip():
        return translated_text
    
    # Split by newline characters - Requirement 4.1
    original_lines = original_text.split('\n')
    translated_lines = translated_text.split('\n')
    
    result_lines = []
    max_lines = max(len(original_lines), len(translated_lines))
    
    # Interleave lines - Requirement 4.2
    # Handle unequal line counts - Requirements 4.3, 4.4
    for i in range(max_lines):
        if i < len(original_lines):
            result_lines.append(original_lines[i])
        if i < len(translated_lines):
            result_lines.append(translated_lines[i])
    
    return '\n'.join(result_lines)


def apply_output_mode(
    original_text: str,
    translated_text: str,
    auto_append: bool,
    interleaved_mode: bool
) -> str:
    """
    Apply the appropriate output mode to determine final text.
    
    Routes to the appropriate mode handler based on the flags:
    - Interleaved mode: interleave original and translated lines
    - Append mode: append translated text after original
    - Replace mode (default): return translated text only
    
    Args:
        original_text: Original text from document
        translated_text: Translated text
        auto_append: Whether to append translated text after original
        interleaved_mode: Whether to interleave lines
        
    Returns:
        Final text to write to document
        
    Requirements:
        - 4.6: Apply output mode consistently across all document types
    """
    if interleaved_mode:
        return apply_interleaved_mode(original_text, translated_text)
    elif auto_append:
        return apply_auto_append(original_text, translated_text, True)
    else:
        return translated_text


class DocumentType(str, Enum):
    """Enumeration of supported document types."""
    EXCEL = "excel"
    WORD = "word"
    POWERPOINT = "powerpoint"
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"


@dataclass
class TextSegment:
    """
    Represents a translatable text segment with metadata.
    
    Attributes:
        id: Unique identifier for the segment within the document
        text: Original text content to be translated
        location: Human-readable location (e.g., "Sheet1!A1", "Slide 1, Shape 2")
        metadata: Format-specific metadata for reconstruction during writing
    """
    id: str
    text: str
    location: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """
    Result of document processing operation.
    
    Attributes:
        success: Whether the processing completed successfully
        segments_total: Total number of text segments in the document
        segments_translated: Number of segments that were translated
        output_path: Path to the output file (if successful)
        error: Error message (if failed)
    """
    success: bool
    segments_total: int
    segments_translated: int
    output_path: Optional[Path] = None
    error: Optional[str] = None


class DocumentProcessor(ABC):
    """
    Abstract base class for document processors.
    
    Each document format (Excel, Word, PowerPoint, PDF) implements this interface
    to provide format-specific text extraction and translation writing while
    sharing the common translation infrastructure.
    """
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """
        Return list of supported file extensions.
        
        Returns:
            List of extensions including the dot (e.g., ['.docx'])
        """
        pass
    
    @property
    @abstractmethod
    def document_type(self) -> DocumentType:
        """
        Return the document type this processor handles.
        
        Returns:
            DocumentType enum value
        """
        pass
    
    @abstractmethod
    async def extract_text(self, file_path: Path) -> List[TextSegment]:
        """
        Extract all translatable text segments from the document.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            List of TextSegment objects containing text and metadata
            
        Raises:
            ValueError: If the file cannot be processed
        """
        pass
    
    @abstractmethod
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
        Write translated text back to document, preserving formatting.
        
        Output modes (mutually exclusive):
        - Replace: translated text replaces original (default)
        - Append: translated text appended after original (auto_append=True)
        - Interleaved: original and translated lines interleaved (interleaved_mode=True)
        
        Args:
            file_path: Path to the original document
            segments: List of original text segments
            translations: List of translated texts (same order as segments)
            output_path: Path where the translated document should be saved
            auto_append: Whether to append translation to original text (default: False)
            interleaved_mode: Whether to interleave original and translated lines (default: False)
            
        Returns:
            True if writing succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    async def validate_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate that the file can be processed.
        
        Checks for:
        - File existence and readability
        - Password protection
        - File corruption
        - Format-specific validation (e.g., scanned PDFs)
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if file can be processed
            - error_message: None if valid, otherwise description of the issue
        """
        pass
    
    def generate_output_filename(
        self,
        source_path: Path,
        language_suffix: str = "vi"
    ) -> str:
        """
        Generate output filename with language suffix.
        
        Args:
            source_path: Original file path
            language_suffix: Language code suffix (default: "vi")
            
        Returns:
            Filename with suffix before extension (e.g., "document_vi.docx")
        """
        return f"{source_path.stem}_{language_suffix}{source_path.suffix}"


class DocumentProcessorFactory:
    """
    Factory for creating appropriate document processor based on file type.
    
    Maintains a registry of processors mapped to their supported file extensions.
    Allows dynamic registration of new processors for extensibility.
    """
    
    def __init__(self):
        """Initialize the factory with an empty processor registry."""
        self._processors: dict[str, DocumentProcessor] = {}
    
    def register(self, processor: DocumentProcessor) -> None:
        """
        Register a processor for its supported extensions.
        
        Args:
            processor: DocumentProcessor instance to register
        """
        for ext in processor.supported_extensions:
            self._processors[ext.lower()] = processor
    
    def get_processor(self, file_path: Path) -> Optional[DocumentProcessor]:
        """
        Get appropriate processor for file type.
        
        Args:
            file_path: Path to the file (used to determine extension)
            
        Returns:
            DocumentProcessor instance if supported, None otherwise
        """
        ext = file_path.suffix.lower()
        return self._processors.get(ext)
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get all supported file extensions.
        
        Returns:
            List of supported extensions (e.g., ['.xlsx', '.docx'])
        """
        return list(self._processors.keys())
    
    def is_supported(self, file_path: Path) -> bool:
        """
        Check if a file type is supported.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file extension is supported
        """
        return file_path.suffix.lower() in self._processors
    
    def get_document_type(self, file_path: Path) -> Optional[DocumentType]:
        """
        Get the document type for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            DocumentType if supported, None otherwise
        """
        processor = self.get_processor(file_path)
        return processor.document_type if processor else None
