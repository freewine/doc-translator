"""Tests for the TranslationService.

Tests cover:
- Service initialization
- Translation functionality with model-based language detection
- System prompt construction for language detection and English preservation
- JSON batch format for batch translations
- Retry logic with exponential backoff
- Dynamic language pair support
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock
from src.services.translation_service import TranslationService, TranslationResult
from src.models.job import LanguagePair


@pytest.fixture
def chinese_vietnamese_pair():
    """Create a Chinese-Vietnamese language pair for testing."""
    return LanguagePair(
        id="zh-vi",
        source_language="Chinese",
        target_language="Vietnamese",
        source_language_code="zh",
        target_language_code="vi"
    )


@pytest.fixture
def english_spanish_pair():
    """Create an English-Spanish language pair for testing."""
    return LanguagePair(
        id="en-es",
        source_language="English",
        target_language="Spanish",
        source_language_code="en",
        target_language_code="es"
    )


@pytest.fixture
def mock_bedrock_client():
    """Create a mock Bedrock client."""
    with patch('boto3.client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        yield mock_instance


class TestSystemPromptConstruction:
    """Tests for system prompt construction with language detection and English preservation rules."""
    
    def test_system_prompt_contains_language_detection_instructions(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that system prompt contains language detection instructions."""
        service = TranslationService()
        
        prompt = service._build_system_prompt(chinese_vietnamese_pair, is_batch=False)
        
        # Verify language detection rule is present
        assert "LANGUAGE DETECTION" in prompt
        assert "Translate all" in prompt
        assert "Chinese" in prompt
        assert "return that item unchanged" in prompt.lower()
        assert "when in doubt, always translate" in prompt.lower()
    
    def test_system_prompt_contains_english_preservation_rules(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that system prompt contains English preservation rules."""
        service = TranslationService()
        
        prompt = service._build_system_prompt(chinese_vietnamese_pair, is_batch=False)
        
        # Verify English preservation rule is present
        assert "ENGLISH PRESERVATION" in prompt
        assert "Do NOT translate English" in prompt
        assert "technical terms" in prompt.lower()
    
    def test_system_prompt_contains_mixed_content_rules(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that system prompt contains mixed content handling rules."""
        service = TranslationService()
        
        prompt = service._build_system_prompt(chinese_vietnamese_pair, is_batch=False)
        
        # Verify mixed content rule is present
        assert "MIXED CONTENT" in prompt
        assert "translate the" in prompt.lower()
        assert "Do NOT skip" in prompt
    
    def test_system_prompt_contains_output_format_rules(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that system prompt contains output format rules."""
        service = TranslationService()
        
        prompt = service._build_system_prompt(chinese_vietnamese_pair, is_batch=False)
        
        # Verify output format rule is present
        assert "OUTPUT FORMAT" in prompt
        assert "ONLY the translation" in prompt
        assert "without any explanations" in prompt.lower()
    
    def test_system_prompt_batch_mode_contains_json_format_instructions(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that batch mode system prompt contains JSON format instructions."""
        service = TranslationService()
        
        prompt = service._build_system_prompt(chinese_vietnamese_pair, is_batch=True)
        
        # Verify JSON format rule is present in batch mode
        assert "JSON FORMAT" in prompt
        assert '"index"' in prompt
        assert '"text"' in prompt
        assert '"translation"' in prompt
    
    def test_system_prompt_non_batch_mode_no_json_instructions(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that non-batch mode system prompt does not contain JSON format instructions."""
        service = TranslationService()
        
        prompt = service._build_system_prompt(chinese_vietnamese_pair, is_batch=False)
        
        # Verify JSON format rule is NOT present in non-batch mode
        assert "JSON FORMAT" not in prompt


class TestJSONBatchFormatting:
    """Tests for JSON batch request formatting and response parsing."""
    
    def test_format_batch_request_creates_valid_json(self, mock_bedrock_client):
        """Test that _format_batch_request creates valid JSON with indices."""
        service = TranslationService()
        
        texts = ["你好", "世界", "测试"]
        result = service._format_batch_request(texts)
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        
        # Verify structure
        assert isinstance(parsed, list)
        assert len(parsed) == 3
        
        for idx, item in enumerate(parsed):
            assert item["index"] == idx
            assert item["text"] == texts[idx]
    
    def test_format_batch_request_handles_unicode(self, mock_bedrock_client):
        """Test that _format_batch_request handles Unicode characters correctly."""
        service = TranslationService()
        
        texts = ["中文", "Tiếng Việt", "日本語"]
        result = service._format_batch_request(texts)
        
        # Verify Unicode is preserved (not escaped)
        assert "中文" in result
        assert "Tiếng Việt" in result
        assert "日本語" in result
    
    def test_parse_batch_response_valid_json(self, mock_bedrock_client):
        """Test that _parse_batch_response correctly parses valid JSON response."""
        service = TranslationService()
        
        response = '[{"index": 0, "translation": "Xin chào"}, {"index": 1, "translation": "Thế giới"}]'
        result = service._parse_batch_response(response, expected_count=2)
        
        assert result is not None
        assert len(result) == 2
        assert result[0] == "Xin chào"
        assert result[1] == "Thế giới"
    
    def test_parse_batch_response_out_of_order_indices(self, mock_bedrock_client):
        """Test that _parse_batch_response handles out-of-order indices correctly."""
        service = TranslationService()
        
        # Response with indices in different order
        response = '[{"index": 1, "translation": "Thế giới"}, {"index": 0, "translation": "Xin chào"}]'
        result = service._parse_batch_response(response, expected_count=2)
        
        assert result is not None
        assert len(result) == 2
        assert result[0] == "Xin chào"  # Index 0 should be first
        assert result[1] == "Thế giới"  # Index 1 should be second
    
    def test_parse_batch_response_count_mismatch(self, mock_bedrock_client):
        """Test that _parse_batch_response returns None on count mismatch."""
        service = TranslationService()
        
        response = '[{"index": 0, "translation": "Xin chào"}]'
        result = service._parse_batch_response(response, expected_count=2)
        
        assert result is None
    
    def test_parse_batch_response_invalid_json(self, mock_bedrock_client):
        """Test that _parse_batch_response returns None on invalid JSON."""
        service = TranslationService()
        
        response = 'not valid json'
        result = service._parse_batch_response(response, expected_count=1)
        
        assert result is None
    
    def test_parse_batch_response_missing_fields(self, mock_bedrock_client):
        """Test that _parse_batch_response returns None when required fields are missing."""
        service = TranslationService()
        
        # Missing "translation" field
        response = '[{"index": 0, "text": "你好"}]'
        result = service._parse_batch_response(response, expected_count=1)
        
        assert result is None
    
    def test_parse_batch_response_missing_index(self, mock_bedrock_client):
        """Test that _parse_batch_response returns None when an index is missing."""
        service = TranslationService()
        
        # Missing index 1
        response = '[{"index": 0, "translation": "Xin chào"}, {"index": 2, "translation": "Test"}]'
        result = service._parse_batch_response(response, expected_count=3)
        
        assert result is None


class TestJSONRepair:
    """Tests for JSON repair of malformed LLM batch responses."""

    def test_repair_trailing_comma(self, mock_bedrock_client):
        service = TranslationService()
        text = '[{"index": 0, "translation": "Xin chào"},]'
        result = service._repair_json(text)
        assert result is not None
        assert json.loads(result) == [{"index": 0, "translation": "Xin chào"}]

    def test_repair_trailing_comma_in_batch_response(self, mock_bedrock_client):
        service = TranslationService()
        response = '[{"index": 0, "translation": "Xin chào"}, {"index": 1, "translation": "Thế giới"},]'
        result = service._parse_batch_response(response, expected_count=2)
        assert result is not None
        assert result[0] == "Xin chào"
        assert result[1] == "Thế giới"

    def test_repair_truncated_response(self, mock_bedrock_client):
        service = TranslationService()
        text = '[{"index": 0, "translation": "Xin chào"}, {"index": 1, "translation": "Thế giới"}, {"index": 2, "translat'
        result = service._repair_json(text)
        assert result is not None
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_repair_truncated_in_batch_response(self, mock_bedrock_client):
        """Truncated response repairs to fewer items than expected, so batch parsing returns None (count mismatch)."""
        service = TranslationService()
        response = '[{"index": 0, "translation": "Xin chào"}, {"index": 1, "translat'
        result = service._parse_batch_response(response, expected_count=2)
        assert result is None

    def test_repair_truncated_matches_expected(self, mock_bedrock_client):
        """Truncated response where complete items match expected count."""
        service = TranslationService()
        response = '[{"index": 0, "translation": "Xin chào"}, {"index": 1, "translation": "Thế giới"}, {"index": 2, "tr'
        result = service._parse_batch_response(response, expected_count=2)
        assert result is not None
        assert result[0] == "Xin chào"
        assert result[1] == "Thế giới"

    def test_repair_valid_json_passthrough(self, mock_bedrock_client):
        service = TranslationService()
        text = '[{"index": 0, "translation": "Xin chào"}]'
        result = service._repair_json(text)
        assert result is not None
        assert json.loads(result) == [{"index": 0, "translation": "Xin chào"}]

    def test_repair_unrepairable_returns_none(self, mock_bedrock_client):
        service = TranslationService()
        result = service._repair_json('completely broken garbage')
        assert result is None

    def test_repair_unrepairable_in_batch_response(self, mock_bedrock_client):
        service = TranslationService()
        result = service._parse_batch_response('completely broken garbage', expected_count=1)
        assert result is None


class TestTranslationServiceInitialization:
    """Tests for TranslationService initialization."""

    def test_initialization_with_defaults(self, mock_bedrock_client):
        """Test service initializes with default parameters."""
        service = TranslationService()

        assert service.model_id == 'global.amazon.nova-2-lite-v1:0'
        assert service.bedrock_client is not None

    def test_initialization_with_custom_params(self, mock_bedrock_client):
        """Test service initializes with custom parameters."""
        service = TranslationService(
            model_id='custom-model-id'
        )

        assert service.model_id == 'custom-model-id'


class TestTranslationFunctionality:
    """Tests for translation functionality."""
    
    @pytest.mark.asyncio
    async def test_translate_text_async_success(self, mock_bedrock_client, chinese_vietnamese_pair):
        """Test successful async translation."""
        service = TranslationService()
        
        # Mock successful Bedrock response
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': 'Xin chào thế giới'}
                    ]
                }
            }
        }
        
        result = await service.translate_text_async("你好世界", chinese_vietnamese_pair)

        assert isinstance(result, TranslationResult)
        assert result.text == 'Xin chào thế giới'
        assert not result.failed
        assert mock_bedrock_client.converse.called
    
    @pytest.mark.asyncio
    async def test_translate_text_async_preserves_non_source_language(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that non-source language text is preserved by the model.
        
        With model-based language detection, all non-empty text is sent to the model.
        The model's system prompt instructs it to return non-source language text unchanged.
        """
        service = TranslationService()
        
        # Mock the model returning the text unchanged (as per system prompt instructions)
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': 'Hello World'}
                    ]
                }
            }
        }
        
        result = await service.translate_text_async("Hello World", chinese_vietnamese_pair)

        assert result.text == "Hello World"
        # With model-based detection, the API is called and the model decides
        assert mock_bedrock_client.converse.called
    
    @pytest.mark.asyncio
    async def test_translate_text_async_handles_empty_text(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test handling of empty text."""
        service = TranslationService()
        
        result = await service.translate_text_async("", chinese_vietnamese_pair)

        assert result.text == ""
        assert not result.failed
        assert not mock_bedrock_client.converse.called
    
    def test_translate_text_sync_wrapper(self, mock_bedrock_client, chinese_vietnamese_pair):
        """Test synchronous wrapper for translate_text."""
        service = TranslationService()
        
        # Mock successful Bedrock response
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': 'Xin chào'}
                    ]
                }
            }
        }
        
        result = service.translate_text("你好", chinese_vietnamese_pair)

        assert result.text == 'Xin chào'


class TestRetryLogic:
    """Tests for retry logic with exponential backoff."""
    
    @pytest.mark.asyncio
    async def test_retries_on_throttling(self, mock_bedrock_client, chinese_vietnamese_pair):
        """Test retry logic on throttling errors."""
        service = TranslationService()
        
        # Mock throttling error on first two attempts, success on third
        from botocore.exceptions import ClientError
        
        mock_bedrock_client.converse.side_effect = [
            ClientError(
                {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                'converse'
            ),
            ClientError(
                {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                'converse'
            ),
            {
                'output': {
                    'message': {
                        'content': [
                            {'text': 'Xin chào'}
                        ]
                    }
                }
            }
        ]
        
        result = await service.translate_text_async("你好", chinese_vietnamese_pair)

        assert result.text == 'Xin chào'
        assert not result.failed
        assert mock_bedrock_client.converse.call_count == 3
    
    @pytest.mark.asyncio
    async def test_returns_original_after_max_retries(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that original text is returned after max retries."""
        service = TranslationService()
        
        # Mock persistent error
        from botocore.exceptions import ClientError
        
        mock_bedrock_client.converse.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailableException', 'Message': 'Service down'}},
            'converse'
        )
        
        result = await service.translate_text_async("你好", chinese_vietnamese_pair)

        assert result.text == "你好"  # Original text returned
        assert result.failed is True
        assert result.error_code == "ServiceUnavailableException"
        assert mock_bedrock_client.converse.call_count == 3  # Max retries
    
    @pytest.mark.asyncio
    async def test_no_retry_on_validation_error(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that validation errors are not retried."""
        service = TranslationService()
        
        # Mock validation error
        from botocore.exceptions import ClientError
        
        mock_bedrock_client.converse.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}},
            'converse'
        )
        
        result = await service.translate_text_async("你好", chinese_vietnamese_pair)

        assert result.text == "你好"  # Original text returned
        assert result.failed is True
        assert result.error_code == "ValidationException"
        assert mock_bedrock_client.converse.call_count == 1  # No retries


class TestBatchTranslation:
    """Tests for batch translation functionality."""
    
    @pytest.mark.asyncio
    async def test_batch_translate_async(self, mock_bedrock_client, chinese_vietnamese_pair):
        """Test async batch translation with JSON format."""
        service = TranslationService()
        
        # Mock successful batch response in JSON format
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': '[{"index": 0, "translation": "Xin chào"}, {"index": 1, "translation": "Tạm biệt"}, {"index": 2, "translation": "Cảm ơn"}]'}
                    ]
                }
            }
        }
        
        texts = ["你好", "再见", "谢谢"]
        results = await service.batch_translate_async(texts, chinese_vietnamese_pair)

        assert len(results) == 3
        assert results[0].text == 'Xin chào'
        assert results[1].text == 'Tạm biệt'
        assert results[2].text == 'Cảm ơn'
        assert all(not r.failed for r in results)
    
    @pytest.mark.asyncio
    async def test_batch_translate_preserves_non_source_language(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that non-source language texts are preserved in batch.
        
        With model-based language detection, all non-empty texts are sent to the model.
        The model's system prompt instructs it to preserve non-source language text.
        """
        service = TranslationService()
        
        # Mock response in JSON format - model preserves non-Chinese text
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': '[{"index": 0, "translation": "Xin chào"}, {"index": 1, "translation": "Hello"}, {"index": 2, "translation": "123"}]'}
                    ]
                }
            }
        }
        
        texts = ["你好", "Hello", "123"]
        results = await service.batch_translate_async(texts, chinese_vietnamese_pair)
        
        assert len(results) == 3
        assert results[0].text == 'Xin chào'  # Translated
        assert results[1].text == 'Hello'  # Preserved by model
        assert results[2].text == '123'  # Preserved by model
    
    def test_batch_translate_sync_wrapper(self, mock_bedrock_client, chinese_vietnamese_pair):
        """Test synchronous wrapper for batch translation."""
        service = TranslationService()
        
        # Mock successful batch response in JSON format
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': '[{"index": 0, "translation": "Xin chào"}]'}
                    ]
                }
            }
        }
        
        texts = ["你好"]
        results = service.batch_translate(texts, chinese_vietnamese_pair)

        assert len(results) == 1
        assert results[0].text == 'Xin chào'
    
    @pytest.mark.asyncio
    async def test_batch_translate_fallback_on_invalid_json(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that batch translation falls back to single-cell mode on invalid JSON response.
        
        When the model returns invalid JSON, the system should fall back to translating
        each text individually.
        """
        service = TranslationService()
        
        # First call returns invalid JSON (batch mode), subsequent calls return individual translations
        mock_bedrock_client.converse.side_effect = [
            # First call: batch mode returns invalid JSON
            {
                'output': {
                    'message': {
                        'content': [
                            {'text': 'This is not valid JSON'}
                        ]
                    }
                }
            },
            # Fallback: individual translation for first text
            {
                'output': {
                    'message': {
                        'content': [
                            {'text': 'Xin chào'}
                        ]
                    }
                }
            },
            # Fallback: individual translation for second text
            {
                'output': {
                    'message': {
                        'content': [
                            {'text': 'Tạm biệt'}
                        ]
                    }
                }
            }
        ]
        
        texts = ["你好", "再见"]
        results = await service.batch_translate_async(texts, chinese_vietnamese_pair)
        
        assert len(results) == 2
        assert results[0].text == 'Xin chào'
        assert results[1].text == 'Tạm biệt'
        # Should have called API 3 times: 1 batch + 2 individual fallbacks
        assert mock_bedrock_client.converse.call_count == 3
    
    @pytest.mark.asyncio
    async def test_batch_translate_handles_empty_texts(
        self,
        mock_bedrock_client,
        chinese_vietnamese_pair
    ):
        """Test that batch translation handles empty texts correctly."""
        service = TranslationService()
        
        # Mock response for non-empty texts only
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': '[{"index": 0, "translation": "Xin chào"}]'}
                    ]
                }
            }
        }
        
        texts = ["你好", "", "  "]  # Mix of non-empty and empty texts
        results = await service.batch_translate_async(texts, chinese_vietnamese_pair)
        
        assert len(results) == 3
        assert results[0].text == 'Xin chào'  # Translated
        assert results[1].text == ""  # Empty preserved
        assert results[2].text == "  "  # Whitespace preserved


class TestDynamicLanguagePairs:
    """Tests for dynamic language pair support."""
    
    @pytest.mark.asyncio
    async def test_uses_correct_language_names_in_system_prompt(
        self,
        mock_bedrock_client,
        english_spanish_pair
    ):
        """Test that correct language names are used in system prompt.
        
        With the new implementation, language names are in the system prompt,
        not the user message. The user message contains only the text to translate.
        """
        service = TranslationService()
        
        # Mock successful response
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': 'Hola'}
                    ]
                }
            }
        }
        
        await service.translate_text_async("Hello", english_spanish_pair)
        
        # Verify the system prompt contains the correct language names
        call_args = mock_bedrock_client.converse.call_args
        system_config = call_args[1]['system']
        system_prompt = system_config[0]['text']
        
        assert 'English' in system_prompt
        assert 'Spanish' in system_prompt
        
        # Verify the user message contains only the text to translate
        messages = call_args[1]['messages']
        user_text = messages[0]['content'][0]['text']
        assert user_text == "Hello"
    
    @pytest.mark.asyncio
    async def test_different_language_pairs(self, mock_bedrock_client):
        """Test translation with different language pairs."""
        service = TranslationService()
        
        # Test Chinese to Vietnamese
        zh_vi_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )
        
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': 'Xin chào'}
                    ]
                }
            }
        }
        
        result1 = await service.translate_text_async("你好", zh_vi_pair)
        assert result1.text == 'Xin chào'
        
        # Test English to Spanish
        en_es_pair = LanguagePair(
            id="en-es",
            source_language="English",
            target_language="Spanish",
            source_language_code="en",
            target_language_code="es"
        )
        
        mock_bedrock_client.converse.return_value = {
            'output': {
                'message': {
                    'content': [
                        {'text': 'Hola'}
                    ]
                }
            }
        }
        
        result2 = await service.translate_text_async("Hello", en_es_pair)
        assert result2.text == 'Hola'
