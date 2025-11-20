"""HTML parser using BeautifulSoup."""
import logging
from typing import Optional
from bs4 import BeautifulSoup
from app.core.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class HTMLParser(BaseParser):
    """HTML document parser."""

    def parse(self, file_content: bytes, filename: str) -> ParsedDocument:
        """
        Parse HTML file.

        Args:
            file_content: Raw HTML bytes
            filename: Original filename

        Returns:
            ParsedDocument with text and metadata
        """
        try:
            # Detect encoding and decode
            try:
                text_content = file_content.decode("utf-8")
            except UnicodeDecodeError:
                # Try with chardet if utf-8 fails
                import chardet
                detected = chardet.detect(file_content)
                encoding = detected.get("encoding", "utf-8")
                text_content = file_content.decode(encoding, errors="replace")

            # Parse with BeautifulSoup
            soup = BeautifulSoup(text_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()

            # Extract metadata from head
            metadata = {}
            if soup.head:
                title_tag = soup.head.find("title")
                if title_tag:
                    metadata["title"] = title_tag.get_text().strip()

                meta_tags = soup.head.find_all("meta")
                for meta in meta_tags:
                    name = meta.get("name") or meta.get("property") or meta.get("http-equiv")
                    content = meta.get("content")
                    if name and content:
                        metadata[f"meta_{name.lower()}"] = content

            # Extract text content
            text = soup.get_text(separator="\n", strip=True)

            # Clean up excessive whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)

            if not text.strip():
                raise ValueError("No text content extracted from HTML")

            # Estimate pages (rough approximation: ~3000 characters per page)
            estimated_pages = max(1, len(text) // 3000)
            metadata["total_pages"] = estimated_pages

            return ParsedDocument(
                text=text,
                metadata=metadata,
                pages=None,  # HTML doesn't have explicit page boundaries
            )

        except Exception as e:
            logger.error(f"Error parsing HTML {filename}: {e}")
            raise ValueError(f"Failed to parse HTML: {str(e)}")

