"""Analytics models for tracking user usage."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum


class QueryLog(Base):
    """Log of user queries for analytics."""
    __tablename__ = "query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    query_id = Column(String(255), nullable=False, index=True)  # Query UUID from query endpoint
    query_text = Column(Text, nullable=False)
    answer_length = Column(Integer, nullable=False)  # Length of answer in characters
    chunks_retrieved = Column(Integer, nullable=False)
    context_length = Column(Integer, nullable=False)
    retrieval_latency_ms = Column(Float, nullable=False)
    llm_latency_ms = Column(Float, nullable=False)
    total_latency_ms = Column(Float, nullable=False)
    tokens_used = Column(Integer, nullable=True)  # Total tokens used
    model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="query_logs")

    def __repr__(self):
        return f"<QueryLog(id={self.id}, user_id={self.user_id}, query_id={self.query_id})>"


class DocumentOperation(Base):
    """Log of document operations (upload, delete, etc.) for analytics."""
    __tablename__ = "document_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False)
    operation_type = Column(String(50), nullable=False)  # upload, delete, index
    file_size = Column(Integer, nullable=True)  # Size in bytes
    chunks_count = Column(Integer, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User")
    document = relationship("Document")

    def __repr__(self):
        return f"<DocumentOperation(id={self.id}, user_id={self.user_id}, operation_type={self.operation_type})>"

