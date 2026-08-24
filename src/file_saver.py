"""File saving module with correct UTF-8 buffer handling.

Fixed in v2.3.2: Buffer allocation now uses byte length instead of
character count, preventing overflow when multibyte UTF-8 characters
cause the byte representation to exceed the character-count-based
buffer size.
"""

# Prior to the fix, BUFFER_SIZE was compared against len(text) which
# counts characters, not bytes.  For multibyte UTF-8 content the byte
# representation can be significantly larger than the character count,
# causing writes to overflow the allocated buffer.

BUFFER_SIZE = 65536  # 64 KiB


def save_file(path: str, content: str) -> None:
    """Save *content* to *path*, handling arbitrarily large UTF-8 text.

    The function encodes *content* to UTF-8 bytes first and then writes
    in chunks sized by **byte length** so the buffer is never overflowed
    regardless of whether the text contains multibyte characters.
    """
    encoded = content.encode("utf-8")
    with open(path, "wb") as fh:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + BUFFER_SIZE]
            fh.write(chunk)
            offset += len(chunk)


def read_file(path: str) -> str:
    """Read a UTF-8 encoded file and return its text content."""
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")
