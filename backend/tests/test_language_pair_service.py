"""
Unit tests for LanguagePairService.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.config import LanguagePair, DEFAULT_LANGUAGE_PAIR
from src.services.language_pair_service import LanguagePairService


@pytest.fixture
def mock_repository():
    """Create a mock DynamoDB repository."""
    repo = MagicMock()
    repo.create_user_language_pair = AsyncMock()
    repo.get_user_language_pair = AsyncMock()
    repo.get_user_language_pairs = AsyncMock()
    repo.update_user_language_pair = AsyncMock()
    repo.delete_user_language_pair = AsyncMock()
    repo.check_user_language_pair_exists = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repository):
    """Create a LanguagePairService instance."""
    return LanguagePairService(repository=mock_repository)


class TestCreateLanguagePair:
    """Tests for create_language_pair method."""
    
    async def test_create_language_pair_success(self, service, mock_repository):
        """Test successful language pair creation."""
        mock_repository.check_user_language_pair_exists.return_value = False
        mock_repository.create_user_language_pair.return_value = {
            "id": "lp-123",
            "user_id": "user-456",
            "source_language": "zh",
            "target_language": "vi",
            "display_name": "Chinese→Vietnamese",
            "is_enabled": True,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        result = await service.create_language_pair(
            user_id="user-456",
            source_language="zh",
            target_language="vi",
            display_name="Chinese→Vietnamese",
        )
        
        assert result.source_language == "zh"
        assert result.target_language == "vi"
        assert result.user_id == "user-456"
        mock_repository.create_user_language_pair.assert_called_once()
    
    async def test_create_language_pair_same_language_fails(self, service):
        """Test that creating pair with same source and target fails."""
        with pytest.raises(ValueError, match="same"):
            await service.create_language_pair(
                user_id="user-456",
                source_language="zh",
                target_language="zh",
                display_name="Chinese→Chinese",
            )
    
    async def test_create_language_pair_display_name_too_long(self, service):
        """Test that display name over 100 chars fails."""
        with pytest.raises(ValueError, match="100"):
            await service.create_language_pair(
                user_id="user-456",
                source_language="zh",
                target_language="vi",
                display_name="x" * 101,
            )
    
    async def test_create_language_pair_duplicate_fails(self, service, mock_repository):
        """Test that creating duplicate pair fails."""
        mock_repository.check_user_language_pair_exists.return_value = True
        
        with pytest.raises(ValueError, match="already exists"):
            await service.create_language_pair(
                user_id="user-456",
                source_language="zh",
                target_language="vi",
                display_name="Chinese→Vietnamese",
            )


class TestGetLanguagePairs:
    """Tests for get_language_pairs method."""
    
    async def test_get_language_pairs_returns_existing(self, service, mock_repository):
        """Test getting existing language pairs."""
        mock_repository.get_user_language_pairs.return_value = [
            {
                "id": "lp-1",
                "user_id": "user-456",
                "source_language": "zh",
                "target_language": "vi",
                "display_name": "Chinese→Vietnamese",
                "is_enabled": True,
                "created_at": "2026-01-28T10:00:00+00:00",
                "updated_at": "2026-01-28T10:00:00+00:00",
            }
        ]
        
        result = await service.get_language_pairs("user-456")
        
        assert len(result) == 1
        assert result[0].source_language == "zh"
    
    async def test_get_language_pairs_creates_default_if_empty(self, service, mock_repository):
        """Test that default pair is created if user has none."""
        # Use a counter to track calls
        call_count = [0]
        
        async def mock_get_pairs(user_id, include_disabled=False):
            call_count[0] += 1
            if call_count[0] == 1:
                return []  # First call - no pairs
            return [{   # Second call - after default created
                "id": "lp-default",
                "user_id": "user-456",
                "source_language": "zh",
                "target_language": "vi",
                "display_name": "Chinese→Vietnamese",
                "is_enabled": True,
                "created_at": "2026-01-28T10:00:00+00:00",
                "updated_at": "2026-01-28T10:00:00+00:00",
            }]
        
        mock_repository.get_user_language_pairs = mock_get_pairs
        mock_repository.check_user_language_pair_exists = AsyncMock(return_value=False)
        mock_repository.create_user_language_pair = AsyncMock(return_value={
            "id": "lp-default",
            "user_id": "user-456",
            "source_language": "zh",
            "target_language": "vi",
            "display_name": "Chinese→Vietnamese",
            "is_enabled": True,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        })
        
        result = await service.get_language_pairs("user-456")
        
        assert len(result) == 1
        assert result[0].source_language == DEFAULT_LANGUAGE_PAIR["source_language"]


class TestUpdateLanguagePair:
    """Tests for update_language_pair method."""
    
    async def test_update_language_pair_success(self, service, mock_repository):
        """Test successful language pair update."""
        mock_repository.update_user_language_pair.return_value = {
            "id": "lp-123",
            "user_id": "user-456",
            "source_language": "zh",
            "target_language": "vi",
            "display_name": "新名称",
            "is_enabled": False,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T11:00:00+00:00",
        }
        
        result = await service.update_language_pair(
            user_id="user-456",
            language_pair_id="lp-123",
            display_name="新名称",
            is_enabled=False,
        )
        
        assert result.display_name == "新名称"
        assert result.is_enabled is False
    
    async def test_update_language_pair_not_found(self, service, mock_repository):
        """Test updating non-existent pair returns None."""
        mock_repository.update_user_language_pair.return_value = None
        
        result = await service.update_language_pair(
            user_id="user-456",
            language_pair_id="nonexistent",
            display_name="新名称",
        )
        
        assert result is None
    
    async def test_update_language_pair_invalid_display_name(self, service):
        """Test that invalid display name fails."""
        with pytest.raises(ValueError, match="100"):
            await service.update_language_pair(
                user_id="user-456",
                language_pair_id="lp-123",
                display_name="x" * 101,
            )


class TestDeleteLanguagePair:
    """Tests for delete_language_pair method."""
    
    async def test_delete_language_pair_success(self, service, mock_repository):
        """Test successful language pair deletion."""
        mock_repository.delete_user_language_pair.return_value = True
        
        result = await service.delete_language_pair("user-456", "lp-123")
        
        assert result is True
        mock_repository.delete_user_language_pair.assert_called_once_with(
            "user-456", "lp-123"
        )
    
    async def test_delete_language_pair_not_found(self, service, mock_repository):
        """Test deleting non-existent pair returns False."""
        mock_repository.delete_user_language_pair.return_value = False
        
        result = await service.delete_language_pair("user-456", "nonexistent")
        
        assert result is False


class TestEnsureDefaultLanguagePair:
    """Tests for ensure_default_language_pair method."""
    
    async def test_ensure_default_creates_when_empty(self, service, mock_repository):
        """Test that default is created when user has no pairs."""
        mock_repository.get_user_language_pairs.return_value = []
        mock_repository.check_user_language_pair_exists.return_value = False
        mock_repository.create_user_language_pair.return_value = {
            "id": "lp-default",
            "user_id": "user-456",
            "source_language": "zh",
            "target_language": "vi",
            "display_name": "Chinese→Vietnamese",
            "is_enabled": True,
            "created_at": "2026-01-28T10:00:00+00:00",
            "updated_at": "2026-01-28T10:00:00+00:00",
        }
        
        await service.ensure_default_language_pair("user-456")
        
        mock_repository.create_user_language_pair.assert_called_once()
    
    async def test_ensure_default_skips_when_exists(self, service, mock_repository):
        """Test that default is not created when user has pairs."""
        mock_repository.get_user_language_pairs.return_value = [
            {"id": "existing", "source_language": "en", "target_language": "zh"}
        ]
        
        await service.ensure_default_language_pair("user-456")
        
        mock_repository.create_user_language_pair.assert_not_called()
