"""Database models for document ingestion."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum


class DocumentStatus(str, enum.Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    ERROR = "error"


class Document(Base):
    """Document model."""
    __tablename__ = "documents"

    doc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, docx, txt, html
    file_size = Column(Integer, nullable=False)  # Size in bytes
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    owner = Column(String(255), nullable=True)  # For future auth integration
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    total_pages = Column(Integer, nullable=True)  # Number of pages (if available)
    total_chunks = Column(Integer, default=0, nullable=False)
    total_characters = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)  # Error details if status is ERROR

    # Relationships
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(doc_id={self.doc_id}, filename={self.filename}, status={self.status})>"


class Chunk(Base):
    """Chunk model."""
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(Integer, nullable=False)  # Sequential chunk number within document
    start_char = Column(Integer, nullable=False)  # Character offset start
    end_char = Column(Integer, nullable=False)  # Character offset end
    page_number = Column(Integer, nullable=True)  # Page number (if available)
    text = Column(Text, nullable=False)  # Chunk text content
    token_count = Column(Integer, nullable=True)  # Estimated token count

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<Chunk(id={self.id}, doc_id={self.doc_id}, chunk_id={self.chunk_id})>"

