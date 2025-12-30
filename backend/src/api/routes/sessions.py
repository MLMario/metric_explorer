"""Session management API routes."""

from uuid import UUID

from fastapi import APIRouter

from ...models.schemas import SessionResponse, SuccessResponse
from ...services.session_manager import session_manager

router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session():
    """Create a new investigation session."""
    metadata = session_manager.create_session()
    return SessionResponse(
        session_id=metadata.session_id,
        status=metadata.status,
        created_at=metadata.created_at,
        expires_at=metadata.expires_at,
        file_count=metadata.file_count,
        report_ready=metadata.report_ready,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID):
    """Get session status and metadata."""
    metadata = session_manager.get_session(session_id)
    return SessionResponse(
        session_id=metadata.session_id,
        status=metadata.status,
        created_at=metadata.created_at,
        expires_at=metadata.expires_at,
        file_count=metadata.file_count,
        report_ready=metadata.report_ready,
    )


@router.delete("/{session_id}", response_model=SuccessResponse)
async def delete_session(session_id: UUID):
    """Delete a session and all its data."""
    session_manager.delete_session(session_id)
    return SuccessResponse(success=True)
