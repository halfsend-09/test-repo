"""Tests for file_saver – UTF-8 boundary conditions.

Covers the scenarios from the triage checklist:
  1. 64 KB ASCII-only file
  2. 64 KB file with multibyte UTF-8 (emoji / CJK)
  3. 70 KB file with multibyte UTF-8
  4. 128 KB mixed-content file
  Plus round-trip verification for each case.
"""

import os
import tempfile

from src.file_saver import save_file


def _round_trip(content: str) -> str:
    """Save *content* via save_file, read it back, return the result."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    finally:
        os.unlink(path)


def test_64kb_ascii_only():
    """64 KB of pure ASCII saves and round-trips correctly."""
    content = "A" * (64 * 1024)
    assert _round_trip(content) == content


def test_64kb_multibyte_utf8():
    """64 KB worth of *characters* that are multibyte in UTF-8."""
    # Each emoji is 4 bytes in UTF-8, so 16384 emoji = 64 KB of chars
    # but 64 KB of encoded bytes.  The old code would have allocated
    # by len() == 16384 (characters), not by encoded size.
    emoji = "\U0001F600"  # 😀 — 4 bytes in UTF-8
    count = (64 * 1024) // len(emoji.encode("utf-8"))
    content = emoji * count
    assert _round_trip(content) == content


def test_70kb_multibyte_utf8():
    """70 KB file with multibyte UTF-8 — the exact scenario from the
    bug report.  Previously triggered a segfault."""
    emoji = "\U0001F680"  # 🚀 — 4 bytes in UTF-8
    target_bytes = 70 * 1024
    count = target_bytes // len(emoji.encode("utf-8"))
    content = emoji * count
    assert len(content.encode("utf-8")) >= 64 * 1024
    assert _round_trip(content) == content


def test_128kb_mixed_content():
    """128 KB of mixed ASCII and multibyte characters."""
    block = "Hello 🌍 world! "  # 18 bytes in UTF-8 (4-byte emoji)
    reps = (128 * 1024) // len(block.encode("utf-8")) + 1
    content = block * reps
    assert len(content.encode("utf-8")) >= 128 * 1024
    assert _round_trip(content) == content


def test_empty_file():
    """Edge case: empty content should not crash."""
    assert _round_trip("") == ""


def test_single_multibyte_char():
    """Edge case: a single multibyte character."""
    assert _round_trip("漢") == "漢"
