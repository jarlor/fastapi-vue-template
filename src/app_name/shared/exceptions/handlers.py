"""Global exception handlers for the FastAPI application.

Call ``register_exception_handlers(app)`` once during app creation to wire up
BusinessError, RequestValidationError, and unhandled Exception handlers.
"""

from __future__ import annotations

import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from app_name.shared.exceptions.business_error import BusinessError
from app_name.shared.exceptions.error_codes import ErrorCode


async def business_error_handler(_request: Request, exc: BusinessError) -> JSONResponse:
    """Return a structured 200 response for known business errors."""
    return JSONResponse(
        status_code=200,
        content={
            "code": exc.code,
            "success": False,
            "message": exc.message,
        },
    )


async def validation_error_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return a clean 422 response for request validation failures."""
    messages: list[str] = []
    for err in exc.errors():
        loc = " -> ".join(str(part) for part in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        messages.append(f"{loc}: {msg}" if loc else msg)

    return JSONResponse(
        status_code=422,
        content={
            "code": int(ErrorCode.VALIDATION_ERROR),
            "success": False,
            "message": "; ".join(messages),
        },
    )


async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected exceptions -- log traceback, return generic error."""
    logger.error("Unhandled exception:\n{}", traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "code": int(ErrorCode.UNKNOWN_ERROR),
            "success": False,
            "message": ErrorCode.UNKNOWN_ERROR.message,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""
    app.add_exception_handler(BusinessError, business_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)  # type: ignore[arg-type]
