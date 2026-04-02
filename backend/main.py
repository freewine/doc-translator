"""Main entry point for the Doc Translation Backend API."""

import io
import os
import re
import logging
import mimetypes
import secrets
import tempfile
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from strawberry.asgi import GraphQL
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from src.graphql.schema import schema
from src.graphql.resolvers import ResolverContext
from src.core.app_config import AppConfig
from src.services.auth_service import AuthService
from src.services.user_service import UserService
from src.services.job_manager import JobManager
from src.services.translation_orchestrator import TranslationOrchestrator
from src.services.translation_service import TranslationService
from src.services.excel_processor import ExcelProcessor
from src.services.concurrent_executor import ConcurrentExecutor
from src.storage.s3_file_storage import S3FileStorage
from src.storage.job_store import JobStore
from src.storage.job_repository import JobRepository
from src.storage.dynamodb_repository import DynamoDBRepository
from src.services.thesaurus_service import ThesaurusService
from src.services.global_config_service import GlobalConfigService
from src.services.language_pair_service import LanguagePairService
from src.services.user_settings_service import UserSettingsService

# Load environment variables
load_dotenv()

# Configure logging - ensure logs directory exists
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

# Get log level from environment (default: INFO)
log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(logs_dir / 'backend.log')
    ]
)

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str | None) -> str | None:
    """
    Sanitize a filename to prevent path traversal and header injection.

    Returns the sanitized filename, or None if invalid.
    """
    if not filename:
        return None

    # Strip path components (handles both / and \ separators)
    # Replace backslashes first so os.path.basename works on Linux too
    filename = os.path.basename(filename.replace('\\', '/'))

    # Reject null bytes and control characters
    if re.search(r'[\x00-\x1f\x7f]', filename):
        return None

    # Reject path traversal
    if '..' in filename:
        return None

    # Strip leading/trailing whitespace and dots
    filename = filename.strip().strip('.')

    if not filename:
        return None

    return filename


class AppContext:
    """Application context holding all service instances."""
    
    def __init__(self):
        """Initialize all services."""
        logger.info("Initializing application services...")

        # Load configuration from environment variables
        self.app_config = AppConfig.from_env()
        logger.info("Configuration loaded from environment")
        
        # Initialize DynamoDB repository
        # Region is determined by boto3 default chain (env vars, config file, instance metadata)
        self.dynamodb_repository = DynamoDBRepository()
        
        # Initialize UserService (for user management)
        self.user_service = UserService(
            repository=self.dynamodb_repository
        )
        
        # Initialize AuthService with UserService for DynamoDB-based authentication
        self.auth_service = AuthService(
            jwt_secret=self.app_config.jwt_secret,
            user_service=self.user_service
        )
        
        # Initialize other services
        self.job_store = JobStore()
        

        # Initialize S3 file storage (mandatory - s3_bucket is required in AppConfig)
        self.s3_file_storage = S3FileStorage(bucket_name=self.app_config.s3_bucket)
        logger.info(f"S3FileStorage initialized with bucket: {self.app_config.s3_bucket}")

        # Initialize JobRepository for DynamoDB job storage
        self.job_repository = JobRepository()

        # Initialize ThesaurusService
        self.thesaurus_service = ThesaurusService(
            repository=self.dynamodb_repository
        )
        
        # Initialize Unit-2 Config Storage Services
        self.global_config_service = GlobalConfigService(
            repository=self.dynamodb_repository
        )
        self.language_pair_service = LanguagePairService(
            repository=self.dynamodb_repository
        )
        self.user_settings_service = UserSettingsService(
            repository=self.dynamodb_repository,
            global_config_service=self.global_config_service
        )
        logger.info("Config storage services initialized (Unit-2)")
        
        # Initialize translation components
        # TranslationService uses boto3 default region chain; model_id is runtime config from DynamoDB
        self.translation_service = TranslationService(
            batch_size=self.app_config.translation_batch_size
        )
        self.excel_processor = ExcelProcessor()
        self.concurrent_executor = ConcurrentExecutor(
            max_file_concurrency=self.app_config.max_concurrent_files
        )
        
        # Initialize orchestrator
        # Use temp directory for intermediate file processing (outputs go to S3)
        temp_output_dir = Path(tempfile.mkdtemp(prefix="doc-translation-"))
        self.translation_orchestrator = TranslationOrchestrator(
            excel_processor=self.excel_processor,
            translation_service=self.translation_service,
            concurrent_executor=self.concurrent_executor,
            output_dir=temp_output_dir,
            thesaurus_service=self.thesaurus_service,
            s3_file_storage=self.s3_file_storage
        )
        
        # Initialize job manager
        self.job_manager = JobManager(
            job_store=self.job_store
        )
        
        logger.info("All services initialized successfully")
    
    async def initialize_async_services(self) -> None:
        """
        Initialize async services (DynamoDB tables, default config).

        This should be called during application startup.
        """
        logger.info("Initializing async services...")

        # Initialize DynamoDB tables (thesaurus tables)
        await self.dynamodb_repository.initialize_tables()

        # Initialize config storage tables (language pairs, user settings, global config)
        await self.dynamodb_repository.initialize_config_tables()

        # Initialize users table
        await self.dynamodb_repository.initialize_users_table()

        # Initialize job repository table
        await self.job_repository.initialize_table()

        # Ensure default configuration exists in DynamoDB
        await self.global_config_service.ensure_defaults_exist()

        # Ensure default admin user exists
        await self._ensure_default_admin_exists()

        logger.info("Async services initialized successfully")

    async def _ensure_default_admin_exists(self) -> None:
        """
        Create default admin user if no admin users exist.

        This enables first-run bootstrap without manual CLI commands.
        A random temporary password is generated and logged once.
        """
        try:
            admin_count = await self.dynamodb_repository.count_active_admins()
            if admin_count == 0:
                logger.info("No admin users found. Creating default admin user...")
                password = secrets.token_urlsafe(12)
                await self.user_service.create_user(
                    username="admin",
                    password=password,
                    role="admin"
                )
                logger.warning(f"Default admin created with temporary password: {password}")
                logger.warning("Change this password immediately! It will not be shown again.")
        except Exception as e:
            logger.error(f"Failed to check/create default admin: {e}", exc_info=True)
            # Don't fail startup - admin can be created manually via CLI
    
    def get_resolver_context(self) -> ResolverContext:
        """
        Get resolver context for GraphQL.

        Returns:
            ResolverContext with all service instances
        """
        return ResolverContext(
            auth_service=self.auth_service,
            job_manager=self.job_manager,
            s3_file_storage=self.s3_file_storage,
            translation_orchestrator=self.translation_orchestrator,
            thesaurus_service=self.thesaurus_service,
            user_service=self.user_service,
            language_pair_service=self.language_pair_service,
            user_settings_service=self.user_settings_service,
            global_config_service=self.global_config_service
        )


