"""Uvicorn runner for local development."""

from __future__ import annotations

import uvicorn

from app_name.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app_name.main:create_app",
        factory=True,
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        log_level=settings.logging.level.lower(),
    )


if __name__ == "__main__":
    main()
