"""
Simple MongoDB migration runner skeleton.

Migrations are Python functions registered in ``MIGRATIONS``.
Each migration runs at most once, tracked by the ``_migrations`` collection.

Usage:
    from app_name.migrations.runner import run_migrations
    await run_migrations(db_manager)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Awaitable

from loguru import logger

if TYPE_CHECKING:
    from app_name.database.mongo import MongoDBManager

# Type for a migration function: async (db) -> None
MigrationFn = Callable[["MongoDBManager"], Awaitable[None]]

# Register migrations here in order. Each tuple is (version_id, description, fn).
MIGRATIONS: list[tuple[str, str, MigrationFn]] = [
    # Example:
    # ("001", "Create users collection indexes", migration_001_user_indexes),
]


async def run_migrations(db: MongoDBManager) -> None:
    """Execute any pending migrations in order.

    Completed migrations are tracked in the ``_migrations`` collection
    so they only run once.
    """
    coll = db.get_collection("_migrations")

    for version_id, description, fn in MIGRATIONS:
        existing = await coll.find_one({"version_id": version_id})
        if existing is not None:
            logger.debug("Migration {} already applied, skipping", version_id)
            continue

        logger.info("Running migration {}: {}", version_id, description)
        try:
            await fn(db)
            await coll.insert_one(
                {
                    "version_id": version_id,
                    "description": description,
                    "applied_at": datetime.now(timezone.utc),
                }
            )
            logger.info("Migration {} completed", version_id)
        except Exception:
            logger.exception("Migration {} failed", version_id)
            raise
