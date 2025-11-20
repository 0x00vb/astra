"""Text chunking utilities with overlap support."""
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    text: str
    start_char: int
    end_char: int
    chunk_id: int
    page_number: Optional[int] = None


def chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 160,
    min_chunk_size: int = 100,
    max_chunk_size: int = 1500,
    pages: Optional[List[str]] = None,
) -> List[Chunk]:
    """
    Chunk text with overlap, preserving page boundaries when possible.

    Args:
        text: Text to chunk
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap size in characters (should be ~10-20% of chunk_size)
        min_chunk_size: Minimum chunk size
        max_chunk_size: Maximum chunk size
        pages: Optional list of page texts for page-level metadata

    Returns:
        List of Chunk objects
    """
    if not text or len(text.strip()) == 0:
        return []

    # Validate parameters
    if chunk_overlap >= chunk_size:
        logger.warning(f"Overlap ({chunk_overlap}) >= chunk_size ({chunk_size}), reducing overlap")
        chunk_overlap = max(1, chunk_size // 10)

    if chunk_size > max_chunk_size:
        chunk_size = max_chunk_size
    if chunk_size < min_chunk_size:
        chunk_size = min_chunk_size

    chunks: List[Chunk] = []
    text_length = len(text)
    start = 0
    chunk_id = 0

    # Build page mapping if pages are provided
    page_map = None
    if pages:
        page_map = _build_page_map(text, pages)

    while start < text_length:
        # Calculate end position
        end = min(start + chunk_size, text_length)

        # If not at the end, try to break at a sentence or word boundary
        if end < text_length:
            # Try to find a good break point (sentence end, then word boundary)
            break_point = _find_break_point(text, end, chunk_size // 4)
            if break_point > start + min_chunk_size:
                end = break_point

        # Extract chunk text
        chunk_text_content = text[start:end].strip()

        # Skip if chunk is too small (unless it's the last chunk)
        if len(chunk_text_content) < min_chunk_size and end < text_length:
            # Try to extend to meet minimum size
            extended_end = min(start + min_chunk_size, text_length)
            chunk_text_content = text[start:extended_end].strip()
            end = extended_end

        if chunk_text_content:
            # Determine page number if page mapping is available
            page_number = None
            if page_map:
                page_number = _get_page_number(start, page_map)

            chunk = Chunk(
                text=chunk_text_content,
                start_char=start,
                end_char=end,
                chunk_id=chunk_id,
                page_number=page_number,
            )
            chunks.append(chunk)
            chunk_id += 1

        # Move start position with overlap
        if end >= text_length:
            break
        start = end - chunk_overlap
        if start < 0:
            start = 0

    return chunks


def _find_break_point(text: str, position: int, lookback: int) -> int:
    """
    Find a good break point near the given position.

    Args:
        text: Full text
        position: Target position
        lookback: How far back to look for break points

    Returns:
        Best break point position
    """
    # Look for sentence endings first
    search_start = max(0, position - lookback)
    search_end = min(len(text), position + lookback)

    # Check for sentence endings
    for i in range(position, search_start - 1, -1):
        if i < len(text) - 1:
            if text[i] in ".!?" and (i == len(text) - 1 or text[i + 1].isspace()):
                return i + 1

    # Check for paragraph breaks
    for i in range(position, search_start - 1, -1):
        if i < len(text) - 1:
            if text[i] == "\n" and (i == 0 or text[i - 1] == "\n"):
                return i + 1

    # Check for word boundaries
    for i in range(position, search_start - 1, -1):
        if i < len(text) - 1:
            if text[i].isspace() and not text[i + 1].isspace():
                return i + 1

    # Fallback to original position
    return position


def _build_page_map(text: str, pages: List[str]) -> List[Tuple[int, int, int]]:
    """
    Build a mapping from character positions to page numbers.

    Args:
        text: Full concatenated text
        pages: List of page texts

    Returns:
        List of tuples (start_char, end_char, page_number)
    """
    page_map = []
    current_pos = 0

    for page_num, page_text in enumerate(pages, start=1):
        page_start = current_pos
        # Try to find the page text in the full text
        page_text_stripped = page_text.strip()
        if page_text_stripped:
            # Find approximate position
            found_pos = text.find(page_text_stripped[:min(100, len(page_text_stripped))], current_pos)
            if found_pos != -1:
                page_start = found_pos

        page_end = page_start + len(page_text_stripped)
        page_map.append((page_start, page_end, page_num))
        current_pos = page_end

    return page_map


def _get_page_number(char_position: int, page_map: List[Tuple[int, int, int]]) -> Optional[int]:
    """
    Get page number for a given character position.

    Args:
        char_position: Character position in text
        page_map: Page mapping from _build_page_map

    Returns:
        Page number or None
    """
    for start, end, page_num in page_map:
        if start <= char_position < end:
            return page_num
    # Return last page if position is beyond all pages
    if page_map:
        return page_map[-1][2]
    return None

