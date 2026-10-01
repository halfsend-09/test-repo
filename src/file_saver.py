"""File saving module with proper UTF-8 buffer handling.

Allocates write buffers based on encoded byte length rather than
character count so that multibyte UTF-8 sequences do not overflow
the buffer.
"""

CHUNK_SIZE = 64 * 1024  # 64 KB


def save_file(path: str, content: str) -> None:
    """Write *content* to *path* in chunked UTF-8 mode.

    The content is encoded to UTF-8 first, then written in chunks
    whose size is measured in **bytes** (not characters).  This
    avoids overflowing the internal buffer when the text contains
    multibyte characters such as emoji or CJK ideographs.
    """
    encoded = content.encode("utf-8")
    with open(path, "wb") as fh:
        for offset in range(0, len(encoded), CHUNK_SIZE):
            fh.write(encoded[offset : offset + CHUNK_SIZE])
