"""Global error handler middleware."""

import logging
import traceback

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ...models.errors import APIError, ErrorCode, ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next) -> Response:
    """Global middleware to handle all exceptions and return consistent error responses."""
    try:
        return await call_next(request)
    except APIError as e:
        # Handle our custom API errors
        logger.warning(f"API error: {e.code} - {e.message}")
        return JSONResponse(
            status_code=e.status_code,
            content=e.to_response().model_dump(),
        )
    except ValidationError as e:
        # Handle Pydantic validation errors
        logger.warning(f"Validation error: {e}")
        error_response = ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.VALIDATION_ERROR,
                message="Request validation failed",
                details={"errors": e.errors()},
            )
        )
        return JSONResponse(
            status_code=422,
            content=error_response.model_dump(),
        )
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error: {e}\n{traceback.format_exc()}")
        error_response = ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred",
                details={"type": type(e).__name__} if logger.isEnabledFor(logging.DEBUG) else None,
            )
        )
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(),
        )
