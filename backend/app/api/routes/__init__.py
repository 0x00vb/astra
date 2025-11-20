from fastapi import APIRouter
from .health import router as health_router
from .ingest import router as ingest_router

router = APIRouter()

# Include health routes
router.include_router(health_router)

# Include ingestion routes
router.include_router(ingest_router)
