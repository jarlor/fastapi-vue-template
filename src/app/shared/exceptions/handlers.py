"""Global handlers for transport validation and unexpected server failures."""

from __future__ import annotations

import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from app.shared.exceptions.error_codes import ErrorCode
from app.shared.schemas.response import APIResponse


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
        content=APIResponse.error(
            code=int(ErrorCode.VALIDATION_ERROR),
            message="; ".join(messages),
        ).model_dump(),
    )


async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected exceptions -- log traceback, return generic error."""
    logger.error("Unhandled exception:\n{}", traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content=APIResponse.error(
            code=int(ErrorCode.UNKNOWN_ERROR),
            message=ErrorCode.UNKNOWN_ERROR.message,
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)  # type: ignore[arg-type]
