"""
GraphQL resolver implementations.

This module implements the business logic for all GraphQL queries and mutations,
coordinating between the various services and storage layers.
"""
import logging
from typing import List, Optional, TYPE_CHECKING

from strawberry.types import Info
from strawberry.file_uploads import Upload

from .schema import (
    User, AuthPayload, LanguagePair as GQLLanguagePair,
    TranslationJob as GQLTranslationJob, FileUpload, FileProgress, FileError,
    CompletedFile, JobStatus as GQLJobStatus, ModelInfo as GQLModelInfo,
    ModelConfig as GQLModelConfig, DocumentType as GQLDocumentType,
    JobHistoryResponse
)
from .decorators import (
    get_current_user_from_context,
    verify_and_get_user,
    PermissionError as AuthPermissionError,
)
from ..models.user import UserRole
from ..services.auth_service import AuthService
from ..services.job_manager import JobManager
from ..services.translation_orchestrator import TranslationOrchestrator
from ..storage.s3_file_storage import S3FileStorage
from ..models.job import LanguagePair

if TYPE_CHECKING:
    from ..services.thesaurus_service import ThesaurusService
    from ..services.user_service import UserService
    from ..services.language_pair_service import LanguagePairService
    from ..services.user_settings_service import UserSettingsService
    from ..services.global_config_service import GlobalConfigService
from ..models.job import JobStatus, TranslationJob

logger = logging.getLogger(__name__)

# Hold strong references to background tasks to prevent garbage collection.
# Python's event loop only keeps weak references to tasks, so an unreferenced
# task can be collected mid-execution. Tasks remove themselves from this set
# when they complete.
_background_tasks: set = set()


class AuthenticationError(Exception):
    """Raised when authentication fails or is required."""
    pass


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class ResolverContext:
    """
    Context object passed to all resolvers containing service instances.

    Attributes:
        auth_service: Authentication service instance
        job_manager: Job manager instance
        s3_file_storage: S3 file storage instance for file operations
        translation_orchestrator: Translation orchestrator instance
        thesaurus_service: Thesaurus service instance for term management
        user_service: User service instance for user management
        language_pair_service: Language pair service for user language pairs
        user_settings_service: User settings service
        global_config_service: Global config service for system-wide settings
    """

    def __init__(
        self,
        auth_service: AuthService,
        job_manager: JobManager,
        s3_file_storage: S3FileStorage,
        translation_orchestrator: TranslationOrchestrator,
        thesaurus_service: Optional["ThesaurusService"] = None,
        user_service: Optional["UserService"] = None,
        language_pair_service: Optional["LanguagePairService"] = None,
        user_settings_service: Optional["UserSettingsService"] = None,
        global_config_service: Optional["GlobalConfigService"] = None
    ):
        self.auth_service = auth_service
        self.job_manager = job_manager
        self.s3_file_storage = s3_file_storage
        self.translation_orchestrator = translation_orchestrator
        self.thesaurus_service = thesaurus_service
        self.user_service = user_service
        self.language_pair_service = language_pair_service
        self.user_settings_service = user_settings_service
        self.global_config_service = global_config_service


def get_auth_token(info: Info) -> Optional[str]:
    """
    Extract authentication token from request headers.
    
    Args:
        info: Strawberry Info object containing request context
        
    Returns:
        JWT token string if present, None otherwise
    """
    # Get token from Authorization header
    request = info.context.get("request")
    if not request:
        return None
    
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    
    return None


def require_auth(info: Info) -> str:
    """
    Require authentication and return the username.
    
    Args:
        info: Strawberry Info object
        
    Returns:
        Username of authenticated user
        
    Raises:
        AuthenticationError: If authentication fails
    """
    context: ResolverContext = info.context.get("resolver_context")
    if not context:
        raise AuthenticationError("Resolver context not available")
    
    token = get_auth_token(info)
    if not token:
        raise AuthenticationError("Authentication required")
    
    username = context.auth_service.get_username_from_token(token)
    if not username:
        raise AuthenticationError("Invalid or expired token")
    
    return username


