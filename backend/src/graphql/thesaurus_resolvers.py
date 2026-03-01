"""
GraphQL resolver implementations for thesaurus operations.

This module implements the business logic for all thesaurus-related GraphQL
queries and mutations, including term pair and catalog management.
"""
import logging
from typing import List, Optional

from strawberry.types import Info

from .schema import (
    TermPair as GQLTermPair,
    Catalog as GQLCatalog,
    ImportResult as GQLImportResult,
    PaginatedTermPairs as GQLPaginatedTermPairs,
)
from .resolvers import require_auth, ResolverContext, ValidationError
from .decorators import (
    get_current_user_from_context,
    verify_and_get_user,
    AuthenticationError,
    PermissionError as AuthPermissionError,
)
from ..models.user import UserRole
from ..services.thesaurus_service import (
    ThesaurusService,
    ValidationError as ThesaurusValidationError,
    TermNotFoundError,
    CatalogNotFoundError,
    DuplicateCatalogError,
)
from ..models.thesaurus import (
    TermPair,
    Catalog,
    CatalogWithCount,
    ImportResult,
    PaginatedTermPairs,
)

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Raised when a resource is not found."""
    pass


# =========================================================================
# Conversion Functions
# =========================================================================

def convert_term_pair(term_pair: TermPair) -> GQLTermPair:
    """Convert domain TermPair to GraphQL TermPair."""
    return GQLTermPair(
        id=term_pair.id,
        language_pair_id=term_pair.language_pair_id,
        catalog_id=term_pair.catalog_id,
        source_term=term_pair.source_term,
        target_term=term_pair.target_term,
        created_at=term_pair.created_at,
        updated_at=term_pair.updated_at,
    )


def convert_catalog(catalog: CatalogWithCount) -> GQLCatalog:
    """Convert domain CatalogWithCount to GraphQL Catalog."""
    return GQLCatalog(
        id=catalog.id,
        language_pair_id=catalog.language_pair_id,
        name=catalog.name,
        description=catalog.description,
        term_count=catalog.term_count,
        created_at=catalog.created_at,
        updated_at=catalog.updated_at,
    )


def convert_catalog_basic(catalog: Catalog, term_count: int = 0) -> GQLCatalog:
    """Convert domain Catalog to GraphQL Catalog with term count."""
    return GQLCatalog(
        id=catalog.id,
        language_pair_id=catalog.language_pair_id,
        name=catalog.name,
        description=catalog.description,
        term_count=term_count,
        created_at=catalog.created_at,
        updated_at=catalog.updated_at,
    )


def convert_import_result(result: ImportResult) -> GQLImportResult:
    """Convert domain ImportResult to GraphQL ImportResult."""
    return GQLImportResult(
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=result.errors,
    )


def convert_paginated_term_pairs(paginated: PaginatedTermPairs) -> GQLPaginatedTermPairs:
    """Convert domain PaginatedTermPairs to GraphQL PaginatedTermPairs."""
    return GQLPaginatedTermPairs(
        items=[convert_term_pair(tp) for tp in paginated.items],
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        has_next=paginated.has_next,
    )


def get_thesaurus_service(info: Info) -> ThesaurusService:
    """Get ThesaurusService from resolver context."""
    context: ResolverContext = info.context.get("resolver_context")
    if not context or not context.thesaurus_service:
        raise ValidationError("Thesaurus service not available")
    return context.thesaurus_service


async def require_admin_access(info: Info) -> str:
    """
    Require admin role for thesaurus mutations. Returns username.

    This function verifies the JWT token, loads the full user object,
    and checks for admin role. It is used by thesaurus mutation
    resolvers to enforce admin-only access.

    Args:
        info: Strawberry Info object

    Returns:
        Username of authenticated admin user

    Raises:
        AuthenticationError: If user is not authenticated or user not found
        PermissionError: If user does not have admin role
    """
    # Verify auth and get full user object (includes role)
    user = await verify_and_get_user(info)
    if user.role != UserRole.ADMIN:
        raise AuthPermissionError("Admin access required")
    return user.username


# =========================================================================
# Query Resolvers (Requirements 3.1, 3.2, 3.4, 9.1)
# =========================================================================

async def resolve_term_pairs(
    info: Info,
    language_pair_id: str,
    catalog_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 100
) -> GQLPaginatedTermPairs:
    """
    Get paginated term pairs with optional filtering.
    
    Args:
        info: Strawberry Info object
        language_pair_id: Language pair ID to filter by
        catalog_id: Optional catalog ID to filter by
        search: Optional text to search in source terms
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        PaginatedTermPairs with results and pagination info
        
    Raises:
        AuthenticationError: If user is not authenticated
    """
    require_auth(info)
    
    thesaurus_service = get_thesaurus_service(info)
    
    result = await thesaurus_service.search_term_pairs(
        language_pair_id=language_pair_id,
        catalog_id=catalog_id,
        search_text=search,
        page=page,
        page_size=page_size,
    )
    
    return convert_paginated_term_pairs(result)


async def resolve_catalogs(
    info: Info,
    language_pair_id: str
) -> List[GQLCatalog]:
    """
    Get all catalogs for a language pair with term counts.
    
    Args:
        info: Strawberry Info object
        language_pair_id: Language pair ID
        
    Returns:
        List of catalogs with term counts
        
    Raises:
        AuthenticationError: If user is not authenticated
    """
    require_auth(info)
    
    thesaurus_service = get_thesaurus_service(info)
    
    catalogs = await thesaurus_service.get_catalogs(language_pair_id)
    
    return [convert_catalog(cat) for cat in catalogs]


async def resolve_export_terms_csv(
    info: Info,
    language_pair_id: str,
    catalog_id: str
) -> str:
    """
    Export term pairs as CSV content.
    
    Args:
        info: Strawberry Info object
        language_pair_id: Language pair ID
        catalog_id: Catalog ID
        
    Returns:
        CSV content as string
        
    Raises:
        AuthenticationError: If user is not authenticated
    """
    require_auth(info)
    
    thesaurus_service = get_thesaurus_service(info)
    
    csv_content = await thesaurus_service.export_to_csv(
        language_pair_id=language_pair_id,
        catalog_id=catalog_id,
    )
    
    return csv_content


# =========================================================================
# Term Pair Mutation Resolvers (Requirements 1.1, 1.3, 1.5, 2.1, 4.1, 4.2)
# =========================================================================

async def resolve_add_term_pair(
    info: Info,
    language_pair_id: str,
    catalog_id: str,
    source_term: str,
    target_term: str
) -> GQLTermPair:
    """
    Add or update a term pair (upsert behavior).
    
    Args:
        info: Strawberry Info object
        language_pair_id: Language pair ID
        catalog_id: Catalog ID
        source_term: Source language term
        target_term: Target language translation
        
    Returns:
        Created or updated term pair
        
    Raises:
        AuthenticationError: If user is not authenticated
        PermissionError: If user is not an admin
        ValidationError: If term validation fails
    """
    await require_admin_access(info)
    
    thesaurus_service = get_thesaurus_service(info)
    
    try:
        term_pair = await thesaurus_service.add_term_pair(
            language_pair_id=language_pair_id,
            catalog_id=catalog_id,
            source_term=source_term,
            target_term=target_term,
        )
        
        logger.info(f"Added/updated term pair: {term_pair.id}")
        return convert_term_pair(term_pair)
        
    except ThesaurusValidationError as e:
        raise ValidationError(str(e))


async def resolve_edit_term_pair(
    info: Info,
    term_id: str,
    target_term: str
) -> GQLTermPair:
    """
    Edit an existing term pair's target term.
    
    Args:
        info: Strawberry Info object
        term_id: Unique term pair ID
        target_term: New target term translation
        
    Returns:
        Updated term pair
        
    Raises:
        AuthenticationError: If user is not authenticated
        PermissionError: If user is not an admin
        ValidationError: If target term validation fails
        NotFoundError: If term pair is not found
    """
    await require_admin_access(info)
    
    thesaurus_service = get_thesaurus_service(info)
    
    try:
        term_pair = await thesaurus_service.edit_term_pair(
            term_id=term_id,
            target_term=target_term,
        )
        
        logger.info(f"Edited term pair: {term_id}")
        return convert_term_pair(term_pair)
        
    except ThesaurusValidationError as e:
        raise ValidationError(str(e))
    except TermNotFoundError as e:
        raise NotFoundError(str(e))


async def resolve_delete_term_pair(
    info: Info,
    term_id: str
) -> bool:
    """
    Delete a term pair by ID.
    
    Args:
        info: Strawberry Info object
        term_id: Unique term pair ID
        
    Returns:
        True if deleted successfully
        
    Raises:
        AuthenticationError: If user is not authenticated
        PermissionError: If user is not an admin
        NotFoundError: If term pair is not found
    """
    await require_admin_access(info)
    
    thesaurus_service = get_thesaurus_service(info)
    
    try:
        deleted = await thesaurus_service.delete_term_pair(term_id)
        
        logger.info(f"Deleted term pair: {term_id}")
        return deleted
        
    except TermNotFoundError as e:
        raise NotFoundError(str(e))


async def resolve_bulk_delete_term_pairs(
    info: Info,
    language_pair_id: str,
    catalog_id: str
) -> int:
    """
    Delete all term pairs in a catalog.
    
    Args:
        info: Strawberry Info object
        language_pair_id: Language pair ID
        catalog_id: Catalog ID
        
    Returns:
        Number of deleted term pairs
        
    Raises:
        AuthenticationError: If user is not authenticated
        PermissionError: If user is not an admin
    """
    await require_admin_access(info)
    
    thesaurus_service = get_thesaurus_service(info)
    
    count = await thesaurus_service.bulk_delete_by_catalog(
        language_pair_id=language_pair_id,
        catalog_id=catalog_id,
    )
    
    logger.info(f"Bulk deleted {count} term pairs from catalog {catalog_id}")
    return count


async def resolve_import_terms_csv(
    info: Info,
    language_pair_id: str,
    catalog_id: str,
    csv_content: str
) -> GQLImportResult:
    """
    Import term pairs from CSV content.
    
    Args:
        info: Strawberry Info object
        language_pair_id: Language pair ID
        catalog_id: Catalog ID
        csv_content: CSV content as string
        
    Returns:
        Import summary with counts
        
    Raises:
        AuthenticationError: If user is not authenticated
        PermissionError: If user is not an admin
    """
    await require_admin_access(info)
    
    thesaurus_service = get_thesaurus_service(info)
    
    result = await thesaurus_service.import_from_csv(
        language_pair_id=language_pair_id,
        catalog_id=catalog_id,
        csv_content=csv_content,
    )
    
    logger.info(
        f"CSV import: {result.created} created, {result.updated} updated, "
        f"{result.skipped} skipped"
    )
    return convert_import_result(result)


# =========================================================================
# Catalog Mutation Resolvers (Requirements 5.1, 5.2, 5.3, 5.4)
# =========================================================================

async def resolve_create_catalog(
    info: Info,
    language_pair_id: str,
    name: str,
    description: Optional[str] = None
) -> GQLCatalog:
    """
    Create a new catalog.
    
    Args:
        info: Strawberry Info object
        language_pair_id: Language pair ID
        name: Catalog name
        description: Optional description
        
    Returns:
        Created catalog
        
    Raises:
        AuthenticationError: If user is not authenticated
        PermissionError: If user is not an admin
        ValidationError: If name is empty or duplicate
    """
    await require_admin_access(info)
    
    thesaurus_service = get_thesaurus_service(info)
    
    try:
        catalog = await thesaurus_service.create_catalog(
            language_pair_id=language_pair_id,
            name=name,
            description=description,
        )
        
        logger.info(f"Created catalog: {catalog.id}")
        return convert_catalog_basic(catalog, term_count=0)
        
    except ThesaurusValidationError as e:
        raise ValidationError(str(e))
    except DuplicateCatalogError as e:
        raise ValidationError(str(e))


async def resolve_update_catalog(
    info: Info,
    language_pair_id: str,
    catalog_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> GQLCatalog:
    """
    Update a catalog's name or description.
    
    Args:
        info: Strawberry Info object
        language_pair_id: Language pair ID
        catalog_id: Catalog ID
        name: New name (optional)
        description: New description (optional)
        
    Returns:
        Updated catalog
        
    Raises:
        AuthenticationError: If user is not authenticated
        PermissionError: If user is not an admin
        NotFoundError: If catalog is not found
        ValidationError: If new name is empty or duplicate
    """
    await require_admin_access(info)
    
    thesaurus_service = get_thesaurus_service(info)
    
    try:
        catalog = await thesaurus_service.update_catalog(
            language_pair_id=language_pair_id,
            catalog_id=catalog_id,
            name=name,
            description=description,
        )
        
        # Get term count for the updated catalog
        catalogs = await thesaurus_service.get_catalogs(language_pair_id)
        term_count = 0
        for cat in catalogs:
            if cat.id == catalog_id:
                term_count = cat.term_count
                break
        
        logger.info(f"Updated catalog: {catalog_id}")
        return convert_catalog_basic(catalog, term_count=term_count)
        
    except ThesaurusValidationError as e:
        raise ValidationError(str(e))
    except DuplicateCatalogError as e:
        raise ValidationError(str(e))
    except CatalogNotFoundError as e:
        raise NotFoundError(str(e))


async def resolve_delete_catalog(
    info: Info,
    language_pair_id: str,
    catalog_id: str
) -> int:
    """
    Delete a catalog and all its term pairs.
    
    Args:
        info: Strawberry Info object
        language_pair_id: Language pair ID
        catalog_id: Catalog ID
        
    Returns:
        Number of deleted items (term pairs + catalog)
        
    Raises:
        AuthenticationError: If user is not authenticated
        PermissionError: If user is not an admin
        NotFoundError: If catalog is not found
    """
    await require_admin_access(info)
    
    thesaurus_service = get_thesaurus_service(info)
    
    try:
        count = await thesaurus_service.delete_catalog(
            language_pair_id=language_pair_id,
            catalog_id=catalog_id,
        )
        
        logger.info(f"Deleted catalog {catalog_id} with {count - 1} term pairs")
        return count
        
    except CatalogNotFoundError as e:
        raise NotFoundError(str(e))
