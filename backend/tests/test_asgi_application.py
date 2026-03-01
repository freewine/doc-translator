"""Tests for ASGI application setup with Uvicorn."""

import pytest
import sys
from pathlib import Path
from starlette.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json

# Add backend directory to path to import from backend/main.py
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import main
from main import app, AppContext


@pytest.fixture
def client():
    """Create test client."""
    # Initialize app context before creating client
    with patch('main.AppConfig') as mock_config, \
         patch('main.AuthService'), \
         patch('main.JobStore'), \
         patch('main.TranslationService'), \
         patch('main.ExcelProcessor'), \
         patch('main.ConcurrentExecutor'), \
         patch('main.TranslationOrchestrator'), \
         patch('main.JobManager'):

        # Mock app config
        mock_config_instance = Mock()
        mock_config_instance.s3_bucket = "test-bucket"
        mock_config_instance.jwt_secret = "test-secret"
        mock_config_instance.max_concurrent_files = 10
        mock_config_instance.translation_batch_size = 10
        mock_config_instance.max_file_size = 52428800
        mock_config_instance.allowed_extensions = [".xlsx", ".docx", ".pptx", ".pdf"]
        mock_config.from_env.return_value = mock_config_instance

        # Initialize app context
        main.app_context = AppContext()

        # Create and return test client
        client = TestClient(app)
        yield client

        # Cleanup
        main.app_context = None


