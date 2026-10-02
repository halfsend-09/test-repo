"""Tests for the chunked file writer's UTF-8 boundary handling."""

import os
import tempfile

from src.file_writer import CHUNK_SIZE, _find_utf8_safe_boundary, save_file


class TestFindUtf8SafeBoundary:
    """Unit tests for _find_utf8_safe_boundary."""

    def test_boundary_on_ascii(self):
        data = b"hello world"
        assert _find_utf8_safe_boundary(data, 5) == 5

    def test_boundary_past_end(self):
        data = b"abc"
        assert _find_utf8_safe_boundary(data, 10) == 3

    def test_boundary_on_continuation_byte_2byte(self):
        # U+00E9 (é) is 0xC3 0xA9 in UTF-8
        data = b"a\xc3\xa9b"
        # Boundary at index 2 (continuation byte 0xA9) → back up to 1
        assert _find_utf8_safe_boundary(data, 2) == 1

    def test_boundary_on_continuation_byte_3byte(self):
        # U+4E16 (世) is 0xE4 0xB8 0x96
        data = b"a\xe4\xb8\x96b"
        # Boundary on second continuation byte → back up to 1
        assert _find_utf8_safe_boundary(data, 3) == 1
        # Boundary on first continuation byte → also back up to 1
        assert _find_utf8_safe_boundary(data, 2) == 1

    def test_boundary_on_continuation_byte_4byte(self):
        # U+1F600 (😀) is 0xF0 0x9F 0x98 0x80
        data = b"a\xf0\x9f\x98\x80b"
        # Boundary on any continuation byte → back up to 1
        assert _find_utf8_safe_boundary(data, 4) == 1
        assert _find_utf8_safe_boundary(data, 3) == 1
        assert _find_utf8_safe_boundary(data, 2) == 1

    def test_boundary_on_lead_byte(self):
        # Boundary exactly on the lead byte is safe
        data = b"a\xc3\xa9b"
        assert _find_utf8_safe_boundary(data, 1) == 1

    def test_empty_data(self):
        assert _find_utf8_safe_boundary(b"", 0) == 0

    def test_boundary_zero(self):
        data = b"\xc3\xa9"
        assert _find_utf8_safe_boundary(data, 0) == 0


class TestSaveFile:
    """Integration tests for save_file."""

    def test_small_ascii_file(self):
        content = "Hello, world!"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            save_file(path, content)
            with open(path, "rb") as fh:
                assert fh.read() == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_file_over_64kb_ascii_only(self):
        # 70 KB of ASCII — should save without issue
        content = "A" * (70 * 1024)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            save_file(path, content)
            with open(path, "rb") as fh:
                assert fh.read() == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_file_exactly_64kb_emoji(self):
        # Fill exactly 64 KB with emoji (U+1F600 = 4 bytes each)
        emoji = "\U0001F600"
        count = CHUNK_SIZE // 4  # 16384 emoji = 65536 bytes
        content = emoji * count
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            save_file(path, content)
            with open(path, "rb") as fh:
                result = fh.read()
            assert result == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_file_over_64kb_emoji(self):
        # 70 KB of emoji — the critical regression case
        emoji = "\U0001F600"
        byte_target = 70 * 1024
        count = byte_target // 4 + 1
        content = emoji * count
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            save_file(path, content)
            with open(path, "rb") as fh:
                result = fh.read()
            assert result == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_file_over_64kb_mixed_ascii_cjk(self):
        # Mix of ASCII and CJK — 70 KB
        cjk_block = "世界你好"  # 4 chars × 3 bytes = 12 bytes
        ascii_block = "hello "  # 6 bytes
        unit = ascii_block + cjk_block  # 18 bytes
        repeats = (70 * 1024) // 18 + 1
        content = unit * repeats
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            save_file(path, content)
            with open(path, "rb") as fh:
                result = fh.read()
            assert result == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_4byte_emoji_straddles_chunk_boundary(self):
        # Construct content so a 4-byte emoji straddles byte offset 65536.
        # Fill with ASCII up to offset 65534, then place a 4-byte emoji.
        # The emoji bytes would span offsets 65534..65537, straddling the
        # 64 KB boundary.
        prefix = "A" * (CHUNK_SIZE - 2)
        emoji = "\U0001F600"  # 4 bytes in UTF-8
        suffix = "B" * 1024
        content = prefix + emoji + suffix

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            save_file(path, content)
            with open(path, "rb") as fh:
                result = fh.read()
            assert result == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_3byte_cjk_straddles_chunk_boundary(self):
        # 3-byte CJK character straddling the 64 KB boundary.
        prefix = "A" * (CHUNK_SIZE - 1)
        cjk = "世"  # 3 bytes in UTF-8
        suffix = "B" * 1024
        content = prefix + cjk + suffix

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            save_file(path, content)
            with open(path, "rb") as fh:
                result = fh.read()
            assert result == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_content_integrity_multiple_chunks(self):
        # Verify byte-for-byte match across many chunks.
        # Use a mix that forces boundary adjustments in multiple chunks.
        emoji = "\U0001F600"
        unit = "test" + emoji  # 4 + 4 = 8 bytes
        repeats = (CHUNK_SIZE * 3) // 8 + 1  # spans ~3 chunks
        content = unit * repeats

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            save_file(path, content)
            with open(path, "rb") as fh:
                result = fh.read()
            assert result == content.encode("utf-8")
        finally:
            os.unlink(path)
