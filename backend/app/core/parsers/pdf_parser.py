"""PDF parser using pypdf."""
import io
import logging
from typing import List, Optional
from pypdf import PdfReader
from app.core.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """PDF document parser."""

    def parse(self, file_content: bytes, filename: str) -> ParsedDocument:
        """
        Parse PDF file.

        Args:
            file_content: Raw PDF bytes
            filename: Original filename

        Returns:
            ParsedDocument with text, metadata, and pages
        """
        try:
            pdf_file = io.BytesIO(file_content)
            reader = PdfReader(pdf_file)

            # Extract metadata
            metadata = {
                "title": reader.metadata.get("/Title", "") if reader.metadata else "",
                "author": reader.metadata.get("/Author", "") if reader.metadata else "",
                "subject": reader.metadata.get("/Subject", "") if reader.metadata else "",
                "creator": reader.metadata.get("/Creator", "") if reader.metadata else "",
                "producer": reader.metadata.get("/Producer", "") if reader.metadata else "",
                "creation_date": str(reader.metadata.get("/CreationDate", "")) if reader.metadata else "",
                "modification_date": str(reader.metadata.get("/ModDate", "")) if reader.metadata else "",
                "total_pages": len(reader.pages),
            }

            # Extract text from each page
            pages: List[str] = []
            full_text_parts: List[str] = []

            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        pages.append(page_text)
                        full_text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {e}")
                    pages.append("")
                    full_text_parts.append("")

            full_text = "\n\n".join(full_text_parts)

            if not full_text.strip():
                raise ValueError("No text content extracted from PDF")

            return ParsedDocument(
                text=full_text,
                metadata=metadata,
                pages=pages if pages else None,
            )

        except Exception as e:
            logger.error(f"Error parsing PDF {filename}: {e}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")

