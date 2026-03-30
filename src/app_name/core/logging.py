"""
Loguru logging setup.

Call ``setup_logging()`` exactly once during application startup.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_dir: str = "logs") -> None:
    """Configure loguru handlers for console and file output.

    Args:
        log_dir: Directory for log files (created automatically).
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Remove default handler so we control formatting
    logger.remove()

    # --- Console handler (coloured, INFO+) ---
    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # --- Rotating daily log file (30-day retention) ---
    logger.add(
        log_path / "app.log",
        level="DEBUG",
        rotation="00:00",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # --- Error-only file (90-day retention) ---
    logger.add(
        log_path / "error.log",
        level="ERROR",
        rotation="00:00",
        retention="90 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    logger.info("Logging initialised (log_dir={})", log_dir)
