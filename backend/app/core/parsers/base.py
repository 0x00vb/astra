"""Base parser interface."""
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ParsedDocument:
    """Parsed document data structure."""
    text: str
    metadata: dict
    pages: Optional[List[str]] = None  # List of page texts (for page-level metadata)


class BaseParser(ABC):
    """Base parser interface for all document parsers."""

    @abstractmethod
    def parse(self, file_content: bytes, filename: str) -> ParsedDocument:
        """
        Parse document content.

        Args:
            file_content: Raw file bytes
            filename: Original filename

        Returns:
            ParsedDocument with text and metadata

        Raises:
            ValueError: If file cannot be parsed
        """
        pass

    @staticmethod
    def detect_file_type(filename: str) -> str:
        """Detect file type from filename extension."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        if ext in ["pdf"]:
            return "pdf"
        elif ext in ["docx", "doc"]:
            return "docx"
        elif ext in ["txt", "text"]:
            return "txt"
        elif ext in ["html", "htm"]:
            return "html"
        else:
            raise ValueError(f"Unsupported file type: {ext}")

