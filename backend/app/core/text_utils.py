"""Text normalization and cleaning utilities."""
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """
    Normalize text by:
    - Removing repeated headers and footers
    - Fixing whitespace and line endings
    - Cleaning control characters
    - Preserving structure

    Args:
        text: Raw text to normalize

    Returns:
        Normalized text
    """
    if not text:
        return ""

    # Step 1: Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Step 2: Remove excessive blank lines (more than 2 consecutive)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Step 3: Fix whitespace issues
    # Remove trailing whitespace from lines
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Step 4: Remove control characters except newlines and tabs
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # Step 5: Normalize unicode spaces
    text = re.sub(r"[\u2000-\u200b\u2028-\u2029\u3000]", " ", text)

    # Step 6: Fix multiple spaces (but preserve intentional spacing)
    text = re.sub(r" {2,}", " ", text)

    # Step 7: Remove repeated headers/footers
    text = remove_repeated_headers_footers(text)

    # Step 8: Final cleanup - remove excessive blank lines again
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def remove_repeated_headers_footers(text: str, min_repeats: int = 3) -> str:
    """
    Remove repeated headers and footers that appear multiple times.

    Args:
        text: Text to process
        min_repeats: Minimum number of repetitions to consider it a header/footer

    Returns:
        Text with repeated headers/footers removed
    """
    lines = text.split("\n")
    if len(lines) < min_repeats * 2:
        return text

    # Count line occurrences
    line_counts = {}
    for line in lines:
        normalized_line = line.strip().lower()
        if len(normalized_line) > 0 and len(normalized_line) < 100:  # Likely header/footer
            line_counts[normalized_line] = line_counts.get(normalized_line, 0) + 1

    # Find lines that repeat too often (likely headers/footers)
    repeated_lines = {
        line for line, count in line_counts.items()
        if count >= min_repeats and len(line) < 100
    }

    if not repeated_lines:
        return text

    # Remove repeated lines, but keep first occurrence
    seen = set()
    filtered_lines = []
    for line in lines:
        normalized = line.strip().lower()
        if normalized in repeated_lines:
            if normalized not in seen:
                seen.add(normalized)
                filtered_lines.append(line)
            # Skip subsequent occurrences
        else:
            filtered_lines.append(line)

    return "\n".join(filtered_lines)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count (rough approximation: ~4 characters per token).

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    # Rough approximation: 1 token ≈ 4 characters
    return len(text) // 4


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences (simple approach).

    Args:
        text: Text to split

    Returns:
        List of sentences
    """
    # Simple sentence splitting (can be improved with nltk or spacy)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

