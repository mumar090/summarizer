_SEPARATORS = ("\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ")


def chunk_text(text: str, max_chars: int, overlap: int = 0) -> list[str]:
    """Split text into chunks of at most `max_chars`, preferring natural boundaries.

    Each chunk ends at the latest paragraph/sentence/word break in its second half, and the next
    chunk starts `overlap` characters earlier so context that straddles a boundary is not lost.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if not 0 <= overlap < max_chars // 2:
        raise ValueError("overlap must be between 0 and max_chars / 2")

    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            end = _find_break(text, start + max_chars // 2, end)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        next_start = end - overlap
        if overlap:
            # Start the overlap on a word boundary rather than mid-word.
            space = text.find(" ", next_start, end)
            if space != -1:
                next_start = space + 1
        start = next_start if next_start > start else end
    return chunks


def _find_break(text: str, lo: int, hi: int) -> int:
    for sep in _SEPARATORS:
        idx = text.rfind(sep, lo, hi)
        if idx != -1:
            return idx + len(sep)
    return hi
