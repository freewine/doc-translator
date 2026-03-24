"""Services module for business logic components."""

from .auth_service import AuthService, create_password_hash
from .translation_service import TranslationService, TranslationResult
from .excel_processor import ExcelProcessor, CellData, WorksheetProgress
from .concurrent_executor import ConcurrentExecutor, ProcessingResult
from .job_manager import JobManager
from .translation_orchestrator import TranslationOrchestrator, FileProcessingResult
from .document_processor import (
    DocumentProcessor,
    DocumentType,
    TextSegment,
    ProcessingResult as DocumentProcessingResult,
    DocumentProcessorFactory,
)
from .excel_document_processor import ExcelDocumentProcessor
from .text_processor import TextProcessor
from .markdown_processor import MarkdownProcessor
from .user_service import (
    PasswordService,
    UserService,
    UserServiceError,
    UserNotFoundError,
    UserAlreadyExistsError,
    PermissionDeniedError,
    ValidationError,
)
from .global_config_service import GlobalConfigService
from .language_pair_service import LanguagePairService
from .user_settings_service import UserSettingsService

__all__ = [
    "AuthService",
    "create_password_hash",
    "TranslationService",
    "TranslationResult",
    "ExcelProcessor",
    "CellData",
    "WorksheetProgress",
    "ConcurrentExecutor",
    "ProcessingResult",
    "JobManager",
    "TranslationOrchestrator",
    "FileProcessingResult",
    # Document processor infrastructure
    "DocumentProcessor",
    "DocumentType",
    "TextSegment",
    "DocumentProcessingResult",
    "DocumentProcessorFactory",
    "ExcelDocumentProcessor",
    "TextProcessor",
    "MarkdownProcessor",
    # User service
    "PasswordService",
    "UserService",
    "UserServiceError",
    "UserNotFoundError",
    "UserAlreadyExistsError",
    "PermissionDeniedError",
    "ValidationError",
    # Config storage services (Unit-2)
    "GlobalConfigService",
    "LanguagePairService",
    "UserSettingsService",
]
