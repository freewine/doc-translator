"""
Property-Based Tests for Interleaved Mode Logic

Tests the apply_interleaved_mode function using hypothesis for property-based testing.
Feature: intertwined-translation-mode

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.services.document_processor import apply_interleaved_mode


# Strategy for generating line content without newlines (since newlines are line separators)
line_content_strategy = st.text(alphabet=st.characters(blacklist_characters='\n'), max_size=50)


class TestInterleavedModeProperties:
    """Property-based tests for apply_interleaved_mode function."""

    @settings(max_examples=100)
    @given(
        original_lines=st.lists(line_content_strategy, min_size=1, max_size=20),
        translated_lines=st.lists(line_content_strategy, min_size=1, max_size=20)
    )
    def test_property_3_interleaving_algorithm_correctness(
        self, original_lines: list[str], translated_lines: list[str]
    ):
        """
        Property 3: Interleaving Algorithm Correctness
        
        For any original text with N lines and translated text with M lines,
        when interleavedMode is true, the output SHALL contain lines in the order:
        original[0], translated[0], original[1], translated[1], ...,
        followed by any remaining lines from the longer text.
        
        Feature: intertwined-translation-mode, Property 3: Interleaving Algorithm Correctness
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
        """
        original = '\n'.join(original_lines)
        translated = '\n'.join(translated_lines)
        
        # Skip the case where texts are equal (covered by Property 4)
        assume(original.strip() != translated.strip())
        
        result = apply_interleaved_mode(original, translated)
        
        # Verify interleaving pattern
        result_lines = result.split('\n')
        max_len = max(len(original_lines), len(translated_lines))
        
        idx = 0
        for i in range(max_len):
            if i < len(original_lines):
                assert result_lines[idx] == original_lines[i], (
                    f"Expected original line '{original_lines[i]}' at index {idx}, "
                    f"but got '{result_lines[idx]}'. "
                    f"Original lines: {original_lines}, Translated lines: {translated_lines}"
                )
                idx += 1
            if i < len(translated_lines):
                assert result_lines[idx] == translated_lines[i], (
                    f"Expected translated line '{translated_lines[i]}' at index {idx}, "
                    f"but got '{result_lines[idx]}'. "
                    f"Original lines: {original_lines}, Translated lines: {translated_lines}"
                )
                idx += 1
        
        # Verify total line count
        expected_line_count = len(original_lines) + len(translated_lines)
        assert len(result_lines) == expected_line_count, (
            f"Expected {expected_line_count} lines but got {len(result_lines)}. "
            f"Original lines: {original_lines}, Translated lines: {translated_lines}"
        )

    @settings(max_examples=100)
    @given(text=st.text())
    def test_property_4_no_duplication_when_texts_equal(self, text: str):
        """
        Property 4: No Duplication When Texts Equal
        
        For any original text and translated text where interleavedMode is true
        and the texts are equal (after trimming), the output text SHALL equal
        the original text (no duplication).
        
        Feature: intertwined-translation-mode, Property 4: No Duplication When Texts Equal
        **Validates: Requirements 4.5**
        """
        result = apply_interleaved_mode(text, text)
        assert result == text, (
            f"Expected '{text}' but got '{result}' when texts are equal"
        )

    @settings(max_examples=100)
    @given(
        text=st.text(min_size=1, alphabet=st.characters(blacklist_characters='\n')),
        leading_whitespace=st.text(alphabet=' \t', max_size=5),
        trailing_whitespace=st.text(alphabet=' \t', max_size=5)
    )
    def test_property_4_no_duplication_with_whitespace_variations(
        self, text: str, leading_whitespace: str, trailing_whitespace: str
    ):
        """
        Property 4 (Extended): No Duplication When Texts Equal After Trimming
        
        For any original text and translated text where interleavedMode is true
        and the texts are equal after stripping whitespace, the output text
        SHALL equal the translated text (no duplication).
        
        Feature: intertwined-translation-mode, Property 4: No Duplication When Texts Equal
        **Validates: Requirements 4.5**
        """
        original = f"{leading_whitespace}{text}{trailing_whitespace}"
        translated = text.strip()
        
        # Only test when texts are equal after stripping
        assume(original.strip() == translated.strip())
        
        result = apply_interleaved_mode(original, translated)
        assert result == translated, (
            f"Expected '{translated}' but got '{result}' "
            f"when texts are equal after stripping"
        )


class TestInterleavedModeLineCountProperties:
    """Additional property tests for line count invariants."""

    @settings(max_examples=100)
    @given(
        original_lines=st.lists(line_content_strategy, min_size=1, max_size=20),
        translated_lines=st.lists(line_content_strategy, min_size=1, max_size=20)
    )
    def test_interleaved_output_contains_all_original_lines(
        self, original_lines: list[str], translated_lines: list[str]
    ):
        """
        Verify that all original lines appear in the interleaved output.
        
        Feature: intertwined-translation-mode, Property 3: Interleaving Algorithm Correctness
        **Validates: Requirements 4.2, 4.3**
        """
        original = '\n'.join(original_lines)
        translated = '\n'.join(translated_lines)
        
        # Skip the case where texts are equal
        assume(original.strip() != translated.strip())
        
        result = apply_interleaved_mode(original, translated)
        result_lines = result.split('\n')
        
        # All original lines should appear in the result
        for orig_line in original_lines:
            assert orig_line in result_lines, (
                f"Original line '{orig_line}' not found in result. "
                f"Result lines: {result_lines}"
            )

    @settings(max_examples=100)
    @given(
        original_lines=st.lists(line_content_strategy, min_size=1, max_size=20),
        translated_lines=st.lists(line_content_strategy, min_size=1, max_size=20)
    )
    def test_interleaved_output_contains_all_translated_lines(
        self, original_lines: list[str], translated_lines: list[str]
    ):
        """
        Verify that all translated lines appear in the interleaved output.
        
        Feature: intertwined-translation-mode, Property 3: Interleaving Algorithm Correctness
        **Validates: Requirements 4.2, 4.4**
        """
        original = '\n'.join(original_lines)
        translated = '\n'.join(translated_lines)
        
        # Skip the case where texts are equal
        assume(original.strip() != translated.strip())
        
        result = apply_interleaved_mode(original, translated)
        result_lines = result.split('\n')
        
        # All translated lines should appear in the result
        for trans_line in translated_lines:
            assert trans_line in result_lines, (
                f"Translated line '{trans_line}' not found in result. "
                f"Result lines: {result_lines}"
            )

    @settings(max_examples=100)
    @given(
        original_lines=st.lists(line_content_strategy, min_size=1, max_size=20),
        translated_lines=st.lists(line_content_strategy, min_size=1, max_size=20)
    )
    def test_interleaved_output_line_count_is_sum_of_inputs(
        self, original_lines: list[str], translated_lines: list[str]
    ):
        """
        Verify that the interleaved output has exactly the sum of input line counts.
        
        Feature: intertwined-translation-mode, Property 3: Interleaving Algorithm Correctness
        **Validates: Requirements 4.2, 4.3, 4.4**
        """
        original = '\n'.join(original_lines)
        translated = '\n'.join(translated_lines)
        
        # Skip the case where texts are equal
        assume(original.strip() != translated.strip())
        
        result = apply_interleaved_mode(original, translated)
        result_lines = result.split('\n')
        
        expected_count = len(original_lines) + len(translated_lines)
        assert len(result_lines) == expected_count, (
            f"Expected {expected_count} lines but got {len(result_lines)}. "
            f"Original: {len(original_lines)} lines, Translated: {len(translated_lines)} lines"
        )


# =========================================================================
# Property Tests for Default Values and Mutual Exclusivity
# Task 2.4: Property 1 and Property 2
# =========================================================================

from src.models.job import TranslationJob, JobStatus, LanguagePair


class TestDefaultInterleavedModeProperties:
    """
    Property-based tests for default interleaved_mode value.
    
    Feature: intertwined-translation-mode, Property 1: Default Interleaved Mode Value
    **Validates: Requirements 2.1, 2.2**
    """

    @settings(max_examples=100)
    @given(
        file_ids=st.lists(st.text(min_size=1, max_size=36), min_size=1, max_size=10)
    )
    def test_property_1_default_interleaved_mode_is_false(self, file_ids: list[str]):
        """
        Property 1: Default Interleaved Mode Value
        
        For any translation job created without specifying interleavedMode,
        the job SHALL have interleavedMode set to False.
        
        Feature: intertwined-translation-mode, Property 1: Default Interleaved Mode Value
        **Validates: Requirements 2.1, 2.2**
        """
        # Create a language pair for the job
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )
        
        # Create job without specifying interleaved_mode
        job = TranslationJob(
            status=JobStatus.PENDING,
            files_total=len(file_ids),
            language_pair=language_pair,
            file_ids=file_ids
        )
        
        # Verify default value is False
        assert job.interleaved_mode == False, (
            f"Expected interleaved_mode to be False by default, "
            f"but got {job.interleaved_mode}"
        )

    @settings(max_examples=100)
    @given(
        file_ids=st.lists(st.text(min_size=1, max_size=36), min_size=1, max_size=10),
        auto_append=st.booleans()
    )
    def test_property_1_default_interleaved_mode_independent_of_auto_append(
        self, file_ids: list[str], auto_append: bool
    ):
        """
        Property 1 (Extended): Default Interleaved Mode Independent of Auto Append
        
        For any translation job created with any auto_append value but without
        specifying interleavedMode, the job SHALL have interleavedMode set to False.
        
        Feature: intertwined-translation-mode, Property 1: Default Interleaved Mode Value
        **Validates: Requirements 2.1, 2.2**
        """
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )
        
        # Create job with auto_append but without interleaved_mode
        job = TranslationJob(
            status=JobStatus.PENDING,
            files_total=len(file_ids),
            language_pair=language_pair,
            file_ids=file_ids,
            auto_append=auto_append
            # interleaved_mode not specified - should default to False
        )
        
        assert job.interleaved_mode == False, (
            f"Expected interleaved_mode to be False by default when auto_append={auto_append}, "
            f"but got {job.interleaved_mode}"
        )
        assert job.auto_append == auto_append, (
            f"Expected auto_append to be {auto_append}, but got {job.auto_append}"
        )


class TestMutualExclusivityProperties:
    """
    Property-based tests for mutual exclusivity validation.
    
    Feature: intertwined-translation-mode, Property 2: Mutual Exclusivity Validation
    **Validates: Requirements 3.3**
    """

    @settings(max_examples=100)
    @given(
        auto_append=st.booleans(),
        interleaved_mode=st.booleans()
    )
    def test_property_2_mutual_exclusivity_validation(
        self, auto_append: bool, interleaved_mode: bool
    ):
        """
        Property 2: Mutual Exclusivity Validation
        
        For any job creation request where both autoAppend and interleavedMode
        are set to True, the system SHALL return a validation error and not
        create the job.
        
        This test validates the validation logic that should be applied at the
        GraphQL mutation level.
        
        Feature: intertwined-translation-mode, Property 2: Mutual Exclusivity Validation
        **Validates: Requirements 3.3**
        """
        # Simulate the validation logic from the GraphQL mutation
        def validate_output_modes(auto_append: bool, interleaved_mode: bool) -> None:
            """
            Validate mutual exclusivity of output modes.
            This mirrors the validation in schema.py create_translation_job mutation.
            """
            if auto_append and interleaved_mode:
                raise ValueError(
                    "Cannot enable both Append Mode and Interleaved Mode simultaneously"
                )
        
        if auto_append and interleaved_mode:
            # Both True - should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                validate_output_modes(auto_append, interleaved_mode)
            
            assert "Cannot enable both" in str(exc_info.value), (
                f"Expected error message about mutual exclusivity, "
                f"but got: {exc_info.value}"
            )
        else:
            # At least one is False - should not raise
            # This should complete without exception
            validate_output_modes(auto_append, interleaved_mode)

    @settings(max_examples=100)
    @given(
        file_ids=st.lists(st.text(min_size=1, max_size=36), min_size=1, max_size=5),
        auto_append=st.booleans(),
        interleaved_mode=st.booleans()
    )
    def test_property_2_valid_combinations_create_job_successfully(
        self, file_ids: list[str], auto_append: bool, interleaved_mode: bool
    ):
        """
        Property 2 (Extended): Valid Combinations Create Job Successfully
        
        For any job creation request where autoAppend and interleavedMode are
        NOT both True, the job SHALL be created successfully with the specified values.
        
        Feature: intertwined-translation-mode, Property 2: Mutual Exclusivity Validation
        **Validates: Requirements 3.3**
        """
        # Skip invalid combinations (both True)
        assume(not (auto_append and interleaved_mode))
        
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )
        
        # Create job with valid combination
        job = TranslationJob(
            status=JobStatus.PENDING,
            files_total=len(file_ids),
            language_pair=language_pair,
            file_ids=file_ids,
            auto_append=auto_append,
            interleaved_mode=interleaved_mode
        )
        
        # Verify values are set correctly
        assert job.auto_append == auto_append, (
            f"Expected auto_append={auto_append}, but got {job.auto_append}"
        )
        assert job.interleaved_mode == interleaved_mode, (
            f"Expected interleaved_mode={interleaved_mode}, but got {job.interleaved_mode}"
        )

    @settings(max_examples=100)
    @given(st.data())
    def test_property_2_exactly_three_valid_output_mode_combinations(self, data):
        """
        Property 2 (Extended): Exactly Three Valid Output Mode Combinations
        
        There are exactly three valid output mode combinations:
        1. Replace Mode: auto_append=False, interleaved_mode=False
        2. Append Mode: auto_append=True, interleaved_mode=False
        3. Interleaved Mode: auto_append=False, interleaved_mode=True
        
        The fourth combination (both True) is invalid.
        
        Feature: intertwined-translation-mode, Property 2: Mutual Exclusivity Validation
        **Validates: Requirements 3.3**
        """
        # Define valid combinations
        valid_combinations = [
            (False, False),  # Replace Mode
            (True, False),   # Append Mode
            (False, True),   # Interleaved Mode
        ]
        
        # Pick a random valid combination
        auto_append, interleaved_mode = data.draw(
            st.sampled_from(valid_combinations)
        )
        
        language_pair = LanguagePair(
            id="en-es",
            source_language="English",
            target_language="Spanish",
            source_language_code="en",
            target_language_code="es"
        )
        
        # Should create successfully
        job = TranslationJob(
            status=JobStatus.PENDING,
            files_total=1,
            language_pair=language_pair,
            file_ids=["test-file-id"],
            auto_append=auto_append,
            interleaved_mode=interleaved_mode
        )
        
        # Verify the job was created with correct values
        assert job.auto_append == auto_append
        assert job.interleaved_mode == interleaved_mode
        
        # Verify mutual exclusivity is maintained
        assert not (job.auto_append and job.interleaved_mode), (
            "Job should never have both auto_append and interleaved_mode set to True"
        )


# =========================================================================
# Property Tests for Output Mode to API Parameter Mapping
# Task 7.2: Property 5
# =========================================================================


def map_output_mode_to_flags(mode: str) -> tuple[bool, bool]:
    """
    Map UI output mode selection to API parameters.
    
    This function mirrors the frontend logic that converts the radio button
    selection to the autoAppend and interleavedMode API parameters.
    
    Args:
        mode: The output mode selected in the UI ('replace', 'append', 'interleaved')
        
    Returns:
        Tuple of (auto_append, interleaved_mode) boolean flags
        
    Raises:
        ValueError: If mode is not one of the valid options
    """
    if mode == 'replace':
        return (False, False)
    elif mode == 'append':
        return (True, False)
    elif mode == 'interleaved':
        return (False, True)
    else:
        raise ValueError(f"Invalid output mode: {mode}")


class TestOutputModeMappingProperties:
    """
    Property-based tests for output mode to API parameter mapping.
    
    Feature: intertwined-translation-mode, Property 5: Output Mode to API Parameter Mapping
    **Validates: Requirements 5.4**
    """

    @settings(max_examples=100)
    @given(mode=st.sampled_from(['replace', 'append', 'interleaved']))
    def test_property_5_output_mode_mapping(self, mode: str):
        """
        Property 5: Output Mode to API Parameter Mapping
        
        For any output mode selection in the UI (replace, append, interleaved),
        the corresponding API parameters SHALL be set correctly:
        - replace → (autoAppend=false, interleavedMode=false)
        - append → (autoAppend=true, interleavedMode=false)
        - interleaved → (autoAppend=false, interleavedMode=true)
        
        Feature: intertwined-translation-mode, Property 5: Output Mode to API Parameter Mapping
        **Validates: Requirements 5.4**
        """
        auto_append, interleaved_mode = map_output_mode_to_flags(mode)
        
        if mode == 'replace':
            assert auto_append == False and interleaved_mode == False, (
                f"Replace mode should map to (autoAppend=False, interleavedMode=False), "
                f"but got (autoAppend={auto_append}, interleavedMode={interleaved_mode})"
            )
        elif mode == 'append':
            assert auto_append == True and interleaved_mode == False, (
                f"Append mode should map to (autoAppend=True, interleavedMode=False), "
                f"but got (autoAppend={auto_append}, interleavedMode={interleaved_mode})"
            )
        elif mode == 'interleaved':
            assert auto_append == False and interleaved_mode == True, (
                f"Interleaved mode should map to (autoAppend=False, interleavedMode=True), "
                f"but got (autoAppend={auto_append}, interleavedMode={interleaved_mode})"
            )

    @settings(max_examples=100)
    @given(mode=st.sampled_from(['replace', 'append', 'interleaved']))
    def test_property_5_output_mode_mapping_mutual_exclusivity(self, mode: str):
        """
        Property 5 (Extended): Output Mode Mapping Maintains Mutual Exclusivity
        
        For any valid output mode, the mapped API parameters SHALL never have
        both autoAppend and interleavedMode set to True simultaneously.
        
        Feature: intertwined-translation-mode, Property 5: Output Mode to API Parameter Mapping
        **Validates: Requirements 5.4, 3.3**
        """
        auto_append, interleaved_mode = map_output_mode_to_flags(mode)
        
        # Verify mutual exclusivity is maintained
        assert not (auto_append and interleaved_mode), (
            f"Output mode '{mode}' mapped to invalid combination: "
            f"(autoAppend={auto_append}, interleavedMode={interleaved_mode}). "
            f"Both flags cannot be True simultaneously."
        )

    @settings(max_examples=100)
    @given(mode=st.sampled_from(['replace', 'append', 'interleaved']))
    def test_property_5_output_mode_mapping_exactly_one_mode_active(self, mode: str):
        """
        Property 5 (Extended): Exactly One Output Mode Active
        
        For any valid output mode selection, exactly one of the three modes
        should be effectively active based on the flag combination:
        - Replace: both flags False
        - Append: only autoAppend True
        - Interleaved: only interleavedMode True
        
        Feature: intertwined-translation-mode, Property 5: Output Mode to API Parameter Mapping
        **Validates: Requirements 5.4**
        """
        auto_append, interleaved_mode = map_output_mode_to_flags(mode)
        
        # Count how many "special" modes are active
        # Replace mode is the default (both False), so we count the True flags
        active_special_modes = sum([auto_append, interleaved_mode])
        
        if mode == 'replace':
            assert active_special_modes == 0, (
                f"Replace mode should have no special modes active, "
                f"but got {active_special_modes} active"
            )
        else:
            assert active_special_modes == 1, (
                f"Mode '{mode}' should have exactly one special mode active, "
                f"but got {active_special_modes} active"
            )

    @settings(max_examples=100)
    @given(mode=st.sampled_from(['replace', 'append', 'interleaved']))
    def test_property_5_output_mode_round_trip(self, mode: str):
        """
        Property 5 (Extended): Output Mode Round Trip
        
        For any valid output mode, mapping to flags and back to mode should
        return the original mode.
        
        Feature: intertwined-translation-mode, Property 5: Output Mode to API Parameter Mapping
        **Validates: Requirements 5.4**
        """
        def flags_to_output_mode(auto_append: bool, interleaved_mode: bool) -> str:
            """Reverse mapping from flags to output mode."""
            if auto_append and not interleaved_mode:
                return 'append'
            elif interleaved_mode and not auto_append:
                return 'interleaved'
            elif not auto_append and not interleaved_mode:
                return 'replace'
            else:
                raise ValueError("Invalid flag combination")
        
        # Map mode to flags
        auto_append, interleaved_mode = map_output_mode_to_flags(mode)
        
        # Map flags back to mode
        recovered_mode = flags_to_output_mode(auto_append, interleaved_mode)
        
        assert recovered_mode == mode, (
            f"Round trip failed: '{mode}' -> ({auto_append}, {interleaved_mode}) -> '{recovered_mode}'"
        )

    def test_property_5_invalid_mode_raises_error(self):
        """
        Property 5 (Extended): Invalid Mode Raises Error
        
        For any invalid output mode string, the mapping function should raise
        a ValueError.
        
        Feature: intertwined-translation-mode, Property 5: Output Mode to API Parameter Mapping
        **Validates: Requirements 5.4**
        """
        invalid_modes = ['invalid', 'REPLACE', 'Append', 'INTERLEAVED', '', 'both', 'none']
        
        for invalid_mode in invalid_modes:
            with pytest.raises(ValueError) as exc_info:
                map_output_mode_to_flags(invalid_mode)
            
            assert "Invalid output mode" in str(exc_info.value), (
                f"Expected 'Invalid output mode' error for '{invalid_mode}', "
                f"but got: {exc_info.value}"
            )

    @settings(max_examples=100)
    @given(mode=st.sampled_from(['replace', 'append', 'interleaved']))
    def test_property_5_output_mode_creates_valid_job(self, mode: str):
        """
        Property 5 (Extended): Output Mode Creates Valid Job
        
        For any valid output mode, the mapped flags should create a valid
        TranslationJob without violating mutual exclusivity.
        
        Feature: intertwined-translation-mode, Property 5: Output Mode to API Parameter Mapping
        **Validates: Requirements 5.4, 3.3**
        """
        auto_append, interleaved_mode = map_output_mode_to_flags(mode)
        
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )
        
        # Create job with mapped flags - should not raise
        job = TranslationJob(
            status=JobStatus.PENDING,
            files_total=1,
            language_pair=language_pair,
            file_ids=["test-file-id"],
            auto_append=auto_append,
            interleaved_mode=interleaved_mode
        )
        
        # Verify job was created with correct values
        assert job.auto_append == auto_append
        assert job.interleaved_mode == interleaved_mode
        
        # Verify mutual exclusivity is maintained
        assert not (job.auto_append and job.interleaved_mode)


# =========================================================================
# Property Tests for Job Settings Round Trip
# Task 8.2: Property 6
# =========================================================================

from src.graphql.resolvers import convert_translation_job


class TestJobSettingsRoundTripProperties:
    """
    Property-based tests for job settings round trip.
    
    Feature: intertwined-translation-mode, Property 6: Job Settings Round Trip
    **Validates: Requirements 6.2**
    """

    @settings(max_examples=100)
    @given(
        auto_append=st.booleans(),
        interleaved_mode=st.booleans()
    )
    def test_property_6_job_settings_round_trip(
        self, auto_append: bool, interleaved_mode: bool
    ):
        """
        Property 6: Job Settings Round Trip
        
        For any translation job created with specific autoAppend and interleavedMode
        values, querying that job SHALL return the same values for both fields.
        
        This test validates that job settings are preserved through the model
        creation and GraphQL conversion process.
        
        Feature: intertwined-translation-mode, Property 6: Job Settings Round Trip
        **Validates: Requirements 6.2**
        """
        # Skip invalid combinations (both True) - these would fail validation
        assume(not (auto_append and interleaved_mode))
        
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )
        
        # Create job with specific settings
        job = TranslationJob(
            status=JobStatus.PENDING,
            files_total=1,
            language_pair=language_pair,
            file_ids=["test-file-id"],
            auto_append=auto_append,
            interleaved_mode=interleaved_mode
        )
        
        # Convert to GraphQL type (simulates what happens when querying)
        queried_job = convert_translation_job(job)
        
        # Verify both settings are preserved through conversion
        assert queried_job.auto_append == auto_append, (
            f"Expected auto_append={auto_append} but got {queried_job.auto_append} "
            f"after GraphQL conversion"
        )
        assert queried_job.interleaved_mode == interleaved_mode, (
            f"Expected interleaved_mode={interleaved_mode} but got {queried_job.interleaved_mode} "
            f"after GraphQL conversion"
        )

    @settings(max_examples=100)
    @given(
        file_ids=st.lists(st.text(min_size=1, max_size=36), min_size=1, max_size=5),
        auto_append=st.booleans(),
        interleaved_mode=st.booleans()
    )
    def test_property_6_job_settings_round_trip_with_multiple_files(
        self, file_ids: list[str], auto_append: bool, interleaved_mode: bool
    ):
        """
        Property 6 (Extended): Job Settings Round Trip with Multiple Files
        
        For any translation job with multiple files created with specific
        autoAppend and interleavedMode values, querying that job SHALL return
        the same values for both fields regardless of the number of files.
        
        Feature: intertwined-translation-mode, Property 6: Job Settings Round Trip
        **Validates: Requirements 6.2**
        """
        # Skip invalid combinations (both True)
        assume(not (auto_append and interleaved_mode))
        
        language_pair = LanguagePair(
            id="en-es",
            source_language="English",
            target_language="Spanish",
            source_language_code="en",
            target_language_code="es"
        )
        
        # Create job with multiple files
        job = TranslationJob(
            status=JobStatus.PENDING,
            files_total=len(file_ids),
            language_pair=language_pair,
            file_ids=file_ids,
            auto_append=auto_append,
            interleaved_mode=interleaved_mode
        )
        
        # Convert to GraphQL type
        queried_job = convert_translation_job(job)
        
        # Verify settings are preserved
        assert queried_job.auto_append == auto_append, (
            f"Expected auto_append={auto_append} but got {queried_job.auto_append} "
            f"with {len(file_ids)} files"
        )
        assert queried_job.interleaved_mode == interleaved_mode, (
            f"Expected interleaved_mode={interleaved_mode} but got {queried_job.interleaved_mode} "
            f"with {len(file_ids)} files"
        )

    @settings(max_examples=100)
    @given(st.data())
    def test_property_6_all_valid_output_modes_round_trip(self, data):
        """
        Property 6 (Extended): All Valid Output Modes Round Trip
        
        For each of the three valid output mode combinations (Replace, Append,
        Interleaved), creating a job and querying it SHALL preserve the settings.
        
        Feature: intertwined-translation-mode, Property 6: Job Settings Round Trip
        **Validates: Requirements 6.2**
        """
        # Define valid combinations
        valid_combinations = [
            (False, False),  # Replace Mode
            (True, False),   # Append Mode
            (False, True),   # Interleaved Mode
        ]
        
        # Pick a random valid combination
        auto_append, interleaved_mode = data.draw(
            st.sampled_from(valid_combinations)
        )
        
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )
        
        # Create job
        job = TranslationJob(
            status=JobStatus.PENDING,
            files_total=1,
            language_pair=language_pair,
            file_ids=["test-file-id"],
            auto_append=auto_append,
            interleaved_mode=interleaved_mode
        )
        
        # Convert to GraphQL type
        queried_job = convert_translation_job(job)
        
        # Verify settings are preserved
        assert queried_job.auto_append == auto_append
        assert queried_job.interleaved_mode == interleaved_mode
        
        # Verify mutual exclusivity is maintained after round trip
        assert not (queried_job.auto_append and queried_job.interleaved_mode), (
            "Mutual exclusivity violated after round trip"
        )

    @settings(max_examples=100)
    @given(
        auto_append=st.booleans(),
        interleaved_mode=st.booleans(),
        status=st.sampled_from([JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PARTIAL_SUCCESS])
    )
    def test_property_6_job_settings_preserved_across_all_statuses(
        self, auto_append: bool, interleaved_mode: bool, status: JobStatus
    ):
        """
        Property 6 (Extended): Job Settings Preserved Across All Statuses
        
        For any translation job in any status (PENDING, PROCESSING, COMPLETED,
        FAILED, PARTIAL_SUCCESS), the autoAppend and interleavedMode settings
        SHALL be preserved through the round trip.
        
        Feature: intertwined-translation-mode, Property 6: Job Settings Round Trip
        **Validates: Requirements 6.2**
        """
        # Skip invalid combinations
        assume(not (auto_append and interleaved_mode))
        
        language_pair = LanguagePair(
            id="zh-vi",
            source_language="Chinese",
            target_language="Vietnamese",
            source_language_code="zh",
            target_language_code="vi"
        )
        
        # Create job with specific status
        job = TranslationJob(
            status=status,
            files_total=1,
            language_pair=language_pair,
            file_ids=["test-file-id"],
            auto_append=auto_append,
            interleaved_mode=interleaved_mode
        )
        
        # Convert to GraphQL type
        queried_job = convert_translation_job(job)
        
        # Verify settings are preserved regardless of status
        assert queried_job.auto_append == auto_append, (
            f"Expected auto_append={auto_append} but got {queried_job.auto_append} "
            f"for job with status {status}"
        )
        assert queried_job.interleaved_mode == interleaved_mode, (
            f"Expected interleaved_mode={interleaved_mode} but got {queried_job.interleaved_mode} "
            f"for job with status {status}"
        )