def convert_language_pair_for_gql(lp) -> GQLLanguagePair:
    """
    Convert language pair to GraphQL LanguagePair.

    Handles both job.LanguagePair (with source_language_code/target_language_code)
    and config.LanguagePair (with source_language/target_language as codes).
    """
    if hasattr(lp, 'source_language_code'):
        return GQLLanguagePair(
            id=lp.id,
            source_language=lp.source_language,
            target_language=lp.target_language,
            source_language_code=lp.source_language_code,
            target_language_code=lp.target_language_code
        )

    display = getattr(lp, 'display_name', f"{lp.source_language}→{lp.target_language}")
    parts = display.split('→') if '→' in display else [lp.source_language, lp.target_language]

    return GQLLanguagePair(
        id=lp.id,
        source_language=parts[0].strip() if parts else lp.source_language,
        target_language=parts[1].strip() if len(parts) > 1 else lp.target_language,
        source_language_code=lp.source_language,
        target_language_code=lp.target_language
    )


def convert_model_info(model) -> GQLModelInfo:
    """
    Convert model info to GraphQL ModelInfo.

    Handles both legacy ModelInfo (name, id) and new ModelConfig (display_name, model_id).
    """
    if hasattr(model, 'model_id'):
        return GQLModelInfo(name=model.display_name, id=model.model_id)

    return GQLModelInfo(name=model.name, id=model.id)


def convert_job_status(status: JobStatus) -> GQLJobStatus:
    """Convert domain JobStatus to GraphQL JobStatus."""
    return GQLJobStatus[status.name]


def convert_document_type(doc_type) -> Optional[GQLDocumentType]:
    """Convert domain DocumentType to GraphQL DocumentType."""
    if doc_type is None:
        return None
    return GQLDocumentType[doc_type.name]


def convert_translation_job(job: TranslationJob) -> GQLTranslationJob:
    """Convert domain TranslationJob to GraphQL TranslationJob."""
    return GQLTranslationJob(
        id=job.id,
        status=convert_job_status(job.status),
        progress=job.progress,
        files_total=job.files_total,
        files_completed=job.files_completed,
        files_processing=[
            FileProgress(
                filename=fp.filename,
                progress=fp.progress,
                segments_total=fp.segments_total,
                segments_translated=fp.segments_translated,
                document_type=convert_document_type(fp.document_type),
                cells_total=fp.cells_total,
                cells_translated=fp.cells_translated,
                worksheets_completed=fp.worksheets_completed,
                worksheets_total=fp.worksheets_total
            )
            for fp in job.files_processing
        ],
        files_failed=[
            FileError(
                filename=fe.filename,
                error=fe.error,
                error_type=fe.error_type,
                timestamp=fe.timestamp
            )
            for fe in job.files_failed
        ],
        completed_files=[
            CompletedFile(
                original_filename=cf.original_filename,
                output_filename=cf.output_filename,
                segments_translated=cf.segments_translated,
                document_type=convert_document_type(cf.document_type),
                cells_translated=cf.cells_translated
            )
            for cf in job.completed_files
        ],
        created_at=job.created_at,
        completed_at=job.completed_at,
        language_pair=convert_language_pair_for_gql(job.language_pair) if job.language_pair else None,
        output_mode=job.output_mode
    )


# Query Resolvers

async def resolve_me(info: Info) -> User:
    """
    Get the currently authenticated user.

    Args:
        info: Strawberry Info object

    Returns:
        User object with username, role, and mustChangePassword

    Raises:
        AuthenticationError: If user is not authenticated
    """
    username = require_auth(info)

    context = info.context
    user_service = context.get("user_service") if hasattr(context, "get") else getattr(context, "user_service", None)

    if user_service:
        user_model = await user_service.get_user(username)
        if user_model:
            return User(
                username=user_model.username,
                role=user_model.role.value,
                mustChangePassword=user_model.must_change_password
            )

    return User(username=username)


async def resolve_job(info: Info, id: str) -> Optional[GQLTranslationJob]:
    """
    Get a specific translation job by ID.

    Args:
        info: Strawberry Info object
        id: Job ID

    Returns:
        TranslationJob if found, None otherwise

    Raises:
        AuthenticationError: If user is not authenticated
    """
    username = require_auth(info)

    context: ResolverContext = info.context.get("resolver_context")

    # Set user context on job_store to ensure users only see their own jobs
    context.job_manager.job_store.set_user_context(username)

    job = await context.job_manager.get_job(id)
    
    if job:
        return convert_translation_job(job)
    return None


async def resolve_jobs(info: Info) -> List[GQLTranslationJob]:
    """
    Get all translation jobs for the authenticated user.

    Args:
        info: Strawberry Info object

    Returns:
        List of all translation jobs for the current user

    Raises:
        AuthenticationError: If user is not authenticated
    """
    username = require_auth(info)

    context: ResolverContext = info.context.get("resolver_context")

    # Set user context on job_store to ensure users only see their own jobs
    context.job_manager.job_store.set_user_context(username)

    jobs = await context.job_manager.list_jobs()

    return [convert_translation_job(job) for job in jobs]


