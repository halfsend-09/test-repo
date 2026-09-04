"""Tests for file_saver — focused on UTF-8 multibyte boundary handling."""

import os
import tempfile

import pytest

from file_saver import BUFFER_SIZE, save_file


@pytest.fixture()
def tmp_path_file(tmp_path):
    """Return a path string inside a temporary directory."""
    return str(tmp_path / "output.txt")


class TestSaveFileUTF8Boundaries:
    """Verify that multibyte UTF-8 characters near the buffer boundary
    do not cause crashes or data corruption."""

    def test_large_file_with_emoji(self, tmp_path_file):
        """70 KB file full of emoji should save and roundtrip."""
        # Each emoji is 4 bytes in UTF-8; build >64 KB of them
        emoji = "\U0001F600"  # 😀
        content = emoji * (70 * 1024 // len(emoji.encode("utf-8")) + 1)
        assert len(content.encode("utf-8")) > BUFFER_SIZE

        save_file(content, tmp_path_file)

        with open(tmp_path_file, "r", encoding="utf-8") as fh:
            assert fh.read() == content

    def test_multibyte_straddles_buffer_boundary(self, tmp_path_file):
        """A multibyte char that would straddle byte offset 65536 must
        not be split across writes."""
        # Fill up to exactly BUFFER_SIZE - 1 bytes with ASCII, then
        # append a 4-byte emoji so the sequence crosses the boundary.
        padding = "A" * (BUFFER_SIZE - 1)
        emoji = "\U0001F4A9"  # 💩 — 4 bytes in UTF-8
        content = padding + emoji + "tail"

        save_file(content, tmp_path_file)

        with open(tmp_path_file, "r", encoding="utf-8") as fh:
            assert fh.read() == content

    def test_large_ascii_only_file(self, tmp_path_file):
        """70 KB ASCII-only file should save without issue (regression
        guard)."""
        content = "A" * (70 * 1024)

        save_file(content, tmp_path_file)

        with open(tmp_path_file, "r", encoding="utf-8") as fh:
            assert fh.read() == content

    def test_small_file_with_emoji(self, tmp_path_file):
        """60 KB file with emoji (under boundary) should save fine."""
        emoji = "\U0001F60D"  # 😍
        content = emoji * (60 * 1024 // len(emoji.encode("utf-8")))
        assert len(content.encode("utf-8")) < BUFFER_SIZE

        save_file(content, tmp_path_file)

        with open(tmp_path_file, "r", encoding="utf-8") as fh:
            assert fh.read() == content

    def test_cjk_characters_large_file(self, tmp_path_file):
        """70 KB of CJK characters (3-byte UTF-8 sequences)."""
        # U+4E00 is 3 bytes in UTF-8
        char = "\u4e00"
        content = char * (70 * 1024 // len(char.encode("utf-8")) + 1)
        assert len(content.encode("utf-8")) > BUFFER_SIZE

        save_file(content, tmp_path_file)

        with open(tmp_path_file, "r", encoding="utf-8") as fh:
            assert fh.read() == content

    def test_mixed_ascii_and_multibyte(self, tmp_path_file):
        """Mixed content crossing the buffer boundary."""
        # Build content that crosses the boundary with mixed chars
        block = "Hello 🌍 World 你好 "
        repeat = BUFFER_SIZE // len(block.encode("utf-8")) + 10
        content = block * repeat

        save_file(content, tmp_path_file)

        with open(tmp_path_file, "r", encoding="utf-8") as fh:
            assert fh.read() == content

    def test_empty_file(self, tmp_path_file):
        """Empty content should produce an empty file."""
        save_file("", tmp_path_file)

        with open(tmp_path_file, "r", encoding="utf-8") as fh:
            assert fh.read() == ""

    def test_exactly_buffer_size_ascii(self, tmp_path_file):
        """Content that is exactly BUFFER_SIZE bytes (ASCII)."""
        content = "B" * BUFFER_SIZE

        save_file(content, tmp_path_file)

        with open(tmp_path_file, "r", encoding="utf-8") as fh:
            assert fh.read() == content