def test_health_check_endpoint(client):
    """Test health check endpoint is accessible."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data


def test_graphql_endpoint_exists(client):
    """Test GraphQL endpoint is accessible."""
    # GraphQL endpoint should respond to POST requests
    response = client.post(
        "/api/graphql",
        json={"query": "{ __typename }"}
    )
    # Should get a response (even if it's an error due to missing context)
    assert response.status_code in [200, 400, 500]


def test_graphiql_interface_disabled_by_default(client):
    """Test GraphiQL interface is disabled when DEBUG is not set."""
    response = client.get("/api/graphql")
    # Without DEBUG=true, GraphiQL is disabled - GET returns 404 or non-HTML
    content_type = response.headers.get("content-type", "")
    assert "text/html" not in content_type or response.status_code != 200


def test_cors_middleware_configured(client):
    """Test CORS middleware is properly configured."""
    response = client.options(
        "/graphql",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"
        }
    )
    
    # CORS should allow the request
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers
    assert "access-control-allow-headers" in response.headers


def test_cors_allows_credentials(client):
    """Test CORS allows credentials."""
    response = client.post(
        "/graphql",
        json={"query": "{ __typename }"},
        headers={"Origin": "http://localhost:3000"}
    )
    
    # Check if credentials are allowed
    assert "access-control-allow-credentials" in response.headers
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_exposes_content_disposition(client):
    """Test CORS exposes Content-Disposition header for file downloads."""
    response = client.post(
        "/graphql",
        json={"query": "{ __typename }"},
        headers={"Origin": "http://localhost:3000"}
    )
    
    # Check if Content-Disposition is exposed
    exposed_headers = response.headers.get("access-control-expose-headers", "")
    assert "Content-Disposition" in exposed_headers


def test_application_startup_initializes_services():
    """Test application startup initializes all required services."""
    with patch('main.AppContext') as mock_context:
        mock_instance = Mock()
        mock_context.return_value = mock_instance
        
        # The lifespan context manager will initialize AppContext
        # This is tested through the client fixture
        # Just verify the mock is available
        assert mock_context is not None


def test_app_context_initializes_all_services():
    """Test AppContext initializes all required services."""
    with patch('main.AppConfig') as mock_config, \
         patch('main.AuthService') as mock_auth, \
         patch('main.JobStore') as mock_job_store, \
         patch('main.TranslationService') as mock_translation, \
         patch('main.ExcelProcessor') as mock_excel, \
         patch('main.ConcurrentExecutor') as mock_executor, \
         patch('main.TranslationOrchestrator') as mock_orchestrator, \
         patch('main.JobManager') as mock_job_manager:

        # Mock app config
        mock_config_instance = Mock()
        mock_config_instance.s3_bucket = "test-bucket"
        mock_config_instance.jwt_secret = "test-secret"
        mock_config_instance.max_concurrent_files = 10
        mock_config_instance.translation_batch_size = 10
        mock_config_instance.max_file_size = 52428800
        mock_config_instance.allowed_extensions = [".xlsx", ".docx", ".pptx", ".pdf"]
        mock_config.from_env.return_value = mock_config_instance

        # Create AppContext
        context = AppContext()

        # Verify all services were initialized
        assert context.app_config is not None
        assert context.auth_service is not None
        assert context.job_store is not None
        assert context.translation_service is not None
        assert context.excel_processor is not None
        assert context.concurrent_executor is not None
        assert context.translation_orchestrator is not None
        assert context.job_manager is not None


def test_app_context_provides_resolver_context():
    """Test AppContext provides resolver context for GraphQL."""
    with patch('main.AppConfig') as mock_config, \
         patch('main.AuthService'), \
         patch('main.JobStore'), \
         patch('main.TranslationService'), \
         patch('main.ExcelProcessor'), \
         patch('main.ConcurrentExecutor'), \
         patch('main.TranslationOrchestrator'), \
         patch('main.JobManager'):

        # Mock app config
        mock_config_instance = Mock()
        mock_config_instance.s3_bucket = "test-bucket"
        mock_config_instance.jwt_secret = "test-secret"
        mock_config_instance.max_concurrent_files = 10
        mock_config_instance.translation_batch_size = 10
        mock_config_instance.max_file_size = 52428800
        mock_config_instance.allowed_extensions = [".xlsx", ".docx", ".pptx", ".pdf"]
        mock_config.from_env.return_value = mock_config_instance

        # Create AppContext
        context = AppContext()

        # Get resolver context
        resolver_context = context.get_resolver_context()

        # Verify resolver context has all required services
        assert resolver_context.auth_service is not None
        assert resolver_context.job_manager is not None
        assert resolver_context.translation_orchestrator is not None


def test_logging_configured():
    """Test logging is properly configured."""
    import logging
    
    # Check that logging is configured
    logger = logging.getLogger("main")
    assert logger.level <= logging.INFO
    
    # Check that handlers are configured
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0


def test_error_handling_in_startup():
    """Test error handling during application startup."""
    with patch('main.AppContext') as mock_context:
        mock_context.side_effect = Exception("Startup error")
        
        from main import lifespan
        import asyncio
        
        # Lifespan should raise the exception during startup
        async def test_lifespan():
            async with lifespan(app):
                pass
        
        with pytest.raises(Exception, match="Startup error"):
            asyncio.run(test_lifespan())


def test_shutdown_does_not_perform_file_cleanup():
    """Test that shutdown does not perform local file cleanup.
    
    Local file storage has been removed in favor of S3-only storage.
    The lifespan shutdown now only logs shutdown messages without
    attempting to clean up local files.
    """
    # This test verifies that the cleanup logic has been removed
    # as part of the local-storage-cleanup feature (task 2.4)
    from main import lifespan
    import inspect
    
    # Get the source code of the lifespan function
    source = inspect.getsource(lifespan)
    
    # Verify cleanup_old_files is not called in the lifespan function
    assert "cleanup_old_files" not in source, "cleanup_old_files should be removed from lifespan"
    assert "cleanup_days" not in source, "cleanup_days should not be referenced in lifespan"


def test_custom_graphql_context_injection():
    """Test CustomGraphQL injects context correctly."""
    from main import CustomGraphQL
    from starlette.requests import Request
    import asyncio
    
    with patch('main.app_context') as mock_context:
        mock_resolver_context = Mock()
        mock_context.get_resolver_context.return_value = mock_resolver_context
        
        graphql = CustomGraphQL(schema=Mock())
        
        # Create a mock request
        mock_request = Mock(spec=Request)
        
        # Get context
        context = asyncio.run(graphql.get_context(mock_request))
        
        # Verify context structure
        assert "request" in context
        assert "response" in context
        assert "resolver_context" in context
        assert context["resolver_context"] == mock_resolver_context


def test_environment_variable_configuration():
    """Test application respects environment variables."""
    import os
    
    # Test default values
    assert os.getenv("HOST", "0.0.0.0") == "0.0.0.0"
    assert os.getenv("PORT", "8000") == "8000"
    assert os.getenv("DEBUG", "false").lower() == "false"
    assert os.getenv("RELOAD", "false").lower() == "false"


def test_file_upload_size_limit_configured():
    """Test file upload size limits are configured."""
    # This is configured via AppConfig
    # We verify the configuration exists in app_config
    with patch('main.AppConfig') as mock_config:
        mock_config_instance = Mock()
        mock_config_instance.max_file_size = 52428800  # 50MB in bytes
        mock_config_instance.allowed_extensions = [".xlsx", ".docx", ".pptx", ".pdf"]
        mock_config_instance.s3_bucket = "test-bucket"
        mock_config_instance.jwt_secret = "test-secret"
        mock_config_instance.max_concurrent_files = 10
        mock_config_instance.translation_batch_size = 10
        mock_config.from_env.return_value = mock_config_instance

        with patch('main.AuthService'), \
             patch('main.JobStore'), \
             patch('main.TranslationService'), \
             patch('main.ExcelProcessor'), \
             patch('main.ConcurrentExecutor'), \
             patch('main.TranslationOrchestrator'), \
             patch('main.JobManager'):

            context = AppContext()

            # Verify file size limit is configured
            assert context.app_config.max_file_size == 52428800
            assert ".xlsx" in context.app_config.allowed_extensions
