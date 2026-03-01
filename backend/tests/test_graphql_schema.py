"""
Tests for GraphQL schema definition.
"""
import pytest
from src.graphql import (
    schema,
    Query,
    Mutation,
    User,
    AuthPayload,
    LanguagePair,
    TranslationJob,
    FileProgress,
    FileError,
    FileUpload,
    JobStatus,
)


def test_schema_exists():
    """Test that the schema can be instantiated."""
    assert schema is not None
    # Strawberry schema has config attribute
    assert hasattr(schema, 'config')


def test_query_type_has_required_fields():
    """Test that Query type has all required fields."""
    # Get the SDL to verify fields
    sdl = str(schema)
    
    # Check that required query fields are present in SDL
    required_fields = ['me', 'job', 'jobs', 'languagePairs']
    
    for field in required_fields:
        assert field in sdl, f"Missing query field: {field}"


def test_mutation_type_has_required_fields():
    """Test that Mutation type has all required fields."""
    # Get the SDL to verify fields
    sdl = str(schema)
    
    required_fields = [
        'login',
        'logout',
        'createTranslationJob',
        'addLanguagePair',
        'removeLanguagePair',
        'uploadFile'
    ]
    
    for field in required_fields:
        assert field in sdl, f"Missing mutation field: {field}"


def test_user_type_structure():
    """Test that User type has correct structure."""
    # User should have username field
    assert hasattr(User, '__annotations__')
    assert 'username' in User.__annotations__
    assert User.__annotations__['username'] == str


def test_auth_payload_type_structure():
    """Test that AuthPayload type has correct structure."""
    assert hasattr(AuthPayload, '__annotations__')
    assert 'token' in AuthPayload.__annotations__
    assert 'user' in AuthPayload.__annotations__
    assert AuthPayload.__annotations__['token'] == str
    assert AuthPayload.__annotations__['user'] == User


def test_language_pair_type_structure():
    """Test that LanguagePair type has correct structure."""
    assert hasattr(LanguagePair, '__annotations__')
    required_fields = {
        'id': str,
        'source_language': str,
        'target_language': str,
        'source_language_code': str,
        'target_language_code': str,
    }
    
    for field_name, field_type in required_fields.items():
        assert field_name in LanguagePair.__annotations__
        assert LanguagePair.__annotations__[field_name] == field_type


def test_file_progress_type_structure():
    """Test that FileProgress type has correct structure."""
    assert hasattr(FileProgress, '__annotations__')
    required_fields = {
        'filename': str,
        'progress': float,
        'cells_total': int,
        'cells_translated': int,
        'worksheets_completed': int,
        'worksheets_total': int,
    }
    
    for field_name, field_type in required_fields.items():
        assert field_name in FileProgress.__annotations__
        assert FileProgress.__annotations__[field_name] == field_type


def test_file_error_type_structure():
    """Test that FileError type has correct structure."""
    assert hasattr(FileError, '__annotations__')
    assert 'filename' in FileError.__annotations__
    assert 'error' in FileError.__annotations__
    assert 'error_type' in FileError.__annotations__
    assert 'timestamp' in FileError.__annotations__


def test_translation_job_type_structure():
    """Test that TranslationJob type has correct structure."""
    assert hasattr(TranslationJob, '__annotations__')
    required_fields = [
        'id',
        'status',
        'progress',
        'files_total',
        'files_completed',
        'files_processing',
        'files_failed',
        'created_at',
        'completed_at',
        'language_pair',
    ]
    
    for field_name in required_fields:
        assert field_name in TranslationJob.__annotations__, \
            f"Missing field: {field_name}"


def test_file_upload_type_structure():
    """Test that FileUpload type has correct structure."""
    assert hasattr(FileUpload, '__annotations__')
    required_fields = {
        'id': str,
        'filename': str,
        'size': int,
    }
    
    for field_name, field_type in required_fields.items():
        assert field_name in FileUpload.__annotations__
        assert FileUpload.__annotations__[field_name] == field_type


def test_job_status_enum():
    """Test that JobStatus enum has all required values."""
    required_values = {
        'PENDING',
        'PROCESSING',
        'COMPLETED',
        'FAILED',
        'PARTIAL_SUCCESS',
    }
    
    enum_values = {status.name for status in JobStatus}
    
    assert required_values == enum_values, \
        f"JobStatus enum mismatch. Expected: {required_values}, Got: {enum_values}"


def test_schema_can_generate_sdl():
    """Test that the schema can generate SDL (Schema Definition Language)."""
    sdl = str(schema)
    
    # Check that key types are present in the SDL
    assert 'type Query' in sdl
    assert 'type Mutation' in sdl
    assert 'type User' in sdl
    assert 'type AuthPayload' in sdl
    assert 'type LanguagePair' in sdl
    assert 'type TranslationJob' in sdl
    assert 'type FileProgress' in sdl
    assert 'type FileError' in sdl
    assert 'type FileUpload' in sdl
    assert 'enum JobStatus' in sdl


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
