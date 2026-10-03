"""File save module with correct UTF-8 buffer handling.

Fixed in response to issue #1969: the previous implementation used
len(content) (character count) to allocate the write buffer, which
underflows for multibyte UTF-8 sequences and causes a segfault when
the encoded byte length exceeds the 64KB buffer boundary.

The fix uses len(content.encode('utf-8')) (byte count) so the buffer
is always large enough for the encoded data.
"""

BUFFER_SIZE = 65536  # 64KB


def save_file(path, content):
    """Save content to a file, handling UTF-8 multibyte characters correctly.

    The buffer is sized based on the byte length of the UTF-8-encoded
    content, not the character count. This prevents overflow when
    multibyte characters (emoji, CJK, etc.) cause the encoded size
    to exceed the character count.

    Args:
        path: Destination file path.
        content: String content to write.

    Returns:
        Number of bytes written.
    """
    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    with open(path, "wb") as f:
        offset = 0
        while offset < byte_length:
            chunk = encoded[offset : offset + BUFFER_SIZE]
            f.write(chunk)
            offset += len(chunk)

    return byte_length
