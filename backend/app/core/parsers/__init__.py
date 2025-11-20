"""Document parsers for various file types."""
from app.core.parsers.pdf_parser import PDFParser
from app.core.parsers.docx_parser import DOCXParser
from app.core.parsers.txt_parser import TXTParser
from app.core.parsers.html_parser import HTMLParser
from app.core.parsers.base import BaseParser, ParsedDocument

__all__ = [
    "BaseParser",
    "ParsedDocument",
    "PDFParser",
    "DOCXParser",
    "TXTParser",
    "HTMLParser",
]

