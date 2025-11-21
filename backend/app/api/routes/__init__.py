from fastapi import APIRouter
from .health import router as health_router
from .ingest import router as ingest_router
from .query import router as query_router
from .auth import router as auth_router
from .analytics import router as analytics_router

router = APIRouter()

# Include auth routes (no prefix, already has /auth prefix)
router.include_router(auth_router)

# Include health routes
router.include_router(health_router)

# Include ingestion routes
router.include_router(ingest_router)

# Include query routes
router.include_router(query_router)

# Include analytics routes
router.include_router(analytics_router)
