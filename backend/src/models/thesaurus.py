"""
Thesaurus data models for term translation pairs and catalogs.

This module defines the data structures used for managing term translation
pairs organized by language pair and catalog.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class TermPair:
    """
    A term translation pair mapping a source term to its target translation.
    
    Attributes:
        id: Unique identifier (UUID)
        language_pair_id: Reference to language pair (e.g., "zh-vi")
        catalog_id: Reference to catalog
        source_term: Source language term
        target_term: Target language translation
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """
    id: str
    language_pair_id: str
    catalog_id: str
    source_term: str
    target_term: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "language_pair_id": self.language_pair_id,
            "catalog_id": self.catalog_id,
            "source_term": self.source_term,
            "target_term": self.target_term,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TermPair":
        """Create TermPair from dictionary."""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        
        # Parse datetime strings if needed
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        
        return cls(
            id=data["id"],
            language_pair_id=data["language_pair_id"],
            catalog_id=data["catalog_id"],
            source_term=data["source_term"],
            target_term=data["target_term"],
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
        )


@dataclass
class Catalog:
    """
    A catalog for organizing term pairs by domain or project.
    
    Attributes:
        id: Unique identifier (UUID)
        language_pair_id: Reference to language pair
        name: Catalog name
        description: Optional description
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """
    id: str
    language_pair_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "language_pair_id": self.language_pair_id,
            "name": self.name,
            "description": self.description or "",
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Catalog":
        """Create Catalog from dictionary."""
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        
        # Parse datetime strings if needed
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        
        return cls(
            id=data["id"],
            language_pair_id=data["language_pair_id"],
            name=data["name"],
            description=data.get("description"),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
        )


@dataclass
class CatalogWithCount(Catalog):
    """
    Catalog with term pair count for display purposes.
    
    Attributes:
        term_count: Number of term pairs in the catalog
    """
    term_count: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        result = super().to_dict()
        result["term_count"] = self.term_count
        return result
    
    @classmethod
    def from_catalog(cls, catalog: Catalog, term_count: int) -> "CatalogWithCount":
        """Create CatalogWithCount from a Catalog and term count."""
        return cls(
            id=catalog.id,
            language_pair_id=catalog.language_pair_id,
            name=catalog.name,
            description=catalog.description,
            created_at=catalog.created_at,
            updated_at=catalog.updated_at,
            term_count=term_count,
        )


@dataclass
class ImportResult:
    """
    Result of a CSV import operation.
    
    Attributes:
        created: Number of new term pairs created
        updated: Number of existing term pairs updated
        skipped: Number of invalid rows skipped
        errors: List of error messages for skipped rows
    """
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def total_processed(self) -> int:
        """Total number of rows processed."""
        return self.created + self.updated + self.skipped


@dataclass
class PaginatedTermPairs:
    """
    Paginated list of term pairs.
    
    Attributes:
        items: Term pairs for current page
        total: Total number of matching term pairs
        page: Current page number (1-indexed)
        page_size: Items per page
        has_next: Whether there are more pages
    """
    items: List[TermPair]
    total: int
    page: int
    page_size: int
    has_next: bool
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size