# Global app context
app_context: AppContext = None


async def health_check(request: Request) -> JSONResponse:
    """
    Health check endpoint.
    
    Args:
        request: Starlette request object
        
    Returns:
        JSON response with health status
    """
    return JSONResponse({
        "status": "healthy",
        "service": "Doc Translation Backend API",
        "version": "1.0.0"
    })


async def upload_file(request: Request) -> JSONResponse:
    """
    Upload a document file for translation.

    Supports multiple document formats: Excel (.xlsx), Word (.docx),
    PowerPoint (.pptx), and PDF (.pdf).

    Files are stored in S3 with user-scoped paths.

    Args:
        request: Starlette request object with multipart form data

    Returns:
        JSON response with file ID, metadata, and document type
    """
    import uuid
    from pathlib import Path

    # Verify authentication
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            {"error": "Authentication required"},
            status_code=401
        )

    token = auth_header.replace("Bearer ", "")
    username = app_context.auth_service.get_username_from_token(token)
    if not username:
        return JSONResponse(
            {"error": "Invalid or expired token"},
            status_code=401
        )

    try:
        # Parse multipart form data
        form = await request.form()
        file = form.get("file")

        if not file or not hasattr(file, 'read'):
            return JSONResponse(
                {"error": "No file provided"},
                status_code=400
            )

        # Read file content
        content = await file.read()
        filename = sanitize_filename(file.filename)

        if not filename:
            return JSONResponse(
                {"error": "Invalid filename"},
                status_code=400
            )

        # Validate file extension
        allowed_extensions = app_context.app_config.allowed_extensions
        file_ext = Path(filename).suffix.lower()
        if file_ext not in [ext.lower() for ext in allowed_extensions]:
            return JSONResponse(
                {"error": f"File extension not allowed. Allowed extensions: {allowed_extensions}"},
                status_code=400
            )

        # Validate file size
        max_size_bytes = app_context.app_config.max_file_size
        if len(content) > max_size_bytes:
            max_size_mb = max_size_bytes // (1024 * 1024)
            return JSONResponse(
                {"error": f"File size exceeds maximum of {max_size_mb}MB"},
                status_code=400
            )

        # Upload to S3 storage
        # Generate unique file ID
        file_id = str(uuid.uuid4())

        try:
            # Upload to S3 with user-scoped path
            await app_context.s3_file_storage.upload_file(
                user_id=username,
                file_id=file_id,
                file_content=content,
                original_filename=filename
            )
        except Exception as e:
            logger.error(f"Error uploading file to S3: {e}", exc_info=True)
            return JSONResponse(
                {"error": "Failed to upload file to storage"},
                status_code=500
            )

        # Detect document type from extension
        doc_type_map = {
            '.xlsx': 'excel', '.xls': 'excel',
            '.docx': 'word', '.doc': 'word',
            '.pptx': 'powerpoint', '.ppt': 'powerpoint',
            '.pdf': 'pdf',
            '.txt': 'text', '.md': 'markdown'
        }
        document_type = doc_type_map.get(file_ext)

        logger.info(f"File uploaded to S3: {filename} (ID: {file_id}, User: {username}, Type: {document_type or 'unknown'})")

        return JSONResponse({
            "id": file_id,
            "filename": filename,
            "size": len(content),
            "documentType": document_type
        })

    except ValueError as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=400
        )
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Internal server error"},
            status_code=500
        )


