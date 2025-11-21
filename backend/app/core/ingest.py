"""Main document ingestion pipeline."""
import uuid
import logging
import hashlib
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.db.models import Document, Chunk, DocumentStatus
from app.core.parsers import (
    PDFParser,
    DOCXParser,
    TXTParser,
    HTMLParser,
    BaseParser,
    ParsedDocument,
)
from app.core.text_utils import normalize_text, estimate_tokens
from app.core.chunking import chunk_text, Chunk as ChunkData
from app.core.embeddings import generate_embeddings
from app.core.chroma_client import add_embeddings_to_chroma, delete_embeddings_from_chroma

logger = logging.getLogger(__name__)


def _compute_chunk_hash(text: str) -> str:
    """Compute SHA256 hash for a chunk text."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


class DocumentIngestionPipeline:
    """Main pipeline for ingesting documents."""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 160,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1500,
        embedding_model: str = "all-MiniLM-L6-v2",
        collection_name: str = "documents",
    ):
        """
        Initialize ingestion pipeline.

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap size in characters
            min_chunk_size: Minimum chunk size
            max_chunk_size: Maximum chunk size
            embedding_model: SentenceTransformer model name
            collection_name: ChromaDB collection name
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.embedding_model = embedding_model
        self.collection_name = collection_name

        # Initialize parsers
        self.parsers: Dict[str, BaseParser] = {
            "pdf": PDFParser(),
            "docx": DOCXParser(),
            "txt": TXTParser(),
            "html": HTMLParser(),
        }

    def ingest_document(
        self,
        db: Session,
        file_content: bytes,
        filename: str,
        owner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ingest a document through the full pipeline.

        Args:
            db: Database session
            file_content: Raw file bytes
            filename: Original filename
            owner: Document owner (optional)

        Returns:
            Dictionary with ingestion results and stats
        """
        doc_id = uuid.uuid4()
        file_size = len(file_content)

        # Detect file type
        try:
            file_type = BaseParser.detect_file_type(filename)
        except ValueError as e:
            logger.error(f"Unsupported file type for {filename}: {e}")
            raise ValueError(f"Unsupported file type: {e}")

        # Create document record
        # If owner is provided and is a UUID string, use it as user_id
        user_id = None
        if owner:
            try:
                import uuid as uuid_lib
                user_id = uuid_lib.UUID(owner)
            except (ValueError, TypeError):
                # If owner is not a valid UUID, keep it as None (will be set by route handler)
                pass
        
        document = Document(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            user_id=user_id,  # Set user_id if owner was a valid UUID
            status=DocumentStatus.PROCESSING,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        try:
            # Step 1: Parse document
            logger.info(f"Parsing document {doc_id} ({filename})")
            parser = self.parsers.get(file_type)
            if not parser:
                raise ValueError(f"No parser available for file type: {file_type}")

            parsed_doc = parser.parse(file_content, filename)

            # Step 2: Normalize text
            logger.info(f"Normalizing text for document {doc_id}")
            normalized_text = normalize_text(parsed_doc.text)

            # Step 3: Chunk text
            logger.info(f"Chunking text for document {doc_id}")
            chunks_data = chunk_text(
                normalized_text,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                min_chunk_size=self.min_chunk_size,
                max_chunk_size=self.max_chunk_size,
                pages=parsed_doc.pages,
            )

            if not chunks_data:
                raise ValueError("No chunks created from document")

            # Step 4: Store chunks in database
            logger.info(f"Storing {len(chunks_data)} chunks in database for document {doc_id}")
            db_chunks = []
            for chunk_data in chunks_data:
                token_count = estimate_tokens(chunk_data.text)
                db_chunk = Chunk(
                    id=uuid.uuid4(),
                    doc_id=doc_id,
                    chunk_id=chunk_data.chunk_id,
                    start_char=chunk_data.start_char,
                    end_char=chunk_data.end_char,
                    page_number=chunk_data.page_number,
                    text=chunk_data.text,
                    token_count=token_count,
                )
                db_chunks.append(db_chunk)
                db.add(db_chunk)

            # Update document with stats
            total_pages = parsed_doc.metadata.get("total_pages") or (
                len(parsed_doc.pages) if parsed_doc.pages else None
            )
            document.total_pages = total_pages
            document.total_chunks = len(db_chunks)
            document.total_characters = len(normalized_text)
            document.status = DocumentStatus.INDEXED

            db.commit()

            # Step 5: Generate embeddings
            logger.info(f"Generating embeddings for {len(chunks_data)} chunks")
            chunk_texts = [chunk.text for chunk in chunks_data]
            # Use CPU-optimized batch size (8 for CPU)
            embeddings = generate_embeddings(
                chunk_texts,
                model_name=self.embedding_model,
                batch_size=8,
                show_progress_bar=False,
            )

            # Step 6: Store embeddings in ChromaDB
            logger.info(f"Storing embeddings in ChromaDB for document {doc_id}")
            metadatas = []
            ids = []
            for i, (chunk_data, db_chunk) in enumerate(zip(chunks_data, db_chunks)):
                chunk_hash = _compute_chunk_hash(chunk_data.text)
                metadata = {
                    "doc_id": str(doc_id),
                    "chunk_id": chunk_data.chunk_id,
                    "chunk_uuid": str(db_chunk.id),
                    "start_char": chunk_data.start_char,
                    "end_char": chunk_data.end_char,
                    "hash": chunk_hash,
                }
                if chunk_data.page_number is not None:
                    metadata["page_number"] = chunk_data.page_number
                metadatas.append(metadata)
                ids.append(f"{doc_id}_{chunk_data.chunk_id}")

            add_embeddings_to_chroma(
                collection_name=self.collection_name,
                embeddings=embeddings,
                texts=chunk_texts,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info(f"Successfully ingested document {doc_id}")

            return {
                "document_id": str(doc_id),
                "filename": filename,
                "status": "indexed",
                "stats": {
                    "chunks": len(chunks_data),
                    "pages": total_pages,
                    "characters": len(normalized_text),
                },
            }

        except Exception as e:
            logger.error(f"Error ingesting document {doc_id}: {e}", exc_info=True)
            # Update document status to ERROR
            document.status = DocumentStatus.ERROR
            document.error_message = str(e)
            db.commit()

            # Clean up ChromaDB embeddings if any were created
            try:
                delete_embeddings_from_chroma(self.collection_name, str(doc_id))
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup ChromaDB embeddings: {cleanup_error}")

            raise

