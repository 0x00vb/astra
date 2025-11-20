"""FastAPI routes for document ingestion."""
import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import Document, Chunk, DocumentStatus
from app.core.ingest import DocumentIngestionPipeline
from app.core.indexing import EmbeddingIndexer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# Initialize ingestion pipeline
ingestion_pipeline = DocumentIngestionPipeline()

# Lazy initialization for embedding indexer (only loads model when needed)
_embedding_indexer: Optional[EmbeddingIndexer] = None


def get_embedding_indexer() -> EmbeddingIndexer:
    """Get or create embedding indexer instance (lazy initialization)."""
    global _embedding_indexer
    if _embedding_indexer is None:
        _embedding_indexer = EmbeddingIndexer()
    return _embedding_indexer


# Response models
class IngestionResponse(BaseModel):
    """Response model for document ingestion."""
    document_id: str
    filename: str
    status: str
    stats: dict


class DocumentResponse(BaseModel):
    """Response model for document listing."""
    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    chunks_count: int
    total_pages: Optional[int]
    created_at: str


class DocumentDetailResponse(BaseModel):
    """Response model for document details."""
    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    chunks_count: int
    total_pages: Optional[int]
    total_characters: int
    created_at: str
    error_message: Optional[str]


class ProgressResponse(BaseModel):
    """Response model for ingestion progress."""
    document_id: str
    progress: int
    status: str
    chunks_processed: int
    total_chunks: int


class IndexResponse(BaseModel):
    """Response model for indexing endpoint."""
    doc_id: str
    chunks_indexed: int
    total_chunks: int
    total_time_seconds: float
    collection_size: int
    metrics: dict


@router.post("/upload", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    owner: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Upload and ingest a document.

    Supports: PDF, DOCX, TXT, HTML
    Max file size: 50MB
    """
    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".doc", ".txt", ".html", ".htm"}
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}",
        )

    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error(f"Error reading file {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}",
        )

    # Check file size (50MB limit)
    max_size = 50 * 1024 * 1024  # 50MB
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of 50MB",
        )

    # Ingest document
    try:
        result = ingestion_pipeline.ingest_document(
            db=db,
            file_content=file_content,
            filename=file.filename,
            owner=owner,
        )
        return IngestionResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error ingesting document {file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest document: {str(e)}",
        )


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List all documents.

    Args:
        skip: Number of documents to skip
        limit: Maximum number of documents to return
    """
    try:
        documents = db.query(Document).offset(skip).limit(limit).all()

        return [
            DocumentResponse(
                id=str(doc.doc_id),
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                status=doc.status.value,
                chunks_count=doc.total_chunks,
                total_pages=doc.total_pages,
                created_at=doc.uploaded_at.isoformat(),
            )
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )


@router.get("/document/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    Get document details.

    Args:
        document_id: Document UUID
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )

    document = db.query(Document).filter(Document.doc_id == doc_uuid).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentDetailResponse(
        id=str(document.doc_id),
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        status=document.status.value,
        chunks_count=document.total_chunks,
        total_pages=document.total_pages,
        total_characters=document.total_characters,
        created_at=document.uploaded_at.isoformat(),
        error_message=document.error_message,
    )


@router.get("/progress/{document_id}", response_model=ProgressResponse)
async def get_ingestion_progress(
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    Get ingestion progress for a document.

    Args:
        document_id: Document UUID
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )

    document = db.query(Document).filter(Document.doc_id == doc_uuid).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Calculate progress based on status
    if document.status == DocumentStatus.INDEXED:
        progress = 100
    elif document.status == DocumentStatus.ERROR:
        progress = 0
    elif document.status == DocumentStatus.PROCESSING:
        # Estimate progress (could be improved with actual progress tracking)
        progress = 50
    else:
        progress = 0

    return ProgressResponse(
        document_id=str(document.doc_id),
        progress=progress,
        status=document.status.value,
        chunks_processed=document.total_chunks if document.status == DocumentStatus.INDEXED else 0,
        total_chunks=document.total_chunks,
    )


@router.get("/document/{document_id}/content")
async def get_document_content(
    document_id: str,
    chunk_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Get document content and metadata.

    Args:
        document_id: Document UUID
        chunk_id: Optional chunk ID to get specific chunk
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )

    document = db.query(Document).filter(Document.doc_id == doc_uuid).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if chunk_id is not None:
        # Get specific chunk
        chunk = (
            db.query(Chunk)
            .filter(Chunk.doc_id == doc_uuid, Chunk.chunk_id == chunk_id)
            .first()
        )
        if not chunk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chunk not found",
            )
        return {
            "document_id": str(document.doc_id),
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
            "page_number": chunk.page_number,
            "token_count": chunk.token_count,
        }
    else:
        # Get all chunks
        chunks = db.query(Chunk).filter(Chunk.doc_id == doc_uuid).order_by(Chunk.chunk_id).all()
        return {
            "document_id": str(document.doc_id),
            "filename": document.filename,
            "total_chunks": len(chunks),
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "page_number": chunk.page_number,
                    "token_count": chunk.token_count,
                }
                for chunk in chunks
            ],
        }


@router.post("/index", response_model=IndexResponse, status_code=status.HTTP_200_OK)
async def index_document(
    doc_id: str = Query(..., description="Document UUID to index"),
    skip_existing: bool = Query(True, description="Skip chunks already indexed in ChromaDB"),
    db: Session = Depends(get_db),
):
    """
    Generate and persist embeddings for all chunks of a document.
    
    This endpoint:
    - Retrieves all chunks for the specified document from the database
    - Generates embeddings in batches with OOM handling
    - Persists embeddings and metadata to ChromaDB
    - Returns indexing summary with metrics
    
    Args:
        doc_id: Document UUID
        skip_existing: If True, skip chunks already indexed in ChromaDB
        db: Database session
        
    Returns:
        Indexing results with metrics
    """
    try:
        doc_uuid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )
    
    # Verify document exists
    document = db.query(Document).filter(Document.doc_id == doc_uuid).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    # Check if document has chunks
    if document.total_chunks == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no chunks to index",
        )
    
    try:
        # Index document chunks (lazy initialization)
        indexer = get_embedding_indexer()
        result = indexer.index_document_chunks(
            db=db,
            doc_id=doc_uuid,
            skip_existing=skip_existing,
        )
        
        return IndexResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error indexing document {doc_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index document: {str(e)}",
        )


@router.delete("/document/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete a document and all its chunks/embeddings.

    Args:
        document_id: Document UUID
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )

    document = db.query(Document).filter(Document.doc_id == doc_uuid).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    try:
        # Delete embeddings from ChromaDB
        try:
            from app.core.chroma_client import delete_embeddings_from_chroma
            delete_embeddings_from_chroma(ingestion_pipeline.collection_name, str(doc_uuid))
        except Exception as e:
            logger.warning(f"Failed to delete ChromaDB embeddings: {e}")

        # Delete document (cascades to chunks)
        db.delete(document)
        db.commit()

        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )

