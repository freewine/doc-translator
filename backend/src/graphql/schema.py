"""
GraphQL schema definition using Strawberry.

This module defines all GraphQL types, queries, and mutations for the
Doc Translation System API.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
import strawberry
from strawberry.file_uploads import Upload
from strawberry.types import Info

from ..models.job import JobStatus as JobStatusEnum


@strawberry.enum
class JobStatus(Enum):
    """Status of a translation job."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"


@strawberry.enum
class DocumentType(Enum):
    """Type of document being processed."""
    EXCEL = "excel"
    WORD = "word"
    POWERPOINT = "powerpoint"
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"


@strawberry.type
class User:
    """
    Represents an authenticated user.

    Attributes:
        username: The user's username
        role: The user's role (admin or user)
        mustChangePassword: Whether the user must change their password
    """
    username: str
    role: Optional[str] = None
    mustChangePassword: bool = False


@strawberry.enum
class UserRoleEnum(Enum):
    """User role for access control."""
    ADMIN = "admin"
    USER = "user"


@strawberry.enum
class UserStatusEnum(Enum):
    """User account status."""
    PENDING_PASSWORD = "pending_password"
    ACTIVE = "active"
    LOCKED = "locked"
    DELETED = "deleted"


@strawberry.type
class UserInfo:
    """
    Detailed user information for user management.
    
    Attributes:
        username: The user's username
        role: User role (admin or user)
        status: Account status
        must_change_password: Whether user must change password
        failed_login_count: Number of consecutive failed login attempts
        created_at: Account creation timestamp
        updated_at: Last modification timestamp
        deleted_at: Soft deletion timestamp (if deleted)
    """
    username: str
    role: UserRoleEnum
    status: UserStatusEnum
    must_change_password: bool
    failed_login_count: int
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None


@strawberry.type
class AuthResultInfo:
    """
    Authentication result with detailed information.
    
    Attributes:
        success: Whether authentication succeeded
        token: JWT token (if successful)
        must_change_password: Whether user must change password
        error: Error message (if failed)
        error_code: Error code (if failed)
        remaining_attempts: Remaining login attempts before lockout
        user: User information (if successful)
    """
    success: bool
    token: Optional[str] = None
    must_change_password: bool = False
    error: Optional[str] = None
    error_code: Optional[str] = None
    remaining_attempts: Optional[int] = None
    user: Optional[UserInfo] = None


@strawberry.type
class AuthPayload:
    """
    Payload returned after successful authentication.
    
    Attributes:
        token: JWT authentication token
        user: The authenticated user
    """
    token: str
    user: User


@strawberry.type
class ModelInfo:
    """
    Information about an available translation model.
    
    Attributes:
        name: Human-readable model name (e.g., "Nova 2 Lite")
        id: Model identifier for AWS Bedrock (e.g., "global.amazon.nova-2-lite-v1:0")
    """
    name: str
    id: str


@strawberry.type
class ModelConfig:
    """
    Current model configuration.
    
    Attributes:
        model_id: Currently selected model ID
        model_name: Currently selected model name
        available_models: List of available models
    """
    model_id: str
    model_name: str
    available_models: List[ModelInfo]


@strawberry.type
class LanguagePair:
    """
    Represents a language pair configuration for translation.
    
    Attributes:
        id: Unique identifier for the language pair
        source_language: Human-readable source language name (e.g., "Chinese")
        target_language: Human-readable target language name (e.g., "Vietnamese")
        source_language_code: ISO language code for source (e.g., "zh")
        target_language_code: ISO language code for target (e.g., "vi")
    """
    id: str
    source_language: str
    target_language: str
    source_language_code: str
    target_language_code: str


@strawberry.type
class FileProgress:
    """
    Progress information for a single file in a translation job.
    
    Attributes:
        filename: Name of the file being processed
        progress: Progress percentage (0.0 to 1.0)
        segments_total: Total number of text segments to translate
        segments_translated: Number of segments translated so far
        document_type: Type of document being processed
        cells_total: Total number of cells to translate (legacy, for backward compatibility)
        cells_translated: Number of cells translated so far (legacy, for backward compatibility)
        worksheets_completed: Number of worksheets/pages completed
        worksheets_total: Total number of worksheets/pages in the file
    """
    filename: str
    progress: float
    segments_total: int
    segments_translated: int
    document_type: Optional[DocumentType]
    cells_total: int
    cells_translated: int
    worksheets_completed: int
    worksheets_total: int


