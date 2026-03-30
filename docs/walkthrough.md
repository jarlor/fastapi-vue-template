# Walkthrough: 从零创建一个完整功能

以创建一个 `catalog`（分类管理）上下文为例，演示完整的端到端流程。

## Step 0: 理解你要做什么

假设需求：管理商品分类（CRUD），其他上下文需要查询分类信息。

涉及的变更点：
- 后端: 新建 `contexts/catalog/` 四层结构
- 后端: 注册路由、DI 接线
- 前端: 新增页面、API 函数、路由

## Step 1: 创建目录结构

复制 `_template/` 并重命名：

```bash
cp -r src/app_name/contexts/_template src/app_name/contexts/catalog
```

得到：
```
contexts/catalog/
├── domain/
├── application/
│   ├── services/
│   └── ports/
├── infrastructure/
│   ├── repositories/
│   ├── gateways/
│   └── adapters/
└── interface/
    └── api/
```

## Step 2: 定义领域实体

```python
# contexts/catalog/domain/entities.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    category_id: str
    name: str
    description: str
    parent_id: str | None = None
```

要点：
- `frozen=True` 保证不可变
- 领域实体不依赖任何框架（无 Pydantic、无 Motor）

## Step 3: 定义端口 (Port)

```python
# contexts/catalog/application/ports/catalog_port.py
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app_name.contexts.catalog.domain.entities import Category


@runtime_checkable
class CatalogRepository(Protocol):
    async def find_by_id(self, category_id: str) -> Category | None: ...
    async def find_all(self) -> list[Category]: ...
    async def save(self, category: Category) -> None: ...
    async def delete(self, category_id: str) -> bool: ...
```

要点：
- 用 `Protocol` 不用 `ABC` — 结构化子类型，无需显式继承
- 端口定义在 `application/ports/`，不在 `domain/`

## Step 4: 实现应用服务

```python
# contexts/catalog/application/services/catalog_service.py
from __future__ import annotations

from uuid import uuid4

from app_name.contexts.catalog.application.ports.catalog_port import CatalogRepository
from app_name.contexts.catalog.domain.entities import Category


class CatalogService:
    def __init__(self, repo: CatalogRepository) -> None:
        self._repo = repo

    async def list_categories(self) -> list[Category]:
        return await self._repo.find_all()

    async def get_category(self, category_id: str) -> Category | None:
        return await self._repo.find_by_id(category_id)

    async def create_category(
        self, name: str, description: str, parent_id: str | None = None
    ) -> Category:
        category = Category(
            category_id=uuid4().hex,
            name=name,
            description=description,
            parent_id=parent_id,
        )
        await self._repo.save(category)
        return category

    async def delete_category(self, category_id: str) -> bool:
        return await self._repo.delete(category_id)
```

要点：
- 构造器注入 `CatalogRepository`（端口，非具体实现）
- 服务不知道 MongoDB 的存在
- 返回领域实体，不返回 dict

## Step 5: 实现基础设施适配器

```python
# contexts/catalog/infrastructure/repositories/mongo_catalog_repo.py
from __future__ import annotations

from typing import TYPE_CHECKING

from app_name.contexts.catalog.domain.entities import Category

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection


class MongoCatalogRepository:
    """Implements CatalogRepository port using MongoDB."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    async def find_by_id(self, category_id: str) -> Category | None:
        doc = await self._col.find_one({"_id": category_id})
        return Category(**doc) if doc else None

    async def find_all(self) -> list[Category]:
        cursor = self._col.find({})
        docs = await cursor.to_list(length=1000)
        return [Category(**doc) for doc in docs]

    async def save(self, category: Category) -> None:
        doc = {
            "_id": category.category_id,
            "name": category.name,
            "description": category.description,
            "parent_id": category.parent_id,
        }
        await self._col.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    async def delete(self, category_id: str) -> bool:
        result = await self._col.delete_one({"_id": category_id})
        return result.deleted_count > 0
```

要点：
- 不继承 `CatalogRepository` — Protocol 是结构化匹配
- 只在 `infrastructure/` 层出现 Motor 依赖
- `TYPE_CHECKING` 避免运行时 import Motor

## Step 6: 创建 API 路由

```python
# contexts/catalog/interface/api/catalog_router.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app_name.contexts.catalog.application.services.catalog_service import CatalogService
from app_name.shared.schemas.response import APIResponse


router = APIRouter(prefix="/catalogs", tags=["catalogs"])


# --- Schemas ---

class CreateCategoryRequest(BaseModel):
    name: str
    description: str
    parent_id: str | None = None


class CategoryResponse(BaseModel):
    category_id: str
    name: str
    description: str
    parent_id: str | None


# --- Dependency (局部接线) ---

def get_catalog_service(request: Request) -> CatalogService:
    from app_name.contexts.catalog.infrastructure.repositories.mongo_catalog_repo import (
        MongoCatalogRepository,
    )

    registry = request.app.state.registry
    repo = MongoCatalogRepository(registry.db.get_collection("catalogs"))
    return CatalogService(repo)


# --- Endpoints ---

@router.get("", response_model=APIResponse[list[CategoryResponse]])
async def list_categories(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> APIResponse[list[CategoryResponse]]:
    categories = await service.list_categories()
    return APIResponse.ok(data=[CategoryResponse(**vars(c)) for c in categories])


@router.post("", response_model=APIResponse[CategoryResponse], status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CreateCategoryRequest,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> APIResponse[CategoryResponse]:
    category = await service.create_category(
        name=body.name,
        description=body.description,
        parent_id=body.parent_id,
    )
    return APIResponse.ok(data=CategoryResponse(**vars(category)))


@router.get("/{category_id}", response_model=APIResponse[CategoryResponse])
async def get_category(
    category_id: str,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> APIResponse[CategoryResponse]:
    category = await service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return APIResponse.ok(data=CategoryResponse(**vars(category)))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> None:
    deleted = await service.delete_category(category_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
```

