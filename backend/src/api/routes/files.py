"""File management API routes."""

from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile

from ...models.errors import FileNotFoundError as FileNotFoundAPIError
from ...models.errors import FileOperationNotAllowedError
from ...models.schemas import FileMetadataUpdate, FileUploadResponse, SuccessResponse
from ...services.file_handler import file_handler
from ...services.session_manager import session_manager

router = APIRouter()


@router.post("", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    session_id: UUID,
    file: UploadFile = File(...),
    description: str = Form(..., max_length=2000),
):
    """
    Upload a CSV file to the session.

    The file must be a valid CSV with headers, under 50MB.
    A description is required to explain what data the file contains.
    """
    # Validate session exists and is not running
    session = session_manager.get_session(session_id)
    if session.status == "running":
        raise FileOperationNotAllowedError(
            "Cannot upload files while investigation is running"
        )

    # Read file content
    content = await file.read()

    # Save file with validation
    metadata = await file_handler.save_file(
        session_id=session_id,
        filename=file.filename or "unnamed.csv",
        content=content,
        description=description,
    )

    return FileUploadResponse(
        file_id=metadata.file_id,
        original_name=metadata.original_name,
        row_count=metadata.row_count,
        size_bytes=metadata.size_bytes,
    )


@router.put("/{file_id}", response_model=SuccessResponse)
async def update_file_description(
    session_id: UUID,
    file_id: UUID,
    body: FileMetadataUpdate,
):
    """Update the description for an uploaded file."""
    # Validate session exists and is not running
    session = session_manager.get_session(session_id)
    if session.status == "running":
        raise FileOperationNotAllowedError(
            "Cannot modify files while investigation is running"
        )

    metadata = file_handler.update_file_description(
        session_id=session_id,
        file_id=file_id,
        description=body.description,
    )

    if metadata is None:
        raise FileNotFoundAPIError(str(file_id), str(session_id))

    return SuccessResponse(success=True)


@router.delete("/{file_id}", response_model=SuccessResponse)
async def delete_file(
    session_id: UUID,
    file_id: UUID,
):
    """Remove a file from the session."""
    # Validate session exists and is not running
    session = session_manager.get_session(session_id)
    if session.status == "running":
        raise FileOperationNotAllowedError(
            "Cannot delete files while investigation is running"
        )

    deleted = file_handler.delete_file(session_id=session_id, file_id=file_id)

    if not deleted:
        raise FileNotFoundAPIError(str(file_id), str(session_id))

    return SuccessResponse(success=True)
