from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.oauth import router as oauth_router
from app.api.v1.preferences import router as preferences_router
from app.api.v1.trips import router as trips_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.calendar import router as calendar_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(oauth_router)
router.include_router(preferences_router)
router.include_router(trips_router)
router.include_router(recommendations_router)
router.include_router(calendar_router)
