from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
import time
from typing import Dict

router = APIRouter()

@router.get("/health")
async def health_check(db: Session = Depends(get_db)) -> Dict:
    """
    Health check endpoint that verifies:
    - Application status
    - Database connectivity
    """
    start_time = time.time()

    # Check database connectivity
    try:
        # Simple query to test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
        db_response_time = round((time.time() - start_time) * 1000, 2)  # in milliseconds
    except Exception as e:
        db_status = "unhealthy"
        db_response_time = None
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "database": {
                "status": db_status,
                "response_time_ms": db_response_time
            }
        }
    }
