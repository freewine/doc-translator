"""
Property-Based Tests for Auto Append Logic

Tests the apply_auto_append function using hypothesis for property-based testing.
Feature: auto-append-translation

Validates: Requirements 2.1, 2.2, 2.3, 1.1, 4.2
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.services.document_processor import apply_auto_append
from src.models.job import TranslationJob, JobStatus, LanguagePair
from src.graphql.resolvers import convert_translation_job


# Strategy for generating non-empty text strings
text_strategy = st.text(min_size=1, max_size=100)


class TestAutoAppendProperties:
    """Property-based tests for apply_auto_append function."""

    @settings(max_examples=100)
    @given(
        original=text_strategy,
        translated=text_strategy
    )
    def test_property_1_auto_append_output_format(self, original: str, translated: str):
        """
        Property 1: Auto Append Output Format
        
        For any original text and translated text where auto_append is true
        and the texts differ, the output text SHALL be in the format
        {original_text}\\n{translated_text}.
        
        Feature: auto-append-translation, Property 1: Auto Append Output Format
        Validates: Requirements 2.1
        """
        # Only test when texts differ (after stripping)
        if original.strip() != translated.strip():
            result = apply_auto_append(original, translated, auto_append=True)
            expected = f"{original}\n{translated}"
            assert result == expected, (
                f"Expected '{expected}' but got '{result}' "
                f"for original='{original}', translated='{translated}'"
            )

    @settings(max_examples=100)
    @given(text=text_strategy)
    def test_property_2_no_duplication_when_texts_equal(self, text: str):
        """
        Property 2: No Duplication When Texts Equal
        
        For any original text and translated text where auto_append is true
        and the texts are equal (after trimming), the output text SHALL equal
        the translated text (no duplication).
        
        Feature: auto-append-translation, Property 2: No Duplication When Texts Equal
        Validates: Requirements 2.2
        """
        # Test with identical texts
        result = apply_auto_append(text, text, auto_append=True)
        assert result == text, (
            f"Expected '{text}' but got '{result}' when texts are equal"
        )
        
        # Test with texts that are equal after stripping
        padded_original = f"  {text}  "
        padded_translated = f"\t{text}\n"
        result = apply_auto_append(padded_original, padded_translated, auto_append=True)
        assert result == padded_translated, (
            f"Expected '{padded_translated}' but got '{result}' "
            f"when texts are equal after stripping"
        )

    @settings(max_examples=100)
    @given(
        original=text_strategy,
        translated=text_strategy
    )
    def test_property_3_replace_mode_output(self, original: str, translated: str):
        """
        Property 3: Replace Mode Output
        
        For any original text and translated text where auto_append is false,
        the output text SHALL equal the translated text only.
        
        Feature: auto-append-translation, Property 3: Replace Mode Output
        Validates: Requirements 2.3
        """
        result = apply_auto_append(original, translated, auto_append=False)
        assert result == translated, (
            f"Expected '{translated}' but got '{result}' "
            f"for original='{original}' in replace mode"
        )



class TestAutoAppendRoundTripProperties:
    """Property-based tests for auto_append setting round-trip through GraphQL conversion."""

    @settings(max_examples=100)
    @given(auto_append_value=st.booleans())
    def test_property_4_auto_append_setting_round_trip(self, auto_append_value: bool):
        """
        Property 4: Auto Append Setting Round Trip
        
        For any translation job created with a specific auto_append value,
        querying that job SHALL return the same auto_append value.
        
        Feature: auto-append-translation, Property 4: Auto Append Setting Round Trip
        Validates: Requirements 1.1, 4.2
        """
        # Create a domain TranslationJob with the given auto_append value
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )
        
        job = TranslationJob(
            status=JobStatus.PENDING,
            files_total=1,
            language_pair=language_pair,
            file_ids=["test-file-id"],
            auto_append=auto_append_value
        )
        
        # Convert to GraphQL type (simulates what happens when querying)
        gql_job = convert_translation_job(job)
        
        # Verify the auto_append value is preserved through conversion
        assert gql_job.auto_append == auto_append_value, (
            f"Expected auto_append={auto_append_value} but got {gql_job.auto_append} "
            f"after GraphQL conversion"
        )
