"""API routes registration."""

from fastapi import APIRouter

from .files import router as files_router
from .investigate import router as investigate_router
from .sessions import router as sessions_router

# Main API router
router = APIRouter()

# Register route modules
router.include_router(sessions_router, prefix="/sessions", tags=["Sessions"])
router.include_router(
    files_router, prefix="/sessions/{session_id}/files", tags=["Files"]
)
router.include_router(
    investigate_router, prefix="/sessions/{session_id}/investigate", tags=["Investigation"]
)

# Note: Additional routers will be added as they are implemented:
# - chat_router (T078-T080)
