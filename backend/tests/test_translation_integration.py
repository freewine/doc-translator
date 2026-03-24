"""Integration tests for TranslationService with LanguagePair."""

import pytest
from unittest.mock import patch, MagicMock
from src.services.translation_service import TranslationService
from src.models.job import LanguagePair


@pytest.fixture
def mock_bedrock_client():
    """Create a mock Bedrock client."""
    with patch('boto3.client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def zh_vi_pair():
    """Create a Chinese-Vietnamese language pair."""
    return LanguagePair(
        id="zh-vi",
        source_language="Chinese",
        target_language="Vietnamese",
        source_language_code="zh",
        target_language_code="vi"
    )


@pytest.fixture
def en_es_pair():
    """Create an English-Spanish language pair."""
    return LanguagePair(
        id="en-es",
        source_language="English",
        target_language="Spanish",
        source_language_code="en",
        target_language_code="es"
    )


class TestTranslationServiceIntegration:
    """Integration tests for TranslationService with LanguagePair."""

    def test_translation_with_language_pair(
        self,
        mock_bedrock_client,
        zh_vi_pair
    ):
        """Test translation using a language pair."""
        assert zh_vi_pair.source_language == "Chinese"
        assert zh_vi_pair.target_language == "Vietnamese"

        # Create translation service (region determined by boto3 default chain)
        service = TranslationService(
            model_id="global.amazon.nova-2-lite-v1:0"
        )

        # Mock successful translation
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': 'Xin chào'}
                    ]
                }
            }
        }

        # Test translation
        result = service.translate_text("你好", zh_vi_pair)
        assert result.text == 'Xin chào'

    def test_translation_with_different_language_pair(
        self,
        mock_bedrock_client,
        en_es_pair
    ):
        """Test translation with a different language pair."""
        # Create translation service (region determined by boto3 default chain)
        service = TranslationService(
            model_id="global.amazon.nova-2-lite-v1:0"
        )

        # Mock successful translation
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': 'Hola'}
                    ]
                }
            }
        }

        # Test translation with new pair
        result = service.translate_text("Hello", en_es_pair)
        assert result.text == 'Hola'

    @pytest.mark.asyncio
    async def test_async_translation_with_language_pair(
        self,
        mock_bedrock_client,
        zh_vi_pair
    ):
        """Test async translation with language pair."""
        # Region determined by boto3 default chain
        service = TranslationService(
            model_id="global.amazon.nova-2-lite-v1:0"
        )

        # Mock successful translation
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': 'Xin chào thế giới'}
                    ]
                }
            }
        }

        # Test async translation
        result = await service.translate_text_async("你好世界", zh_vi_pair)
        assert result.text == 'Xin chào thế giới'

    def test_language_pair_structure(
        self,
        mock_bedrock_client,
        zh_vi_pair
    ):
        """Test that language pairs have the required structure.

        Language detection is handled by the model's system prompt.
        """
        # Verify the language pair has required fields
        assert zh_vi_pair.id == "zh-vi"
        assert zh_vi_pair.source_language == "Chinese"
        assert zh_vi_pair.target_language == "Vietnamese"
        assert zh_vi_pair.source_language_code == "zh"
        assert zh_vi_pair.target_language_code == "vi"

    def test_language_pair_direct_construction(
        self,
        mock_bedrock_client
    ):
        """Test that LanguagePair can be constructed directly with all fields."""
        pair = LanguagePair(
            id="ja-en",
            source_language="Japanese",
            target_language="English",
            source_language_code="ja",
            target_language_code="en"
        )

        assert pair.id == "ja-en"
        assert pair.source_language == "Japanese"
        assert pair.target_language == "English"
        assert pair.source_language_code == "ja"
        assert pair.target_language_code == "en"
