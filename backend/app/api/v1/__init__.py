"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1.catalog import router as catalog_router
from app.api.v1.coors import router as coors_router
from app.api.v1.forecasts import router as forecasts_router
from app.api.v1.health import router as health_router
from app.api.v1.models import router as models_router
from app.api.v1.status import router as status_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(status_router, tags=["status"])
router.include_router(models_router, tags=["models"])
router.include_router(coors_router)
router.include_router(catalog_router)
router.include_router(forecasts_router)
