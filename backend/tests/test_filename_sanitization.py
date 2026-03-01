"""Tests for filename sanitization."""

import pytest

# Import from main module
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from main import sanitize_filename


class TestSanitizeFilename:
    """Tests for the sanitize_filename helper."""

    def test_normal_filename(self):
        assert sanitize_filename("report.xlsx") == "report.xlsx"

    def test_filename_with_spaces(self):
        assert sanitize_filename("my report.docx") == "my report.docx"

    def test_unicode_filename(self):
        assert sanitize_filename("报告.xlsx") == "报告.xlsx"

    def test_path_traversal_unix_strips_to_basename(self):
        """Path traversal is neutralized by stripping to basename."""
        assert sanitize_filename("../../etc/passwd") == "passwd"

    def test_path_traversal_windows_strips_to_basename(self):
        """Windows path traversal is neutralized by stripping to basename."""
        assert sanitize_filename("..\\..\\windows\\system32\\config") == "config"

    def test_bare_double_dot_rejected(self):
        """Bare '..' as filename is rejected."""
        assert sanitize_filename("..") is None

    def test_double_dot_in_name_rejected(self):
        assert sanitize_filename("file..txt") is None

    def test_strips_directory_components_unix(self):
        assert sanitize_filename("/usr/local/bin/file.txt") == "file.txt"

    def test_strips_directory_components_windows(self):
        assert sanitize_filename("C:\\Users\\test\\file.txt") == "file.txt"

    def test_null_byte(self):
        assert sanitize_filename("file\x00.txt") is None

    def test_control_characters(self):
        assert sanitize_filename("file\n.txt") is None
        assert sanitize_filename("file\r.txt") is None
        assert sanitize_filename("file\t.txt") is None

    def test_empty_string(self):
        assert sanitize_filename("") is None

    def test_none_input(self):
        assert sanitize_filename(None) is None

    def test_only_dots(self):
        assert sanitize_filename("...") is None

    def test_only_whitespace(self):
        assert sanitize_filename("   ") is None

    def test_leading_trailing_dots_stripped(self):
        assert sanitize_filename(".hidden") == "hidden"

    def test_leading_trailing_whitespace_stripped(self):
        assert sanitize_filename("  report.xlsx  ") == "report.xlsx"

    def test_filename_with_special_chars(self):
        """Filenames with non-control special characters should be kept."""
        assert sanitize_filename("file (1).xlsx") == "file (1).xlsx"
        assert sanitize_filename("file-name_v2.docx") == "file-name_v2.docx"

    def test_del_character(self):
        """DEL (0x7f) is a control character and should be rejected."""
        assert sanitize_filename("file\x7f.txt") is None
