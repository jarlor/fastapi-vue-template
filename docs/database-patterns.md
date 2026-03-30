# 数据库集成指南

---

## 选择数据库

| 数据库 | 推荐场景 | Python 驱动 |
|---|---|---|
| **MongoDB** | 文档型数据、快速迭代、schema 灵活 | Motor (async) |
| **PostgreSQL** | 关系型数据、复杂查询、事务完整性 | asyncpg + SQLAlchemy 2.0 |
| **SQLite** | 本地开发、嵌入式、单用户工具 | aiosqlite + SQLAlchemy 2.0 |

本模板不内置任何数据库依赖。按以下指南选择并集成。

---

## MongoDB + Motor 集成

### 1. 安装依赖

```bash
uv add motor
```

### 2. 创建 MongoDBManager

在 `src/app_name/database/` 下新建 `mongo.py`:

```python
# src/app_name/database/mongo.py
"""Async MongoDB connection manager with retry and graceful shutdown."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

if TYPE_CHECKING:
    from app_name.config import MongoConfig


class MongoDBManager:
    """Manages a single Motor client with retry-on-connect and collection access."""

    def __init__(self) -> None:
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

    # -- lifecycle --------------------------------------------------------

    async def connect(
        self,
        config: MongoConfig,
        *,
        max_retries: int = 5,
        retry_delay: float = 2.0,
    ) -> None:
        """Connect to MongoDB with exponential back-off retry."""
        for attempt in range(1, max_retries + 1):
            try:
                self._client = AsyncIOMotorClient(
                    config.url,
                    minPoolSize=config.min_pool_size,
                    maxPoolSize=config.max_pool_size,
                )
                # Force a round-trip to verify the connection is alive.
                await self._client.admin.command("ping")
                self._db = self._client[config.database]
                logger.info(
                    "MongoDB connected (db={}), attempt {}/{}",
                    config.database,
                    attempt,
                    max_retries,
                )
                return
            except Exception:
                logger.warning(
                    "MongoDB connect attempt {}/{} failed, retrying in {}s ...",
                    attempt,
                    max_retries,
                    retry_delay,
                )
                if attempt == max_retries:
                    raise
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # exponential back-off

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB disconnected")

    # -- access -----------------------------------------------------------

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._db is None:
            raise RuntimeError("MongoDBManager is not connected. Call connect() first.")
        return self._db

    def get_collection(self, name: str) -> AsyncIOMotorDatabase:
        """Shortcut: ``manager.get_collection('users')``."""
        return self.db[name]


# Module-level singleton -------------------------------------------------

_manager = MongoDBManager()


async def init_mongo(config: MongoConfig) -> None:
    """Call once during lifespan startup."""
    await _manager.connect(config)


async def close_mongo() -> None:
    """Call once during lifespan shutdown."""
    await _manager.disconnect()


def get_manager() -> MongoDBManager:
    """Return the singleton manager for use in service factories."""
    return _manager
```

### 3. 添加 MongoConfig

在 `src/app_name/config.py` 的 nested config 区域添加:

```python
class MongoConfig(BaseModel):
    url: str = "mongodb://localhost:27017"
    database: str = "app_name"
    min_pool_size: int = 5
    max_pool_size: int = 50
```

在 `Settings` 类中添加字段:

```python
class Settings(BaseSettings):
    mongodb: MongoConfig = MongoConfig()
    # ... 其他字段
```

### 4. config.yaml 添加 mongodb 段

```yaml
mongodb:
  url: "mongodb://localhost:27017"
  database: "app_name"
```

### 5. .env 添加连接串

```dotenv
# MongoDB (覆盖 config.yaml 中的默认值)
MONGODB__URL=mongodb://localhost:27017
```

> 嵌套分隔符是 `__`，对应 `mongodb.url`。

### 6. main.py lifespan 中初始化

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app_name.config import get_settings
    from app_name.core.logging import setup_logging
    from app_name.core.service_factory import build_registry
    from app_name.database.mongo import close_mongo, init_mongo   # <-- 新增

    settings = get_settings()
    setup_logging(settings.logging.log_dir)

    # 连接 MongoDB
    await init_mongo(settings.mongodb)                            # <-- 新增

    registry = build_registry(settings=settings)
    app.state.registry = registry

    logger.info("Application startup complete")
    yield

    # Shutdown
    await close_mongo()                                           # <-- 新增
    logger.info("Shutdown complete")