async def download_file(request: Request) -> Response:
    """
    Download a translated file.

    Returns a presigned S3 URL for download. Supports multiple document
    formats with appropriate MIME types.

    Args:
        request: Starlette request object with job_id and filename query params

    Returns:
        JSONResponse with presigned URL for S3 download
    """
    # Verify authentication
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            {"error": "Authentication required"},
            status_code=401
        )

    token = auth_header.replace("Bearer ", "")
    user = app_context.auth_service.verify_token(token)
    if not user:
        return JSONResponse(
            {"error": "Invalid or expired token"},
            status_code=401
        )

    # Get username from token payload - check both "sub" (JWT standard) and "username" (legacy)
    username = user.get("sub") or user.get("username")
    if not username:
        return JSONResponse(
            {"error": "Invalid token payload"},
            status_code=401
        )

    # Get query parameters
    job_id = request.query_params.get("job_id")
    raw_filename = request.query_params.get("filename")

    if not job_id or not raw_filename:
        return JSONResponse(
            {"error": "Missing job_id or filename parameter"},
            status_code=400
        )

    filename = sanitize_filename(raw_filename)
    if not filename:
        return JSONResponse(
            {"error": "Invalid filename"},
            status_code=400
        )

    try:
        # Fetch file content from S3 and stream it directly to the client.
        # This avoids presigned URLs that require direct S3 access, which
        # doesn't work for users on private networks via internal ALB.
        file_content = await app_context.s3_file_storage.get_output(
            user_id=username,
            job_id=job_id,
            filename=filename,
        )

        if file_content is None:
            return JSONResponse(
                {"error": "File not found or access denied"},
                status_code=404,
            )

        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        disposition = f"attachment; filename*=UTF-8''{quote(filename)}"

        logger.info(f"Streaming download: job_id={job_id}, filename={filename}, user={username}")

        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={"Content-Disposition": disposition},
        )

    except Exception as e:
        logger.error(f"Error downloading file: {e}", exc_info=True)
        return JSONResponse(
            {"error": "File not found or access denied"},
            status_code=404
        )


@asynccontextmanager
async def lifespan(app: Starlette):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    global app_context
    
    # Startup
    logger.info("Starting Doc Translation Backend API...")
    
    try:
        # Initialize application context
        app_context = AppContext()
        
        # Initialize async services (DynamoDB tables, config migration)
        await app_context.initialize_async_services()
        
        logger.info("=" * 60)
        logger.info("Doc Translation Backend API started successfully")
        logger.info("=" * 60)
        logger.info("GraphQL endpoint: /api/graphql")
        logger.info("Health check: /api/health")
        logger.info("Upload endpoint: /api/upload")
        logger.info("Download endpoint: /api/download")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Doc Translation Backend API...")
    logger.info("Shutdown complete")


class CustomGraphQL(GraphQL):
    """Custom GraphQL class with context injection."""
    
    async def get_context(self, request: Request, response: Any = None) -> Dict[str, Any]:
        """
        Get GraphQL context for each request.
        
        Args:
            request: Starlette request object
            response: Response object (optional)
            
        Returns:
            Context dictionary with request and resolver context
        """
        resolver_context = app_context.get_resolver_context()
        return {
            "request": request,
            "response": response,
            "resolver_context": resolver_context,
            # Expose services directly for user resolvers
            "user_service": resolver_context.user_service,
            "auth_service": resolver_context.auth_service,
        }


# Create GraphQL app - only enable GraphiQL in debug mode
graphql_ide = "graphiql" if os.getenv("DEBUG", "").lower() == "true" else None
graphql_app = CustomGraphQL(
    schema,
    graphql_ide=graphql_ide
)

# Define API routes with /api prefix for easier deployment
api_routes = [
    Route("/health", health_check),
    Route("/upload", upload_file, methods=["POST"]),
    Route("/download", download_file),
    Mount("/graphql", graphql_app),
]

# Mount all API routes under /api prefix
routes = [
    Mount("/api", routes=api_routes),
]

# Configure CORS middleware
frontend_url = os.getenv("FRONTEND_URL", "").strip() or "http://localhost:3000"
cors_origins = [
    "http://localhost:3000",  # Vite default dev server
    "http://localhost:5173",  # Vite alternative port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
if frontend_url not in cors_origins:
    cors_origins.append(frontend_url)

logger.info(f"CORS allowed origins: {cors_origins}")

class SecurityHeadersMiddleware:
    """ASGI middleware that adds security headers to all HTTP responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"x-xss-protection", b"0"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    (b"content-security-policy", b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"),
                ])
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


middleware = [
    Middleware(SecurityHeadersMiddleware),
    Middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["Content-Disposition"],
    ),
]

# Create Starlette application
app = Starlette(
    debug=os.getenv("DEBUG", "false").lower() == "true",
    routes=routes,
    middleware=middleware,
    lifespan=lifespan
)


def main():
    """Start the ASGI server."""
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
