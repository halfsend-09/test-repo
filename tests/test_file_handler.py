"""Tests for the file save handler with UTF-8 multibyte support.

Covers the regression described in issue #1980: saving files larger than
64 KB that contain multibyte UTF-8 characters (emoji, CJK) must succeed
without crashing, and the file content must round-trip correctly.
"""

import pytest

from src.file_handler import BUFFER_SIZE, read_file, save_file


@pytest.fixture()
def tmp_path_file(tmp_path):
    """Return a path for a temporary file inside *tmp_path*."""
    return str(tmp_path / "output.txt")


# ── core regression tests ───────────────────────────────────────────


class TestLargeMultibyteFiles:
    """Regression tests for #1980: crash on >64 KB multibyte saves."""

    def test_save_large_emoji_file(self, tmp_path_file):
        """~70 KB of emoji (4-byte sequences) must save and read back."""
        # Each emoji is 4 UTF-8 bytes; 18_000 emojis = 72 KB.
        content = "\U0001F600" * 18_000
        assert len(content.encode("utf-8")) > BUFFER_SIZE

        written = save_file(tmp_path_file, content)
        assert written == len(content.encode("utf-8"))
        assert read_file(tmp_path_file) == content

    def test_save_large_cjk_file(self, tmp_path_file):
        """~70 KB of CJK characters (3-byte sequences) must round-trip."""
        # Each CJK char is 3 UTF-8 bytes; 24_000 chars = 72 KB.
        content = "世" * 24_000
        assert len(content.encode("utf-8")) > BUFFER_SIZE

        written = save_file(tmp_path_file, content)
        assert written == len(content.encode("utf-8"))
        assert read_file(tmp_path_file) == content

    def test_save_mixed_ascii_and_multibyte_at_boundary(self, tmp_path_file):
        """Mixed ASCII/multibyte content crossing the 64 KB boundary."""
        # 60 KB of ASCII + enough emoji to exceed the boundary.
        ascii_part = "A" * (60 * 1024)
        emoji_part = "\U0001F600" * 2_000  # 8 KB of emoji
        content = ascii_part + emoji_part
        assert len(content.encode("utf-8")) > BUFFER_SIZE

        written = save_file(tmp_path_file, content)
        assert written == len(content.encode("utf-8"))
        assert read_file(tmp_path_file) == content


# ── boundary / edge cases ───────────────────────────────────────────


class TestBoundaryCases:
    """Edge cases around the 64 KB buffer boundary."""

    def test_exactly_64kb_multibyte(self, tmp_path_file):
        """Content that encodes to exactly 64 KB of UTF-8."""
        # 3-byte chars: 64*1024 / 3 = 21845 chars + 1 byte remainder
        # Use 21845 CJK chars (65535 bytes) + 1 ASCII = 65536 bytes.
        cjk_count = (BUFFER_SIZE - 1) // 3  # 21845
        content = "世" * cjk_count + "A"
        assert len(content.encode("utf-8")) == BUFFER_SIZE

        written = save_file(tmp_path_file, content)
        assert written == BUFFER_SIZE
        assert read_file(tmp_path_file) == content

    def test_just_under_64kb_ascii(self, tmp_path_file):
        """Pure ASCII under the boundary should still work."""
        content = "A" * (BUFFER_SIZE - 1)
        written = save_file(tmp_path_file, content)
        assert written == BUFFER_SIZE - 1
        assert read_file(tmp_path_file) == content

    def test_just_over_64kb_ascii(self, tmp_path_file):
        """Pure ASCII over the boundary should still work."""
        content = "A" * (BUFFER_SIZE + 1)
        written = save_file(tmp_path_file, content)
        assert written == BUFFER_SIZE + 1
        assert read_file(tmp_path_file) == content

    def test_empty_content(self, tmp_path_file):
        """Saving empty content must produce an empty file."""
        written = save_file(tmp_path_file, "")
        assert written == 0
        assert read_file(tmp_path_file) == ""

    def test_four_byte_sequences_spanning_boundary(self, tmp_path_file):
        """4-byte UTF-8 sequences at the chunk boundary must not split."""
        # Fill to just under the boundary with ASCII, then add 4-byte chars.
        pad = "X" * (BUFFER_SIZE - 2)
        emoji = "\U0001F600" * 5  # 20 bytes crossing the boundary
        content = pad + emoji
        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE

        written = save_file(tmp_path_file, content)
        assert written == byte_len
        assert read_file(tmp_path_file) == content


# ── directory creation ──────────────────────────────────────────────


class TestDirectoryCreation:
    """Verify save_file creates parent directories."""

    def test_creates_nested_directories(self, tmp_path):
        dest = str(tmp_path / "a" / "b" / "c" / "file.txt")
        save_file(dest, "hello")
        assert read_file(dest) == "hello"
