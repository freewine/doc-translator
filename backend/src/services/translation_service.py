"""
Translation Service Module

Provides translation functionality using Amazon Bedrock with support for multiple language pairs.
Handles configurable language detection and translation with retry logic and async support.
Supports term pair injection for consistent terminology translation.
"""

import asyncio
import json
import re
import time
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, TYPE_CHECKING
import boto3
from botocore.exceptions import ClientError

from ..models.job import LanguagePair


@dataclass
class TranslationResult:
    """Result of a single text translation, carrying error metadata alongside the text."""
    text: str
    failed: bool = False
    error_code: Optional[str] = None  # e.g. "ThrottlingException"

if TYPE_CHECKING:
    from ..models.thesaurus import TermPair


class TranslationService:
    """Service for translating text between multiple languages using Amazon Bedrock"""

    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # Exponential backoff delays in seconds

    def __init__(
        self,
        model_id: str = 'global.amazon.nova-2-lite-v1:0',
        batch_size: int = 50,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the translation service with Bedrock client.

        Args:
            model_id: Bedrock model ID to use (default: 'global.amazon.nova-2-lite-v1:0')
            batch_size: Number of texts to translate in a single batch (default: 50)
            logger: Logger instance for logging operations

        Note:
            AWS region is determined by boto3 default credential/region chain.
        """
        self.model_id = model_id
        self.batch_size = batch_size
        self.logger = logger or logging.getLogger(__name__)

        # Initialize boto3 bedrock-runtime client
        # Region is determined by boto3 default chain (env vars, config files, instance metadata)
        try:
            self.bedrock_client = boto3.client(service_name='bedrock-runtime')
            self.logger.info("Bedrock client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise
    
    def _build_system_prompt(
        self,
        language_pair: LanguagePair,
        is_batch: bool = False,
        term_pairs: Optional[List["TermPair"]] = None
    ) -> str:
        """
        Build system prompt with language detection, English preservation, and format rules.
        
        Constructs a comprehensive system prompt that instructs the LLM model to:
        - Detect if input contains source language text
        - Preserve English text unchanged
        - Return only the translation without explanations
        - For batch mode, use JSON input/output format
        - Use provided term pairs for consistent terminology
        
        Args:
            language_pair: Source and target language configuration
            is_batch: Whether this is for batch translation (includes JSON format rules)
            term_pairs: Optional list of TermPair objects for terminology injection
            
        Returns:
            Complete system prompt string
        """
        source_lang = language_pair.source_language
        target_lang = language_pair.target_language
        
        # Base system prompt with language detection and English preservation rules
        prompt = f"""You are a professional translator. Your task is to translate text from {source_lang} to {target_lang}."""

        # Add terminology reference section if term pairs are provided
        if term_pairs and len(term_pairs) > 0:
            prompt += f"""

TERMINOLOGY REFERENCE:
Use the following term translations consistently throughout the document:"""
            for term in term_pairs:
                prompt += f"\n- {term.source_term} → {term.target_term}"
            prompt += "\n"

        # Add rules section
        prompt += f"""

Rules:
1. TERMINOLOGY: When translating terms from the TERMINOLOGY REFERENCE above, use the provided translations exactly.
2. LANGUAGE DETECTION: Translate all {source_lang} text to {target_lang}. If an individual text item clearly contains no {source_lang} text (e.g., it is purely English or purely {target_lang}), return that item unchanged. When in doubt, always translate. Never skip translating {source_lang} text just because other items in the input are in {target_lang} or English.
3. ENGLISH PRESERVATION: Do NOT translate English text. Keep all English words, technical terms, abbreviations, and proper nouns exactly as they appear.
4. MIXED CONTENT: When text contains both {source_lang} and English, translate the {source_lang} portions while keeping English text in place. If text contains {target_lang} mixed with {source_lang}, translate the {source_lang} portions to {target_lang}. Do NOT skip {source_lang} text just because {target_lang} text is also present.
5. OUTPUT FORMAT: Return ONLY the translation without any explanations, notes, or additional text."""

        # Add JSON format instructions for batch mode
        if is_batch:
            prompt += f"""
6. JSON FORMAT: The input is a JSON array of objects with "index" and "text" fields. Return a JSON array with the same structure, where each object has "index" (matching the input) and "translation" fields. CRITICAL: Evaluate each item INDEPENDENTLY — the language of other items must NOT influence your decision for any given item. If an item contains {source_lang} text, translate it to {target_lang} regardless of what other items contain. Example:
Input: [{{"index": 0, "text": "中文文本"}}, {{"index": 1, "text": "English text"}}, {{"index": 2, "text": "更多中文"}}]
Output: [{{"index": 0, "translation": "Văn bản tiếng Việt"}}, {{"index": 1, "translation": "English text"}}, {{"index": 2, "translation": "Thêm tiếng Trung"}}]"""

        return prompt

    def _format_batch_request(self, texts: List[str]) -> str:
        """
        Format texts as indexed JSON array for batch translation.
        
        Creates a JSON array where each item has an "index" and "text" field.
        Uses pretty-printing with indent=2 for debugging and logging purposes.
        
        Args:
            texts: List of texts to translate
            
        Returns:
            Pretty-printed JSON string with indexed items
        """
        batch_items = [
            {"index": idx, "text": text}
            for idx, text in enumerate(texts)
        ]
        
        formatted_json = json.dumps(batch_items, indent=2, ensure_ascii=False)
        
        self.logger.debug(f"Formatted batch request with {len(texts)} items:\n{formatted_json}")
        
        return formatted_json

    def _extract_json_from_response(self, response: str) -> str:
        """
        Extract JSON content from response, handling markdown code blocks.
        
        The LLM may return JSON in various formats:
        - Raw JSON: [{"index": 0, "translation": "..."}]
        - Markdown wrapped: ```json\n[...]\n```
        - Markdown without language: ```\n[...]\n```
        
        Args:
            response: Raw response string from model
            
        Returns:
            Extracted JSON string
        """
        text = response.strip()
        
        # Handle markdown code blocks: ```json ... ``` or ``` ... ```
        if text.startswith("```"):
            # Find the end of the opening fence
            first_newline = text.find("\n")
            if first_newline != -1:
                # Skip the opening fence line (```json or ```)
                text = text[first_newline + 1:]
            
            # Remove closing fence
            if text.endswith("```"):
                text = text[:-3]
            
            text = text.strip()
        
        return text

    def _repair_json(self, text: str) -> Optional[str]:
        """
        Attempt to repair common JSON malformations from LLM responses.

        Returns repaired JSON string, or None if repair is not possible.
        """
        repaired = text

        # Remove trailing commas before ] or }
        repaired = re.sub(r',\s*([\]}])', r'\1', repaired)

        # Try parsing after trailing comma fix
        try:
            json.loads(repaired)
            return repaired
        except json.JSONDecodeError:
            pass

        # Handle truncated response: try to close at the last complete object
        # Find the last complete object (ending with })
        last_brace = repaired.rfind('}')
        if last_brace != -1:
            truncated = repaired[:last_brace + 1]
            # Remove any trailing comma after the last object
            truncated = truncated.rstrip().rstrip(',')
            # Close the array if needed
            if not truncated.rstrip().endswith(']'):
                truncated += ']'
            # Remove trailing commas again in case truncation introduced them
            truncated = re.sub(r',\s*([\]}])', r'\1', truncated)
            try:
                json.loads(truncated)
                return truncated
            except json.JSONDecodeError:
                pass

        return None

    async def _call_bedrock_with_retry(
        self,
        messages: List[dict],
        system_config: List[dict],
        inference_config: dict
    ) -> Tuple[str, float]:
        """
        Call Bedrock API with exponential backoff retry logic.

        Args:
            messages: Message list for Converse API
            system_config: System prompt configuration
            inference_config: Inference configuration

        Returns:
            Tuple of (response_text, latency_seconds)

        Raises:
            ClientError: If all retries fail or validation error occurs
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                start_time = time.time()
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.bedrock_client.converse(
                        modelId=self.model_id,
                        messages=messages,
                        system=system_config,
                        inferenceConfig=inference_config
                    )
                )
                latency = time.time() - start_time
                response_text = response['output']['message']['content'][0]['text'].strip()

                self.logger.debug(f"Bedrock API call successful (attempt {attempt + 1}, latency: {latency:.3f}s)")
                return response_text, latency

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', str(e))

                if error_code == 'ValidationException':
                    self.logger.error(f"Validation error: {error_message}")
                    raise

                if attempt < self.MAX_RETRIES - 1:
                    self.logger.warning(
                        f"Bedrock API attempt {attempt + 1} failed ({error_code}): {error_message}"
                    )
                    await asyncio.sleep(self.RETRY_DELAYS[attempt])
                else:
                    self.logger.error(
                        f"Bedrock API failed after {self.MAX_RETRIES} attempts: {error_code} - {error_message}"
                    )
                    raise

            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    self.logger.warning(f"Bedrock API attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(self.RETRY_DELAYS[attempt])
                else:
                    self.logger.error(f"Bedrock API failed after {self.MAX_RETRIES} attempts: {e}")
                    raise

    def _parse_batch_response(self, response: str, expected_count: int) -> Optional[List[str]]:
        """
        Parse JSON response and extract translations in order.
        
        Handles both raw JSON and markdown-wrapped JSON responses.
        Validates the count matches expected items and extracts translations by index.
        
        Args:
            response: JSON response string from model (may be wrapped in markdown)
            expected_count: Expected number of translations
            
        Returns:
            List of translations in order, or None if parsing fails or count mismatch
        """
        # Extract JSON from potential markdown wrapper
        json_str = self._extract_json_from_response(response)

        # Try parsing, with repair fallback on failure
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse batch response as JSON: {e}")
            repaired = self._repair_json(json_str)
            if repaired is None:
                self.logger.warning("JSON repair failed, giving up on batch response")
                return None
            self.logger.info("JSON repair succeeded, using repaired response")
            try:
                parsed = json.loads(repaired)
            except json.JSONDecodeError:
                self.logger.warning("Repaired JSON still invalid, giving up on batch response")
                return None

        return self._validate_batch_translations(parsed, expected_count)

    def _validate_batch_translations(self, parsed: object, expected_count: int) -> Optional[List[str]]:
        """Validate parsed JSON and extract ordered translations."""
        # Validate it's a list
        if not isinstance(parsed, list):
            self.logger.warning(f"Batch response is not a list: {type(parsed)}")
            return None

        # Validate count matches
        if len(parsed) != expected_count:
            self.logger.warning(
                f"Batch response count mismatch: expected {expected_count}, got {len(parsed)}"
            )
            return None

        # Extract translations ordered by index
        translation_map = {}
        for item in parsed:
            if not isinstance(item, dict) or "index" not in item or "translation" not in item:
                self.logger.warning(f"Invalid batch response item: {item}")
                return None
            translation_map[item["index"]] = item["translation"]

        # Build ordered list - check all indices exist
        if set(translation_map.keys()) != set(range(expected_count)):
            self.logger.warning(f"Missing or invalid indices in response")
            return None

        translations = [translation_map[idx] for idx in range(expected_count)]

        self.logger.debug(f"Successfully parsed batch response with {len(translations)} translations")
        return translations

    async def translate_text_async(
        self,
        source_text: str,
        language_pair: LanguagePair,
        term_pairs: Optional[List["TermPair"]] = None
    ) -> TranslationResult:
        """
        Translate text from source to target language using Amazon Bedrock (async version).

        Returns a TranslationResult containing the translated text and error metadata.
        On failure after retries, returns the original text with failed=True and the error code.

        Args:
            source_text: Text in source language to translate
            language_pair: LanguagePair specifying source and target languages
            term_pairs: Optional list of TermPair objects for terminology injection

        Returns:
            TranslationResult with translated text, or original text with error info on failure
        """
        if not source_text or not source_text.strip():
            return TranslationResult(text=source_text)

        system_prompt = self._build_system_prompt(language_pair, is_batch=False, term_pairs=term_pairs)

        try:
            messages = [
                {
                    "role": "user",
                    "content": [{"text": source_text}]
                }
            ]

            system_config = [{"text": system_prompt}]

            inference_config = {
                "maxTokens": 32000,
                "temperature": 0.3
            }

            translated_text, latency = await self._call_bedrock_with_retry(
                messages, system_config, inference_config
            )

            self.logger.debug(
                f"Translation successful ({language_pair.source_language} → "
                f"{language_pair.target_language}, latency: {latency:.3f}s)"
            )
            return TranslationResult(text=translated_text)

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            self.logger.error(f"Translation failed ({error_code}), returning original text")
            return TranslationResult(text=source_text, failed=True, error_code=error_code)

        except Exception as e:
            self.logger.error(f"Translation failed: {str(e)}, returning original text")
            return TranslationResult(text=source_text, failed=True, error_code="UnexpectedError")

    def translate_text(
        self,
        source_text: str,
        language_pair: LanguagePair,
        term_pairs: Optional[List["TermPair"]] = None
    ) -> TranslationResult:
        """
        Translate text from source to target language using Amazon Bedrock (synchronous version).

        This is a synchronous wrapper around translate_text_async for backward compatibility.

        Args:
            source_text: Text in source language to translate
            language_pair: LanguagePair specifying source and target languages
            term_pairs: Optional list of TermPair objects for terminology injection

        Returns:
            TranslationResult with translated text, or original text with error info on failure
        """
        # Create event loop if needed and run async version
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.translate_text_async(source_text, language_pair, term_pairs))

    async def batch_translate_async(
        self,
        texts: List[str],
        language_pair: LanguagePair,
        term_pairs: Optional[List["TermPair"]] = None
    ) -> List[TranslationResult]:
        """
        Translate multiple texts in batches using JSON format for reliable ordering (async version).

        Returns TranslationResult objects that carry error metadata alongside translations.
        On failure, falls back to individual translation. Failed segments have failed=True.

        Args:
            texts: List of texts in source language to translate
            language_pair: LanguagePair specifying source and target languages
            term_pairs: Optional list of TermPair objects for terminology injection

        Returns:
            List of TranslationResult in the same order as input
        """
        if not texts:
            return []

        results: List[TranslationResult] = []

        # Process texts in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]

            # Filter out empty texts - let the model handle language detection
            batch_with_indices = []
            for idx, text in enumerate(batch):
                if text and text.strip():
                    batch_with_indices.append((idx, text))

            # If no non-empty texts in this batch, just return originals
            if not batch_with_indices:
                results.extend(TranslationResult(text=t) for t in batch)
                continue

            # Prepare batch translation request using JSON format
            batch_texts = [text for _, text in batch_with_indices]

            # Format request as JSON array with indices
            json_request = self._format_batch_request(batch_texts)

            # Build system prompt with batch mode enabled and term pairs
            system_prompt = self._build_system_prompt(language_pair, is_batch=True, term_pairs=term_pairs)

            try:
                messages = [
                    {
                        "role": "user",
                        "content": [{"text": json_request}]
                    }
                ]

                system_config = [{"text": system_prompt}]

                inference_config = {
                    "maxTokens": 32000,
                    "temperature": 0.3
                }

                batch_result, _ = await self._call_bedrock_with_retry(
                    messages, system_config, inference_config
                )

                # Parse JSON response and extract translations
                parsed_translations = self._parse_batch_response(batch_result, len(batch_texts))

                if parsed_translations is None:
                    # JSON parsing failed - fall back to single-cell translation
                    self.logger.warning(
                        f"JSON response parsing failed, falling back to single-cell translation mode"
                    )
                    batch_results: List[TranslationResult] = [TranslationResult(text=t) for t in batch]
                    for original_idx, text in batch_with_indices:
                        batch_results[original_idx] = await self.translate_text_async(text, language_pair, term_pairs)
                    results.extend(batch_results)
                else:
                    # Map translations back to original positions
                    batch_results = [TranslationResult(text=t) for t in batch]
                    for (original_idx, _), translation in zip(batch_with_indices, parsed_translations):
                        batch_results[original_idx] = TranslationResult(text=translation)

                    results.extend(batch_results)

                    self.logger.debug(
                        f"Batch translated {len(batch_texts)} texts successfully using JSON format "
                        f"({language_pair.source_language} → {language_pair.target_language})"
                    )

            except Exception as e:
                self.logger.error(
                    f"Batch translation failed: {str(e)}, falling back to individual translation"
                )
                # Fallback: translate individually
                batch_results = [TranslationResult(text=t) for t in batch]
                for original_idx, text in batch_with_indices:
                    # translate_text_async returns TranslationResult with error info
                    batch_results[original_idx] = await self.translate_text_async(text, language_pair, term_pairs)
                results.extend(batch_results)

        return results

    def batch_translate(
        self,
        texts: List[str],
        language_pair: LanguagePair,
        term_pairs: Optional[List["TermPair"]] = None
    ) -> List[TranslationResult]:
        """
        Translate multiple texts in batches for efficiency (synchronous version).

        This is a synchronous wrapper around batch_translate_async for backward compatibility.

        Args:
            texts: List of texts in source language to translate
            language_pair: LanguagePair specifying source and target languages
            term_pairs: Optional list of TermPair objects for terminology injection

        Returns:
            List of TranslationResult in the same order as input
        """
        # Create event loop if needed and run async version
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.batch_translate_async(texts, language_pair, term_pairs))