```

### 7. AppRegistry 添加 db 字段

```python
# src/app_name/core/registry.py
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app_name.config import Settings
    from app_name.database.mongo import MongoDBManager
    from app_name.shared.events.bus import InProcessEventBus


@dataclass(slots=True)
class AppRegistry:
    settings: Settings
    event_bus: InProcessEventBus
    db: MongoDBManager              # <-- 新增
```

在 `service_factory.py` 的 `build_registry()` 中传入:

```python
from app_name.database.mongo import get_manager

def build_registry(*, settings: Settings) -> AppRegistry:
    event_bus = InProcessEventBus()
    registry = AppRegistry(
        settings=settings,
        event_bus=event_bus,
        db=get_manager(),           # <-- 新增
    )
    return registry
```

### 8. 在上下文中创建 Repository

参考 [walkthrough.md](walkthrough.md) Step 5，在你的上下文 `infrastructure/repositories/` 下创建 MongoDB 实现:

```python
# contexts/<your_context>/infrastructure/repositories/mongo_xxx_repo.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


class MongoXxxRepository:
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    async def find_by_id(self, doc_id: str) -> dict | None:
        return await self._col.find_one({"_id": doc_id})

    async def save(self, doc: dict) -> None:
        await self._col.replace_one(
            {"_id": doc["_id"]}, doc, upsert=True,
        )
```

路由中通过 `registry.db.get_collection("xxx")` 获取 collection 并注入到 Repository。

---

## PostgreSQL + SQLAlchemy 集成

### 1. 安装依赖

```bash
uv add "sqlalchemy[asyncio]" asyncpg
```

### 2. AsyncEngine + AsyncSession 模式

```python
# src/app_name/database/postgres.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


class PostgresManager:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def connect(self, url: str, *, pool_size: int = 10) -> None:
        self._engine = create_async_engine(url, pool_size=pool_size, echo=False)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False,
        )

    async def disconnect(self) -> None:
        if self._engine:
            await self._engine.dispose()

    def session(self) -> AsyncSession:
        if self._session_factory is None:
            raise RuntimeError("PostgresManager not connected")
        return self._session_factory()
```

### 3. Alembic 迁移

```bash
uv add alembic
alembic init alembic
```

修改 `alembic/env.py` 使用 async engine:

```python
from sqlalchemy.ext.asyncio import async_engine_from_config

# 在 run_async_migrations() 中:
connectable = async_engine_from_config(config.get_section("alembic"), prefix="sqlalchemy.")
```

常用命令:

```bash
alembic revision --autogenerate -m "add users table"
alembic upgrade head
```

---

## SQLite（开发/轻量场景）

```bash
uv add aiosqlite "sqlalchemy[asyncio]"
```

使用与 PostgreSQL 相同的 SQLAlchemy 模式，只需替换连接串:

```python
engine = create_async_engine("sqlite+aiosqlite:///./dev.db")
```

> 注意: SQLite 不适合生产环境的并发场景。

---

## 集成步骤 Checklist

- [ ] 安装数据库驱动 (`uv add motor` / `uv add "sqlalchemy[asyncio]" asyncpg`)
- [ ] 创建 `database/` 目录和 Manager 类
- [ ] 在 `config.py` 添加数据库配置 section
- [ ] 在 `config.yaml` 添加默认连接参数
- [ ] 在 `.env` 添加连接串 (敏感信息)
- [ ] 在 `main.py` lifespan 中调用 connect/disconnect
- [ ] 在 `AppRegistry` 添加 db 字段
- [ ] 在 `service_factory.py` 注入 Manager
- [ ] 在上下文 `infrastructure/` 层创建 Repository 实现
- [ ] 编写 Repository 单元测试
- [ ] `uv run poe lint` 通过
- [ ] `uv run poe test` 通过
