"""File save module with proper UTF-8 multibyte character handling.

Writes content to disk using a chunked buffer strategy that operates
on the encoded byte stream.  This prevents buffer overflows when
multibyte UTF-8 sequences (emoji, CJK, etc.) cause the byte length
to exceed the allocated buffer size.

Prior to the fix, the buffer was sized by character count, not byte
count, so multibyte content could overflow the 64 KB boundary and
trigger a segmentation fault.
"""

import os
import tempfile

# 64 KB default buffer size (in bytes)
BUFFER_SIZE = 65536


def save_file(content: str, path: str) -> None:
    """Save string content to a file using byte-aware chunked writes.

    Encodes content to UTF-8 first, then writes in chunks that never
    split a multibyte sequence.  Uses a temporary file with atomic
    rename to avoid partial writes on failure.

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

            # When not at the end of the data, avoid splitting a
            # multibyte UTF-8 sequence.  Continuation bytes have the
            # bit pattern 10xxxxxx (0x80..0xBF).  Walk backwards
            # until we reach a lead byte or single-byte character.
            if end < len(data):
                while end > offset and (data[end] & 0xC0) == 0x80:
                    end -= 1

            os.write(fd, data[offset:end])
            offset = end
    except BaseException:
        os.close(fd)
        os.unlink(tmp_path)
        raise
    else:
        os.close(fd)
        os.replace(tmp_path, path)
