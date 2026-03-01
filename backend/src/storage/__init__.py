"""
Storage layer for the translation system.

This package provides storage abstractions for:
- Job storage: DynamoDB-backed via JobRepository/JobStore
- File storage: S3FileStorage for Amazon S3 (required)
- Configuration: DynamoDB via DynamoDBRepository

File Storage Architecture:
- S3FileStorage: Amazon S3 storage for uploaded and translated files
- S3_BUCKET environment variable is required for the application to start
"""
from .job_store import JobStore
from .job_repository import JobRepository
from .dynamodb_repository import DynamoDBRepository
from .s3_file_storage import S3FileStorage

__all__ = [
    "JobStore",
    "JobRepository",
    "DynamoDBRepository",
    "S3FileStorage",
]
