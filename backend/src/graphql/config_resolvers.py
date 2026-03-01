"""
GraphQL resolvers for configuration management.

This module provides GraphQL types and resolvers for:
- Language pair management (user-level)
- User settings management
- Global configuration access
- Available models query
"""
import logging
from typing import List, Optional

import strawberry
from strawberry.types import Info

from ..models.config import (
    LanguagePair as DomainLanguagePair,
    UserSettings as DomainUserSettings,
    ModelConfig as DomainModelConfig,
)
from ..services.global_config_service import GlobalConfigService
from ..services.language_pair_service import LanguagePairService
from ..services.user_settings_service import UserSettingsService
from .resolvers import require_auth, AuthenticationError, ValidationError
from .decorators import (
    get_current_user_from_context,
    PermissionError as AuthPermissionError,
)
from ..models.user import UserRole

logger = logging.getLogger(__name__)


# =============================================================================
# GraphQL Types for Config
# =============================================================================

@strawberry.type
class ConfigLanguagePair:
    """
    User-level language pair configuration.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Owner user ID
        source_language: Source language code (e.g., "zh")
        target_language: Target language code (e.g., "vi")
        display_name: Human-readable name (e.g., "Chinese→Vietnamese")
        is_enabled: Whether this pair is active
        created_at: Creation timestamp (ISO format)
        updated_at: Last modification timestamp (ISO format)
    """
    id: str
    user_id: str
    source_language: str
    target_language: str
    display_name: str
    is_enabled: bool
    created_at: str
    updated_at: str


@strawberry.type
class ConfigUserSettings:
    """
    User preference settings.
    
    Attributes:
        user_id: User ID
        default_model_id: Default translation model ID
        ui_language: Interface language ("zh", "vi", "en")
        translation_batch_size: Translation batch size (1-100)
        max_concurrent_tasks: Maximum concurrent tasks (1-10)
        created_at: Creation timestamp (ISO format)
        updated_at: Last modification timestamp (ISO format)
    """
    user_id: str
    default_model_id: str
    ui_language: str
    translation_batch_size: int
    max_concurrent_tasks: int
    created_at: str
    updated_at: str


@strawberry.type
class ConfigModelInfo:
    """
    Model configuration information.
    
    Attributes:
        model_id: Model ID (e.g., "global.amazon.nova-2-lite-v1:0")
        display_name: Display name (e.g., "Nova 2 Lite")
        provider: Provider name (e.g., "amazon", "anthropic")
        is_default: Whether this is the system default model
    """
    model_id: str
    display_name: str
    provider: str
    is_default: bool


# =============================================================================
# Conversion Functions
# =============================================================================

def convert_language_pair(lp: DomainLanguagePair) -> ConfigLanguagePair:
    """Convert domain LanguagePair to GraphQL ConfigLanguagePair."""
    return ConfigLanguagePair(
        id=lp.id,
        user_id=lp.user_id,
        source_language=lp.source_language,
        target_language=lp.target_language,
        display_name=lp.display_name,
        is_enabled=lp.is_enabled,
        created_at=lp.created_at.isoformat() if hasattr(lp.created_at, 'isoformat') else str(lp.created_at),
        updated_at=lp.updated_at.isoformat() if hasattr(lp.updated_at, 'isoformat') else str(lp.updated_at),
    )


def convert_user_settings(settings: DomainUserSettings) -> ConfigUserSettings:
    """Convert domain UserSettings to GraphQL ConfigUserSettings."""
    return ConfigUserSettings(
        user_id=settings.user_id,
        default_model_id=settings.default_model_id,
        ui_language=settings.ui_language,
        translation_batch_size=settings.translation_batch_size,
        max_concurrent_tasks=settings.max_concurrent_tasks,
        created_at=settings.created_at.isoformat() if hasattr(settings.created_at, 'isoformat') else str(settings.created_at),
        updated_at=settings.updated_at.isoformat() if hasattr(settings.updated_at, 'isoformat') else str(settings.updated_at),
    )


