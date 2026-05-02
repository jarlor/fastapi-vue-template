#!/usr/bin/env python3
"""Check the template runtime baseline exposed through Poe."""

from __future__ import annotations

import asyncio
import sys

from httpx import ASGITransport, AsyncClient

from app_name.config import Settings
from app_name.main import create_app


def runtime_settings() -> Settings:
    """Return deterministic settings for runtime harness checks."""
    return Settings(
        app_name="runtime_harness",
        debug=True,
        server={"host": "127.0.0.1", "port": 8665, "reload": False},
        cors={
            "allow_origins": ["http://localhost:8006"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        },
        frontend={"base_url": "http://localhost:8006"},
        logging={
            "level": "WARNING",
            "log_dir": "logs",
            "retention_days": 1,
            "error_retention_days": 1,
            "rotation": "00:00",
            "compression": "gz",
        },
    )


async def check_runtime_baseline() -> list[str]:
    """Return runtime baseline failures."""
    settings = runtime_settings()
    app = create_app(settings=settings)
    failures: list[str] = []

    if app.state.settings is not settings:
        failures.append("create_app(settings=...) must preserve injected settings on app.state.settings")

    if hasattr(app.state, "registry"):
        failures.append("create_app() must not build the registry before lifespan startup")

    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://runtime-harness") as client,
        app.router.lifespan_context(app),
    ):
        if app.state.registry.settings is not settings:
            failures.append("lifespan startup must build a registry from injected settings")

        root_health = await client.get("/health")
        if root_health.status_code != 200:
            failures.append("/health must return 200")
        elif root_health.json().get("data", {}).get("status") != "ok":
            failures.append("/health must return the standard APIResponse health envelope")

        versioned_health = await client.get("/api/v1/health")
        if versioned_health.status_code != 200:
            failures.append("/api/v1/health must return 200")
        elif versioned_health.json().get("data", {}).get("status") != "ok":
            failures.append("/api/v1/health must return the standard APIResponse health envelope")

    return failures


def main() -> int:
    """CLI entry point."""
    failures = asyncio.run(check_runtime_baseline())
    if not failures:
        return 0

    print("runtime baseline failed:", file=sys.stderr)
    for failure in failures:
        print(f"- {failure}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
