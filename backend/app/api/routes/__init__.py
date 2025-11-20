from fastapi import APIRouter
from .health import router as health_router
from .ingest import router as ingest_router
from .query import router as query_router

router = APIRouter()

# Include health routes
router.include_router(health_router)

# Include ingestion routes
router.include_router(ingest_router)

# Include query routes
router.include_router(query_router)
