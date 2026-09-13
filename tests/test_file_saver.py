"""Tests for the file_saver module.

Covers the fix for issue #1187: saving files larger than 64 KB that
contain UTF-8 multibyte characters no longer causes a buffer overflow.
"""

import os
import tempfile

from src.file_saver import read_file, save_file


def _tmp_path(tmp_dir: str, name: str) -> str:
    return os.path.join(tmp_dir, name)


class TestFileSaveMultibyteLarge:
    """Regression tests for the 64 KB + multibyte crash (issue #1187)."""

    def test_save_63kb_multibyte(self, tmp_path):
        """A 63 KB file with multibyte UTF-8 chars saves successfully."""
        # Each emoji is 4 bytes in UTF-8; 63 * 1024 / 4 = 16128 chars
        content = "\U0001f600" * 16128  # just under 64 KB in bytes
        path = str(tmp_path / "63kb_multibyte.txt")
        save_file(path, content)
        assert read_file(path) == content

    def test_save_65kb_multibyte(self, tmp_path):
        """A 65 KB file with multibyte UTF-8 chars saves successfully.

        This is the primary regression case — before the fix this
        triggered a segfault because the buffer was allocated using
        character count (< 64 KB) while the byte representation
        exceeded 64 KB.
        """
        # 65 * 1024 / 4 = 16640 chars → 66560 bytes
        content = "\U0001f600" * 16640
        path = str(tmp_path / "65kb_multibyte.txt")
        save_file(path, content)
        assert read_file(path) == content

    def test_save_65kb_ascii(self, tmp_path):
        """A 65 KB ASCII-only file saves successfully."""
        content = "A" * (65 * 1024)
        path = str(tmp_path / "65kb_ascii.txt")
        save_file(path, content)
        assert read_file(path) == content

    def test_save_128kb_mixed(self, tmp_path):
        """A 128 KB file with mixed ASCII and multibyte content saves."""
        # Mix of ASCII and 3-byte CJK characters
        segment = "Hello 世界 "  # "Hello 世界 " — 12 bytes
        repeat_count = (128 * 1024) // len(segment.encode("utf-8")) + 1
        content = (segment * repeat_count)[: 128 * 1024]
        # Trim to valid UTF-8 boundary by encoding/decoding
        content = content.encode("utf-8", errors="ignore").decode(
            "utf-8", errors="ignore"
        )
        path = str(tmp_path / "128kb_mixed.txt")
        save_file(path, content)
        assert read_file(path) == content

    def test_roundtrip_preserves_content(self, tmp_path):
        """Saved content matches original on re-read."""
        content = "Emoji: \U0001f680\U0001f30d CJK: 你好 ASCII: hello"
        path = str(tmp_path / "roundtrip.txt")
        save_file(path, content)
        assert read_file(path) == content

    def test_empty_file(self, tmp_path):
        """Saving an empty string produces an empty file."""
        path = str(tmp_path / "empty.txt")
        save_file(path, "")
        assert read_file(path) == ""
        assert os.path.getsize(path) == 0
