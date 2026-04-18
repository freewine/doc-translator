"""
Thesaurus service for managing term translation pairs and catalogs.

This module provides business logic for term and catalog management,
including validation, CRUD operations, CSV import/export, and
translation integration.
"""
import csv
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models.thesaurus import (
    Catalog,
    CatalogWithCount,
    ImportResult,
    PaginatedTermPairs,
    TermPair,
)
from ..storage.dynamodb_repository import DynamoDBRepository

logger = logging.getLogger(__name__)


# Constants
MAX_TERM_LENGTH = 500
MAX_TERMS_FOR_TRANSLATION = 5000


class ThesaurusServiceError(Exception):
    """Base exception for ThesaurusService errors."""
    pass


class ValidationError(ThesaurusServiceError):
    """Raised when term validation fails."""
    pass


class TermNotFoundError(ThesaurusServiceError):
    """Raised when a term pair is not found."""
    pass


class CatalogNotFoundError(ThesaurusServiceError):
    """Raised when a catalog is not found."""
    pass


class DuplicateCatalogError(ThesaurusServiceError):
    """Raised when attempting to create a duplicate catalog."""
    pass


class ThesaurusService:
    """
    Service for managing term translation pairs and catalogs.
    
    This service provides:
    - Term pair CRUD operations with validation
    - Catalog management
    - CSV import/export
    - Term retrieval for translation integration
    """
    
    def __init__(
        self,
        repository: DynamoDBRepository,
        logger_instance: Optional[logging.Logger] = None
    ):
        """
        Initialize the ThesaurusService.
        
        Args:
            repository: DynamoDB repository for persistence.
            logger_instance: Optional logger instance.
        """
        self._repository = repository
        self._logger = logger_instance or logger
    
    # =========================================================================
    # Validation Methods (Task 4.2)
    # =========================================================================
    
    def validate_term(self, term: str, field_name: str = "term") -> None:
        """
        Validate a term string.
        
        Args:
            term: The term to validate.
            field_name: Name of the field for error messages.
            
        Raises:
            ValidationError: If validation fails.
        """
        # Check for empty or whitespace-only terms
        if not term or not term.strip():
            raise ValidationError(f"{field_name} cannot be empty or whitespace-only")
        
        # Check length
        if len(term) > MAX_TERM_LENGTH:
            raise ValidationError(
                f"{field_name} exceeds maximum length of {MAX_TERM_LENGTH} characters"
            )
    
    def validate_term_pair(self, source_term: str, target_term: str) -> None:
        """
        Validate both source and target terms.
        
        Args:
            source_term: The source term to validate.
            target_term: The target term to validate.
            
        Raises:
            ValidationError: If validation fails.
        """
        self.validate_term(source_term, "Source term")
        self.validate_term(target_term, "Target term")


    # =========================================================================
    # Term Pair CRUD Operations (Tasks 4.4, 4.6, 4.8)
    # =========================================================================
    
    async def add_term_pair(
        self,
        language_pair_id: str,
        catalog_id: str,
        source_term: str,
        target_term: str
    ) -> TermPair:
        """
        Add or update a term pair with validation (upsert behavior).
        
        If a term pair with the same language_pair_id, catalog_id, and source_term
        already exists, it will be updated with the new target_term.
        
        Args:
            language_pair_id: Language pair ID (e.g., "zh-vi").
            catalog_id: Catalog ID.
            source_term: Source language term.
            target_term: Target language translation.
            
        Returns:
            Created or updated TermPair.
            
        Raises:
            ValidationError: If term validation fails.
        """
        # Validate terms
        self.validate_term_pair(source_term, target_term)
        
        # Normalize terms (strip whitespace)
        source_term = source_term.strip()
        target_term = target_term.strip()
        
        # Check for existing term pair
        existing = await self._repository.get_term_pair(
            language_pair_id, source_term, catalog_id
        )
        
        now = datetime.now(timezone.utc)
        
        if existing:
            # Update existing term pair
            term_data = {
                "id": existing["id"],
                "language_pair_id": language_pair_id,
                "catalog_id": catalog_id,
                "source_term": source_term,
                "target_term": target_term,
                "created_at": existing.get("created_at"),
            }
            self._logger.debug(f"Updating existing term pair: {source_term}")
        else:
            # Create new term pair
            term_data = {
                "id": str(uuid.uuid4()),
                "language_pair_id": language_pair_id,
                "catalog_id": catalog_id,
                "source_term": source_term,
                "target_term": target_term,
            }
            self._logger.debug(f"Creating new term pair: {source_term}")
        
        # Store in DynamoDB
        result = await self._repository.put_term_pair(term_data)
        
        return TermPair.from_dict(result)
    
    async def edit_term_pair(
        self,
        term_id: str,
        target_term: str
    ) -> TermPair:
        """
        Edit an existing term pair's target term.
        
        Args:
            term_id: Unique term pair ID.
            target_term: New target term translation.
            
        Returns:
            Updated TermPair.
            
        Raises:
            ValidationError: If target term validation fails.
            TermNotFoundError: If term pair is not found.
        """
        # Validate target term
        self.validate_term(target_term, "Target term")
        target_term = target_term.strip()
        
        # Get existing term pair
        existing = await self._repository.get_term_pair_by_id(term_id)
        if not existing:
            raise TermNotFoundError(f"Term pair not found: {term_id}")
        
        # Update with new target term
        term_data = {
            "id": existing["id"],
            "language_pair_id": existing["language_pair_id"],
            "catalog_id": existing["catalog_id"],
            "source_term": existing["source_term"],
            "target_term": target_term,
            "created_at": existing.get("created_at"),
        }
        
        result = await self._repository.put_term_pair(term_data)
        
        self._logger.info(f"Updated term pair {term_id}")
        return TermPair.from_dict(result)
    
    async def delete_term_pair(self, term_id: str) -> bool:
        """
        Delete a term pair by ID.
        
        Args:
            term_id: Unique term pair ID.
            
        Returns:
            True if deleted successfully.
            
        Raises:
            TermNotFoundError: If term pair is not found.
        """
        # Check if exists
        existing = await self._repository.get_term_pair_by_id(term_id)
        if not existing:
            raise TermNotFoundError(f"Term pair not found: {term_id}")
        
        # Delete
        deleted = await self._repository.delete_term_pair_by_id(term_id)
        
        if deleted:
            self._logger.info(f"Deleted term pair {term_id}")
        
        return deleted
    
    async def bulk_delete_by_catalog(
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
        count = await self._repository.batch_delete_by_catalog(
            language_pair_id, catalog_id
        )
        
        self._logger.info(
            f"Bulk deleted {count} term pairs from catalog {catalog_id}"
        )
        return count
    
    # =========================================================================
    # Search and Pagination (Task 4.10)
    # =========================================================================
    
    async def search_term_pairs(
        self,
        language_pair_id: str,
        catalog_id: Optional[str] = None,
        search_text: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> PaginatedTermPairs:
        """
        Search and paginate term pairs.
        
        Args:
            language_pair_id: Language pair ID to filter by.
            catalog_id: Optional catalog ID to filter by.
            search_text: Optional text to search in source terms.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            
        Returns:
            PaginatedTermPairs with results and pagination info.
        """
        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 100
        if page_size > 100:
            page_size = 100
        
        # For proper pagination, we need to fetch all matching items
        # and then slice for the requested page
        all_items: List[Dict[str, Any]] = []
        last_key = None
        
        # Fetch all matching items (up to a reasonable limit)
        max_fetch = 10000  # Safety limit
        while len(all_items) < max_fetch:
            items, last_key = await self._repository.query_term_pairs(
                language_pair_id=language_pair_id,
                catalog_id=catalog_id,
                search_text=search_text,
                limit=1000,
                last_evaluated_key=last_key
            )
            all_items.extend(items)
            
            if not last_key:
                break
        
        # Calculate pagination
        total = len(all_items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Slice for current page
        page_items = all_items[start_idx:end_idx]
        
        # Convert to TermPair objects
        term_pairs = [TermPair.from_dict(item) for item in page_items]
        
        # Calculate has_next
        has_next = end_idx < total
        
        return PaginatedTermPairs(
            items=term_pairs,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next
        )
    
    async def get_term_pair_by_id(self, term_id: str) -> Optional[TermPair]:
        """
        Get a term pair by its unique ID.
        
        Args:
            term_id: Unique term pair ID.
            
        Returns:
            TermPair if found, None otherwise.
        """
        data = await self._repository.get_term_pair_by_id(term_id)
        if data:
            return TermPair.from_dict(data)
        return None


    # =========================================================================
    # Catalog Management (Task 6 - partial implementation for service layer)
    # =========================================================================
    
    async def create_catalog(
        self,
        language_pair_id: str,
        name: str,
        description: Optional[str] = None
    ) -> Catalog:
        """
        Create a new catalog.
        
        Args:
            language_pair_id: Language pair ID.
            name: Catalog name.
            description: Optional description.
            
        Returns:
            Created Catalog.
            
        Raises:
            ValidationError: If name is empty.
            DuplicateCatalogError: If catalog with same name exists.
        """
        # Validate name
        if not name or not name.strip():
            raise ValidationError("Catalog name cannot be empty")
        
        name = name.strip()
        
        # Check for duplicate name
        existing_catalogs = await self._repository.get_catalogs(language_pair_id)
        for cat in existing_catalogs:
            if cat["name"].lower() == name.lower():
                raise DuplicateCatalogError(
                    f"A catalog with name '{name}' already exists"
                )
        
        # Create catalog
        catalog_data = {
            "id": str(uuid.uuid4()),
            "language_pair_id": language_pair_id,
            "name": name,
            "description": description,
        }
        
        result = await self._repository.put_catalog(catalog_data)
        
        self._logger.info(f"Created catalog: {name}")
        return Catalog.from_dict(result)
    
    async def get_catalogs(self, language_pair_id: str) -> List[CatalogWithCount]:
        """
        Get all catalogs for a language pair with term counts.
        
        Args:
            language_pair_id: Language pair ID.
            
        Returns:
            List of CatalogWithCount objects.
        """
        catalogs_data = await self._repository.get_catalogs(language_pair_id)
        
        result = []
        for cat_data in catalogs_data:
            catalog = Catalog.from_dict(cat_data)
            term_count = await self._repository.get_term_count_by_catalog(
                language_pair_id, catalog.id
            )
            result.append(CatalogWithCount.from_catalog(catalog, term_count))
        
        return result
    
    async def get_catalog_by_id(
        self,
        language_pair_id: str,
        catalog_id: str
    ) -> Optional[Catalog]:
        """
        Get a specific catalog by ID.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            
        Returns:
            Catalog if found, None otherwise.
        """
        data = await self._repository.get_catalog(language_pair_id, catalog_id)
        if data:
            return Catalog.from_dict(data)
        return None
    
    async def update_catalog(
        self,
        language_pair_id: str,
        catalog_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Catalog:
        """
        Update a catalog's name or description.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            name: New name (optional).
            description: New description (optional).
            
        Returns:
            Updated Catalog.
            
        Raises:
            CatalogNotFoundError: If catalog is not found.
            ValidationError: If new name is empty.
            DuplicateCatalogError: If new name conflicts with existing catalog.
        """
        # Get existing catalog
        existing = await self._repository.get_catalog(language_pair_id, catalog_id)
        if not existing:
            raise CatalogNotFoundError(f"Catalog not found: {catalog_id}")
        
        # Validate and check for duplicate name if changing
        if name is not None:
            if not name.strip():
                raise ValidationError("Catalog name cannot be empty")
            name = name.strip()
            
            # Check for duplicate name (excluding current catalog)
            existing_catalogs = await self._repository.get_catalogs(language_pair_id)
            for cat in existing_catalogs:
                if cat["id"] != catalog_id and cat["name"].lower() == name.lower():
                    raise DuplicateCatalogError(
                        f"A catalog with name '{name}' already exists"
                    )
        
        # Update catalog
        catalog_data = {
            "id": catalog_id,
            "language_pair_id": language_pair_id,
            "name": name if name is not None else existing["name"],
            "description": description if description is not None else existing.get("description"),
            "created_at": existing.get("created_at"),
        }
        
        result = await self._repository.put_catalog(catalog_data)
        
        self._logger.info(f"Updated catalog: {catalog_id}")
        return Catalog.from_dict(result)
    
    async def delete_catalog(
        self,
        language_pair_id: str,
        catalog_id: str
    ) -> int:
        """
        Delete a catalog and all associated term pairs.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            
        Returns:
            Number of deleted items (term pairs + 1 for catalog).
            
        Raises:
            CatalogNotFoundError: If catalog is not found.
        """
        # Check if catalog exists
        existing = await self._repository.get_catalog(language_pair_id, catalog_id)
        if not existing:
            raise CatalogNotFoundError(f"Catalog not found: {catalog_id}")
        
        # Delete all term pairs in the catalog first
        term_count = await self._repository.batch_delete_by_catalog(
            language_pair_id, catalog_id
        )
        
        # Delete the catalog
        await self._repository.delete_catalog(language_pair_id, catalog_id)
        
        self._logger.info(
            f"Deleted catalog {catalog_id} with {term_count} term pairs"
        )
        
        return term_count + 1  # term pairs + catalog itself
    
    # =========================================================================
    # CSV Import/Export (Task 7 - partial implementation for service layer)
    # =========================================================================
    
    async def import_from_csv(
        self,
        language_pair_id: str,
        catalog_id: str,
        csv_content: str
    ) -> ImportResult:
        """
        Import term pairs from CSV content.
        
        Expected CSV format:
        source_term,target_term
        服务器,máy chủ
        数据库,cơ sở dữ liệu
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            csv_content: CSV content as string.
            
        Returns:
            ImportResult with counts of created, updated, and skipped rows.
        """
        result = ImportResult()
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            
            # Validate headers
            if not reader.fieldnames:
                result.errors.append("CSV file is empty or has no headers")
                return result
            
            required_fields = {"source_term", "target_term"}
            actual_fields = set(reader.fieldnames)
            
            if not required_fields.issubset(actual_fields):
                missing = required_fields - actual_fields
                result.errors.append(f"Missing required columns: {missing}")
                return result
            
            row_num = 1  # Start after header
            for row in reader:
                row_num += 1
                source_term = row.get("source_term", "").strip()
                target_term = row.get("target_term", "").strip()
                
                # Validate row
                try:
                    self.validate_term_pair(source_term, target_term)
                except ValidationError as e:
                    result.skipped += 1
                    result.errors.append(f"Row {row_num}: {str(e)}")
                    continue
                
                # Check if term pair exists
                existing = await self._repository.get_term_pair(
                    language_pair_id, source_term, catalog_id
                )
                
                # Add or update term pair
                term_data = {
                    "language_pair_id": language_pair_id,
                    "catalog_id": catalog_id,
                    "source_term": source_term,
                    "target_term": target_term,
                }
                
                if existing:
                    term_data["id"] = existing["id"]
                    term_data["created_at"] = existing.get("created_at")
                    result.updated += 1
                else:
                    term_data["id"] = str(uuid.uuid4())
                    result.created += 1
                
                await self._repository.put_term_pair(term_data)
        
        except csv.Error as e:
            result.errors.append(f"CSV parsing error: {str(e)}")
        except Exception as e:
            result.errors.append(f"Import error: {str(e)}")
            self._logger.error(f"CSV import error: {e}")
        
        self._logger.info(
            f"CSV import complete: {result.created} created, "
            f"{result.updated} updated, {result.skipped} skipped"
        )
        
        return result
    
    async def export_to_csv(
        self,
        language_pair_id: str,
        catalog_id: str
    ) -> str:
        """
        Export term pairs to CSV format.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_id: Catalog ID.
            
        Returns:
            CSV content as string.
        """
        # Get all term pairs in the catalog
        items = await self._repository.query_term_pairs_by_catalog(catalog_id)
        
        # Filter by language pair (GSI returns all items for catalog)
        items = [
            item for item in items
            if item.get("language_pair_id") == language_pair_id
        ]
        
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["source_term", "target_term", "updated_at"])
        
        # Write data rows
        for item in items:
            writer.writerow([
                item.get("source_term", ""),
                item.get("target_term", ""),
                item.get("updated_at", ""),
            ])
        
        return output.getvalue()
    
    # =========================================================================
    # Translation Integration (Task 9 - partial implementation for service layer)
    # =========================================================================
    
    async def get_terms_for_translation(
        self,
        language_pair_id: str,
        catalog_ids: List[str],
        max_terms: int = MAX_TERMS_FOR_TRANSLATION
    ) -> List[TermPair]:
        """
        Get merged term pairs for translation from multiple catalogs.
        
        Terms are merged with priority given to catalogs appearing first
        in the catalog_ids list. Results are ordered by updated_at descending
        and limited to max_terms.
        
        Args:
            language_pair_id: Language pair ID.
            catalog_ids: List of catalog IDs in priority order.
            max_terms: Maximum number of terms to return.
            
        Returns:
            List of TermPair objects for injection into system prompt.
        """
        if not catalog_ids:
            return []
        
        # Collect terms from all catalogs, respecting priority
        seen_source_terms: set = set()
        all_terms: List[Dict[str, Any]] = []
        
        for catalog_id in catalog_ids:
            items = await self._repository.query_term_pairs_by_catalog(catalog_id)
            
            # Filter by language pair and deduplicate
            for item in items:
                if item.get("language_pair_id") != language_pair_id:
                    continue
                
                source_term = item.get("source_term", "")
                if source_term in seen_source_terms:
                    continue  # Skip duplicate - earlier catalog has priority
                
                seen_source_terms.add(source_term)
                all_terms.append(item)
        
        # Sort by updated_at descending (most recent first)
        all_terms.sort(
            key=lambda x: x.get("updated_at", ""),
            reverse=True
        )
        
        # Limit to max_terms
        if len(all_terms) > max_terms:
            self._logger.info(
                f"Term pairs truncated from {len(all_terms)} to {max_terms}"
            )
            all_terms = all_terms[:max_terms]
        
        # Convert to TermPair objects
        return [TermPair.from_dict(item) for item in all_terms]
