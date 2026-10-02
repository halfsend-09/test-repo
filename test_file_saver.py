"""Tests for file saver with UTF-8 multibyte content exceeding 64KB."""

import os
import tempfile

from file_saver import BUFFER_SIZE, save_file


def test_save_multibyte_over_64kb():
    """Save file with multibyte UTF-8 content exceeding 64KB."""
    # Each emoji is 4 bytes in UTF-8; 20000 emojis = 80KB > 64KB
    content = "\U0001f389" * 20000
    assert len(content.encode("utf-8")) > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        filepath = f.name

    try:
        save_file(content, filepath)
        with open(filepath, encoding="utf-8") as f:
            result = f.read()
        assert result == content
    finally:
        os.unlink(filepath)


def test_save_exact_64kb_boundary_multibyte():
    """Save file with multibyte content at exactly 64KB byte boundary."""
    # 3-byte CJK character: enough chars to cross the 64KB boundary
    char_count = BUFFER_SIZE // 3 + 1
    content = "中" * char_count

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        filepath = f.name

    try:
        save_file(content, filepath)
        with open(filepath, encoding="utf-8") as f:
            result = f.read()
        assert result == content
    finally:
        os.unlink(filepath)


def test_save_mixed_content_over_64kb():
    """Save file with mixed ASCII and multibyte content crossing 64KB."""
    ascii_part = "a" * (BUFFER_SIZE - 100)
    multibyte_part = "\U0001f389" * 100  # 400 bytes in UTF-8
    content = ascii_part + multibyte_part
    assert len(content.encode("utf-8")) > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        filepath = f.name

    try:
        save_file(content, filepath)
        with open(filepath, encoding="utf-8") as f:
            result = f.read()
        assert result == content
    finally:
        os.unlink(filepath)


def test_save_ascii_over_64kb():
    """Save file with ASCII-only content over 64KB (regression check)."""
    content = "x" * (BUFFER_SIZE + 1000)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        filepath = f.name

    try:
        save_file(content, filepath)
        with open(filepath, encoding="utf-8") as f:
            result = f.read()
        assert result == content
    finally:
        os.unlink(filepath)


def test_save_varying_utf8_widths():
    """Save file with characters of varying UTF-8 widths exceeding 64KB."""
    two_byte = "é" * 5000  # 10000 bytes (2 bytes each)
    three_byte = "中" * 5000  # 15000 bytes (3 bytes each)
    four_byte = "\U0001f389" * 10500  # 42000 bytes (4 bytes each)
    content = two_byte + three_byte + four_byte  # 67000 bytes total
    assert len(content.encode("utf-8")) > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        filepath = f.name

    try:
        save_file(content, filepath)
        with open(filepath, encoding="utf-8") as f:
            result = f.read()
        assert result == content
    finally:
        os.unlink(filepath)
