"""Tests for the file save module.

Verifies that files larger than 64KB with multibyte UTF-8 characters
are saved and reloaded correctly, covering the buffer allocation fix.
"""

import os
import tempfile

import pytest

from src.filesaver import BUFFER_SIZE, _allocate_buffer, load_file, save_file


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestAllocateBuffer:
    """Tests for the internal buffer allocation logic."""

    def test_ascii_under_buffer_size(self):
        """ASCII content under 64KB uses the default buffer size."""
        content = "a" * 1000
        encoded, buf_size = _allocate_buffer(content)
        assert buf_size == BUFFER_SIZE
        assert len(encoded) == 1000

    def test_ascii_over_buffer_size(self):
        """ASCII content over 64KB expands the buffer."""
        content = "a" * (BUFFER_SIZE + 1000)
        encoded, buf_size = _allocate_buffer(content)
        assert buf_size == len(encoded)
        assert buf_size == BUFFER_SIZE + 1000

    def test_multibyte_byte_count_exceeds_char_count(self):
        """Multibyte chars: byte count exceeds character count.

        This is the core regression test. When multibyte characters push
        the byte count past 64KB while the character count stays under,
        the buffer must be sized by byte count, not character count.
        """
        # Each emoji is 4 bytes in UTF-8. 20000 emoji = 80000 bytes > 64KB,
        # but only 20000 characters < 64K characters.
        emoji_content = "\U0001f600" * 20000
        assert len(emoji_content) == 20000  # character count
        encoded, buf_size = _allocate_buffer(emoji_content)
        assert len(encoded) == 80000  # byte count
        assert buf_size >= len(encoded)

    def test_boundary_exactly_64kb_bytes(self):
        """Content whose byte length is exactly 64KB."""
        # 2-byte UTF-8 chars to hit exactly 65536 bytes
        # U+00E9 (é) is 2 bytes in UTF-8
        char_count = BUFFER_SIZE // 2  # 32768 chars * 2 bytes = 65536 bytes
        content = "é" * char_count
        encoded, buf_size = _allocate_buffer(content)
        assert len(encoded) == BUFFER_SIZE
        assert buf_size == BUFFER_SIZE


class TestSaveFile:
    """Tests for the save_file function."""

    def test_save_ascii_small(self, tmp_dir):
        """Small ASCII file saves and reloads correctly."""
        path = os.path.join(tmp_dir, "small.txt")
        content = "Hello, world!"
        save_file(path, content)
        assert load_file(path) == content

    def test_save_large_emoji_content(self, tmp_dir):
        """~70KB of emoji text saves without crash and reloads correctly."""
        path = os.path.join(tmp_dir, "emoji_large.txt")
        # ~70KB of emoji: each emoji is 4 bytes, 17920 chars = 71680 bytes
        content = "\U0001f600" * 17920
        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE  # confirm > 64KB in bytes

        save_file(path, content)
        reloaded = load_file(path)
        assert reloaded == content

    def test_save_large_cjk_content(self, tmp_dir):
        """~70KB of CJK characters saves and reloads correctly."""
        path = os.path.join(tmp_dir, "cjk_large.txt")
        # CJK chars are 3 bytes each. 23894 chars = 71682 bytes > 64KB
        content = "世" * 23894
        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE

        save_file(path, content)
        reloaded = load_file(path)
        assert reloaded == content

    def test_save_mixed_ascii_multibyte_crossing_boundary(self, tmp_dir):
        """Mixed ASCII + multibyte where byte count crosses 64KB but char count does not."""
        path = os.path.join(tmp_dir, "mixed.txt")
        # 30000 ASCII chars (30000 bytes) + 10000 emoji (40000 bytes) = 70000 bytes > 64KB
        # but only 40000 characters < 64K characters
        content = "a" * 30000 + "\U0001f600" * 10000
        byte_len = len(content.encode("utf-8"))
        char_count = len(content)
        assert byte_len > BUFFER_SIZE
        assert char_count < BUFFER_SIZE

        save_file(path, content)
        reloaded = load_file(path)
        assert reloaded == content

    def test_save_exactly_64kb_multibyte(self, tmp_dir):
        """Exactly 64KB of multibyte content (boundary case)."""
        path = os.path.join(tmp_dir, "boundary.txt")
        # 2-byte chars to hit exactly 65536 bytes
        char_count = BUFFER_SIZE // 2
        content = "é" * char_count
        assert len(content.encode("utf-8")) == BUFFER_SIZE

        save_file(path, content)
        reloaded = load_file(path)
        assert reloaded == content

    def test_save_large_ascii_over_64kb(self, tmp_dir):
        """Large ASCII file (>64KB) saves correctly (no multibyte)."""
        path = os.path.join(tmp_dir, "ascii_large.txt")
        content = "x" * (BUFFER_SIZE + 5000)
        save_file(path, content)
        reloaded = load_file(path)
        assert reloaded == content

    def test_save_rejects_non_string(self, tmp_dir):
        """save_file raises TypeError for non-string content."""
        path = os.path.join(tmp_dir, "bad.txt")
        with pytest.raises(TypeError, match="content must be a string"):
            save_file(path, b"bytes")

    def test_save_atomic_no_partial_on_failure(self, tmp_dir):
        """If saving fails, the target file is not left in a partial state."""
        path = os.path.join(tmp_dir, "no_partial.txt")
        save_file(path, "original content")

        # Try to save to a path where the temp file dir doesn't exist
        bad_path = os.path.join(tmp_dir, "nonexistent_dir", "file.txt")
        with pytest.raises(OSError):
            save_file(bad_path, "new content")

        # Original file should be unchanged
        assert load_file(path) == "original content"


class TestLoadFile:
    """Tests for the load_file function."""

    def test_load_nonexistent_file(self):
        """load_file raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            load_file("/tmp/nonexistent_file_abc123.txt")

    def test_load_utf8_content(self, tmp_dir):
        """load_file correctly decodes UTF-8 content."""
        path = os.path.join(tmp_dir, "utf8.txt")
        content = "Hello \U0001f600 World 世界"
        save_file(path, content)
        assert load_file(path) == content
