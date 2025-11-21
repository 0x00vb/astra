"""FastAPI routes for analytics."""
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.db.session import get_db
from app.db.models.user import User
from app.db.models.analytics import QueryLog, DocumentOperation
from app.db.models import Document
from app.core.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# Response models
class QueryStats(BaseModel):
    """Query statistics."""
    total_queries: int
    total_tokens_used: int
    average_latency_ms: float
    average_chunks_retrieved: float
    total_answer_length: int


class DocumentStats(BaseModel):
    """Document statistics."""
    total_documents: int
    total_size_bytes: int
    total_chunks: int
    total_characters: int
    uploads_count: int
    deletes_count: int


class UsageByDate(BaseModel):
    """Usage statistics by date."""
    date: str
    queries_count: int
    documents_uploaded: int
    tokens_used: int


class UserAnalytics(BaseModel):
    """Complete user analytics."""
    user_id: str
    email: str
    query_stats: QueryStats
    document_stats: DocumentStats
    usage_by_date: List[UsageByDate]
    period_start: str
    period_end: str


@router.get("/stats", response_model=UserAnalytics)
async def get_user_analytics(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get comprehensive analytics for the current user.
    
    Args:
        days: Number of days to analyze (default: 30)
        current_user: Current authenticated user
        
    Returns:
        UserAnalytics with complete usage statistics
    """
    try:
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)
        
        # Query statistics
        query_logs = db.query(QueryLog).filter(
            and_(
                QueryLog.user_id == current_user.user_id,
                QueryLog.created_at >= period_start,
                QueryLog.created_at <= period_end
            )
        ).all()
        
        total_queries = len(query_logs)
        total_tokens = sum(q.tokens_used for q in query_logs if q.tokens_used)
        avg_latency = sum(q.total_latency_ms for q in query_logs) / total_queries if total_queries > 0 else 0
        avg_chunks = sum(q.chunks_retrieved for q in query_logs) / total_queries if total_queries > 0 else 0
        total_answer_length = sum(q.answer_length for q in query_logs)
        
        query_stats = QueryStats(
            total_queries=total_queries,
            total_tokens_used=total_tokens or 0,
            average_latency_ms=round(avg_latency, 2),
            average_chunks_retrieved=round(avg_chunks, 2),
            total_answer_length=total_answer_length,
        )
        
        # Document statistics
        documents = db.query(Document).filter(
            Document.user_id == current_user.user_id
        ).all()
        
        uploads = db.query(DocumentOperation).filter(
            and_(
                DocumentOperation.user_id == current_user.user_id,
                DocumentOperation.operation_type == "upload",
                DocumentOperation.created_at >= period_start,
                DocumentOperation.created_at <= period_end
            )
        ).all()
        
        deletes = db.query(DocumentOperation).filter(
            and_(
                DocumentOperation.user_id == current_user.user_id,
                DocumentOperation.operation_type == "delete",
                DocumentOperation.created_at >= period_start,
                DocumentOperation.created_at <= period_end
            )
        ).all()
        
        total_size = sum(d.file_size for d in documents)
        total_chunks = sum(d.total_chunks for d in documents)
        total_chars = sum(d.total_characters for d in documents)
        
        document_stats = DocumentStats(
            total_documents=len(documents),
            total_size_bytes=total_size,
            total_chunks=total_chunks,
            total_characters=total_chars,
            uploads_count=len(uploads),
            deletes_count=len(deletes),
        )
        
        # Usage by date
        usage_by_date = []
        current_date = period_start.date()
        while current_date <= period_end.date():
            date_start = datetime.combine(current_date, datetime.min.time())
            date_end = datetime.combine(current_date, datetime.max.time())
            
            day_queries = db.query(QueryLog).filter(
                and_(
                    QueryLog.user_id == current_user.user_id,
                    QueryLog.created_at >= date_start,
                    QueryLog.created_at <= date_end
                )
            ).all()
            
            day_uploads = db.query(DocumentOperation).filter(
                and_(
                    DocumentOperation.user_id == current_user.user_id,
                    DocumentOperation.operation_type == "upload",
                    DocumentOperation.created_at >= date_start,
                    DocumentOperation.created_at <= date_end
                )
            ).count()
            
            day_tokens = sum(q.tokens_used for q in day_queries if q.tokens_used)
            
            usage_by_date.append(UsageByDate(
                date=current_date.isoformat(),
                queries_count=len(day_queries),
                documents_uploaded=day_uploads,
                tokens_used=day_tokens or 0,
            ))
            
            current_date += timedelta(days=1)
        
        return UserAnalytics(
            user_id=str(current_user.user_id),
            email=current_user.email,
            query_stats=query_stats,
            document_stats=document_stats,
            usage_by_date=usage_by_date,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
        )
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}",
        )


@router.get("/queries", response_model=List[dict])
async def get_query_history(
    limit: int = Query(100, description="Maximum number of queries to return", ge=1, le=1000),
    skip: int = Query(0, description="Number of queries to skip", ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get query history for the current user.
    
    Args:
        limit: Maximum number of queries to return
        skip: Number of queries to skip
        current_user: Current authenticated user
        
    Returns:
        List of query logs
    """
    try:
        queries = db.query(QueryLog).filter(
            QueryLog.user_id == current_user.user_id
        ).order_by(QueryLog.created_at.desc()).offset(skip).limit(limit).all()
        
        return [
            {
                "id": str(q.id),
                "query_id": q.query_id,
                "query_text": q.query_text,
                "answer_length": q.answer_length,
                "chunks_retrieved": q.chunks_retrieved,
                "context_length": q.context_length,
                "retrieval_latency_ms": q.retrieval_latency_ms,
                "llm_latency_ms": q.llm_latency_ms,
                "total_latency_ms": q.total_latency_ms,
                "tokens_used": q.tokens_used,
                "model_used": q.model_used,
                "created_at": q.created_at.isoformat(),
            }
            for q in queries
        ]
    except Exception as e:
        logger.error(f"Error getting query history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get query history: {str(e)}",
        )