def convert_model_config(model: DomainModelConfig) -> ConfigModelInfo:
    """Convert domain ModelConfig to GraphQL ConfigModelInfo."""
    return ConfigModelInfo(
        model_id=model.model_id,
        display_name=model.display_name,
        provider=model.provider,
        is_default=model.is_default,
    )


# =============================================================================
# Helper Functions
# =============================================================================

def get_config_services(info: Info) -> tuple:
    """
    Get config services from resolver context.
    
    Returns:
        Tuple of (language_pair_service, user_settings_service, global_config_service)
        
    Raises:
        AuthenticationError: If services are not available
    """
    context = info.context.get("resolver_context")
    if not context:
        raise AuthenticationError("Resolver context not available")
    
    # Get services from context (they should be added to ResolverContext)
    language_pair_service = getattr(context, 'language_pair_service', None)
    user_settings_service = getattr(context, 'user_settings_service', None)
    global_config_service = getattr(context, 'global_config_service', None)
    
    return language_pair_service, user_settings_service, global_config_service


# =============================================================================
# Query Resolvers
# =============================================================================

async def resolve_config_language_pairs(
    info: Info,
    include_disabled: bool = False
) -> List[ConfigLanguagePair]:
    """
    Get all language pairs for the current user.
    
    Args:
        info: Strawberry Info object
        include_disabled: Whether to include disabled pairs
        
    Returns:
        List of ConfigLanguagePair objects
    """
    username = require_auth(info)
    language_pair_service, _, _ = get_config_services(info)
    
    if not language_pair_service:
        logger.warning("LanguagePairService not available, returning empty list")
        return []
    
    pairs = await language_pair_service.get_language_pairs("__global__", include_disabled)
    return [convert_language_pair(p) for p in pairs]


async def resolve_config_user_settings(info: Info) -> ConfigUserSettings:
    """
    Get settings for the current user.
    
    Args:
        info: Strawberry Info object
        
    Returns:
        ConfigUserSettings object
    """
    username = require_auth(info)
    _, user_settings_service, _ = get_config_services(info)
    
    if not user_settings_service:
        raise AuthenticationError("UserSettingsService not available")
    
    settings = await user_settings_service.get_user_settings(username)
    return convert_user_settings(settings)


async def resolve_available_models(info: Info) -> List[ConfigModelInfo]:
    """
    Get all available translation models.
    
    Args:
        info: Strawberry Info object
        
    Returns:
        List of ConfigModelInfo objects
    """
    require_auth(info)
    _, _, global_config_service = get_config_services(info)
    
    if not global_config_service:
        logger.warning("GlobalConfigService not available, returning empty list")
        return []
    
    models = await global_config_service.get_available_models()
    return [convert_model_config(m) for m in models]


# =============================================================================
# Mutation Resolvers
# =============================================================================

async def resolve_create_config_language_pair(
    info: Info,
    source_language: str,
    target_language: str,
    display_name: str,
    is_enabled: bool = True
) -> ConfigLanguagePair:
    """
    Create a new language pair for the current user.
    
    Args:
        info: Strawberry Info object
        source_language: Source language code
        target_language: Target language code
        display_name: Display name
        is_enabled: Whether the pair is enabled
        
    Returns:
        Created ConfigLanguagePair
    """
    username = require_auth(info)
    
    # Admin role check - only admins can create language pairs
    user = get_current_user_from_context(info)
    if not user or user.role != UserRole.ADMIN:
        raise AuthPermissionError("Admin access required")
    
    language_pair_service, _, _ = get_config_services(info)
    
    if not language_pair_service:
        raise AuthenticationError("LanguagePairService not available")
    
    try:
        pair = await language_pair_service.create_language_pair(
            user_id="__global__",
            source_language=source_language,
            target_language=target_language,
            display_name=display_name,
            is_enabled=is_enabled,
        )
        logger.info(f"Created language pair {pair.id} by admin {username}")
        return convert_language_pair(pair)
    except ValueError as e:
        raise ValidationError(str(e))