async def resolve_job_history(
    info: Info,
    page: int = 1,
    page_size: int = 20,
    status: Optional[GQLJobStatus] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> JobHistoryResponse:
    """
    Get paginated job history for the authenticated user.

    Args:
        info: Strawberry Info object
        page: Page number (1-based, default 1)
        page_size: Number of jobs per page (1-100, default 20)
        status: Optional status filter (GraphQL JobStatus enum)
        date_from: Optional start date filter (ISO format string)
        date_to: Optional end date filter (ISO format string)

    Returns:
        JobHistoryResponse with jobs, total, page, page_size, has_next

    Raises:
        AuthenticationError: If user is not authenticated
    """
    from datetime import datetime

    username = require_auth(info)

    context: ResolverContext = info.context.get("resolver_context")

    # Set user context on job_store
    context.job_manager.job_store.set_user_context(username)

    # Clamp page and page_size to valid ranges
    clamped_page = max(1, page)
    clamped_page_size = max(1, min(100, page_size))

    # Convert GraphQL JobStatus enum to domain JobStatus
    status_filter = None
    if status is not None:
        status_filter = JobStatus[status.name]

    # Parse date strings to datetime objects
    parsed_date_from = None
    parsed_date_to = None
    if date_from:
        try:
            parsed_date_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        except ValueError:
            pass  # Ignore invalid date format
    if date_to:
        try:
            parsed_date_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        except ValueError:
            pass  # Ignore invalid date format

    # Call job_store.list_jobs with parameters
    jobs, total = await context.job_manager.job_store.list_jobs(
        page=clamped_page,
        page_size=clamped_page_size,
        status_filter=status_filter,
        date_from=parsed_date_from,
        date_to=parsed_date_to
    )

    # Convert domain jobs to GraphQL types
    gql_jobs = [convert_translation_job(job) for job in jobs]

    return JobHistoryResponse(
        jobs=gql_jobs,
        total=total,
        page=clamped_page,
        page_size=clamped_page_size,
        has_next=(clamped_page * clamped_page_size) < total
    )


async def resolve_language_pairs(info: Info) -> List[GQLLanguagePair]:
    """
    Get all configured language pairs for the current user.

    Args:
        info: Strawberry Info object

    Returns:
        List of language pairs

    Raises:
        AuthenticationError: If user is not authenticated
        RuntimeError: If language_pair_service is not available
    """
    username = require_auth(info)

    context: ResolverContext = info.context.get("resolver_context")

    if not context.language_pair_service:
        raise RuntimeError("LanguagePairService is required but not available")

    pairs = await context.language_pair_service.get_language_pairs("__global__")

    return [convert_language_pair_for_gql(pair) for pair in pairs]


async def resolve_model_config(info: Info) -> GQLModelConfig:
    """
    Get current model configuration and available models.

    Args:
        info: Strawberry Info object

    Returns:
        Model configuration with user's saved model preference

    Raises:
        AuthenticationError: If user is not authenticated
        RuntimeError: If global_config_service or user_settings_service is not available
    """
    username = require_auth(info)

    context: ResolverContext = info.context.get("resolver_context")

    if not context.global_config_service:
        raise RuntimeError("GlobalConfigService is required but not available")
    if not context.user_settings_service:
        raise RuntimeError("UserSettingsService is required but not available")

    available_models = await context.global_config_service.get_available_models()

    # Get user's saved model preference (falls back to system default if not set)
    user_settings = await context.user_settings_service.get_user_settings(username)
    model_id = user_settings.default_model_id

    # Find the model's name
    model_name = "Unknown"
    for model in available_models:
        if model.model_id == model_id:
            model_name = model.display_name
            break

    return GQLModelConfig(
        model_id=model_id,
        model_name=model_name,
        available_models=[convert_model_info(model) for model in available_models]
    )


# Mutation Resolvers

async def resolve_login(username: str, password: str, info: Info) -> AuthPayload:
    """
    Authenticate a user and return a JWT token.

    Args:
        username: Username
        password: Password
        info: Strawberry Info object

    Returns:
        AuthPayload with token and user

    Raises:
        AuthenticationError: If credentials are invalid
    """
    context: ResolverContext = info.context.get("resolver_context")

    # Use authenticate_user which works with DynamoDB-backed user_service
    result = await context.auth_service.authenticate_user(username, password)

    if not result.success:
        raise AuthenticationError(result.error or "Invalid username or password")

    return AuthPayload(
        token=result.token,
        user=User(
            username=username,
            role=result.user.role.value if result.user else None,
            mustChangePassword=result.must_change_password
        )
    )


async def resolve_logout(info: Info) -> bool:
    """
    Logout the current user.
    
    Note: JWT tokens are stateless, so logout is handled client-side
    by discarding the token. This resolver just validates authentication.
    
    Args:
        info: Strawberry Info object
        
    Returns:
        True if logout was successful
        
    Raises:
        AuthenticationError: If user is not authenticated
    """
    require_auth(info)
    return True


async def resolve_create_translation_job(
    info: Info,
    file_ids: List[str],
    language_pair_id: str,
    catalog_ids: Optional[List[str]] = None,
    output_mode: str = "replace"
) -> GQLTranslationJob:
    """
    Create a new translation job with optional catalog selection.

    Args:
        info: Strawberry Info object
        file_ids: List of file IDs to translate
        language_pair_id: ID of language pair to use
        catalog_ids: Optional list of catalog IDs for term injection (in priority order)
        output_mode: One of "replace", "append", "prepend", "interleave", "interleave_reverse" (default: "replace")

    Returns:
        Created translation job

    Raises:
        AuthenticationError: If user is not authenticated
        ValidationError: If inputs are invalid
        RuntimeError: If language_pair_service is not available
        ValueError: If output_mode is not one of "replace", "append", "prepend", "interleave", "interleave_reverse"
    """
    import asyncio
    import shutil
    import tempfile
    from pathlib import Path

    valid_output_modes = {"replace", "append", "prepend", "interleave", "interleave_reverse"}
    if output_mode not in valid_output_modes:
        raise ValidationError(f"Invalid output_mode: {output_mode}. Must be one of: {', '.join(sorted(valid_output_modes))}")

    username = require_auth(info)

    context: ResolverContext = info.context.get("resolver_context")

    # Set user context on job_store for user-scoped job storage
    context.job_manager.job_store.set_user_context(username)

    # Validate inputs
    if not file_ids:
        raise ValidationError("At least one file ID is required")

    if not context.language_pair_service:
        raise RuntimeError("LanguagePairService is required but not available")

    # Get language pair from LanguagePairService (use global store, not user-specific)
    config_lp = await context.language_pair_service.get_language_pair("__global__", language_pair_id)

    if not config_lp:
        raise ValidationError(f"Language pair not found: {language_pair_id}")

    # Convert config.LanguagePair to job.LanguagePair for translation
    # Parse display_name to get human-readable names, or use codes as fallback
    display = config_lp.display_name or f"{config_lp.source_language}→{config_lp.target_language}"
    parts = display.split('→') if '→' in display else [config_lp.source_language, config_lp.target_language]
    language_pair = LanguagePair(
        id=config_lp.id,
        source_language=parts[0].strip(),
        target_language=parts[1].strip() if len(parts) > 1 else config_lp.target_language,
        source_language_code=config_lp.source_language,
        target_language_code=config_lp.target_language
    )
    
    # Create temp directory for this job's input files
    temp_input_dir = Path(tempfile.mkdtemp(prefix=f"doc-translation-input-"))
    
    # Retrieve files from S3 and write to temp directory
    file_paths_with_metadata = []
    try:
        for file_id in file_ids:
            # Get file content and metadata from S3
            result = await context.s3_file_storage.get_upload(username, file_id)
            if not result:
                # Clean up temp directory on error
                shutil.rmtree(temp_input_dir, ignore_errors=True)
                raise ValidationError(f"File not found: {file_id}")
            
            file_content, metadata = result
            original_filename = metadata.get("original_filename", f"{file_id}.bin")
            
            # Write content to temp file
            temp_file_path = temp_input_dir / f"{file_id}_{original_filename}"
            temp_file_path.write_bytes(file_content)
            
            # Store as tuple: (file_path, original_filename)
            file_paths_with_metadata.append((temp_file_path, original_filename))
    except ValidationError:
        raise
    except Exception as e:
        # Clean up temp directory on error
        shutil.rmtree(temp_input_dir, ignore_errors=True)
        raise ValidationError(f"Failed to retrieve files from storage: {str(e)}")
    
    # Create job with output_mode setting
    job = await context.job_manager.create_job(file_ids, language_pair, output_mode=output_mode)

    # Create job-specific output directory (temp)
    job_output_dir = Path(tempfile.mkdtemp(prefix=f"doc-translation-output-{job.id}-"))

    # Get user's preferred model ID, fall back to global default
    user_model_id = None
    if context.user_settings_service and context.global_config_service:
        try:
            user_settings = await context.user_settings_service.get_user_settings(username)
            user_model_id = user_settings.default_model_id

            # Validate model ID is still available
            if not await context.global_config_service.is_model_valid(user_model_id):
                logger.warning(
                    f"User {username}'s model {user_model_id} is no longer valid, falling back to default"
                )
                user_model_id = await context.global_config_service.get_default_model_id()
        except Exception as e:
            logger.warning(f"Failed to get user model preference: {e}, using shared service")

    # Create a per-job TranslationService with the user's preferred model
    from ..services.translation_service import TranslationService
    if user_model_id:
        job_translation_service = TranslationService(
            model_id=user_model_id,
            batch_size=context.translation_orchestrator.translation_service.batch_size
        )
        logger.info(f"Job {job.id}: using model {user_model_id} (user preference)")
    else:
        job_translation_service = context.translation_orchestrator.translation_service
        logger.info(f"Job {job.id}: using shared translation service (default model)")

    # Start processing asynchronously (don't await)
    # This allows the mutation to return immediately while processing continues

    # Create a new orchestrator instance with job-specific output directory
    # Include s3_file_storage for uploading output files to S3
    from ..services.translation_orchestrator import TranslationOrchestrator
    job_orchestrator = TranslationOrchestrator(
        excel_processor=context.translation_orchestrator.excel_processor,
        translation_service=job_translation_service,
        concurrent_executor=context.translation_orchestrator.executor,
        output_dir=job_output_dir,
        thesaurus_service=context.translation_orchestrator.thesaurus_service,
        s3_file_storage=context.translation_orchestrator.s3_file_storage,
        job_store=context.job_manager.job_store
    )

    async def process_and_cleanup():
        """Process the job and clean up temp directories afterwards."""
        try:
            await job_orchestrator.process_job(
                job,
                file_paths_with_metadata,
                language_pair,
                catalog_ids=catalog_ids,
                user_id=username
            )
        finally:
            # Clean up temp directories after processing completes
            shutil.rmtree(temp_input_dir, ignore_errors=True)
            shutil.rmtree(job_output_dir, ignore_errors=True)

    task = asyncio.create_task(process_and_cleanup())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return convert_translation_job(job)


async def resolve_add_language_pair(
    info: Info,
    source_language: str,
    target_language: str,
    source_language_code: str,
    target_language_code: str
) -> GQLLanguagePair:
    """
    Add a new language pair configuration for the current user.

    Args:
        info: Strawberry Info object
        source_language: Human-readable source language name
        target_language: Human-readable target language name
        source_language_code: ISO language code for source
        target_language_code: ISO language code for target

    Returns:
        Created language pair

    Raises:
        AuthenticationError: If user is not authenticated
        ValidationError: If language pair is invalid or already exists
        RuntimeError: If language_pair_service is not available
    """
    # Verify auth and get full user object (includes role)
    user = await verify_and_get_user(info)

    # Admin role check - only admins can add language pairs
    if user.role != UserRole.ADMIN:
        raise AuthPermissionError("Admin access required")

    context: ResolverContext = info.context.get("resolver_context")

    if not context.language_pair_service:
        raise RuntimeError("LanguagePairService is required but not available")

    try:
        # Create display name from human-readable names
        display_name = f"{source_language}→{target_language}"
        language_pair = await context.language_pair_service.create_language_pair(
            user_id="__global__",
            source_language=source_language_code,
            target_language=target_language_code,
            display_name=display_name
        )
        logger.info(f"Added language pair via LanguagePairService: {language_pair.id}")
        return convert_language_pair_for_gql(language_pair)

    except ValueError as e:
        raise ValidationError(str(e))


async def resolve_remove_language_pair(info: Info, id: str) -> bool:
    """
    Remove a language pair configuration for the current user.

    Args:
        info: Strawberry Info object
        id: ID of language pair to remove

    Returns:
        True if removed successfully

    Raises:
        AuthenticationError: If user is not authenticated
        ValidationError: If language pair doesn't exist
        RuntimeError: If language_pair_service is not available
    """
    # Verify auth and get full user object (includes role)
    user = await verify_and_get_user(info)

    # Admin role check - only admins can remove language pairs
    if user.role != UserRole.ADMIN:
        raise AuthPermissionError("Admin access required")

    context: ResolverContext = info.context.get("resolver_context")

    if not context.language_pair_service:
        raise RuntimeError("LanguagePairService is required but not available")

    try:
        await context.language_pair_service.delete_language_pair("__global__", id)
        logger.info(f"Removed language pair via LanguagePairService: {id}")
        return True

    except ValueError as e:
        raise ValidationError(str(e))


async def resolve_upload_file(info: Info, file: Upload) -> FileUpload:
    """
    Upload a document file for translation.

    Supports multiple document formats: Excel (.xlsx), Word (.docx),
    PowerPoint (.pptx), and PDF (.pdf).

    Files are stored in S3 with user-scoped paths.

    Args:
        info: Strawberry Info object
        file: Uploaded file

    Returns:
        FileUpload with file ID, metadata, and document type

    Raises:
        AuthenticationError: If user is not authenticated
        ValidationError: If file is invalid or too large
    """
    import uuid
    from pathlib import Path
    
    username = require_auth(info)

    context: ResolverContext = info.context.get("resolver_context")

    # Read file content
    content = file.read()

    # Default file upload settings
    max_file_size_mb = 50
    allowed_extensions = [".xlsx", ".docx", ".pptx", ".pdf", ".txt", ".md"]

    # Validate file size
    max_size_bytes = max_file_size_mb * 1024 * 1024
    if len(content) > max_size_bytes:
        raise ValidationError(
            f"File size exceeds maximum of {max_file_size_mb}MB"
        )

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [ext.lower() for ext in allowed_extensions]:
        raise ValidationError(
            f"File extension not allowed. Allowed extensions: {allowed_extensions}"
        )

    # Generate unique file ID
    file_id = str(uuid.uuid4())

    # Upload to S3
    try:
        await context.s3_file_storage.upload_file(
            user_id=username,
            file_id=file_id,
            file_content=content,
            original_filename=file.filename
        )

        # Detect document type from extension
        doc_type_map = {
            '.xlsx': 'excel', '.xls': 'excel',
            '.docx': 'word', '.doc': 'word',
            '.pptx': 'powerpoint', '.ppt': 'powerpoint',
            '.pdf': 'pdf'
        }
        doc_type_str = doc_type_map.get(file_ext)
        
        # Convert to GraphQL DocumentType enum
        gql_doc_type = None
        if doc_type_str:
            gql_doc_type = GQLDocumentType[doc_type_str.upper()]

        logger.info(f"File uploaded to S3: {file.filename} (ID: {file_id}, User: {username}, Type: {doc_type_str or 'unknown'})")

        return FileUpload(
            id=file_id,
            filename=file.filename,
            size=len(content),
            document_type=gql_doc_type
        )

    except Exception as e:
        logger.error(f"Error uploading file to S3: {e}", exc_info=True)
        raise ValidationError("Failed to upload file to storage")


async def resolve_update_model(info: Info, model_id: str) -> GQLModelConfig:
    """
    Update the selected translation model for the current user.

    Args:
        info: Strawberry Info object
        model_id: ID of the model to use

    Returns:
        Updated model configuration

    Raises:
        AuthenticationError: If user is not authenticated
        ValidationError: If model_id is invalid
        RuntimeError: If required services are not available
    """
    username = require_auth(info)

    context: ResolverContext = info.context.get("resolver_context")

    if not context.global_config_service:
        raise RuntimeError("GlobalConfigService is required but not available")
    if not context.user_settings_service:
        raise RuntimeError("UserSettingsService is required but not available")

    try:
        # Validate model_id exists
        is_valid = await context.global_config_service.is_model_valid(model_id)
        if not is_valid:
            raise ValidationError(f"Invalid model ID: {model_id}")

        # Update user's default model setting
        await context.user_settings_service.update_user_settings(
            username,
            default_model_id=model_id
        )

        # Get model info for response
        available_models = await context.global_config_service.get_available_models()
        model_name = "Unknown"
        for model in available_models:
            if model.model_id == model_id:
                model_name = model.display_name
                break

        logger.info(f"Model updated for user {username} to: {model_name} ({model_id})")

        return GQLModelConfig(
            model_id=model_id,
            model_name=model_name,
            available_models=[convert_model_info(model) for model in available_models]
        )

    except ValueError as e:
        raise ValidationError(str(e))
