"""
MongoDB connection manager using Motor (async driver).

Provides:
- ``MongoDBManager``: connection pooling, retry logic, collection access.
- ``init_mongo(settings)``: module-level initialiser called during startup.
- ``get_manager()``: accessor for the singleton manager.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

if TYPE_CHECKING:
    from app_name.config import Settings

_manager: MongoDBManager | None = None


class MongoDBManager:
    """Wraps an ``AsyncIOMotorClient`` with connection pooling and helpers."""

    def __init__(
        self,
        url: str,
        database: str,
        *,
        min_pool_size: int = 5,
        max_pool_size: int = 50,
    ) -> None:
        self._url = url
        self._database_name = database
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size

    async def connect(self, *, max_retries: int = 5, base_delay: float = 1.0) -> None:
        """Connect to MongoDB with exponential backoff retry.

        Args:
            max_retries: Maximum number of connection attempts.
            base_delay: Initial delay in seconds (doubled each retry).
        """
        for attempt in range(1, max_retries + 1):
            try:
                self._client = AsyncIOMotorClient(
                    self._url,
                    minPoolSize=self._min_pool_size,
                    maxPoolSize=self._max_pool_size,
                )
                # Force a round-trip to verify the connection
                await self._client.admin.command("ping")
                self._db = self._client[self._database_name]
                logger.info(
                    "Connected to MongoDB (database={})",
                    self._database_name,
                )
                return
            except Exception:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "MongoDB connection attempt {}/{} failed, retrying in {:.1f}s",
                    attempt,
                    max_retries,
                    delay,
                )
                if attempt == max_retries:
                    raise
                await asyncio.sleep(delay)

    async def disconnect(self) -> None:
        """Close the Motor client."""
        if self._client is not None:
            self._client.close()
            logger.info("Disconnected from MongoDB")

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Return the database handle; raises if not connected."""
        if self._db is None:
            raise RuntimeError("MongoDBManager is not connected. Call connect() first.")
        return self._db

    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """Shortcut to access a named collection."""
        return self.db[name]


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

async def init_mongo(settings: Settings) -> MongoDBManager:
    """Create and connect the global MongoDBManager."""
    global _manager  # noqa: PLW0603
    _manager = MongoDBManager(
        url=settings.mongo.url,
        database=settings.mongo.database,
        min_pool_size=settings.mongo.min_pool_size,
        max_pool_size=settings.mongo.max_pool_size,
    )
    await _manager.connect()
    return _manager


def get_manager() -> MongoDBManager:
    """Return the initialised MongoDBManager singleton."""
    if _manager is None:
        raise RuntimeError("MongoDBManager not initialised. Call init_mongo() first.")
    return _manager