async def resolve_update_config_language_pair(
    info: Info,
    language_pair_id: str,
    display_name: Optional[str] = None,
    is_enabled: Optional[bool] = None
) -> Optional[ConfigLanguagePair]:
    """
    Update a language pair.
    
    Args:
        info: Strawberry Info object
        language_pair_id: Language pair ID
        display_name: New display name (optional)
        is_enabled: New enabled status (optional)
        
    Returns:
        Updated ConfigLanguagePair or None if not found
    """
    username = require_auth(info)
    
    # Admin role check - only admins can update language pairs
    user = get_current_user_from_context(info)
    if not user or user.role != UserRole.ADMIN:
        raise AuthPermissionError("Admin access required")
    
    language_pair_service, _, _ = get_config_services(info)
    
    if not language_pair_service:
        raise AuthenticationError("LanguagePairService not available")
    
    try:
        pair = await language_pair_service.update_language_pair(
            user_id="__global__",
            language_pair_id=language_pair_id,
            display_name=display_name,
            is_enabled=is_enabled,
        )
        if pair:
            logger.info(f"Updated language pair {language_pair_id} by admin {username}")
            return convert_language_pair(pair)
        return None
    except ValueError as e:
        raise ValidationError(str(e))


async def resolve_delete_config_language_pair(
    info: Info,
    language_pair_id: str
) -> bool:
    """
    Delete a language pair.
    
    Args:
        info: Strawberry Info object
        language_pair_id: Language pair ID
        
    Returns:
        True if deleted, False if not found
    """
    username = require_auth(info)
    
    # Admin role check - only admins can delete language pairs
    user = get_current_user_from_context(info)
    if not user or user.role != UserRole.ADMIN:
        raise AuthPermissionError("Admin access required")
    
    language_pair_service, _, _ = get_config_services(info)
    
    if not language_pair_service:
        raise AuthenticationError("LanguagePairService not available")
    
    deleted = await language_pair_service.delete_language_pair("__global__", language_pair_id)
    if deleted:
        logger.info(f"Deleted language pair {language_pair_id} by admin {username}")
    return deleted


async def resolve_update_config_user_settings(
    info: Info,
    default_model_id: Optional[str] = None,
    ui_language: Optional[str] = None,
    translation_batch_size: Optional[int] = None,
    max_concurrent_tasks: Optional[int] = None
) -> ConfigUserSettings:
    """
    Update user settings.
    
    Args:
        info: Strawberry Info object
        default_model_id: New default model ID (optional)
        ui_language: New UI language (optional)
        translation_batch_size: New batch size (optional)
        max_concurrent_tasks: New concurrent tasks limit (optional)
        
    Returns:
        Updated ConfigUserSettings
    """
    username = require_auth(info)
    _, user_settings_service, _ = get_config_services(info)
    
    if not user_settings_service:
        raise AuthenticationError("UserSettingsService not available")
    
    try:
        settings = await user_settings_service.update_user_settings(
            user_id=username,
            default_model_id=default_model_id,
            ui_language=ui_language,
            translation_batch_size=translation_batch_size,
            max_concurrent_tasks=max_concurrent_tasks,
        )
        logger.info(f"Updated settings for user {username}")
        return convert_user_settings(settings)
    except ValueError as e:
        raise ValidationError(str(e))


async def resolve_reset_config_user_settings(info: Info) -> ConfigUserSettings:
    """
    Reset user settings to defaults.
    
    Args:
        info: Strawberry Info object
        
    Returns:
        Reset ConfigUserSettings
    """
    username = require_auth(info)
    _, user_settings_service, _ = get_config_services(info)
    
    if not user_settings_service:
        raise AuthenticationError("UserSettingsService not available")
    
    settings = await user_settings_service.reset_user_settings(username)
    logger.info(f"Reset settings for user {username}")
    return convert_user_settings(settings)
