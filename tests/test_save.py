"""Tests for file save with UTF-8 boundary conditions.

Covers the cases from issue #1969 triage:
  - ~63KB file with multibyte UTF-8 chars (below boundary)
  - ~70KB file with multibyte UTF-8 chars (above boundary, was crashing)
  - ~70KB file with ASCII only (above boundary, always worked)
  - ~70KB file with mixed ASCII + multibyte (above boundary)
"""

import os
import tempfile

from src.save import save_file


def _make_multibyte_content(target_bytes):
    """Build a string whose UTF-8 encoding is approximately target_bytes."""
    # Each emoji is 4 bytes in UTF-8
    count = target_bytes // 4
    return "\U0001f600" * count


def _make_ascii_content(target_bytes):
    """Build an ASCII string of approximately target_bytes."""
    return "A" * target_bytes


def _make_mixed_content(target_bytes):
    """Build a mixed ASCII + multibyte string of approximately target_bytes."""
    # Half ASCII (1 byte each), half emoji (4 bytes each)
    ascii_bytes = target_bytes // 2
    emoji_bytes = target_bytes - ascii_bytes
    emoji_count = emoji_bytes // 4
    return "A" * ascii_bytes + "\U0001f600" * emoji_count


def test_save_small_multibyte():
    """~63KB file with multibyte UTF-8 chars — below 64KB boundary."""
    content = _make_multibyte_content(63 * 1024)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        path = f.name
    try:
        written = save_file(path, content)
        assert written > 0
        with open(path, "rb") as f:
            data = f.read()
        assert data == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_large_multibyte():
    """~70KB file with multibyte UTF-8 chars — above boundary, was crashing."""
    content = _make_multibyte_content(70 * 1024)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        path = f.name
    try:
        written = save_file(path, content)
        assert written > 0
        with open(path, "rb") as f:
            data = f.read()
        assert data == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_large_ascii():
    """~70KB file with ASCII only — above boundary, always worked."""
    content = _make_ascii_content(70 * 1024)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        path = f.name
    try:
        written = save_file(path, content)
        assert written == 70 * 1024
        with open(path, "rb") as f:
            data = f.read()
        assert data == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_large_mixed():
    """~70KB file with mixed ASCII + multibyte — above boundary."""
    content = _make_mixed_content(70 * 1024)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        path = f.name
    try:
        written = save_file(path, content)
        assert written > 0
        with open(path, "rb") as f:
            data = f.read()
        assert data == content.encode("utf-8")
    finally:
        os.unlink(path)
