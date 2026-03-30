"""
DynamoDB repository for term translation thesaurus storage.

This module provides a repository pattern implementation for storing and retrieving
term translation pairs and catalogs using Amazon DynamoDB.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from src.models.user import UserStatus

logger = logging.getLogger(__name__)


# Table names
TERM_PAIRS_TABLE = "doc_translation_term_pairs"
CATALOGS_TABLE = "doc_translation_catalogs"


class DynamoDBRepository:
    """
    Repository for DynamoDB operations on term pairs, catalogs, users, and configuration.

    This class provides CRUD operations for:
    - Term translation pairs (source term -> target term mappings)
    - Catalogs (collections of term pairs)
    - Users and authentication
    - Global configuration settings

    All operations are async-compatible using run_in_executor for boto3 calls.
    """
    
    def __init__(
        self,
        logger_instance: Optional[logging.Logger] = None
    ):
        """
        Initialize the DynamoDB repository.

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
        self._loop: Optional[asyncio.AbstractEventLoop] = None

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
    
    async def table_exists(self, table_name: str) -> bool:
        """
        Async check if a DynamoDB table exists.
        
        Args:
            table_name: Name of the table to check.
            
        Returns:
            True if the table exists, False otherwise.
        """
        return await self._run_sync(self._table_exists, table_name)

    def _create_term_pairs_table(self) -> None:
        """
        Create the term pairs table with required indexes.
        
        Table schema:
        - pk: Partition key (LP#{language_pair_id}#CAT#{catalog_id})
        - sk: Sort key (TERM#{source_term})
        
        GSI1: For querying by catalog
        - Partition key: catalog_id
        - Sort key: updated_at
        
        GSI2: For querying by term ID
        - Partition key: id
        """
        client = self._get_client()
        
        try:
            client.create_table(
                TableName=TERM_PAIRS_TABLE,
                KeySchema=[
                    {"AttributeName": "pk", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "pk", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                    {"AttributeName": "catalog_id", "AttributeType": "S"},
                    {"AttributeName": "updated_at", "AttributeType": "S"},
                    {"AttributeName": "id", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "GSI1-catalog-updated",
                        "KeySchema": [
                            {"AttributeName": "catalog_id", "KeyType": "HASH"},
                            {"AttributeName": "updated_at", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                    {
                        "IndexName": "GSI2-id",
                        "KeySchema": [
                            {"AttributeName": "id", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            self._logger.info(f"Created table {TERM_PAIRS_TABLE}")
            
            # Wait for table to be active
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=TERM_PAIRS_TABLE)
            self._logger.info(f"Table {TERM_PAIRS_TABLE} is now active")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                self._logger.info(f"Table {TERM_PAIRS_TABLE} already exists")
            else:
                raise
    
    def _create_catalogs_table(self) -> None:
        """
        Create the catalogs table.
        
        Table schema:
        - pk: Partition key (LP#{language_pair_id})
        - sk: Sort key (CAT#{catalog_id})
        """
        client = self._get_client()
        
        try:
            client.create_table(
                TableName=CATALOGS_TABLE,
                KeySchema=[
                    {"AttributeName": "pk", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "pk", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            self._logger.info(f"Created table {CATALOGS_TABLE}")
            
            # Wait for table to be active
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=CATALOGS_TABLE)
            self._logger.info(f"Table {CATALOGS_TABLE} is now active")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                self._logger.info(f"Table {CATALOGS_TABLE} already exists")
            else:
                raise
    
    async def initialize_tables(self) -> None:
        """
        Create all required DynamoDB tables if they don't exist.
        
        This method should be called during application startup to ensure
        all required tables are available.
        """
        self._logger.info("Initializing DynamoDB tables...")
        
        # Check and create term pairs table
        if not await self.table_exists(TERM_PAIRS_TABLE):
            await self._run_sync(self._create_term_pairs_table)
        else:
            self._logger.info(f"Table {TERM_PAIRS_TABLE} already exists")
        
        # Check and create catalogs table
        if not await self.table_exists(CATALOGS_TABLE):
            await self._run_sync(self._create_catalogs_table)
        else:
            self._logger.info(f"Table {CATALOGS_TABLE} already exists")

        self._logger.info("DynamoDB tables initialization complete")

    # =========================================================================
    # Term Pairs Table Operations
    # =========================================================================
    
    @staticmethod
    def _make_term_pair_pk(language_pair_id: str, catalog_id: str) -> str:
        """Create partition key for term pair."""
        return f"LP#{language_pair_id}#CAT#{catalog_id}"
    
    @staticmethod
    def _make_term_pair_sk(source_term: str) -> str:
        """Create sort key for term pair."""
        return f"TERM#{source_term}"
    
    def _put_term_pair(self, term_pair: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a term pair.
        
        Args:
            term_pair: Term pair data with required fields:
                - language_pair_id
                - catalog_id
                - source_term
                - target_term
                Optional fields:
                - id (generated if not provided)
                - created_at (set if not provided)
                
        Returns:
            The stored term pair with all fields.
        """
        resource = self._get_resource()
        table = resource.Table(TERM_PAIRS_TABLE)
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Generate ID if not provided
        term_id = term_pair.get("id") or str(uuid.uuid4())
        
        item = {
            "pk": self._make_term_pair_pk(
                term_pair["language_pair_id"],
                term_pair["catalog_id"]
            ),
            "sk": self._make_term_pair_sk(term_pair["source_term"]),
            "id": term_id,
            "language_pair_id": term_pair["language_pair_id"],
            "catalog_id": term_pair["catalog_id"],
            "source_term": term_pair["source_term"],
            "target_term": term_pair["target_term"],
            "created_at": term_pair.get("created_at") or now,
            "updated_at": now,
        }
        
        table.put_item(Item=item)
        
        # Return without DynamoDB keys
        result = dict(item)
        result.pop("pk", None)
        result.pop("sk", None)
        return result
    
    async def put_term_pair(self, term_pair: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async create or update a term pair.
        
        Args:
            term_pair: Term pair data.
            
        Returns:
            The stored term pair with all fields.
        """
        return await self._run_sync(self._put_term_pair, term_pair)
    
    def _get_term_pair(
        self,
        language_pair_id: str,
        source_term: str,
        catalog_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific term pair.
        
        Args:
            language_pair_id: Language pair ID.
            source_term: Source term text.
            catalog_id: Catalog ID.
            
        Returns:
            Term pair data if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(TERM_PAIRS_TABLE)
        
        response = table.get_item(
            Key={
                "pk": self._make_term_pair_pk(language_pair_id, catalog_id),
                "sk": self._make_term_pair_sk(source_term),
            }
        )
        
        item = response.get("Item")
        if item:
            item.pop("pk", None)
            item.pop("sk", None)
        return item
    
    async def get_term_pair(
        self,
        language_pair_id: str,
        source_term: str,
        catalog_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Async get a specific term pair.
        
        Args:
            language_pair_id: Language pair ID.
            source_term: Source term text.
            catalog_id: Catalog ID.
            
        Returns:
            Term pair data if found, None otherwise.
        """
        return await self._run_sync(
            self._get_term_pair, language_pair_id, source_term, catalog_id
        )
    
    def _get_term_pair_by_id(self, term_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a term pair by its unique ID using GSI2.
        
        Args:
            term_id: Unique term pair ID.
            
        Returns:
            Term pair data if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(TERM_PAIRS_TABLE)
        
        response = table.query(
            IndexName="GSI2-id",
            KeyConditionExpression="id = :id",
            ExpressionAttributeValues={":id": term_id},
            Limit=1
        )
        
        items = response.get("Items", [])
        if items:
            item = items[0]
            item.pop("pk", None)
            item.pop("sk", None)
            return item
        return None
    
    async def get_term_pair_by_id(self, term_id: str) -> Optional[Dict[str, Any]]:
        """
        Async get a term pair by its unique ID.
        
        Args:
            term_id: Unique term pair ID.
            
        Returns:
            Term pair data if found, None otherwise.
        """
        return await self._run_sync(self._get_term_pair_by_id, term_id)
    
    def _delete_term_pair(
        self,
        language_pair_id: str,
        source_term: str,
        catalog_id: str
    ) -> bool:
        """
        Delete a specific term pair.
        
        Args:
            language_pair_id: Language pair ID.
            source_term: Source term text.
            catalog_id: Catalog ID.
            
        Returns:
            True if deleted, False if not found.
        """
        resource = self._get_resource()
        table = resource.Table(TERM_PAIRS_TABLE)
        
        try:
            response = table.delete_item(
                Key={
                    "pk": self._make_term_pair_pk(language_pair_id, catalog_id),
                    "sk": self._make_term_pair_sk(source_term),
                },
                ReturnValues="ALL_OLD"
            )
            return "Attributes" in response
        except ClientError:
            return False
    
    async def delete_term_pair(
        self,
        language_pair_id: str,
        source_term: str,
        catalog_id: str
    ) -> bool:
        """
        Async delete a specific term pair.
        
        Args:
            language_pair_id: Language pair ID.
            source_term: Source term text.
            catalog_id: Catalog ID.
            
        Returns:
            True if deleted, False if not found.
        """
        return await self._run_sync(
            self._delete_term_pair, language_pair_id, source_term, catalog_id
        )
    
    def _delete_term_pair_by_id(self, term_id: str) -> bool:
        """
        Delete a term pair by its unique ID.
        
        Args:
            term_id: Unique term pair ID.
            
        Returns:
            True if deleted, False if not found.
        """
        # First, get the term pair to find its keys
        term_pair = self._get_term_pair_by_id(term_id)
        if not term_pair:
            return False
        
        return self._delete_term_pair(
            term_pair["language_pair_id"],
            term_pair["source_term"],
            term_pair["catalog_id"]
        )
    
    async def delete_term_pair_by_id(self, term_id: str) -> bool:
        """
        Async delete a term pair by its unique ID.
        
        Args:
            term_id: Unique term pair ID.
            
        Returns:
            True if deleted, False if not found.
        """
        return await self._run_sync(self._delete_term_pair_by_id, term_id)

    def _query_term_pairs(
        self,
        language_pair_id: str,
        catalog_id: Optional[str] = None,
        search_text: Optional[str] = None,
        limit: int = 100,
        last_evaluated_key: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Query term pairs with optional filtering and pagination.
        
        Args:
            language_pair_id: Language pair ID to filter by.
            catalog_id: Optional catalog ID to filter by.
            search_text: Optional text to search in source terms.
            limit: Maximum number of items to return.
            last_evaluated_key: Pagination key from previous query.
            
        Returns:
            Tuple of (list of term pairs, last evaluated key for pagination).
        """
        resource = self._get_resource()
        table = resource.Table(TERM_PAIRS_TABLE)
        
        items = []
        
        if catalog_id:
            # Query specific catalog using primary key
            pk = self._make_term_pair_pk(language_pair_id, catalog_id)
            
            query_kwargs = {
                "KeyConditionExpression": "pk = :pk",
                "ExpressionAttributeValues": {":pk": pk},
                "Limit": limit,
            }
            
            if search_text:
                # Add filter for source term containing search text
                query_kwargs["FilterExpression"] = "contains(source_term, :search)"
                query_kwargs["ExpressionAttributeValues"][":search"] = search_text
            
            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key
            
            response = table.query(**query_kwargs)
            items = response.get("Items", [])
            next_key = response.get("LastEvaluatedKey")
            
        else:
            # Query all catalogs for the language pair using GSI1
            # We need to scan with filter since we can't query by language_pair_id alone
            scan_kwargs = {
                "FilterExpression": "language_pair_id = :lp_id",
                "ExpressionAttributeValues": {":lp_id": language_pair_id},
                "Limit": limit,
            }
            
            if search_text:
                scan_kwargs["FilterExpression"] += " AND contains(source_term, :search)"
                scan_kwargs["ExpressionAttributeValues"][":search"] = search_text
            
            if last_evaluated_key:
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key
            
            response = table.scan(**scan_kwargs)
            items = response.get("Items", [])
            next_key = response.get("LastEvaluatedKey")
        
        # Remove DynamoDB keys from items
        for item in items:
            item.pop("pk", None)
            item.pop("sk", None)
        
        return items, next_key
    
    async def query_term_pairs(
        self,
        language_pair_id: str,
        catalog_id: Optional[str] = None,
        search_text: Optional[str] = None,
        limit: int = 100,
        last_evaluated_key: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Async query term pairs with optional filtering and pagination.
        
        Args:
            language_pair_id: Language pair ID to filter by.
            catalog_id: Optional catalog ID to filter by.
            search_text: Optional text to search in source terms.
            limit: Maximum number of items to return.
            last_evaluated_key: Pagination key from previous query.
            
        Returns:
            Tuple of (list of term pairs, last evaluated key for pagination).
        """
        return await self._run_sync(
            self._query_term_pairs,
            language_pair_id,
            catalog_id,
            search_text,
            limit,
            last_evaluated_key
        )
    
    def _query_term_pairs_by_catalog(
        self,
        catalog_id: str,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Query all term pairs in a catalog using GSI1.
        
        Args:
            catalog_id: Catalog ID to query.
            limit: Maximum number of items to return.
            
        Returns:
            List of term pairs in the catalog.
        """
        resource = self._get_resource()
        table = resource.Table(TERM_PAIRS_TABLE)
        
        items = []
        last_key = None
        
        while True:
            query_kwargs = {
                "IndexName": "GSI1-catalog-updated",
                "KeyConditionExpression": "catalog_id = :cat_id",
                "ExpressionAttributeValues": {":cat_id": catalog_id},
                "ScanIndexForward": False,  # Most recent first
            }
            
            if last_key:
                query_kwargs["ExclusiveStartKey"] = last_key
            
            response = table.query(**query_kwargs)
            batch_items = response.get("Items", [])
            
            for item in batch_items:
                item.pop("pk", None)
                item.pop("sk", None)
                items.append(item)
                
                if len(items) >= limit:
                    return items
            
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
        
        return items
    
    async def query_term_pairs_by_catalog(
        self,
        catalog_id: str,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Async query all term pairs in a catalog.
        
        Args:
            catalog_id: Catalog ID to query.
            limit: Maximum number of items to return.
            
        Returns:
            List of term pairs in the catalog.
        """
        return await self._run_sync(self._query_term_pairs_by_catalog, catalog_id, limit)
    
    def _batch_delete_by_catalog(
        self,
        language_pair_id: str,
        catalog_id: str
    ) -> int:
        """
        Delete all term pairs in a catalog.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            
        Returns:
            Number of deleted term pairs.
        """
        resource = self._get_resource()
        table = resource.Table(TERM_PAIRS_TABLE)
        
        # First, get all term pairs in the catalog
        pk = self._make_term_pair_pk(language_pair_id, catalog_id)
        deleted_count = 0
        last_key = None
        
        while True:
            query_kwargs = {
                "KeyConditionExpression": "pk = :pk",
                "ExpressionAttributeValues": {":pk": pk},
                "ProjectionExpression": "pk, sk",
            }
            
            if last_key:
                query_kwargs["ExclusiveStartKey"] = last_key
            
            response = table.query(**query_kwargs)
            items = response.get("Items", [])
            
            # Batch delete items
            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
                    deleted_count += 1
            
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
        
        return deleted_count
    
    async def batch_delete_by_catalog(
        self,
        language_pair_id: str,
        catalog_id: str
    ) -> int:
        """
        Async delete all term pairs in a catalog.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            
        Returns:
            Number of deleted term pairs.
        """
        return await self._run_sync(
            self._batch_delete_by_catalog, language_pair_id, catalog_id
        )

    # =========================================================================
    # Catalogs Table Operations (Task 1.4)
    # =========================================================================
    
    @staticmethod
    def _make_catalog_pk(language_pair_id: str) -> str:
        """Create partition key for catalog."""
        return f"LP#{language_pair_id}"
    
    @staticmethod
    def _make_catalog_sk(catalog_id: str) -> str:
        """Create sort key for catalog."""
        return f"CAT#{catalog_id}"
    
    def _put_catalog(self, catalog: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a catalog.
        
        Args:
            catalog: Catalog data with required fields:
                - language_pair_id
                - name
                Optional fields:
                - id (generated if not provided)
                - description
                - created_at (set if not provided)
                
        Returns:
            The stored catalog with all fields.
        """
        resource = self._get_resource()
        table = resource.Table(CATALOGS_TABLE)
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Generate ID if not provided
        catalog_id = catalog.get("id") or str(uuid.uuid4())
        
        item = {
            "pk": self._make_catalog_pk(catalog["language_pair_id"]),
            "sk": self._make_catalog_sk(catalog_id),
            "id": catalog_id,
            "language_pair_id": catalog["language_pair_id"],
            "name": catalog["name"],
            "description": catalog.get("description") or "",
            "created_at": catalog.get("created_at") or now,
            "updated_at": now,
        }
        
        table.put_item(Item=item)
        
        # Return without DynamoDB keys
        result = dict(item)
        result.pop("pk", None)
        result.pop("sk", None)
        return result
    
    async def put_catalog(self, catalog: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async create or update a catalog.
        
        Args:
            catalog: Catalog data.
            
        Returns:
            The stored catalog with all fields.
        """
        return await self._run_sync(self._put_catalog, catalog)
    
    def _get_catalog(
        self,
        language_pair_id: str,
        catalog_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific catalog.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            
        Returns:
            Catalog data if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(CATALOGS_TABLE)
        
        response = table.get_item(
            Key={
                "pk": self._make_catalog_pk(language_pair_id),
                "sk": self._make_catalog_sk(catalog_id),
            }
        )
        
        item = response.get("Item")
        if item:
            item.pop("pk", None)
            item.pop("sk", None)
        return item
    
    async def get_catalog(
        self,
        language_pair_id: str,
        catalog_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Async get a specific catalog.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            
        Returns:
            Catalog data if found, None otherwise.
        """
        return await self._run_sync(self._get_catalog, language_pair_id, catalog_id)
    
    def _get_catalogs(self, language_pair_id: str) -> List[Dict[str, Any]]:
        """
        Get all catalogs for a language pair.
        
        Args:
            language_pair_id: Language pair ID.
            
        Returns:
            List of catalog dictionaries.
        """
        resource = self._get_resource()
        table = resource.Table(CATALOGS_TABLE)
        
        pk = self._make_catalog_pk(language_pair_id)
        
        response = table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": pk}
        )
        
        catalogs = []
        for item in response.get("Items", []):
            item.pop("pk", None)
            item.pop("sk", None)
            catalogs.append(item)
        
        return catalogs
    
    async def get_catalogs(self, language_pair_id: str) -> List[Dict[str, Any]]:
        """
        Async get all catalogs for a language pair.
        
        Args:
            language_pair_id: Language pair ID.
            
        Returns:
            List of catalog dictionaries.
        """
        return await self._run_sync(self._get_catalogs, language_pair_id)
    
    def _delete_catalog(
        self,
        language_pair_id: str,
        catalog_id: str
    ) -> bool:
        """
        Delete a catalog.
        
        Note: This only deletes the catalog record, not associated term pairs.
        Use batch_delete_by_catalog to delete term pairs first.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            
        Returns:
            True if deleted, False if not found.
        """
        resource = self._get_resource()
        table = resource.Table(CATALOGS_TABLE)
        
        try:
            response = table.delete_item(
                Key={
                    "pk": self._make_catalog_pk(language_pair_id),
                    "sk": self._make_catalog_sk(catalog_id),
                },
                ReturnValues="ALL_OLD"
            )
            return "Attributes" in response
        except ClientError:
            return False
    
    async def delete_catalog(
        self,
        language_pair_id: str,
        catalog_id: str
    ) -> bool:
        """
        Async delete a catalog.
        
        Note: This only deletes the catalog record, not associated term pairs.
        Use batch_delete_by_catalog to delete term pairs first.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            
        Returns:
            True if deleted, False if not found.
        """
        return await self._run_sync(self._delete_catalog, language_pair_id, catalog_id)
    
    def _get_term_count_by_catalog(
        self,
        language_pair_id: str,
        catalog_id: str
    ) -> int:
        """
        Get the count of term pairs in a catalog.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            
        Returns:
            Number of term pairs in the catalog.
        """
        resource = self._get_resource()
        table = resource.Table(TERM_PAIRS_TABLE)
        
        pk = self._make_term_pair_pk(language_pair_id, catalog_id)
        
        response = table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": pk},
            Select="COUNT"
        )
        
        return response.get("Count", 0)
    
    async def get_term_count_by_catalog(
        self,
        language_pair_id: str,
        catalog_id: str
    ) -> int:
        """
        Async get the count of term pairs in a catalog.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            
        Returns:
            Number of term pairs in the catalog.
        """
        return await self._run_sync(
            self._get_term_count_by_catalog, language_pair_id, catalog_id
        )


    # =========================================================================
    # Users Table Operations (User Management)
    # =========================================================================
    
    USERS_TABLE = "doc_translation_users"
    
    def _create_users_table(self) -> None:
        """
        Create the users table with required indexes.
        
        Table schema:
        - username: Partition key (String)
        
        GSI1: For querying by role
        - Partition key: role
        
        GSI2: For querying by status
        - Partition key: status
        """
        client = self._get_client()
        
        try:
            client.create_table(
                TableName=self.USERS_TABLE,
                KeySchema=[
                    {"AttributeName": "username", "KeyType": "HASH"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "username", "AttributeType": "S"},
                    {"AttributeName": "role", "AttributeType": "S"},
                    {"AttributeName": "status", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "role-index",
                        "KeySchema": [
                            {"AttributeName": "role", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                    {
                        "IndexName": "status-index",
                        "KeySchema": [
                            {"AttributeName": "status", "KeyType": "HASH"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            self._logger.info(f"Created table {self.USERS_TABLE}")
            
            # Wait for table to be active
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=self.USERS_TABLE)
            self._logger.info(f"Table {self.USERS_TABLE} is now active")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                self._logger.info(f"Table {self.USERS_TABLE} already exists")
            else:
                raise
    
    async def initialize_users_table(self) -> None:
        """
        Create users table if it doesn't exist.
        
        This method should be called during application startup.
        """
        if not await self.table_exists(self.USERS_TABLE):
            await self._run_sync(self._create_users_table)
        else:
            self._logger.info(f"Table {self.USERS_TABLE} already exists")
    
    def _create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user in DynamoDB.
        
        Args:
            user_data: User data dictionary with required fields:
                - username
                - password_hash
                - role
                - status
                
        Returns:
            The stored user data.
            
        Raises:
            ClientError: If user already exists or DynamoDB error.
        """
        resource = self._get_resource()
        table = resource.Table(self.USERS_TABLE)
        
        now = datetime.now(timezone.utc).isoformat()
        
        item = {
            "username": user_data["username"],
            "password_hash": user_data["password_hash"],
            "role": user_data["role"],
            "status": user_data["status"],
            "must_change_password": user_data.get("must_change_password", True),
            "failed_login_count": user_data.get("failed_login_count", 0),
            "created_at": user_data.get("created_at") or now,
            "updated_at": now,
        }
        
        # Add deleted_at if present
        if user_data.get("deleted_at"):
            item["deleted_at"] = user_data["deleted_at"]
        
        # Use condition to prevent overwriting existing user
        try:
            table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(username)"
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ValueError(f"User '{user_data['username']}' already exists")
            raise
        
        return item
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async create a new user.
        
        Args:
            user_data: User data dictionary.
            
        Returns:
            The stored user data.
        """
        return await self._run_sync(self._create_user, user_data)
    
    def _get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by username.
        
        Args:
            username: The username to look up.
            
        Returns:
            User data if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(self.USERS_TABLE)
        
        response = table.get_item(Key={"username": username})
        return response.get("Item")
    
    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Async get a user by username.
        
        Args:
            username: The username to look up.
            
        Returns:
            User data if found, None otherwise.
        """
        return await self._run_sync(self._get_user, username)
    
    def _get_users(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        Get all users.
        
        Args:
            include_deleted: Whether to include soft-deleted users.
            
        Returns:
            List of user dictionaries.
        """
        resource = self._get_resource()
        table = resource.Table(self.USERS_TABLE)
        
        if include_deleted:
            response = table.scan()
        else:
            response = table.scan(
                FilterExpression="attribute_not_exists(deleted_at) OR deleted_at = :null",
                ExpressionAttributeValues={":null": None}
            )
        
        return response.get("Items", [])
    
    async def get_users(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        Async get all users.
        
        Args:
            include_deleted: Whether to include soft-deleted users.
            
        Returns:
            List of user dictionaries.
        """
        return await self._run_sync(self._get_users, include_deleted)
    
    def _update_user(self, username: str, **updates) -> Optional[Dict[str, Any]]:
        """
        Update user attributes.
        
        Args:
            username: The username to update.
            **updates: Key-value pairs of attributes to update.
            
        Returns:
            Updated user data if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(self.USERS_TABLE)
        
        # Build update expression
        update_parts = []
        expression_names = {}
        expression_values = {}
        
        # Always update updated_at
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        for key, value in updates.items():
            # Use expression attribute names for reserved words
            attr_name = f"#{key}"
            attr_value = f":{key}"
            update_parts.append(f"{attr_name} = {attr_value}")
            expression_names[attr_name] = key
            expression_values[attr_value] = value
        
        update_expression = "SET " + ", ".join(update_parts)
        
        try:
            response = table.update_item(
                Key={"username": username},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ConditionExpression="attribute_exists(username)",
                ReturnValues="ALL_NEW"
            )
            return response.get("Attributes")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            raise
    
    async def update_user(self, username: str, **updates) -> Optional[Dict[str, Any]]:
        """
        Async update user attributes.
        
        Args:
            username: The username to update.
            **updates: Key-value pairs of attributes to update.
            
        Returns:
            Updated user data if found, None otherwise.
        """
        return await self._run_sync(self._update_user, username, **updates)
    
    def _count_active_admins(self) -> int:
        """
        Count the number of active admin users.
        
        Returns:
            Number of active admins.
        """
        resource = self._get_resource()
        table = resource.Table(self.USERS_TABLE)
        
        response = table.query(
            IndexName="role-index",
            KeyConditionExpression="#role = :admin",
            FilterExpression="(attribute_not_exists(deleted_at) OR deleted_at = :null) AND #status <> :deleted",
            ExpressionAttributeNames={
                "#role": "role",
                "#status": "status"
            },
            ExpressionAttributeValues={
                ":admin": "admin",
                ":null": None,
                ":deleted": "deleted"
            },
            Select="COUNT"
        )
        
        return response.get("Count", 0)
    
    async def count_active_admins(self) -> int:
        """
        Async count the number of active admin users.
        
        Returns:
            Number of active admins.
        """
        return await self._run_sync(self._count_active_admins)
    
    def _user_exists(self, username: str) -> bool:
        """
        Check if an active (non-deleted) username exists.

        Args:
            username: The username to check.

        Returns:
            True if an active user exists, False otherwise.
        """
        user = self._get_user(username)
        return user is not None and user.get("status") != UserStatus.DELETED.value
    
    async def user_exists(self, username: str) -> bool:
        """
        Async check if a username exists.
        
        Args:
            username: The username to check.
            
        Returns:
            True if user exists, False otherwise.
        """
        return await self._run_sync(self._user_exists, username)
    
    def _delete_user_permanent(self, username: str) -> bool:
        """
        Permanently delete a user (for testing/admin purposes).
        
        Args:
            username: The username to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        resource = self._get_resource()
        table = resource.Table(self.USERS_TABLE)
        
        try:
            response = table.delete_item(
                Key={"username": username},
                ReturnValues="ALL_OLD"
            )
            return "Attributes" in response
        except ClientError:
            return False
    
    async def delete_user_permanent(self, username: str) -> bool:
        """
        Async permanently delete a user.
        
        Args:
            username: The username to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        return await self._run_sync(self._delete_user_permanent, username)


    # =========================================================================
    # Configuration Tables Operations (Unit-2: Config Storage Refactor)
    # =========================================================================
    
    # Table names for configuration storage
    LANGUAGE_PAIRS_TABLE = "doc_translation_language_pairs"
    USER_SETTINGS_TABLE = "doc_translation_user_settings"
    GLOBAL_CONFIG_TABLE = "doc_translation_global_config"
    
    def _create_language_pairs_table(self) -> None:
        """
        Create the user language pairs table.
        
        Table schema:
        - PK: USER#{user_id}
        - SK: LP#{language_pair_id}
        
        GSI: ByLanguagePair
        - PK: source_language#target_language
        - SK: user_id
        """
        client = self._get_client()
        
        try:
            client.create_table(
                TableName=self.LANGUAGE_PAIRS_TABLE,
                KeySchema=[
                    {"AttributeName": "pk", "KeyType": "HASH"},
                    {"AttributeName": "sk", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "pk", "AttributeType": "S"},
                    {"AttributeName": "sk", "AttributeType": "S"},
                    {"AttributeName": "language_pair_key", "AttributeType": "S"},
                    {"AttributeName": "user_id", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "ByLanguagePair",
                        "KeySchema": [
                            {"AttributeName": "language_pair_key", "KeyType": "HASH"},
                            {"AttributeName": "user_id", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            self._logger.info(f"Created table {self.LANGUAGE_PAIRS_TABLE}")
            
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=self.LANGUAGE_PAIRS_TABLE)
            self._logger.info(f"Table {self.LANGUAGE_PAIRS_TABLE} is now active")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                self._logger.info(f"Table {self.LANGUAGE_PAIRS_TABLE} already exists")
            else:
                raise
    
    def _create_user_settings_table(self) -> None:
        """
        Create the user settings table.
        
        Table schema:
        - user_id: Partition key (String)
        """
        client = self._get_client()
        
        try:
            client.create_table(
                TableName=self.USER_SETTINGS_TABLE,
                KeySchema=[
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            self._logger.info(f"Created table {self.USER_SETTINGS_TABLE}")
            
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=self.USER_SETTINGS_TABLE)
            self._logger.info(f"Table {self.USER_SETTINGS_TABLE} is now active")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                self._logger.info(f"Table {self.USER_SETTINGS_TABLE} already exists")
            else:
                raise
    
    def _create_global_config_table(self) -> None:
        """
        Create the global configuration table.
        
        Table schema:
        - config_key: Partition key (String)
        """
        client = self._get_client()
        
        try:
            client.create_table(
                TableName=self.GLOBAL_CONFIG_TABLE,
                KeySchema=[
                    {"AttributeName": "config_key", "KeyType": "HASH"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "config_key", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            self._logger.info(f"Created table {self.GLOBAL_CONFIG_TABLE}")
            
            waiter = client.get_waiter("table_exists")
            waiter.wait(TableName=self.GLOBAL_CONFIG_TABLE)
            self._logger.info(f"Table {self.GLOBAL_CONFIG_TABLE} is now active")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                self._logger.info(f"Table {self.GLOBAL_CONFIG_TABLE} already exists")
            else:
                raise
    
    async def initialize_config_tables(self) -> None:
        """
        Create all configuration tables if they don't exist.
        
        This method should be called during application startup.
        """
        self._logger.info("Initializing configuration tables...")
        
        if not await self.table_exists(self.LANGUAGE_PAIRS_TABLE):
            await self._run_sync(self._create_language_pairs_table)
        else:
            self._logger.info(f"Table {self.LANGUAGE_PAIRS_TABLE} already exists")
        
        if not await self.table_exists(self.USER_SETTINGS_TABLE):
            await self._run_sync(self._create_user_settings_table)
        else:
            self._logger.info(f"Table {self.USER_SETTINGS_TABLE} already exists")
        
        if not await self.table_exists(self.GLOBAL_CONFIG_TABLE):
            await self._run_sync(self._create_global_config_table)
        else:
            self._logger.info(f"Table {self.GLOBAL_CONFIG_TABLE} already exists")
        
        self._logger.info("Configuration tables initialization complete")
    
    # -------------------------------------------------------------------------
    # User Language Pairs Operations
    # -------------------------------------------------------------------------
    
    @staticmethod
    def _make_user_lp_pk(user_id: str) -> str:
        """Create partition key for user language pair."""
        return f"USER#{user_id}"
    
    @staticmethod
    def _make_user_lp_sk(language_pair_id: str) -> str:
        """Create sort key for user language pair."""
        return f"LP#{language_pair_id}"
    
    @staticmethod
    def _make_language_pair_key(source_language: str, target_language: str) -> str:
        """Create language pair key for GSI."""
        return f"{source_language}#{target_language}"
    
    def _create_user_language_pair(self, language_pair: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a user language pair.
        
        Args:
            language_pair: Language pair data with required fields:
                - id
                - user_id
                - source_language
                - target_language
                - display_name
                
        Returns:
            The stored language pair data.
        """
        resource = self._get_resource()
        table = resource.Table(self.LANGUAGE_PAIRS_TABLE)
        
        now = datetime.now(timezone.utc).isoformat()
        lp_id = language_pair.get("id") or str(uuid.uuid4())
        
        item = {
            "pk": self._make_user_lp_pk(language_pair["user_id"]),
            "sk": self._make_user_lp_sk(lp_id),
            "id": lp_id,
            "user_id": language_pair["user_id"],
            "source_language": language_pair["source_language"],
            "target_language": language_pair["target_language"],
            "display_name": language_pair["display_name"],
            "is_enabled": language_pair.get("is_enabled", True),
            "language_pair_key": self._make_language_pair_key(
                language_pair["source_language"],
                language_pair["target_language"]
            ),
            "created_at": language_pair.get("created_at") or now,
            "updated_at": now,
        }
        
        table.put_item(Item=item)
        
        result = dict(item)
        result.pop("pk", None)
        result.pop("sk", None)
        result.pop("language_pair_key", None)
        return result
    
    async def create_user_language_pair(self, language_pair: Dict[str, Any]) -> Dict[str, Any]:
        """Async create a user language pair."""
        return await self._run_sync(self._create_user_language_pair, language_pair)
    
    def _get_user_language_pair(self, user_id: str, language_pair_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific user language pair.
        
        Args:
            user_id: User ID.
            language_pair_id: Language pair ID.
            
        Returns:
            Language pair data if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(self.LANGUAGE_PAIRS_TABLE)
        
        response = table.get_item(
            Key={
                "pk": self._make_user_lp_pk(user_id),
                "sk": self._make_user_lp_sk(language_pair_id),
            }
        )
        
        item = response.get("Item")
        if item:
            item.pop("pk", None)
            item.pop("sk", None)
            item.pop("language_pair_key", None)
        return item
    
    async def get_user_language_pair(self, user_id: str, language_pair_id: str) -> Optional[Dict[str, Any]]:
        """Async get a specific user language pair."""
        return await self._run_sync(self._get_user_language_pair, user_id, language_pair_id)
    
    def _get_user_language_pairs(self, user_id: str, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """
        Get all language pairs for a user.
        
        Args:
            user_id: User ID.
            include_disabled: Whether to include disabled pairs.
            
        Returns:
            List of language pair dictionaries.
        """
        resource = self._get_resource()
        table = resource.Table(self.LANGUAGE_PAIRS_TABLE)
        
        pk = self._make_user_lp_pk(user_id)
        
        query_kwargs = {
            "KeyConditionExpression": "pk = :pk",
            "ExpressionAttributeValues": {":pk": pk},
        }
        
        if not include_disabled:
            query_kwargs["FilterExpression"] = "is_enabled = :enabled"
            query_kwargs["ExpressionAttributeValues"][":enabled"] = True
        
        response = table.query(**query_kwargs)
        
        pairs = []
        for item in response.get("Items", []):
            item.pop("pk", None)
            item.pop("sk", None)
            item.pop("language_pair_key", None)
            pairs.append(item)
        
        return pairs
    
    async def get_user_language_pairs(self, user_id: str, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """Async get all language pairs for a user."""
        return await self._run_sync(self._get_user_language_pairs, user_id, include_disabled)
    
    def _check_user_language_pair_exists(
        self,
        user_id: str,
        source_language: str,
        target_language: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        Check if a language pair combination already exists for a user.
        
        Args:
            user_id: User ID.
            source_language: Source language code.
            target_language: Target language code.
            exclude_id: Language pair ID to exclude from check.
            
        Returns:
            True if exists, False otherwise.
        """
        pairs = self._get_user_language_pairs(user_id, include_disabled=True)
        
        for pair in pairs:
            if (pair["source_language"] == source_language and 
                pair["target_language"] == target_language and
                pair["id"] != exclude_id):
                return True
        
        return False
    
    async def check_user_language_pair_exists(
        self,
        user_id: str,
        source_language: str,
        target_language: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """Async check if a language pair combination already exists."""
        return await self._run_sync(
            self._check_user_language_pair_exists,
            user_id, source_language, target_language, exclude_id
        )
    
    def _update_user_language_pair(
        self,
        user_id: str,
        language_pair_id: str,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """
        Update a user language pair.
        
        Args:
            user_id: User ID.
            language_pair_id: Language pair ID.
            **updates: Fields to update.
            
        Returns:
            Updated language pair data if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(self.LANGUAGE_PAIRS_TABLE)
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        update_parts = []
        expression_names = {}
        expression_values = {}
        
        for key, value in updates.items():
            attr_name = f"#{key}"
            attr_value = f":{key}"
            update_parts.append(f"{attr_name} = {attr_value}")
            expression_names[attr_name] = key
            expression_values[attr_value] = value
        
        update_expression = "SET " + ", ".join(update_parts)
        
        try:
            response = table.update_item(
                Key={
                    "pk": self._make_user_lp_pk(user_id),
                    "sk": self._make_user_lp_sk(language_pair_id),
                },
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ConditionExpression="attribute_exists(pk)",
                ReturnValues="ALL_NEW"
            )
            
            item = response.get("Attributes")
            if item:
                item.pop("pk", None)
                item.pop("sk", None)
                item.pop("language_pair_key", None)
            return item
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            raise
    
    async def update_user_language_pair(
        self,
        user_id: str,
        language_pair_id: str,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """Async update a user language pair."""
        return await self._run_sync(
            self._update_user_language_pair,
            user_id, language_pair_id, **updates
        )
    
    def _delete_user_language_pair(self, user_id: str, language_pair_id: str) -> bool:
        """
        Delete a user language pair.
        
        Args:
            user_id: User ID.
            language_pair_id: Language pair ID.
            
        Returns:
            True if deleted, False if not found.
        """
        resource = self._get_resource()
        table = resource.Table(self.LANGUAGE_PAIRS_TABLE)
        
        try:
            response = table.delete_item(
                Key={
                    "pk": self._make_user_lp_pk(user_id),
                    "sk": self._make_user_lp_sk(language_pair_id),
                },
                ReturnValues="ALL_OLD"
            )
            return "Attributes" in response
        except ClientError:
            return False
    
    async def delete_user_language_pair(self, user_id: str, language_pair_id: str) -> bool:
        """Async delete a user language pair."""
        return await self._run_sync(self._delete_user_language_pair, user_id, language_pair_id)

    # -------------------------------------------------------------------------
    # User Settings Operations
    # -------------------------------------------------------------------------
    
    def _create_user_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create user settings.
        
        Args:
            settings: User settings data with required fields:
                - user_id
                - default_model_id
                
        Returns:
            The stored settings data.
        """
        resource = self._get_resource()
        table = resource.Table(self.USER_SETTINGS_TABLE)
        
        now = datetime.now(timezone.utc).isoformat()
        
        item = {
            "user_id": settings["user_id"],
            "default_model_id": settings["default_model_id"],
            "ui_language": settings.get("ui_language", "zh"),
            "translation_batch_size": settings.get("translation_batch_size", 10),
            "max_concurrent_tasks": settings.get("max_concurrent_tasks", 3),
            "created_at": settings.get("created_at") or now,
            "updated_at": now,
        }
        
        table.put_item(Item=item)
        return item
    
    async def create_user_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Async create user settings."""
        return await self._run_sync(self._create_user_settings, settings)
    
    def _get_user_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user settings.
        
        Args:
            user_id: User ID.
            
        Returns:
            User settings if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(self.USER_SETTINGS_TABLE)
        
        response = table.get_item(Key={"user_id": user_id})
        return response.get("Item")
    
    async def get_user_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Async get user settings."""
        return await self._run_sync(self._get_user_settings, user_id)
    
    def _update_user_settings(self, user_id: str, **updates) -> Optional[Dict[str, Any]]:
        """
        Update user settings.
        
        Args:
            user_id: User ID.
            **updates: Fields to update.
            
        Returns:
            Updated settings if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(self.USER_SETTINGS_TABLE)
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        update_parts = []
        expression_names = {}
        expression_values = {}
        
        for key, value in updates.items():
            attr_name = f"#{key}"
            attr_value = f":{key}"
            update_parts.append(f"{attr_name} = {attr_value}")
            expression_names[attr_name] = key
            expression_values[attr_value] = value
        
        update_expression = "SET " + ", ".join(update_parts)
        
        try:
            response = table.update_item(
                Key={"user_id": user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ConditionExpression="attribute_exists(user_id)",
                ReturnValues="ALL_NEW"
            )
            return response.get("Attributes")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            raise
    
    async def update_user_settings(self, user_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Async update user settings."""
        return await self._run_sync(self._update_user_settings, user_id, **updates)
    
    def _delete_user_settings(self, user_id: str) -> bool:
        """
        Delete user settings.
        
        Args:
            user_id: User ID.
            
        Returns:
            True if deleted, False if not found.
        """
        resource = self._get_resource()
        table = resource.Table(self.USER_SETTINGS_TABLE)
        
        try:
            response = table.delete_item(
                Key={"user_id": user_id},
                ReturnValues="ALL_OLD"
            )
            return "Attributes" in response
        except ClientError:
            return False
    
    async def delete_user_settings(self, user_id: str) -> bool:
        """Async delete user settings."""
        return await self._run_sync(self._delete_user_settings, user_id)
    
    # -------------------------------------------------------------------------
    # Global Config Operations
    # -------------------------------------------------------------------------
    
    def _create_global_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a global configuration.
        
        Args:
            config: Configuration data with required fields:
                - config_key
                - config_value
                
        Returns:
            The stored configuration data.
        """
        resource = self._get_resource()
        table = resource.Table(self.GLOBAL_CONFIG_TABLE)
        
        now = datetime.now(timezone.utc).isoformat()
        
        item = {
            "config_key": config["config_key"],
            "config_value": config["config_value"],
            "description": config.get("description", ""),
            "created_at": config.get("created_at") or now,
            "updated_at": now,
        }
        
        table.put_item(Item=item)
        return item
    
    async def create_global_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Async create or update a global configuration."""
        return await self._run_sync(self._create_global_config, config)
    
    def _get_global_config(self, config_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a global configuration by key.
        
        Args:
            config_key: Configuration key.
            
        Returns:
            Configuration data if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(self.GLOBAL_CONFIG_TABLE)
        
        response = table.get_item(Key={"config_key": config_key})
        return response.get("Item")
    
    async def get_global_config(self, config_key: str) -> Optional[Dict[str, Any]]:
        """Async get a global configuration by key."""
        return await self._run_sync(self._get_global_config, config_key)
    
    def _get_all_global_configs(self) -> List[Dict[str, Any]]:
        """
        Get all global configurations.
        
        Returns:
            List of configuration dictionaries.
        """
        resource = self._get_resource()
        table = resource.Table(self.GLOBAL_CONFIG_TABLE)
        
        response = table.scan()
        return response.get("Items", [])
    
    async def get_all_global_configs(self) -> List[Dict[str, Any]]:
        """Async get all global configurations."""
        return await self._run_sync(self._get_all_global_configs)
    
    def _update_global_config(self, config_key: str, **updates) -> Optional[Dict[str, Any]]:
        """
        Update a global configuration.
        
        Args:
            config_key: Configuration key.
            **updates: Fields to update.
            
        Returns:
            Updated configuration if found, None otherwise.
        """
        resource = self._get_resource()
        table = resource.Table(self.GLOBAL_CONFIG_TABLE)
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        update_parts = []
        expression_names = {}
        expression_values = {}
        
        for key, value in updates.items():
            attr_name = f"#{key}"
            attr_value = f":{key}"
            update_parts.append(f"{attr_name} = {attr_value}")
            expression_names[attr_name] = key
            expression_values[attr_value] = value
        
        update_expression = "SET " + ", ".join(update_parts)
        
        try:
            response = table.update_item(
                Key={"config_key": config_key},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ConditionExpression="attribute_exists(config_key)",
                ReturnValues="ALL_NEW"
            )
            return response.get("Attributes")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return None
            raise
    
    async def update_global_config(self, config_key: str, **updates) -> Optional[Dict[str, Any]]:
        """Async update a global configuration."""
        return await self._run_sync(self._update_global_config, config_key, **updates)
    
    def _delete_global_config(self, config_key: str) -> bool:
        """
        Delete a global configuration.
        
        Args:
            config_key: Configuration key.
            
        Returns:
            True if deleted, False if not found.
        """
        resource = self._get_resource()
        table = resource.Table(self.GLOBAL_CONFIG_TABLE)
        
        try:
            response = table.delete_item(
                Key={"config_key": config_key},
                ReturnValues="ALL_OLD"
            )
            return "Attributes" in response
        except ClientError:
            return False
    
    async def delete_global_config(self, config_key: str) -> bool:
        """Async delete a global configuration."""
        return await self._run_sync(self._delete_global_config, config_key)
    
    def _batch_delete_global_configs(self, config_keys: List[str]) -> int:
        """
        Delete multiple global configurations.
        
        Args:
            config_keys: List of configuration keys to delete.
            
        Returns:
            Number of deleted configurations.
        """
        resource = self._get_resource()
        table = resource.Table(self.GLOBAL_CONFIG_TABLE)
        
        deleted_count = 0
        with table.batch_writer() as batch:
            for config_key in config_keys:
                batch.delete_item(Key={"config_key": config_key})
                deleted_count += 1
        
        return deleted_count
    
    async def batch_delete_global_configs(self, config_keys: List[str]) -> int:
        """Async delete multiple global configurations."""
        return await self._run_sync(self._batch_delete_global_configs, config_keys)
