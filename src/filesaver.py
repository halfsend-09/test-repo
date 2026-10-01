"""File save module with proper UTF-8 buffer handling.

Allocates write buffers based on the byte length of UTF-8 encoded content
rather than the character count, preventing buffer overflows when multibyte
characters push the byte count beyond the buffer size.
"""

import os
import tempfile

# Internal buffer size threshold: 64KB
BUFFER_SIZE = 65536


def _allocate_buffer(content):
    """Allocate a buffer large enough for the UTF-8 encoded content.

    Returns the encoded bytes and the buffer size.
    """
    encoded = content.encode("utf-8")
    byte_length = len(encoded)
    # Allocate buffer based on byte length, not character count.
    # Prior to the fix, this used len(content) (character count), which
    # underestimated the required buffer when multibyte characters were
    # present, causing a buffer overrun for content exceeding 64KB in bytes.
    buffer_size = max(BUFFER_SIZE, byte_length)
    return encoded, buffer_size


def save_file(filepath, content):
    """Save content to a file with proper UTF-8 encoding.

    Uses an atomic write pattern: writes to a temporary file first, then
    renames to the target path. The write buffer is sized by the byte
    length of the encoded content to handle multibyte UTF-8 characters
    correctly.

    Args:
        filepath: Path to the target file.
        content: String content to save.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not a string.
    """
    if not isinstance(content, str):
        raise TypeError("content must be a string")

    encoded, buffer_size = _allocate_buffer(content)

    # Validate that the buffer can hold the encoded content
    if len(encoded) > buffer_size:
        raise RuntimeError(
            f"Buffer size {buffer_size} is insufficient for "
            f"{len(encoded)} bytes of encoded content"
        )

    dir_path = os.path.dirname(filepath) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(encoded)
        os.replace(tmp_path, filepath)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_file(filepath):
    """Load and return the UTF-8 content of a file.

    Args:
        filepath: Path to the file to read.

    Returns:
        The file content as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        UnicodeDecodeError: If the file is not valid UTF-8.
    """
    with open(filepath, "rb") as f:
        return f.read().decode("utf-8")
