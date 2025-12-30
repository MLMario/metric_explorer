"""Pydantic request/response schemas for the API."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    """Date range for baseline and comparison periods."""

    start: date
    end: date


class SessionCreate(BaseModel):
    """Request body for creating a session (empty - defaults used)."""

    pass


class SessionResponse(BaseModel):
    """Response for session operations."""

    session_id: UUID
    status: Literal["created", "has_files", "running", "completed", "failed", "expired"]
    created_at: datetime
    expires_at: datetime
    file_count: int = 0
    report_ready: bool = False


class FileUploadResponse(BaseModel):
    """Response after successful file upload."""

    file_id: UUID
    original_name: str
    row_count: int
    size_bytes: int


class FileMetadataUpdate(BaseModel):
    """Request body for updating file description."""

    description: str = Field(..., max_length=2000)


class InvestigationRequest(BaseModel):
    """Request body for starting an investigation."""

    target_metric: str = Field(..., max_length=100)
    metric_definition: str = Field(..., max_length=2000)
    business_context: str | None = Field(None, max_length=5000)
    baseline_period: DateRange
    comparison_period: DateRange
    investigation_prompt: str | None = Field(None, max_length=2000)


class InvestigationResponse(BaseModel):
    """Response for investigation operations."""

    status: Literal["running", "completed", "failed"]
    message: str


class ReportResponse(BaseModel):
    """Response containing the investigation report."""

    content: str
    generated_at: datetime
    status: Literal["completed", "no_findings"]


class ChatRequest(BaseModel):
    """Request body for sending a chat message."""

    message: str = Field(..., max_length=5000)


class ChatResponse(BaseModel):
    """Response for chat operations."""

    response: str
    artifacts_referenced: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    """A single chat message in history."""

    message_id: UUID
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    artifacts_referenced: list[str] = Field(default_factory=list)


class ChatHistoryResponse(BaseModel):
    """Response containing chat history."""

    messages: list[ChatMessage]


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True
