"""Tests for file_saver — UTF-8 multibyte boundary handling.

Covers the cases from the issue:
  1. File just under 64KB with multibyte UTF-8 chars
  2. File just over 64KB with multibyte UTF-8 chars (the crash case)
  3. File over 64KB with ASCII-only content (control)
  4. Large file (~1MB) with mixed ASCII and multibyte chars
"""

import os

import pytest

from file_saver import BUFFER_SIZE, save_file


@pytest.fixture()
def tmp_path_file(tmp_path):
    """Return a file path string inside a temporary directory."""
    return str(tmp_path / "output.txt")


class TestSaveFileUTF8Boundaries:
    """Verify multibyte UTF-8 characters near the 64KB buffer
    boundary do not cause crashes or data corruption."""

    def test_file_over_64kb_with_emoji(self, tmp_path_file):
        """70 KB file of emoji must save and roundtrip correctly.

        This is the primary crash case from the issue report.
        """
        emoji = "\U0001F600"  # U+1F600 GRINNING FACE — 4 bytes
        content = emoji * (70 * 1024 // len(emoji.encode("utf-8")) + 1)
        assert len(content.encode("utf-8")) > BUFFER_SIZE

        save_file(content, tmp_path_file)

        with open(tmp_path_file, encoding="utf-8") as fh:
            assert fh.read() == content

    def test_multibyte_straddles_buffer_boundary(self, tmp_path_file):
        """A 4-byte emoji starting at byte offset 65535 must not be
        split across buffer chunks."""
        padding = "A" * (BUFFER_SIZE - 1)
        emoji = "\U0001F4A9"  # 4 bytes in UTF-8
        content = padding + emoji + "tail"

        save_file(content, tmp_path_file)

        with open(tmp_path_file, encoding="utf-8") as fh:
            assert fh.read() == content

    def test_file_under_64kb_with_emoji(self, tmp_path_file):
        """60 KB file with emoji (under buffer size) saves fine."""
        emoji = "\U0001F60D"
        content = emoji * (60 * 1024 // len(emoji.encode("utf-8")))
        assert len(content.encode("utf-8")) < BUFFER_SIZE

        save_file(content, tmp_path_file)

        with open(tmp_path_file, encoding="utf-8") as fh:
            assert fh.read() == content

    def test_large_ascii_only_file(self, tmp_path_file):
        """70 KB ASCII-only file saves without issue (control case)."""
        content = "A" * (70 * 1024)

        save_file(content, tmp_path_file)

        with open(tmp_path_file, encoding="utf-8") as fh:
            assert fh.read() == content

    def test_cjk_characters_large_file(self, tmp_path_file):
        """70 KB of CJK characters (3-byte UTF-8 sequences)."""
        char = "一"  # U+4E00 — 3 bytes in UTF-8
        content = char * (70 * 1024 // len(char.encode("utf-8")) + 1)
        assert len(content.encode("utf-8")) > BUFFER_SIZE

        save_file(content, tmp_path_file)

        with open(tmp_path_file, encoding="utf-8") as fh:
            assert fh.read() == content

    def test_mixed_ascii_and_multibyte_large(self, tmp_path_file):
        """~1 MB mixed content crossing multiple buffer boundaries."""
        block = "Hello \U0001F30D World 你好 "
        repeat = (1024 * 1024) // len(block.encode("utf-8")) + 1
        content = block * repeat

        save_file(content, tmp_path_file)

        with open(tmp_path_file, encoding="utf-8") as fh:
            assert fh.read() == content

    def test_empty_file(self, tmp_path_file):
        """Empty content produces an empty file."""
        save_file("", tmp_path_file)

        with open(tmp_path_file, encoding="utf-8") as fh:
            assert fh.read() == ""

    def test_exactly_buffer_size_ascii(self, tmp_path_file):
        """Content exactly BUFFER_SIZE bytes (ASCII) roundtrips."""
        content = "B" * BUFFER_SIZE

        save_file(content, tmp_path_file)

        with open(tmp_path_file, encoding="utf-8") as fh:
            assert fh.read() == content
