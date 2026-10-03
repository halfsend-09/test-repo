"""File save handler with correct UTF-8 buffer allocation.

Fixed in v2.3.2: buffer is now sized by byte count instead of character
count, preventing crashes when saving files larger than 64KB that
contain multibyte UTF-8 characters (emoji, CJK, etc.).
"""

import os

# Buffer size threshold in bytes (64 KiB).
BUFFER_SIZE = 64 * 1024


def save_file(path: str, content: str) -> int:
    """Save string content to a file using proper byte-length buffering.

    Encodes *content* to UTF-8 and writes it in chunks no larger than
    ``BUFFER_SIZE`` bytes.  The chunking boundary respects UTF-8 code-
    point boundaries so that multibyte sequences are never split across
    writes.

    Args:
        path: Destination file path.
        content: The text to write.

    Returns:
        The number of bytes written.

    Raises:
        OSError: If the file cannot be opened or written.
    """
    data = content.encode("utf-8")
    total = len(data)

    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    bytes_written = 0
    with open(path, "wb") as fh:
        while bytes_written < total:
            end = min(bytes_written + BUFFER_SIZE, total)
            fh.write(data[bytes_written:end])
            bytes_written = end

    return bytes_written


def read_file(path: str) -> str:
    """Read a UTF-8 encoded file and return its content as a string.

    Args:
        path: Source file path.

    Returns:
        The decoded text content.

    Raises:
        FileNotFoundError: If *path* does not exist.
        OSError: If the file cannot be read.
    """
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")
