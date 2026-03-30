"""
Loguru logging setup.

Call ``setup_logging()`` exactly once during application startup.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from app_name.config import LoggingConfig

# Default format shared across file handlers
_FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logging(config: LoggingConfig) -> None:
    """Configure loguru handlers for console and file output.

    All parameters are driven by ``LoggingConfig`` in config.yaml / env vars:

        logging:
          level: INFO          # console + general log level
          log_dir: logs        # directory for log files
          retention_days: 30   # general log retention
          error_retention_days: 90
          rotation: "00:00"    # daily rotation at midnight
          compression: gz      # gzip compressed archives
    """
    log_path = Path(config.log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Remove default handler so we control formatting
    logger.remove()

    # --- Console handler (coloured) ---
    logger.add(
        sys.stderr,
        level=config.level.upper(),
        format=_CONSOLE_FORMAT,
        colorize=True,
    )

    # --- Rotating daily log file ---
    logger.add(
        log_path / "app.log",
        level="DEBUG",
        rotation=config.rotation,
        retention=f"{config.retention_days} days",
        compression=config.compression,
        format=_FILE_FORMAT,
    )

    # --- Error-only file (longer retention) ---
    logger.add(
        log_path / "error.log",
        level="ERROR",
        rotation=config.rotation,
        retention=f"{config.error_retention_days} days",
        compression=config.compression,
        format=_FILE_FORMAT,
    )

    logger.info("Logging initialised (dir={}, level={})", config.log_dir, config.level)
