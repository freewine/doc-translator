import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.thesaurus_service import ThesaurusService


@pytest.fixture
def mock_repository():
    repo = MagicMock()
    repo.query_term_pairs_by_catalog = AsyncMock()
    return repo


@pytest.fixture
def thesaurus_service(mock_repository):
    return ThesaurusService(repository=mock_repository)


class TestGetTermsForTranslation:
    async def test_returns_all_terms_beyond_old_200_limit(
        self, thesaurus_service, mock_repository
    ):
        """All terms should be returned when catalog has >200 entries."""
        items = [
            {
                "id": f"term-{i}",
                "language_pair_id": "zh-vi",
                "catalog_id": "cat-1",
                "source_term": f"term{i}",
                "target_term": f"translated{i}",
                "updated_at": f"2026-01-01T00:00:{i % 60:02d}+00:00",
            }
            for i in range(300)
        ]
        mock_repository.query_term_pairs_by_catalog.return_value = items

        result = await thesaurus_service.get_terms_for_translation(
            language_pair_id="zh-vi",
            catalog_ids=["cat-1"],
        )

        assert len(result) == 300

    async def test_deduplication_respects_catalog_priority(
        self, thesaurus_service, mock_repository
    ):
        """First catalog wins when the same source_term appears in multiple catalogs."""
        cat1_items = [
            {
                "id": "t1",
                "language_pair_id": "zh-vi",
                "catalog_id": "cat-1",
                "source_term": "server",
                "target_term": "from-cat-1",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ]
        cat2_items = [
            {
                "id": "t2",
                "language_pair_id": "zh-vi",
                "catalog_id": "cat-2",
                "source_term": "server",
                "target_term": "from-cat-2",
                "updated_at": "2026-01-02T00:00:00+00:00",
            }
        ]
        mock_repository.query_term_pairs_by_catalog.side_effect = [
            cat1_items, cat2_items
        ]

        result = await thesaurus_service.get_terms_for_translation(
            language_pair_id="zh-vi",
            catalog_ids=["cat-1", "cat-2"],
        )

        assert len(result) == 1
        assert result[0].target_term == "from-cat-1"
