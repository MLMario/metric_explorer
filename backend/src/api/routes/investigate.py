"""Investigation API routes for starting investigations and retrieving reports."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends

from ...models.errors import (
    ErrorCode,
    APIError,
    InvestigationAlreadyRunningError,
    NoFilesUploadedError,
    SessionNotFoundError,
)
from ...models.schemas import (
    InvestigationRequest,
    InvestigationResponse,
    ReportResponse,
)
from ...services.session_manager import SessionManager, session_manager

router = APIRouter()


def get_session_manager() -> SessionManager:
    """Dependency to get session manager."""
    return session_manager


@router.post("", response_model=InvestigationResponse, status_code=202)
async def start_investigation(
    session_id: UUID,
    request: InvestigationRequest,
    background_tasks: BackgroundTasks,
    sm: SessionManager = Depends(get_session_manager),
):
    """Start an investigation for the session.

    Triggers the AI agent to analyze uploaded files and generate explanations.
    Requires at least one file to be uploaded.
    """
    # Get session and validate status
    metadata = sm.get_session(session_id)

    # Check if investigation is already running
    if metadata.status == "running":
        raise InvestigationAlreadyRunningError(str(session_id))

    # Check if files are uploaded
    file_count = sm.count_files(session_id)
    if file_count == 0:
        raise NoFilesUploadedError()

    # Save investigation context
    session_path = sm.get_session_path(session_id)
    context_path = session_path / "context.json"
    context_data = {
        "target_metric": request.target_metric,
        "metric_definition": request.metric_definition,
        "business_context": request.business_context,
        "baseline_period": {
            "start": request.baseline_period.start.isoformat(),
            "end": request.baseline_period.end.isoformat(),
        },
        "comparison_period": {
            "start": request.comparison_period.start.isoformat(),
            "end": request.comparison_period.end.isoformat(),
        },
        "investigation_prompt": request.investigation_prompt,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(context_path, "w") as f:
        json.dump(context_data, f, indent=2)

    # Update session status to running
    sm.update_session(session_id, status="running")

    # Import agent runner and schedule investigation in background
    from ...services.agent_runner import run_investigation

    background_tasks.add_task(run_investigation, str(session_id), str(session_path))

    return InvestigationResponse(
        status="running",
        message="Investigation started successfully",
    )


@router.get("/report", response_model=ReportResponse)
async def get_report(
    session_id: UUID,
    sm: SessionManager = Depends(get_session_manager),
):
    """Get the investigation report.

    Returns the report content if investigation is complete.
    Returns 202 if investigation is still running.
    """
    metadata = sm.get_session(session_id)
    session_path = sm.get_session_path(session_id)
    report_path = session_path / "report.md"

    # Check if investigation is still running
    if metadata.status == "running":
        raise APIError(
            code=ErrorCode.INVESTIGATION_NOT_COMPLETE,
            message="Investigation in progress",
            status_code=202,
        )

    # Check if report exists
    if not report_path.exists():
        raise APIError(
            code=ErrorCode.INVESTIGATION_NOT_COMPLETE,
            message="No report available. Investigation may have failed or not yet started.",
            status_code=404,
        )

    # Read report content
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Determine status from session
    report_status = "no_findings" if metadata.status == "no_findings" else "completed"

    return ReportResponse(
        content=content,
        generated_at=datetime.now(timezone.utc),
        status=report_status,
    )


@router.get("/report/download")
async def download_report(
    session_id: UUID,
    sm: SessionManager = Depends(get_session_manager),
):
    """Download the investigation report as a markdown file."""
    from fastapi.responses import FileResponse

    metadata = sm.get_session(session_id)
    session_path = sm.get_session_path(session_id)
    report_path = session_path / "report.md"

    # Check if report exists
    if not report_path.exists():
        raise APIError(
            code=ErrorCode.INVESTIGATION_NOT_COMPLETE,
            message="No report available for download.",
            status_code=404,
        )

    return FileResponse(
        path=report_path,
        filename="investigation_report.md",
        media_type="text/markdown",
        headers={
            "Content-Disposition": 'attachment; filename="investigation_report.md"'
        },
    )
