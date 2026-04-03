"""
S3 file storage for uploaded and output files.

This module provides S3-based storage for:
- Uploaded files awaiting translation
- Translated output files
- File metadata

File structure in S3:
- {user_id}/uploads/{file_id}.{ext} - uploaded files
- {user_id}/uploads/{file_id}.metadata.json - file metadata
- {user_id}/outputs/{job_id}/{filename} - translated outputs
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Default chunk size for streaming S3 downloads
STREAM_CHUNK_SIZE = 128 * 1024  # 128 KB


# Content type mappings for supported document formats
CONTENT_TYPE_MAP = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
}

# Document type mappings
DOCUMENT_TYPE_MAP = {
    ".xlsx": "excel",
    ".xls": "excel",
    ".docx": "word",
    ".doc": "word",
    ".pptx": "powerpoint",
    ".ppt": "powerpoint",
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "markdown",
}


class S3FileStorage:
    """
    S3 storage for uploaded and translated files.

    This class provides async operations for:
    - Uploading files with metadata
    - Retrieving uploaded files
    - Saving and retrieving translated outputs
    - Generating presigned download URLs
    - Cleaning up user data

    All boto3 operations are wrapped with run_in_executor for async compatibility.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        logger_instance: Optional[logging.Logger] = None,
    ):
        """
        Initialize the S3 file storage.

        Args:
            bucket_name: S3 bucket name. If not provided, reads from S3_BUCKET env var.
            logger_instance: Optional logger instance for logging.

        Raises:
            ValueError: If no bucket name is provided and S3_BUCKET env var is not set.
        """
        self._bucket_name = bucket_name or os.getenv("S3_BUCKET")
        if not self._bucket_name:
            raise ValueError(
                "S3 bucket name is required. Set S3_BUCKET environment variable "
                "or provide bucket_name parameter."
            )

        self._logger = logger_instance or logger
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        """Get or create the S3 client."""
        if self._client is None:
            self._client = boto3.client("s3")
        return self._client

    async def _run_sync(self, func, *args, **kwargs) -> Any:
        """Run a synchronous function in an executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    def _get_content_type(self, extension: str) -> str:
        """
        Get the content type for a file extension.

        Args:
            extension: File extension including the dot (e.g., ".xlsx").

        Returns:
            Content type string.
        """
        return CONTENT_TYPE_MAP.get(extension.lower(), "application/octet-stream")

    def _detect_document_type(self, filename: str) -> Optional[str]:
        """
        Detect document type based on file extension.

        Args:
            filename: The filename to check.

        Returns:
            Document type string ("excel", "word", "powerpoint", "pdf") or None.
        """
        extension = Path(filename).suffix.lower()
        return DOCUMENT_TYPE_MAP.get(extension)

    def _make_upload_key(self, user_id: str, file_id: str, extension: str) -> str:
        """
        Create S3 key for uploaded file.

        Args:
            user_id: User ID.
            file_id: File ID.
            extension: File extension including the dot.

        Returns:
            S3 key string.
        """
        return f"{user_id}/uploads/{file_id}{extension}"

    def _make_metadata_key(self, user_id: str, file_id: str) -> str:
        """
        Create S3 key for file metadata.

        Args:
            user_id: User ID.
            file_id: File ID.

        Returns:
            S3 key string for metadata.
        """
        return f"{user_id}/uploads/{file_id}.metadata.json"

    def _make_output_key(self, user_id: str, job_id: str, filename: str) -> str:
        """
        Create S3 key for output file.

        Args:
            user_id: User ID.
            job_id: Job ID.
            filename: Output filename.

        Returns:
            S3 key string.
        """
        return f"{user_id}/outputs/{job_id}/{filename}"

    def _upload_file(
        self,
        user_id: str,
        file_id: str,
        file_content: bytes,
        original_filename: str,
    ) -> str:
        """
        Upload a file to S3 with metadata.

        Args:
            user_id: User ID.
            file_id: File ID.
            file_content: File content as bytes.
            original_filename: Original filename.

        Returns:
            S3 key of the uploaded file.
        """
        client = self._get_client()
        extension = Path(original_filename).suffix
        content_type = self._get_content_type(extension)
        document_type = self._detect_document_type(original_filename)

        # Upload the file
        file_key = self._make_upload_key(user_id, file_id, extension)
        client.put_object(
            Bucket=self._bucket_name,
            Key=file_key,
            Body=file_content,
            ContentType=content_type,
        )
        self._logger.info(f"Uploaded file to s3://{self._bucket_name}/{file_key}")

        # Upload metadata
        metadata = {
            "original_filename": original_filename,
            "content_type": content_type,
            "document_type": document_type,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": len(file_content),
        }
        metadata_key = self._make_metadata_key(user_id, file_id)
        client.put_object(
            Bucket=self._bucket_name,
            Key=metadata_key,
            Body=json.dumps(metadata),
            ContentType="application/json",
        )
        self._logger.info(f"Uploaded metadata to s3://{self._bucket_name}/{metadata_key}")

        return file_key

    async def upload_file(
        self,
        user_id: str,
        file_id: str,
        file_content: bytes,
        original_filename: str,
    ) -> str:
        """
        Async upload a file to S3 with metadata.

        Args:
            user_id: User ID.
            file_id: File ID.
            file_content: File content as bytes.
            original_filename: Original filename.

        Returns:
            S3 key of the uploaded file.
        """
        return await self._run_sync(
            self._upload_file, user_id, file_id, file_content, original_filename
        )

    def _get_upload(
        self, user_id: str, file_id: str
    ) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Get an uploaded file with its metadata.

        Args:
            user_id: User ID.
            file_id: File ID.

        Returns:
            Tuple of (file_content, metadata) or None if not found.
        """
        client = self._get_client()

        try:
            # Get metadata first to determine extension
            metadata_key = self._make_metadata_key(user_id, file_id)
            metadata_response = client.get_object(
                Bucket=self._bucket_name, Key=metadata_key
            )
            metadata = json.loads(metadata_response["Body"].read().decode())

            # Get the file
            extension = Path(metadata["original_filename"]).suffix
            file_key = self._make_upload_key(user_id, file_id, extension)
            file_response = client.get_object(Bucket=self._bucket_name, Key=file_key)
            file_content = file_response["Body"].read()

            return file_content, metadata

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                self._logger.debug(f"File not found: user_id={user_id}, file_id={file_id}")
                return None
            raise

    async def get_upload(
        self, user_id: str, file_id: str
    ) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Async get an uploaded file with its metadata.

        Args:
            user_id: User ID.
            file_id: File ID.

        Returns:
            Tuple of (file_content, metadata) or None if not found.
        """
        return await self._run_sync(self._get_upload, user_id, file_id)

    def _save_output(
        self,
        user_id: str,
        job_id: str,
        filename: str,
        content: bytes,
    ) -> str:
        """
        Save a translated output file.

        Args:
            user_id: User ID.
            job_id: Job ID.
            filename: Output filename.
            content: File content as bytes.

        Returns:
            S3 key of the saved file.
        """
        client = self._get_client()
        extension = Path(filename).suffix
        content_type = self._get_content_type(extension)

        output_key = self._make_output_key(user_id, job_id, filename)
        client.put_object(
            Bucket=self._bucket_name,
            Key=output_key,
            Body=content,
            ContentType=content_type,
        )
        self._logger.info(f"Saved output to s3://{self._bucket_name}/{output_key}")

        return output_key

    async def save_output(
        self,
        user_id: str,
        job_id: str,
        filename: str,
        content: bytes,
    ) -> str:
        """
        Async save a translated output file.

        Args:
            user_id: User ID.
            job_id: Job ID.
            filename: Output filename.
            content: File content as bytes.

        Returns:
            S3 key of the saved file.
        """
        return await self._run_sync(self._save_output, user_id, job_id, filename, content)

    def _get_output(
        self, user_id: str, job_id: str, filename: str
    ) -> Optional[bytes]:
        """
        Get a translated output file.

        Args:
            user_id: User ID.
            job_id: Job ID.
            filename: Output filename.

        Returns:
            File content as bytes or None if not found.
        """
        client = self._get_client()

        try:
            output_key = self._make_output_key(user_id, job_id, filename)
            response = client.get_object(Bucket=self._bucket_name, Key=output_key)
            return response["Body"].read()

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                self._logger.debug(
                    f"Output not found: user_id={user_id}, job_id={job_id}, filename={filename}"
                )
                return None
            raise

    async def get_output(
        self, user_id: str, job_id: str, filename: str
    ) -> Optional[bytes]:
        """
        Async get a translated output file.

        Args:
            user_id: User ID.
            job_id: Job ID.
            filename: Output filename.

        Returns:
            File content as bytes or None if not found.
        """
        return await self._run_sync(self._get_output, user_id, job_id, filename)

    def _open_output_stream(
        self, user_id: str, job_id: str, filename: str
    ) -> Optional[Dict[str, Any]]:
        """
        Open an S3 object for streaming without reading the body.

        Returns the raw S3 get_object response (containing Body StreamingBody
        and ContentLength) or None if the key does not exist.
        """
        client = self._get_client()
        try:
            output_key = self._make_output_key(user_id, job_id, filename)
            return client.get_object(Bucket=self._bucket_name, Key=output_key)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                self._logger.debug(
                    f"Output not found: user_id={user_id}, job_id={job_id}, "
                    f"filename={filename}"
                )
                return None
            raise

    async def stream_output(
        self,
        user_id: str,
        job_id: str,
        filename: str,
        chunk_size: int = STREAM_CHUNK_SIZE,
    ) -> Optional[tuple[int, AsyncGenerator[bytes, None]]]:
        """
        Stream a translated output file in chunks.

        Returns a tuple of (content_length, async_generator) or None if
        the file does not exist. The caller must iterate the generator
        to completion or the underlying S3 connection will leak.

        Args:
            user_id: User ID.
            job_id: Job ID.
            filename: Output filename.
            chunk_size: Size of each chunk in bytes (default: 128KB).

        Returns:
            Tuple of (content_length_bytes, async_chunk_generator), or None.
        """
        loop = asyncio.get_event_loop()

        response = await loop.run_in_executor(
            None, self._open_output_stream, user_id, job_id, filename
        )
        if response is None:
            return None

        content_length = response["ContentLength"]
        body = response["Body"]

        async def _chunk_generator() -> AsyncGenerator[bytes, None]:
            try:
                while True:
                    chunk = await loop.run_in_executor(
                        None, body.read, chunk_size
                    )
                    if not chunk:
                        break
                    yield chunk
            finally:
                body.close()

        return content_length, _chunk_generator()

    def _generate_download_url(
        self, s3_key: str, expiry: int = 900, filename: Optional[str] = None
    ) -> str:
        """
        Generate a presigned URL for downloading a file.

        Args:
            s3_key: S3 key of the file.
            expiry: URL expiry time in seconds (default: 15 minutes).
            filename: Optional filename for Content-Disposition header.

        Returns:
            Presigned URL string.
        """
        client = self._get_client()
        params: dict = {"Bucket": self._bucket_name, "Key": s3_key}
        if filename:
            from urllib.parse import quote
            params["ResponseContentDisposition"] = (
                f"attachment; filename*=UTF-8''{quote(filename)}"
            )
        url = client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expiry,
        )
        self._logger.debug(f"Generated presigned URL for {s3_key}, expires in {expiry}s")
        return url

    async def generate_download_url(
        self, s3_key: str, expiry: int = 900, filename: Optional[str] = None
    ) -> str:
        """
        Async generate a presigned URL for downloading a file.

        Args:
            s3_key: S3 key of the file.
            expiry: URL expiry time in seconds (default: 15 minutes).
            filename: Optional filename for Content-Disposition header.

        Returns:
            Presigned URL string.
        """
        return await self._run_sync(self._generate_download_url, s3_key, expiry, filename)

    async def generate_output_download_url(
        self, user_id: str, job_id: str, filename: str, expiry: int = 900
    ) -> str:
        """
        Generate a presigned URL for downloading a translated output file.

        Args:
            user_id: User ID.
            job_id: Job ID.
            filename: Output filename.
            expiry: URL expiry time in seconds (default: 15 minutes).

        Returns:
            Presigned URL string.
        """
        output_key = self._make_output_key(user_id, job_id, filename)
        return await self.generate_download_url(output_key, expiry, filename)

    def _delete_objects(self, prefix: str) -> int:
        """
        Delete all objects with a given prefix.

        Args:
            prefix: S3 key prefix.

        Returns:
            Number of deleted objects.
        """
        client = self._get_client()
        deleted_count = 0
        continuation_token = None

        while True:
            # List objects
            list_kwargs = {
                "Bucket": self._bucket_name,
                "Prefix": prefix,
            }
            if continuation_token:
                list_kwargs["ContinuationToken"] = continuation_token

            response = client.list_objects_v2(**list_kwargs)

            # Delete listed objects
            contents = response.get("Contents", [])
            if contents:
                delete_keys = [{"Key": obj["Key"]} for obj in contents]
                client.delete_objects(
                    Bucket=self._bucket_name,
                    Delete={"Objects": delete_keys},
                )
                deleted_count += len(delete_keys)
                self._logger.info(
                    f"Deleted {len(delete_keys)} objects with prefix {prefix}"
                )

            # Check for more objects
            if response.get("IsTruncated"):
                continuation_token = response.get("NextContinuationToken")
            else:
                break

        return deleted_count

    def _delete_user_data(self, user_id: str) -> int:
        """
        Delete all data for a user.

        Args:
            user_id: User ID.

        Returns:
            Number of deleted objects.
        """
        prefix = f"{user_id}/"
        return self._delete_objects(prefix)

    async def delete_user_data(self, user_id: str) -> int:
        """
        Async delete all data for a user.

        Args:
            user_id: User ID.

        Returns:
            Number of deleted objects.
        """
        return await self._run_sync(self._delete_user_data, user_id)

    def _delete_job_outputs(self, user_id: str, job_id: str) -> int:
        """
        Delete all output files for a job.

        Args:
            user_id: User ID.
            job_id: Job ID.

        Returns:
            Number of deleted objects.
        """
        prefix = f"{user_id}/outputs/{job_id}/"
        return self._delete_objects(prefix)

    async def delete_job_outputs(self, user_id: str, job_id: str) -> int:
        """
        Async delete all output files for a job.

        Args:
            user_id: User ID.
            job_id: Job ID.

        Returns:
            Number of deleted objects.
        """
        return await self._run_sync(self._delete_job_outputs, user_id, job_id)
