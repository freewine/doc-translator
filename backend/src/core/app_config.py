"""Application configuration from environment variables."""
import os
from dataclasses import dataclass
from typing import List


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


@dataclass
class AppConfig:
    """
    Deploy-time configuration loaded from environment variables.

    Attributes:
        jwt_secret: JWT signing key (required)
        s3_bucket: S3 bucket name for file storage (required)
        max_concurrent_files: Max parallel file processing
        translation_batch_size: Cells/paragraphs per Bedrock API call
        max_file_size: Max upload size in bytes
        allowed_extensions: List of allowed file extensions
    """
    jwt_secret: str
    s3_bucket: str
    max_concurrent_files: int
    translation_batch_size: int
    max_file_size: int
    allowed_extensions: List[str]

    @classmethod
    def from_env(cls) -> "AppConfig":
        """
        Load configuration from environment variables.

        Required:
            JWT_SECRET: JWT signing key
            S3_BUCKET: S3 bucket name for file storage

        Optional (with defaults):
            MAX_CONCURRENT_FILES: 5
            TRANSLATION_BATCH_SIZE: 10
            MAX_FILE_SIZE: 52428800 (50MB)

        Note: Default values are mirrored in ecs/cdk.json for CDK/ECS deployments.

        Raises:
            ConfigurationError: If required vars missing or validation fails
        """
        errors = []

        # Required
        jwt_secret = os.environ.get("JWT_SECRET")
        if not jwt_secret:
            errors.append("JWT_SECRET environment variable is required")

        s3_bucket = os.environ.get("S3_BUCKET")
        if not s3_bucket:
            errors.append("S3_BUCKET environment variable is required")

        # Optional with validation
        max_files = os.getenv("MAX_CONCURRENT_FILES", "5")
        if not max_files.isdigit() or int(max_files) < 1:
            errors.append("MAX_CONCURRENT_FILES must be a positive integer")

        batch_size = os.getenv("TRANSLATION_BATCH_SIZE", "10")
        if not batch_size.isdigit() or int(batch_size) < 1:
            errors.append("TRANSLATION_BATCH_SIZE must be a positive integer")

        max_file_size = os.getenv("MAX_FILE_SIZE", "52428800")
        if not max_file_size.isdigit() or int(max_file_size) < 1:
            errors.append("MAX_FILE_SIZE must be a positive integer")

        if errors:
            raise ConfigurationError("\n".join(errors))

        return cls(
            jwt_secret=jwt_secret,
            s3_bucket=s3_bucket,
            max_concurrent_files=int(max_files),
            translation_batch_size=int(batch_size),
            max_file_size=int(max_file_size),
            allowed_extensions=[".xlsx", ".docx", ".pptx", ".pdf", ".txt", ".md"],
        )