要点：
- `get_catalog_service` 在路由文件中局部定义（简单上下文）
- 如果服务需要共享（被其他上下文通过 Port 引用），则移到 `service_factory.py` + `registry`
- Request/Response schemas 定义在 `interface/` 层，不暴露领域实体

## Step 7: 注册路由

```python
# 在 src/app_name/api/v1/router.py 中添加:
from app_name.contexts.catalog.interface.api.catalog_router import router as catalog_router

router.include_router(catalog_router)
```

模板默认只保留一个 `/api/v1` 前缀；如果你的项目后续需要拆成 public/internal，再在具体项目里引入。

## Step 8: 前端 — 添加 API 函数

```typescript
// 在 src/frontend/src/api/index.ts 中添加:
import api, { type ApiResponse } from './index'

// --- Catalog ---
export const listCategories = () =>
  api.get<ApiResponse<CategoryResponse[]>>('/catalogs')

export const createCategory = (data: { name: string; description: string; parent_id?: string }) =>
  api.post<ApiResponse<CategoryResponse>>('/catalogs', data)

export const getCategory = (id: string) =>
  api.get<ApiResponse<CategoryResponse>>(`/catalogs/${id}`)

export const deleteCategory = (id: string) =>
  api.delete(`/catalogs/${id}`)

interface CategoryResponse {
  category_id: string
  name: string
  description: string
  parent_id: string | null
}
```

## Step 9: 前端 — 添加页面和路由

```typescript
// 在 src/frontend/src/router/index.ts 中添加:
{
  path: '/catalogs',
  name: 'catalogs',
  component: () => import('@/pages/Catalogs.vue'),
  meta: { requiresAuth: true },
}
```

创建 `src/frontend/src/pages/Catalogs.vue`，用 Arco Design 表格展示分类列表。

## Step 10: 写测试

```python
# tests/unit/catalog/test_catalog_service.py
import pytest
from unittest.mock import AsyncMock

from app_name.contexts.catalog.application.services.catalog_service import CatalogService
from app_name.contexts.catalog.domain.entities import Category


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.find_all = AsyncMock(return_value=[
        Category(category_id="1", name="Test", description="A test category"),
    ])
    return repo


async def test_list_categories(mock_repo):
    service = CatalogService(repo=mock_repo)
    result = await service.list_categories()
    assert len(result) == 1
    assert result[0].name == "Test"
    mock_repo.find_all.assert_called_once()
```

## Checklist (完成前逐项检查)

- [ ] 四层目录结构完整
- [ ] 领域实体为 frozen dataclass
- [ ] Port 用 Protocol 定义
- [ ] Service 只依赖 Port，不依赖 infrastructure
- [ ] Infrastructure 实现 Port 接口
- [ ] Router 中 schemas 用 Pydantic BaseModel
- [ ] API 返回统一的 `APIResponse` envelope
- [ ] 路由已注册到 `api/v1`
- [ ] 前端 API 函数走 `src/api/index.ts`
- [ ] 前端路由已添加
- [ ] 单元测试覆盖 Service 核心逻辑
- [ ] 无跨上下文 import
- [ ] `uv run poe lint` 通过
- [ ] `uv run poe test` 通过

## 进阶：需要跨上下文通信时

如果 `catalog` 需要在分类删除时通知其他上下文：

1. 在 `shared/events/models.py` 定义事件:
   ```python
   @dataclass(frozen=True)
   class CategoryDeletedEvent:
       category_id: str
       occurred_at: datetime = field(default_factory=lambda: datetime.now(datetime.UTC))
   ```

2. 在 Service 中发布:
   ```python
   await self._event_bus.publish(CategoryDeletedEvent(category_id=category_id))
   ```

3. 在 `main.py` lifespan 中订阅:
   ```python
   bus.subscribe(CategoryDeletedEvent, handle_category_deleted)
   ```

## 进阶：Service 需要注册到 Registry 时

当 Service 被多处使用或需要跨请求共享状态时：

1. 在 `core/service_factory.py` 添加工厂函数
2. 在 `AppRegistry` 添加 factory 字段
3. 在 `api/deps.py` 添加 `get_catalog_service` 依赖
4. 路由中改用 `Depends(get_catalog_service)` 从 deps 引入
