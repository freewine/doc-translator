"""
Language pair service for managing user language pair configurations.

This service provides:
- CRUD operations for user language pairs
- Default language pair creation
- Language pair validation
"""
import logging
import uuid
from typing import List, Optional

from src.models.config import (
    ConfigErrorCode,
    DEFAULT_LANGUAGE_PAIR,
    LanguagePair,
)
from src.storage.dynamodb_repository import DynamoDBRepository

logger = logging.getLogger(__name__)


class LanguagePairService:
    """
    Service for managing user language pair configurations.
    
    This service handles:
    - Creating, reading, updating, and deleting language pairs
    - Ensuring users have default language pairs
    - Validating language pair uniqueness
    """
    
    def __init__(
        self,
        repository: DynamoDBRepository,
        logger_instance: Optional[logging.Logger] = None
    ):
        """
        Initialize the language pair service.
        
        Args:
            repository: DynamoDB repository instance.
            logger_instance: Optional logger instance.
        """
        self.repository = repository
        self._logger = logger_instance or logger
    
    async def create_language_pair(
        self,
        user_id: str,
        source_language: str,
        target_language: str,
        display_name: str,
        is_enabled: bool = True
    ) -> LanguagePair:
        """
        Create a new language pair for a user.
        
        Args:
            user_id: User ID.
            source_language: Source language code.
            target_language: Target language code.
            display_name: Display name for the pair.
            is_enabled: Whether the pair is enabled.
            
        Returns:
            Created LanguagePair.
            
        Raises:
            ValueError: If validation fails or pair already exists.
        """
        # Validate source != target
        if source_language == target_language:
            raise ValueError("Source and target languages cannot be the same")
        
        # Validate display name length
        if not display_name or len(display_name) > 100:
            raise ValueError("Display name must be 1-100 characters")
        
        # Check for duplicate
        exists = await self.repository.check_user_language_pair_exists(
            user_id, source_language, target_language
        )
        if exists:
            raise ValueError(
                f"Language pair {source_language}→{target_language} already exists for this user"
            )
        
        # Create the language pair
        lp_id = str(uuid.uuid4())
        data = await self.repository.create_user_language_pair({
            "id": lp_id,
            "user_id": user_id,
            "source_language": source_language,
            "target_language": target_language,
            "display_name": display_name,
            "is_enabled": is_enabled,
        })
        
        self._logger.info(f"Created language pair {lp_id} for user {user_id}")
        return LanguagePair.from_dict(data)
    
    async def get_language_pairs(
        self,
        user_id: str,
        include_disabled: bool = False
    ) -> List[LanguagePair]:
        """
        Get all language pairs for a user.
        
        If the user has no language pairs, creates the default pair.
        
        Args:
            user_id: User ID.
            include_disabled: Whether to include disabled pairs.
            
        Returns:
            List of LanguagePair objects.
        """
        pairs_data = await self.repository.get_user_language_pairs(
            user_id, include_disabled
        )
        
        # If no pairs exist, create default
        if not pairs_data:
            await self.ensure_default_language_pair(user_id)
            pairs_data = await self.repository.get_user_language_pairs(
                user_id, include_disabled
            )
        
        return [LanguagePair.from_dict(data) for data in pairs_data]
    
    async def get_language_pair(
        self,
        user_id: str,
        language_pair_id: str
    ) -> Optional[LanguagePair]:
        """
        Get a specific language pair.
        
        Args:
            user_id: User ID.
            language_pair_id: Language pair ID.
            
        Returns:
            LanguagePair if found, None otherwise.
        """
        data = await self.repository.get_user_language_pair(user_id, language_pair_id)
        if data:
            return LanguagePair.from_dict(data)
        return None
    
    async def update_language_pair(
        self,
        user_id: str,
        language_pair_id: str,
        display_name: Optional[str] = None,
        is_enabled: Optional[bool] = None
    ) -> Optional[LanguagePair]:
        """
        Update a language pair.
        
        Note: source_language and target_language cannot be modified.
        
        Args:
            user_id: User ID.
            language_pair_id: Language pair ID.
            display_name: New display name (optional).
            is_enabled: New enabled status (optional).
            
        Returns:
            Updated LanguagePair if found, None otherwise.
            
        Raises:
            ValueError: If validation fails.
        """
        # Validate display name if provided
        if display_name is not None:
            if not display_name or len(display_name) > 100:
                raise ValueError("Display name must be 1-100 characters")
        
        # Build updates
        updates = {}
        if display_name is not None:
            updates["display_name"] = display_name
        if is_enabled is not None:
            updates["is_enabled"] = is_enabled
        
        if not updates:
            # No updates, just return current
            return await self.get_language_pair(user_id, language_pair_id)
        
        data = await self.repository.update_user_language_pair(
            user_id, language_pair_id, **updates
        )
        
        if data:
            self._logger.info(f"Updated language pair {language_pair_id}")
            return LanguagePair.from_dict(data)
        
        return None
    
    async def delete_language_pair(
        self,
        user_id: str,
        language_pair_id: str
    ) -> bool:
        """
        Delete a language pair.
        
        Args:
            user_id: User ID.
            language_pair_id: Language pair ID.
            
        Returns:
            True if deleted, False if not found.
        """
        deleted = await self.repository.delete_user_language_pair(
            user_id, language_pair_id
        )
        
        if deleted:
            self._logger.info(f"Deleted language pair {language_pair_id}")
        
        return deleted
    
    async def ensure_default_language_pair(self, user_id: str) -> None:
        """
        Ensure the user has at least the default language pair.
        
        Creates the default zh→vi pair if the user has no language pairs.
        
        Args:
            user_id: User ID.
        """
        pairs = await self.repository.get_user_language_pairs(user_id, include_disabled=True)
        
        if not pairs:
            self._logger.info(f"Creating default language pair for user {user_id}")
            await self.create_language_pair(
                user_id=user_id,
                source_language=DEFAULT_LANGUAGE_PAIR["source_language"],
                target_language=DEFAULT_LANGUAGE_PAIR["target_language"],
                display_name=DEFAULT_LANGUAGE_PAIR["display_name"],
                is_enabled=True,
            )
    
    async def get_language_pair_by_languages(
        self,
        user_id: str,
        source_language: str,
        target_language: str
    ) -> Optional[LanguagePair]:
        """
        Get a language pair by source and target languages.
        
        Args:
            user_id: User ID.
            source_language: Source language code.
            target_language: Target language code.
            
        Returns:
            LanguagePair if found, None otherwise.
        """
        pairs = await self.get_language_pairs(user_id, include_disabled=True)
        
        for pair in pairs:
            if (pair.source_language == source_language and 
                pair.target_language == target_language):
                return pair
        
        return None