@strawberry.type
class FileError:
    """
    Error information for a failed file in a translation job.
    
    Attributes:
        filename: Name of the file that failed
        error: Error message describing what went wrong
        error_type: Type/category of the error
        timestamp: When the error occurred
    """
    filename: str
    error: str
    error_type: str
    timestamp: datetime


@strawberry.type
class CompletedFile:
    """
    Information about a completed file in a translation job.
    
    Attributes:
        original_filename: Name of the original uploaded file
        output_filename: Name of the translated output file (with language suffix)
        segments_translated: Number of text segments that were translated
        document_type: Type of document that was processed
        cells_translated: Number of cells that were translated (legacy, for backward compatibility)
    """
    original_filename: str
    output_filename: str
    segments_translated: int
    document_type: Optional[DocumentType]
    cells_translated: int
    segments_failed: int = 0
    translation_warning: Optional[str] = None


@strawberry.type
class TranslationJob:
    """
    Represents a translation job with status tracking and progress information.

    Attributes:
        id: Unique identifier for the job
        status: Current status of the job
        progress: Overall progress (0.0 to 1.0)
        files_total: Total number of files in the job
        files_completed: Number of files successfully completed
        files_processing: List of files currently being processed with their progress
        files_failed: List of files that failed processing with error details
        completed_files: List of successfully completed files with output filenames
        created_at: Timestamp when the job was created
        completed_at: Timestamp when the job completed (None if not completed)
        language_pair: Language pair used for translation
        output_mode: Output mode for translations ("replace", "append", "prepend", "interleave", "interleave_reverse")
    """
    id: str
    status: JobStatus
    progress: float
    files_total: int
    files_completed: int
    files_processing: List[FileProgress]
    files_failed: List[FileError]
    completed_files: List[CompletedFile]
    created_at: datetime
    completed_at: Optional[datetime]
    language_pair: Optional[LanguagePair]
    output_mode: str


@strawberry.type
class JobHistoryResponse:
    """
    Paginated response for job history query.

    Attributes:
        jobs: List of translation jobs for the current page
        total: Total number of matching jobs
        page: Current page number (1-based)
        page_size: Number of jobs per page
        has_next: Whether there are more pages available
    """
    jobs: List[TranslationJob]
    total: int
    page: int
    page_size: int
    has_next: bool


@strawberry.type
class FileUpload:
    """
    Information about an uploaded file.
    
    Attributes:
        id: Unique identifier for the uploaded file
        filename: Original filename
        size: File size in bytes
        document_type: Type of document (excel, word, powerpoint, pdf)
    """
    id: str
    filename: str
    size: int
    document_type: Optional[DocumentType]


# =========================================================================
# Thesaurus Types (Requirements 3.3)
# =========================================================================

@strawberry.type
class TermPair:
    """
    A term translation pair mapping a source term to its target translation.
    
    Attributes:
        id: Unique identifier (UUID)
        language_pair_id: Reference to language pair (e.g., "zh-vi")
        catalog_id: Reference to catalog
        source_term: Source language term
        target_term: Target language translation
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """
    id: str
    language_pair_id: str
    catalog_id: str
    source_term: str
    target_term: str
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Catalog:
    """
    A catalog for organizing term pairs by domain or project.
    
    Attributes:
        id: Unique identifier (UUID)
        language_pair_id: Reference to language pair
        name: Catalog name
        description: Optional description
        term_count: Number of term pairs in the catalog
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """
    id: str
    language_pair_id: str
    name: str
    description: Optional[str]
    term_count: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ImportResult:
    """
    Result of a CSV import operation.
    
    Attributes:
        created: Number of new term pairs created
        updated: Number of existing term pairs updated
        skipped: Number of invalid rows skipped
        errors: List of error messages for skipped rows
    """
    created: int
    updated: int
    skipped: int
    errors: List[str]


@strawberry.type
class PaginatedTermPairs:
    """
    Paginated list of term pairs.
    
    Attributes:
        items: Term pairs for current page
        total: Total number of matching term pairs
        page: Current page number (1-indexed)
        page_size: Items per page
        has_next: Whether there are more pages
    """
    items: List[TermPair]
    total: int
    page: int
    page_size: int
    has_next: bool


