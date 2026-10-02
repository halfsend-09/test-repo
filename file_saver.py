"""File saver module with correct UTF-8 buffer handling.

Fixed in v2.3.2: Buffer allocation now uses byte length instead of
character count, preventing buffer overflows when saving files larger
than 64KB that contain UTF-8 multibyte characters.
"""

BUFFER_SIZE = 65536  # 64KB


def save_file(content: str, filepath: str) -> None:
    """Save content to a file using byte-length buffer allocation.

    Encodes content to UTF-8 bytes first, then writes in chunks sized
    by byte length (not character count). This correctly handles
    multibyte characters (emoji, CJK, etc.) that occupy 2-4 bytes
    each in UTF-8 encoding.

    Args:
        content: The text content to save.
        filepath: Destination file path.
    """
    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    with open(filepath, "wb") as f:
        offset = 0
        while offset < byte_length:
            chunk = encoded[offset : offset + BUFFER_SIZE]
            f.write(chunk)
            offset += len(chunk)
