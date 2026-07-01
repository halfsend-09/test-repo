"""File save module with proper UTF-8 multibyte character handling.

Writes content to disk using a chunked buffer strategy that respects
UTF-8 character boundaries, preventing crashes when multibyte sequences
(emoji, CJK, etc.) straddle the buffer boundary.
"""

import os
import tempfile

# 64 KB default buffer size
BUFFER_SIZE = 65536


def save_file(content: str, path: str) -> None:
    """Save string content to a file using chunked writes.

    Uses a temporary file + atomic rename to avoid partial writes on
    crash.  The chunking logic operates on the encoded byte stream and
    ensures that no write splits a multibyte UTF-8 sequence across
    buffer boundaries.

    Args:
        content: The text to save.
        path: Destination file path.
    """
    data = content.encode("utf-8")
    dir_name = os.path.dirname(path) or "."

    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        while offset < len(data):
            end = min(offset + BUFFER_SIZE, len(data))

            # If we are not at the end of the data, make sure we don't
            # split a multibyte UTF-8 sequence.  UTF-8 continuation
            # bytes have the bit pattern 10xxxxxx (0x80..0xBF).  Walk
            # backwards until we land on a lead byte or a single-byte
            # ASCII character.
            if end < len(data):
                while end > offset and (data[end] & 0xC0) == 0x80:
                    end -= 1

            chunk = data[offset:end]
            os.write(fd, chunk)
            offset = end
    except BaseException:
        os.close(fd)
        os.unlink(tmp_path)
        raise
    else:
        os.close(fd)
        os.replace(tmp_path, path)
