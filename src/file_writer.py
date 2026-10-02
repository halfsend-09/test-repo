"""Chunked file writer with UTF-8 safety.

Writes content to files in fixed-size chunks. The chunk boundary is
adjusted so that multibyte UTF-8 sequences are never split across
chunks, preventing data corruption and crashes.
"""

CHUNK_SIZE = 65536  # 64 KB


def _find_utf8_safe_boundary(data: bytes, boundary: int) -> int:
    """Return the largest position <= *boundary* that does not split a
    multibyte UTF-8 sequence.

    UTF-8 continuation bytes have the bit pattern ``10xxxxxx``
    (``0x80``–``0xBF``).  If *boundary* falls on a continuation byte we
    walk backward until we reach the lead byte, then split just before
    the character.
    """
    if boundary >= len(data):
        return len(data)

    pos = boundary
    # Walk back over any continuation bytes (at most 3 for a 4-byte
    # sequence).
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1

    # *pos* now points at the lead byte of the character that straddles
    # the boundary — or at *boundary* itself if it was already safe.
    # If we moved, split before this character; otherwise the boundary
    # was already on a character start, so use it directly.
    if pos == boundary:
        return boundary
    return pos


def save_file(path: str, content: str) -> None:
    """Write *content* to *path* in fixed-size chunks.

    Chunks are split on UTF-8 character boundaries so that multibyte
    sequences are never torn across writes.
    """
    data = content.encode("utf-8")

    with open(path, "wb") as fh:
        offset = 0
        while offset < len(data):
            end = min(offset + CHUNK_SIZE, len(data))
            end = _find_utf8_safe_boundary(data, end)

            # Guard against zero-progress when the buffer starts on a
            # continuation byte (should not happen with valid UTF-8).
            if end == offset:
                end = offset + 1

            fh.write(data[offset:end])
            offset = end
