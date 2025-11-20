"""TXT parser for plain text files."""
import logging
from typing import Optional
import chardet
from app.core.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class TXTParser(BaseParser):
    """Plain text file parser with encoding detection."""

    def parse(self, file_content: bytes, filename: str) -> ParsedDocument:
        """
        Parse TXT file with automatic encoding detection.

        Args:
            file_content: Raw text bytes
            filename: Original filename

        Returns:
            ParsedDocument with text and metadata
        """
        try:
            # Detect encoding
            detected = chardet.detect(file_content)
            encoding = detected.get("encoding", "utf-8")
            confidence = detected.get("confidence", 0.0)

            # Try to decode with detected encoding, fallback to utf-8
            try:
                text = file_content.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                logger.warning(
                    f"Failed to decode with {encoding}, trying utf-8 with errors='replace'"
                )
                text = file_content.decode("utf-8", errors="replace")

            if not text.strip():
                raise ValueError("File appears to be empty")

            # Extract metadata
            metadata = {
                "encoding": encoding,
                "encoding_confidence": confidence,
                "line_count": len(text.splitlines()),
                "character_count": len(text),
            }

            # Estimate pages (rough approximation: ~3000 characters per page)
            estimated_pages = max(1, len(text) // 3000)
            metadata["total_pages"] = estimated_pages

            return ParsedDocument(
                text=text,
                metadata=metadata,
                pages=None,  # TXT files don't have explicit page boundaries
            )

        except Exception as e:
            logger.error(f"Error parsing TXT {filename}: {e}")
            raise ValueError(f"Failed to parse TXT: {str(e)}")