@strawberry.type
class Query:
    """
    Root query type for the GraphQL API.
    
    Provides read-only access to user information, jobs, and language pairs.
    """
    
    @strawberry.field
    async def me(self, info: Info) -> User:
        """
        Get the currently authenticated user.
        
        Returns:
            User: The authenticated user
            
        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .resolvers import resolve_me
        return await resolve_me(info)
    
    @strawberry.field
    async def job(self, info: Info, id: str) -> Optional[TranslationJob]:
        """
        Get a specific translation job by ID.
        
        Args:
            id: The job ID
            
        Returns:
            TranslationJob: The job if found, None otherwise
            
        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .resolvers import resolve_job
        return await resolve_job(info, id)
    
    @strawberry.field
    async def jobs(self, info: Info) -> List[TranslationJob]:
        """
        Get all translation jobs for the authenticated user.

        Returns:
            List[TranslationJob]: List of all jobs

        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .resolvers import resolve_jobs
        return await resolve_jobs(info)

    @strawberry.field
    async def job_history(
        self,
        info: Info,
        page: int = 1,
        page_size: int = 20,
        status: Optional[JobStatus] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> JobHistoryResponse:
        """
        Get paginated job history for the authenticated user.

        Args:
            page: Page number (1-based, default 1)
            page_size: Number of jobs per page (1-100, default 20)
            status: Optional status filter
            date_from: Optional start date filter (ISO format)
            date_to: Optional end date filter (ISO format)

        Returns:
            JobHistoryResponse: Paginated list of jobs

        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .resolvers import resolve_job_history
        return await resolve_job_history(info, page, page_size, status, date_from, date_to)

    @strawberry.field
    async def language_pairs(self, info: Info) -> List[LanguagePair]:
        """
        Get all configured language pairs.
        
        Returns:
            List[LanguagePair]: List of available language pairs
            
        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .resolvers import resolve_language_pairs
        return await resolve_language_pairs(info)
    
    @strawberry.field
    async def model_config(self, info: Info) -> ModelConfig:
        """
        Get current model configuration and available models.
        
        Returns:
            ModelConfig: Current model configuration
            
        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .resolvers import resolve_model_config
        return await resolve_model_config(info)
    
    # =========================================================================
    # User Management Queries
    # =========================================================================
    
    @strawberry.field
    async def users(
        self,
        info: Info,
        include_deleted: bool = False
    ) -> List["UserInfo"]:
        """
        Get all users (admin only).
        
        Args:
            include_deleted: Whether to include soft-deleted users
            
        Returns:
            List of users
        """
        from .user_resolvers import UserQuery
        query = UserQuery()
        return await query.users(info, include_deleted)
    
    @strawberry.field
    async def user(
        self,
        info: Info,
        username: str
    ) -> Optional["UserInfo"]:
        """
        Get a specific user by username (admin only).
        
        Args:
            username: Username to look up
            
        Returns:
            User if found, None otherwise
        """
        from .user_resolvers import UserQuery
        query = UserQuery()
        return await query.user(info, username)
    
    @strawberry.field
    async def current_user(self, info: Info) -> "UserInfo":
        """
        Get the current authenticated user with full details.
        
        Returns:
            Current user
        """
        from .user_resolvers import UserQuery
        query = UserQuery()
        return await query.me(info)
    
    # =========================================================================
    # Thesaurus Queries (Requirements 3.1, 3.2, 3.4, 9.1)
    # =========================================================================
    
    @strawberry.field
    async def term_pairs(
        self,
        info: Info,
        language_pair_id: str,
        catalog_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> PaginatedTermPairs:
        """
        Get paginated term pairs with optional filtering.
        
        Args:
            language_pair_id: Language pair ID to filter by
            catalog_id: Optional catalog ID to filter by
            search: Optional text to search in source terms
            page: Page number (1-indexed)
            page_size: Number of items per page (max 100)
            
        Returns:
            PaginatedTermPairs: Paginated list of term pairs
            
        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .thesaurus_resolvers import resolve_term_pairs
        return await resolve_term_pairs(info, language_pair_id, catalog_id, search, page, page_size)
    
    @strawberry.field
    async def catalogs(
        self,
        info: Info,
        language_pair_id: str
    ) -> List[Catalog]:
        """
        Get all catalogs for a language pair with term counts.
        
        Args:
            language_pair_id: Language pair ID
            
        Returns:
            List[Catalog]: List of catalogs with term counts
            
        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .thesaurus_resolvers import resolve_catalogs
        return await resolve_catalogs(info, language_pair_id)
    
    @strawberry.field
    async def export_terms_csv(
        self,
        info: Info,
        language_pair_id: str,
        catalog_id: str
    ) -> str:
        """
        Export term pairs as CSV content.
        
        Args:
            language_pair_id: Language pair ID
            catalog_id: Catalog ID
            
        Returns:
            str: CSV content as string
            
        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .thesaurus_resolvers import resolve_export_terms_csv
        return await resolve_export_terms_csv(info, language_pair_id, catalog_id)
    
    # =========================================================================
    # Config Storage Queries (Unit-2)
    # =========================================================================
    
    @strawberry.field
    async def config_language_pairs(
        self,
        info: Info,
        include_disabled: bool = False
    ) -> List["ConfigLanguagePair"]:
        """
        Get all language pairs for the current user (DynamoDB-backed).
        
        Args:
            include_disabled: Whether to include disabled pairs
            
        Returns:
            List of user language pairs
        """
        from .config_resolvers import resolve_config_language_pairs
        return await resolve_config_language_pairs(info, include_disabled)
    
    @strawberry.field
    async def config_user_settings(self, info: Info) -> "ConfigUserSettings":
        """
        Get settings for the current user (DynamoDB-backed).
        
        Returns:
            User settings
        """
        from .config_resolvers import resolve_config_user_settings
        return await resolve_config_user_settings(info)
    
    @strawberry.field
    async def config_available_models(self, info: Info) -> List["ConfigModelInfo"]:
        """
        Get all available translation models (DynamoDB-backed).
        
        Returns:
            List of available models
        """
        from .config_resolvers import resolve_available_models
        return await resolve_available_models(info)


@strawberry.type
class Mutation:
    """
    Root mutation type for the GraphQL API.
    
    Provides write operations for authentication, job management,
    language pair configuration, and file uploads.
    """
    
    @strawberry.mutation
    async def login(self, username: str, password: str, info: Info) -> AuthPayload:
        """
        Authenticate a user and return a JWT token.
        
        Args:
            username: The user's username
            password: The user's password
            
        Returns:
            AuthPayload: Authentication token and user information
            
        Raises:
            AuthenticationError: If credentials are invalid
        """
        from .resolvers import resolve_login
        return await resolve_login(username, password, info)
    
    @strawberry.mutation
    async def logout(self, info: Info) -> bool:
        """
        Logout the current user (invalidate token on client side).
        
        Returns:
            bool: True if logout was successful
            
        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .resolvers import resolve_logout
        return await resolve_logout(info)
    
    @strawberry.mutation
    async def create_translation_job(
        self,
        info: Info,
        file_ids: List[str],
        language_pair_id: str,
        catalog_ids: Optional[List[str]] = None,
        output_mode: str = "replace"
    ) -> TranslationJob:
        """
        Create a new translation job with optional catalog selection.

        Args:
            file_ids: List of file IDs to translate
            language_pair_id: ID of the language pair to use
            catalog_ids: Optional list of catalog IDs for term injection (in priority order)
            output_mode: One of "replace", "append", "prepend", "interleave", "interleave_reverse" (default: "replace")

        Returns:
            TranslationJob: The created job

        Raises:
            AuthenticationError: If the user is not authenticated
            ValidationError: If file_ids or language_pair_id are invalid
        """
        from .resolvers import resolve_create_translation_job
        return await resolve_create_translation_job(info, file_ids, language_pair_id, catalog_ids, output_mode)
    
    @strawberry.mutation
    async def add_language_pair(
        self,
        info: Info,
        source_language: str,
        target_language: str,
        source_language_code: str,
        target_language_code: str
    ) -> LanguagePair:
        """
        Add a new language pair configuration.
        
        Args:
            source_language: Human-readable source language name
            target_language: Human-readable target language name
            source_language_code: ISO language code for source
            target_language_code: ISO language code for target
            
        Returns:
            LanguagePair: The created language pair
            
        Raises:
            AuthenticationError: If the user is not authenticated
            ValidationError: If the language pair already exists or is invalid
        """
        from .resolvers import resolve_add_language_pair
        return await resolve_add_language_pair(
            info, source_language, target_language,
            source_language_code, target_language_code
        )
    
    @strawberry.mutation
    async def remove_language_pair(self, info: Info, id: str) -> bool:
        """
        Remove a language pair configuration.
        
        Args:
            id: ID of the language pair to remove
            
        Returns:
            bool: True if the language pair was removed successfully
            
        Raises:
            AuthenticationError: If the user is not authenticated
            ValidationError: If the language pair does not exist
        """
        from .resolvers import resolve_remove_language_pair
        return await resolve_remove_language_pair(info, id)
    
    @strawberry.mutation
    async def upload_file(self, info: Info, file: Upload) -> FileUpload:
        """
        Upload an Excel file for translation.
        
        Args:
            file: The file to upload
            
        Returns:
            FileUpload: Information about the uploaded file
            
        Raises:
            AuthenticationError: If the user is not authenticated
            ValidationError: If the file is not a valid Excel file or exceeds size limit
        """
        from .resolvers import resolve_upload_file
        return await resolve_upload_file(info, file)
    
    @strawberry.mutation
    async def update_model(self, info: Info, model_id: str) -> ModelConfig:
        """
        Update the selected translation model.
        
        Args:
            model_id: ID of the model to use
            
        Returns:
            ModelConfig: Updated model configuration
            
        Raises:
            AuthenticationError: If the user is not authenticated
            ValidationError: If model_id is invalid
        """
        from .resolvers import resolve_update_model
        return await resolve_update_model(info, model_id)
    
    # =========================================================================
    # Thesaurus Mutations (Requirements 1.1, 1.3, 1.5, 2.1, 4.1, 4.2, 5.1-5.4)
    # =========================================================================
    
    @strawberry.mutation
    async def add_term_pair(
        self,
        info: Info,
        language_pair_id: str,
        catalog_id: str,
        source_term: str,
        target_term: str
    ) -> TermPair:
        """
        Add or update a term pair (upsert behavior).
        
        If a term pair with the same source term exists in the catalog,
        it will be updated with the new target term.
        
        Args:
            language_pair_id: Language pair ID
            catalog_id: Catalog ID
            source_term: Source language term
            target_term: Target language translation
            
        Returns:
            TermPair: Created or updated term pair
            
        Raises:
            AuthenticationError: If the user is not authenticated
            ValidationError: If term validation fails
        """
        from .thesaurus_resolvers import resolve_add_term_pair
        return await resolve_add_term_pair(info, language_pair_id, catalog_id, source_term, target_term)
    
    @strawberry.mutation
    async def edit_term_pair(
        self,
        info: Info,
        term_id: str,
        target_term: str
    ) -> TermPair:
        """
        Edit an existing term pair's target term.
        
        Args:
            term_id: Unique term pair ID
            target_term: New target term translation
            
        Returns:
            TermPair: Updated term pair
            
        Raises:
            AuthenticationError: If the user is not authenticated
            ValidationError: If target term validation fails
            NotFoundError: If term pair is not found
        """
        from .thesaurus_resolvers import resolve_edit_term_pair
        return await resolve_edit_term_pair(info, term_id, target_term)
    
    @strawberry.mutation
    async def delete_term_pair(
        self,
        info: Info,
        term_id: str
    ) -> bool:
        """
        Delete a term pair by ID.
        
        Args:
            term_id: Unique term pair ID
            
        Returns:
            bool: True if deleted successfully
            
        Raises:
            AuthenticationError: If the user is not authenticated
            NotFoundError: If term pair is not found
        """
        from .thesaurus_resolvers import resolve_delete_term_pair
        return await resolve_delete_term_pair(info, term_id)
    
    @strawberry.mutation
    async def bulk_delete_term_pairs(
        self,
        info: Info,
        language_pair_id: str,
        catalog_id: str
    ) -> int:
        """
        Delete all term pairs in a catalog.
        
        Args:
            language_pair_id: Language pair ID
            catalog_id: Catalog ID
            
        Returns:
            int: Number of deleted term pairs
            
        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .thesaurus_resolvers import resolve_bulk_delete_term_pairs
        return await resolve_bulk_delete_term_pairs(info, language_pair_id, catalog_id)
    
    @strawberry.mutation
    async def import_terms_csv(
        self,
        info: Info,
        language_pair_id: str,
        catalog_id: str,
        csv_content: str
    ) -> ImportResult:
        """
        Import term pairs from CSV content.
        
        Expected CSV format:
        source_term,target_term
        服务器,máy chủ
        
        Args:
            language_pair_id: Language pair ID
            catalog_id: Catalog ID
            csv_content: CSV content as string
            
        Returns:
            ImportResult: Import summary with counts
            
        Raises:
            AuthenticationError: If the user is not authenticated
        """
        from .thesaurus_resolvers import resolve_import_terms_csv
        return await resolve_import_terms_csv(info, language_pair_id, catalog_id, csv_content)
    
    @strawberry.mutation
    async def create_catalog(
        self,
        info: Info,
        language_pair_id: str,
        name: str,
        description: Optional[str] = None
    ) -> Catalog:
        """
        Create a new catalog.
        
        Args:
            language_pair_id: Language pair ID
            name: Catalog name
            description: Optional description
            
        Returns:
            Catalog: Created catalog
            
        Raises:
            AuthenticationError: If the user is not authenticated
            ValidationError: If name is empty or duplicate
        """
        from .thesaurus_resolvers import resolve_create_catalog
        return await resolve_create_catalog(info, language_pair_id, name, description)
    
    @strawberry.mutation
    async def update_catalog(
        self,
        info: Info,
        language_pair_id: str,
        catalog_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Catalog:
        """
        Update a catalog's name or description.
        
        Args:
            language_pair_id: Language pair ID
            catalog_id: Catalog ID
            name: New name (optional)
            description: New description (optional)
            
        Returns:
            Catalog: Updated catalog
            
        Raises:
            AuthenticationError: If the user is not authenticated
            NotFoundError: If catalog is not found
            ValidationError: If new name is empty or duplicate
        """
        from .thesaurus_resolvers import resolve_update_catalog
        return await resolve_update_catalog(info, language_pair_id, catalog_id, name, description)
    
    @strawberry.mutation
    async def delete_catalog(
        self,
        info: Info,
        language_pair_id: str,
        catalog_id: str
    ) -> int:
        """
        Delete a catalog and all its term pairs.
        
        Args:
            language_pair_id: Language pair ID
            catalog_id: Catalog ID
            
        Returns:
            int: Number of deleted items (term pairs + catalog)
            
        Raises:
            AuthenticationError: If the user is not authenticated
            NotFoundError: If catalog is not found
        """
        from .thesaurus_resolvers import resolve_delete_catalog
        return await resolve_delete_catalog(info, language_pair_id, catalog_id)
    
    # =========================================================================
    # User Management Mutations
    # =========================================================================
    
    @strawberry.mutation
    async def create_user(
        self,
        info: Info,
        username: str,
        password: str,
        role: str = "user"
    ) -> UserInfo:
        """
        Create a new user (admin only).
        
        Args:
            username: Unique username (3-50 chars)
            password: Initial password
            role: User role ('admin' or 'user')
            
        Returns:
            Created user
        """
        from .user_resolvers import UserMutation
        mutation = UserMutation()
        return await mutation.create_user(info, username, password, role)
    
    @strawberry.mutation
    async def update_user(
        self,
        info: Info,
        username: str,
        password: Optional[str] = None,
        role: Optional[str] = None
    ) -> UserInfo:
        """
        Update a user's information (admin only).
        
        Args:
            username: Target username
            password: New password (optional)
            role: New role (optional)
            
        Returns:
            Updated user
        """
        from .user_resolvers import UserMutation
        mutation = UserMutation()
        return await mutation.update_user(info, username, password, role)
    
    @strawberry.mutation
    async def delete_user(
        self,
        info: Info,
        username: str
    ) -> bool:
        """
        Soft delete a user (admin only).
        
        Args:
            username: Username to delete
            
        Returns:
            True if deleted successfully
        """
        from .user_resolvers import UserMutation
        mutation = UserMutation()
        return await mutation.delete_user(info, username)
    
    @strawberry.mutation
    async def unlock_user(
        self,
        info: Info,
        username: str
    ) -> UserInfo:
        """
        Unlock a locked user account (admin only).
        
        Args:
            username: Username to unlock
            
        Returns:
            Unlocked user
        """
        from .user_resolvers import UserMutation
        mutation = UserMutation()
        return await mutation.unlock_user(info, username)
    
    @strawberry.mutation
    async def restore_user(
        self,
        info: Info,
        username: str
    ) -> UserInfo:
        """
        Restore a soft-deleted user (admin only).
        
        Args:
            username: Username to restore
            
        Returns:
            Restored user
        """
        from .user_resolvers import UserMutation
        mutation = UserMutation()
        return await mutation.restore_user(info, username)
    
    @strawberry.mutation
    async def change_my_password(
        self,
        info: Info,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change the current user's password.
        
        Args:
            current_password: Current password for verification
            new_password: New password to set
            
        Returns:
            True if password changed successfully
        """
        from .user_resolvers import UserMutation
        mutation = UserMutation()
        return await mutation.change_my_password(info, current_password, new_password)
    
    @strawberry.mutation
    async def login_user(
        self,
        info: Info,
        username: str,
        password: str
    ) -> AuthResultInfo:
        """
        Authenticate a user and get JWT token (DynamoDB-based).
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Authentication result with token if successful
        """
        from .user_resolvers import UserMutation
        mutation = UserMutation()
        return await mutation.login_user(info, username, password)
    
    # =========================================================================
    # Config Storage Mutations (Unit-2)
    # =========================================================================
    
    @strawberry.mutation
    async def create_config_language_pair(
        self,
        info: Info,
        source_language: str,
        target_language: str,
        display_name: str,
        is_enabled: bool = True
    ) -> "ConfigLanguagePair":
        """
        Create a new language pair for the current user (DynamoDB-backed).
        
        Args:
            source_language: Source language code (e.g., "zh")
            target_language: Target language code (e.g., "vi")
            display_name: Human-readable name
            is_enabled: Whether the pair is enabled
            
        Returns:
            Created language pair
        """
        from .config_resolvers import resolve_create_config_language_pair
        return await resolve_create_config_language_pair(
            info, source_language, target_language, display_name, is_enabled
        )
    
    @strawberry.mutation
    async def update_config_language_pair(
        self,
        info: Info,
        language_pair_id: str,
        display_name: Optional[str] = None,
        is_enabled: Optional[bool] = None
    ) -> Optional["ConfigLanguagePair"]:
        """
        Update a language pair (DynamoDB-backed).
        
        Args:
            language_pair_id: Language pair ID
            display_name: New display name (optional)
            is_enabled: New enabled status (optional)
            
        Returns:
            Updated language pair or None if not found
        """
        from .config_resolvers import resolve_update_config_language_pair
        return await resolve_update_config_language_pair(
            info, language_pair_id, display_name, is_enabled
        )
    
    @strawberry.mutation
    async def delete_config_language_pair(
        self,
        info: Info,
        language_pair_id: str
    ) -> bool:
        """
        Delete a language pair (DynamoDB-backed).
        
        Args:
            language_pair_id: Language pair ID
            
        Returns:
            True if deleted, False if not found
        """
        from .config_resolvers import resolve_delete_config_language_pair
        return await resolve_delete_config_language_pair(info, language_pair_id)
    
    @strawberry.mutation
    async def update_config_user_settings(
        self,
        info: Info,
        default_model_id: Optional[str] = None,
        ui_language: Optional[str] = None,
        translation_batch_size: Optional[int] = None,
        max_concurrent_tasks: Optional[int] = None
    ) -> "ConfigUserSettings":
        """
        Update user settings (DynamoDB-backed).
        
        Args:
            default_model_id: New default model ID (optional)
            ui_language: New UI language (optional)
            translation_batch_size: New batch size (optional)
            max_concurrent_tasks: New concurrent tasks limit (optional)
            
        Returns:
            Updated user settings
        """
        from .config_resolvers import resolve_update_config_user_settings
        return await resolve_update_config_user_settings(
            info, default_model_id, ui_language, translation_batch_size, max_concurrent_tasks
        )
    
    @strawberry.mutation
    async def reset_config_user_settings(self, info: Info) -> "ConfigUserSettings":
        """
        Reset user settings to defaults (DynamoDB-backed).
        
        Returns:
            Reset user settings
        """
        from .config_resolvers import resolve_reset_config_user_settings
        return await resolve_reset_config_user_settings(info)


# Import config types for schema registration (Unit-2)
from .config_resolvers import ConfigLanguagePair, ConfigUserSettings, ConfigModelInfo

# Create the schema with additional types and security extensions
from strawberry.extensions import QueryDepthLimiter

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    types=[ConfigLanguagePair, ConfigUserSettings, ConfigModelInfo],
    extensions=[QueryDepthLimiter(max_depth=10)],
)
