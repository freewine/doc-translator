"""
DynamoDB repository for translation job storage.

This module provides a repository pattern implementation for storing and retrieving
translation jobs using Amazon DynamoDB.
"""
import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from ..models.job import (
    TranslationJob,
    JobStatus,
    FileProgress,
    CompletedFile,
    FileError,
    LanguagePair,
    DocumentType,
)

logger = logging.getLogger(__name__)


# Table name
JOBS_TABLE = "doc_translation_jobs"


class JobNotFoundError(Exception):
    """Raised when a job is not found."""
    pass


class JobRepository:
    """
    Repository for DynamoDB operations on translation jobs.

    This class provides CRUD operations for translation jobs with support for:
    - User-scoped job storage (user_id as partition key)
    - Status-based queries via GSI
    - Date range filtering
    - Cursor-based pagination

    All operations are async-compatible using run_in_executor for boto3 calls.

    Table Schema:
    - Primary Key: user_id (HASH), job_id (RANGE)
    - GSI: user_status_index with user_id (HASH), status_created (RANGE)
    """

    def __init__(
        self,
        logger_instance: Optional[logging.Logger] = None
    ):
        """
        Initialize the JobRepository.

        Args:
            logger_instance: Optional logger instance for logging.

        Note:
            AWS region is determined by boto3 default chain:
            - AWS_REGION or AWS_DEFAULT_REGION env vars
            - ~/.aws/config
            - EC2/ECS instance metadata
        """
        self._logger = logger_instance or logger
        self._client: Optional[Any] = None
        self._resource: Optional[Any] = None

    def _get_client(self) -> Any:
        """Get or create the DynamoDB client."""
        if self._client is None:
            self._client = boto3.client("dynamodb")
        return self._client

    def _get_resource(self) -> Any:
        """Get or create the DynamoDB resource."""
        if self._resource is None:
            self._resource = boto3.resource("dynamodb")
        return self._resource

    async def _run_sync(self, func, *args, **kwargs) -> Any:
        """Run a synchronous function in an executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # =========================================================================
    # Serialization/Deserialization
    # =========================================================================

    def _convert_floats_to_decimal(self, obj: Any) -> Any:
        """
        Recursively convert float values to Decimal for DynamoDB.

        Args:
            obj: The object to convert (dict, list, or primitive).

        Returns:
            The object with floats converted to Decimal.
        """
        if isinstance(obj, dict):
            return {k: self._convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimal(item) for item in obj]
        elif isinstance(obj, float):
            return Decimal(str(obj))
        return obj

    def _convert_decimals_to_native(self, obj: Any) -> Any:
        """
        Recursively convert Decimal values to native Python types.

        Args:
            obj: The object to convert (dict, list, or primitive).

        Returns:
            The object with Decimals converted to int or float.
        """
        if isinstance(obj, dict):
            return {k: self._convert_decimals_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals_to_native(item) for item in obj]
        elif isinstance(obj, Decimal):
            # Convert to int if it's a whole number, otherwise float
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return obj

    def _serialize_job(self, job: TranslationJob, user_id: str) -> Dict[str, Any]:
        """
        Serialize a TranslationJob to DynamoDB item format.

        Args:
            job: The TranslationJob to serialize.
            user_id: The user ID for the partition key.

        Returns:
            Dictionary representation suitable for DynamoDB.
        """
        created_at_str = job.created_at.isoformat() if job.created_at else datetime.now(timezone.utc).isoformat()
        completed_at_str = job.completed_at.isoformat() if job.completed_at else None

        # Create status_created composite key for GSI sorting
        status_created = f"{job.status.value}#{created_at_str}"

        # Serialize file progress
        files_processing = []
        for fp in job.files_processing:
            files_processing.append({
                "filename": fp.filename,
                "progress": Decimal(str(fp.progress)),
                "segments_total": fp.segments_total,
                "segments_translated": fp.segments_translated,
                "document_type": fp.document_type.value if fp.document_type else None,
                "cells_total": fp.cells_total,
                "cells_translated": fp.cells_translated,
                "worksheets_completed": fp.worksheets_completed,
                "worksheets_total": fp.worksheets_total,
            })

        # Serialize completed files
        completed_files = []
        for cf in job.completed_files:
            completed_files.append({
                "original_filename": cf.original_filename,
                "output_filename": cf.output_filename,
                "segments_translated": cf.segments_translated,
                "document_type": cf.document_type.value if cf.document_type else None,
                "cells_translated": cf.cells_translated,
            })

        # Serialize failed files
        files_failed = []
        for fe in job.files_failed:
            files_failed.append({
                "filename": fe.filename,
                "error": fe.error,
                "error_type": fe.error_type,
                "timestamp": fe.timestamp.isoformat() if fe.timestamp else None,
            })

        # Serialize language pair
        language_pair = None
        if job.language_pair:
            language_pair = {
                "id": job.language_pair.id,
                "source_language": job.language_pair.source_language,
                "target_language": job.language_pair.target_language,
                "source_language_code": job.language_pair.source_language_code,
                "target_language_code": job.language_pair.target_language_code,
            }

        item = {
            "user_id": user_id,
            "job_id": job.id,
            "status": job.status.value,
            "status_created": status_created,
            "progress": Decimal(str(job.progress)),
            "files_total": job.files_total,
            "files_completed": job.files_completed,
            "files_processing": files_processing,
            "files_failed": files_failed,
            "completed_files": completed_files,
            "created_at": created_at_str,
            "completed_at": completed_at_str,
            "file_ids": job.file_ids,
            "auto_append": job.auto_append,
            "language_pair": language_pair,
        }

        return item

    def _deserialize_job(self, item: Dict[str, Any]) -> TranslationJob:
        """
        Deserialize a DynamoDB item to a TranslationJob.

        Args:
            item: DynamoDB item dictionary.

        Returns:
            Deserialized TranslationJob instance.
        """
        # Convert Decimals to native types
        item = self._convert_decimals_to_native(item)

        # Parse timestamps
        created_at = datetime.fromisoformat(item["created_at"]) if item.get("created_at") else datetime.now(timezone.utc)
        completed_at = datetime.fromisoformat(item["completed_at"]) if item.get("completed_at") else None

        # Deserialize file progress
        files_processing = []
        for fp_data in item.get("files_processing", []):
            doc_type = None
            if fp_data.get("document_type"):
                doc_type = DocumentType(fp_data["document_type"])
            files_processing.append(FileProgress(
                filename=fp_data["filename"],
                progress=float(fp_data.get("progress", 0)),
                segments_total=int(fp_data.get("segments_total", 0)),
                segments_translated=int(fp_data.get("segments_translated", 0)),
                document_type=doc_type,
                cells_total=int(fp_data.get("cells_total", 0)),
                cells_translated=int(fp_data.get("cells_translated", 0)),
                worksheets_completed=int(fp_data.get("worksheets_completed", 0)),
                worksheets_total=int(fp_data.get("worksheets_total", 0)),
            ))

        # Deserialize completed files
        completed_files = []
        for cf_data in item.get("completed_files", []):
            doc_type = None
            if cf_data.get("document_type"):
                doc_type = DocumentType(cf_data["document_type"])
            completed_files.append(CompletedFile(
                original_filename=cf_data["original_filename"],
                output_filename=cf_data["output_filename"],
                segments_translated=int(cf_data.get("segments_translated", 0)),
                document_type=doc_type,
                cells_translated=int(cf_data.get("cells_translated", 0)),
            ))

        # Deserialize failed files
        files_failed = []
        for fe_data in item.get("files_failed", []):
            timestamp = datetime.fromisoformat(fe_data["timestamp"]) if fe_data.get("timestamp") else datetime.now()
            files_failed.append(FileError(
                filename=fe_data["filename"],
                error=fe_data["error"],
                error_type=fe_data.get("error_type", "ProcessingError"),
                timestamp=timestamp,
            ))

        # Deserialize language pair
        language_pair = None
        if item.get("language_pair"):
            lp_data = item["language_pair"]
            language_pair = LanguagePair(
                id=lp_data["id"],
                source_language=lp_data["source_language"],
                target_language=lp_data["target_language"],
                source_language_code=lp_data["source_language_code"],
                target_language_code=lp_data["target_language_code"],
            )

        return TranslationJob(
            id=item["job_id"],
            status=JobStatus(item["status"]),
            progress=float(item.get("progress", 0)),
            files_total=int(item.get("files_total", 0)),
            files_completed=int(item.get("files_completed", 0)),
            files_processing=files_processing,
            files_failed=files_failed,
            completed_files=completed_files,
            created_at=created_at,
            completed_at=completed_at,
            language_pair=language_pair,
            file_ids=item.get("file_ids", []),
            auto_append=item.get("auto_append", True),
        )

    # =========================================================================
    # Table Operations
    # =========================================================================

    def _table_exists(self, table_name: str) -> bool:
        """
        Check if a DynamoDB table exists.

        Args:
            table_name: Name of the table to check.

        Returns:
            True if the table exists, False otherwise.
        """
        client = self._get_client()
        try:
            client.describe_table(TableName=table_name)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return False
            raise
        except Exception:
            return False

    async def table_exists(self, table_name: str) -> bool:
        """
        Async check if a DynamoDB table exists.

        Args:
            table_name: Name of the table to check.

        Returns:
            True if the table exists, False otherwise.
        """
        return await self._run_sync(self._table_exists, table_name)

    def _create_jobs_table(self) -> None:
        """
        Create the jobs table with required indexes.

        Table schema:
        - user_id: Partition key (String)
        - job_id: Sort key (String)

        GSI: user_status_index
        - user_id: Partition key (String)
        - status_created: Sort key (String) - composite of status#created_at
        """
        client = self._get_client()

        try:
            client.create_table(
                TableName=JOBS_TABLE,
                KeySchema=[
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "job_id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "job_id", "AttributeType": "S"},
                    {"AttributeName": "status_created", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "user_status_index",
                        "KeySchema": [
                            {"AttributeName": "user_id", "KeyType": "HASH"},
                            {"AttributeName": "status_created", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            self._logger.info(f"Created table {JOBS_TABLE}")

            # Wait for table to be active
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=JOBS_TABLE)
            self._logger.info(f"Table {JOBS_TABLE} is now active")

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                self._logger.info(f"Table {JOBS_TABLE} already exists")
            else:
                raise

    async def initialize_table(self) -> None:
        """
        Create the jobs table if it doesn't exist.

        This method should be called during application startup to ensure
        the jobs table is available.
        """
        self._logger.info("Initializing jobs table...")

        if not await self.table_exists(JOBS_TABLE):
            await self._run_sync(self._create_jobs_table)
        else:
            self._logger.info(f"Table {JOBS_TABLE} already exists")

        self._logger.info("Jobs table initialization complete")

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def _create_job(self, job: TranslationJob, user_id: str) -> TranslationJob:
        """
        Create a new job in DynamoDB.

        Args:
            job: The TranslationJob to create.
            user_id: The user ID for the partition key.

        Returns:
            The created TranslationJob.

        Raises:
            ClientError: If the job already exists or DynamoDB error.
        """
        resource = self._get_resource()
        table = resource.Table(JOBS_TABLE)

        item = self._serialize_job(job, user_id)

        # Use condition to prevent overwriting existing job
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(user_id) AND attribute_not_exists(job_id)"
        )

        return job

    async def create_job(self, job: TranslationJob, user_id: str) -> TranslationJob:
        """
        Async create a new job.

        Args:
            job: The TranslationJob to create.
            user_id: The user ID for the partition key.

        Returns:
            The created TranslationJob.
        """
        return await self._run_sync(self._create_job, job, user_id)

    def _get_job(self, user_id: str, job_id: str) -> Optional[TranslationJob]:
        """
        Get a job by user ID and job ID.

        Args:
            user_id: The user ID (partition key).
            job_id: The job ID (sort key).

        Returns:
            The TranslationJob if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(JOBS_TABLE)

        response = table.get_item(Key={"user_id": user_id, "job_id": job_id})

        item = response.get("Item")
        if item:
            return self._deserialize_job(item)
        return None

    async def get_job(self, user_id: str, job_id: str) -> Optional[TranslationJob]:
        """
        Async get a job by user ID and job ID.

        Args:
            user_id: The user ID (partition key).
            job_id: The job ID (sort key).

        Returns:
            The TranslationJob if found, None otherwise.
        """
        return await self._run_sync(self._get_job, user_id, job_id)

    def _update_job(self, job: TranslationJob, user_id: str) -> TranslationJob:
        """
        Update an existing job.

        Args:
            job: The TranslationJob with updated data.
            user_id: The user ID for the partition key.

        Returns:
            The updated TranslationJob.

        Raises:
            JobNotFoundError: If the job doesn't exist.
        """
        resource = self._get_resource()
        table = resource.Table(JOBS_TABLE)

        # Check if job exists
        response = table.get_item(Key={"user_id": user_id, "job_id": job.id})
        if not response.get("Item"):
            raise JobNotFoundError(f"Job {job.id} not found for user {user_id}")

        item = self._serialize_job(job, user_id)
        table.put_item(Item=item)

        return job

    async def update_job(self, job: TranslationJob, user_id: str) -> TranslationJob:
        """
        Async update an existing job.

        Args:
            job: The TranslationJob with updated data.
            user_id: The user ID for the partition key.

        Returns:
            The updated TranslationJob.

        Raises:
            JobNotFoundError: If the job doesn't exist.
        """
        return await self._run_sync(self._update_job, job, user_id)

    def _delete_job(self, user_id: str, job_id: str) -> bool:
        """
        Delete a job.

        Args:
            user_id: The user ID (partition key).
            job_id: The job ID (sort key).

        Returns:
            True if deleted, False if not found.
        """
        resource = self._get_resource()
        table = resource.Table(JOBS_TABLE)

        try:
            response = table.delete_item(
                Key={"user_id": user_id, "job_id": job_id},
                ReturnValues="ALL_OLD"
            )
            return "Attributes" in response
        except ClientError:
            return False

    async def delete_job(self, user_id: str, job_id: str) -> bool:
        """
        Async delete a job.

        Args:
            user_id: The user ID (partition key).
            job_id: The job ID (sort key).

        Returns:
            True if deleted, False if not found.
        """
        return await self._run_sync(self._delete_job, user_id, job_id)

    def _list_jobs(
        self,
        user_id: str,
        status: Optional[JobStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> Tuple[List[TranslationJob], Optional[str]]:
        """
        List jobs for a user with optional filtering and pagination.

        Args:
            user_id: The user ID to list jobs for.
            status: Optional status to filter by.
            date_from: Optional start date for filtering.
            date_to: Optional end date for filtering.
            limit: Maximum number of jobs to return.
            cursor: Pagination cursor from previous query.

        Returns:
            Tuple of (list of jobs, next cursor or None).
        """
        resource = self._get_resource()
        table = resource.Table(JOBS_TABLE)

        # Build query parameters
        query_kwargs = {
            "KeyConditionExpression": "user_id = :user_id",
            "ExpressionAttributeValues": {":user_id": user_id},
            "Limit": limit,
            "ScanIndexForward": False,  # Most recent first
        }

        # Build filter expression for status and date range
        filter_parts = []
        expression_names = {}

        if status:
            filter_parts.append("#status = :status_val")
            expression_names["#status"] = "status"
            query_kwargs["ExpressionAttributeValues"][":status_val"] = status.value

        if date_from:
            filter_parts.append("created_at >= :date_from")
            query_kwargs["ExpressionAttributeValues"][":date_from"] = date_from.isoformat()

        if date_to:
            filter_parts.append("created_at <= :date_to")
            query_kwargs["ExpressionAttributeValues"][":date_to"] = date_to.isoformat()

        if filter_parts:
            query_kwargs["FilterExpression"] = " AND ".join(filter_parts)

        if expression_names:
            query_kwargs["ExpressionAttributeNames"] = expression_names

        # Handle pagination cursor
        if cursor:
            try:
                decoded = json.loads(base64.b64decode(cursor).decode("utf-8"))
                # Validate cursor structure: must be a dict with string keys
                if not isinstance(decoded, dict):
                    raise ValueError("Cursor must decode to a dictionary")
                # Validate expected DynamoDB key structure
                expected_keys = {"user_id", "job_id"}
                if not expected_keys.issubset(decoded.keys()):
                    raise ValueError(f"Cursor missing required keys: {expected_keys - decoded.keys()}")
                # Ensure all values are primitive types (str, int, float)
                for key, value in decoded.items():
                    if not isinstance(value, (str, int, float)):
                        raise ValueError(f"Cursor key '{key}' has invalid type: {type(value).__name__}")
                query_kwargs["ExclusiveStartKey"] = decoded
            except (json.JSONDecodeError, ValueError, Exception) as e:
                self._logger.warning(f"Invalid pagination cursor: {e}")

        # Execute query
        response = table.query(**query_kwargs)

        # Deserialize jobs
        jobs = [self._deserialize_job(item) for item in response.get("Items", [])]

        # Create next cursor if there are more results
        next_cursor = None
        last_key = response.get("LastEvaluatedKey")
        if last_key:
            next_cursor = base64.b64encode(
                json.dumps(last_key).encode("utf-8")
            ).decode("utf-8")

        return jobs, next_cursor

    async def list_jobs(
        self,
        user_id: str,
        status: Optional[JobStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> Tuple[List[TranslationJob], Optional[str]]:
        """
        Async list jobs for a user with optional filtering and pagination.

        Args:
            user_id: The user ID to list jobs for.
            status: Optional status to filter by.
            date_from: Optional start date for filtering.
            date_to: Optional end date for filtering.
            limit: Maximum number of jobs to return.
            cursor: Pagination cursor from previous query.

        Returns:
            Tuple of (list of jobs, next cursor or None).
        """
        return await self._run_sync(
            self._list_jobs, user_id, status, date_from, date_to, limit, cursor
        )
