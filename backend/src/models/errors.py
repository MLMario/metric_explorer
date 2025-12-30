"""Error models and error codes for the API."""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Machine-readable error codes."""

    # Session errors
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"

    # File errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    NO_HEADERS = "NO_HEADERS"
    MAX_FILES_EXCEEDED = "MAX_FILES_EXCEEDED"

    # Investigation errors
    NO_FILES_UPLOADED = "NO_FILES_UPLOADED"
    TARGET_METRIC_REQUIRED = "TARGET_METRIC_REQUIRED"
    METRIC_DEFINITION_REQUIRED = "METRIC_DEFINITION_REQUIRED"
    COLUMN_NOT_FOUND = "COLUMN_NOT_FOUND"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    INVESTIGATION_ALREADY_RUNNING = "INVESTIGATION_ALREADY_RUNNING"
    INVESTIGATION_NOT_COMPLETE = "INVESTIGATION_NOT_COMPLETE"

    # General errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    FILE_OPERATION_NOT_ALLOWED = "FILE_OPERATION_NOT_ALLOWED"


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: ErrorDetail


class APIError(Exception):
    """Base API exception with error code."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

    def to_response(self) -> ErrorResponse:
        """Convert to ErrorResponse model."""
        return ErrorResponse(
            error=ErrorDetail(
                code=self.code,
                message=self.message,
                details=self.details,
            )
        )


class SessionNotFoundError(APIError):
    """Session not found error."""

    def __init__(self, session_id: str):
        super().__init__(
            code=ErrorCode.SESSION_NOT_FOUND,
            message=f"Session with ID {session_id} not found",
            status_code=404,
            details={"session_id": session_id},
        )


class FileNotFoundError(APIError):
    """File not found error."""

    def __init__(self, file_id: str, session_id: str):
        super().__init__(
            code=ErrorCode.FILE_NOT_FOUND,
            message=f"File with ID {file_id} not found in session {session_id}",
            status_code=404,
            details={"file_id": file_id, "session_id": session_id},
        )


class FileTooLargeError(APIError):
    """File exceeds size limit error."""

    def __init__(self, max_size_mb: int):
        super().__init__(
            code=ErrorCode.FILE_TOO_LARGE,
            message=f"File exceeds maximum size of {max_size_mb}MB",
            status_code=400,
            details={"max_size_mb": max_size_mb},
        )


class InvalidFileTypeError(APIError):
    """Invalid file type error."""

    def __init__(self):
        super().__init__(
            code=ErrorCode.INVALID_FILE_TYPE,
            message="Only CSV files are accepted",
            status_code=400,
        )


class NoHeadersError(APIError):
    """CSV file missing headers error."""

    def __init__(self):
        super().__init__(
            code=ErrorCode.NO_HEADERS,
            message="CSV file must have a header row",
            status_code=400,
        )


class MaxFilesExceededError(APIError):
    """Max files per session exceeded error."""

    def __init__(self, max_files: int):
        super().__init__(
            code=ErrorCode.MAX_FILES_EXCEEDED,
            message=f"Maximum of {max_files} files per session",
            status_code=400,
            details={"max_files": max_files},
        )


class NoFilesUploadedError(APIError):
    """No files uploaded error."""

    def __init__(self):
        super().__init__(
            code=ErrorCode.NO_FILES_UPLOADED,
            message="At least one CSV file must be uploaded",
            status_code=400,
        )


class ColumnNotFoundError(APIError):
    """Target metric column not found error."""

    def __init__(self, column: str, available_columns: list[str]):
        super().__init__(
            code=ErrorCode.COLUMN_NOT_FOUND,
            message=f"Column '{column}' not found in any uploaded file. "
            f"Available columns: {', '.join(available_columns)}",
            status_code=400,
            details={"column": column, "available_columns": available_columns},
        )


class InvestigationAlreadyRunningError(APIError):
    """Investigation already running error."""

    def __init__(self, session_id: str):
        super().__init__(
            code=ErrorCode.INVESTIGATION_ALREADY_RUNNING,
            message="An investigation is already running for this session",
            status_code=409,
            details={"session_id": session_id},
        )


class InvestigationNotCompleteError(APIError):
    """Investigation not complete error."""

    def __init__(self):
        super().__init__(
            code=ErrorCode.INVESTIGATION_NOT_COMPLETE,
            message="Q&A is only available after investigation completes",
            status_code=409,
        )


class FileOperationNotAllowedError(APIError):
    """File operation not allowed during investigation."""

    def __init__(self, message: str):
        super().__init__(
            code=ErrorCode.FILE_OPERATION_NOT_ALLOWED,
            message=message,
            status_code=409,
        )
