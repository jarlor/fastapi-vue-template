# Module Development Guide

How to create a new bounded context in the project.

## Directory Template

Create the following structure under `src/app_name/contexts/<context_name>/`:

```
<context_name>/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities.py          # domain entities & value objects
│   └── ports.py             # abstract repository interfaces
├── application/
│   ├── __init__.py
│   ├── service.py           # use cases / application service
│   └── dtos.py              # data transfer objects
├── infrastructure/
│   ├── __init__.py
│   └── mongo_repository.py  # concrete adapter for MongoDB
└── interface/
    ├── __init__.py
    ├── router.py             # FastAPI router
    └── schemas.py            # request/response models
```

## Import Rules

### Allowed

| From               | May import                                |
|--------------------|-------------------------------------------|
| interface/         | application/, domain/                     |
| application/       | domain/                                   |
| infrastructure/    | domain/ (to implement ports)              |
| any layer          | `shared/` (cross-cutting utilities)       |

### Forbidden

- Context A **never** imports from Context B.
- `domain/` never imports from `application/`, `infrastructure/`, or `interface/`.
- `application/` never imports from `infrastructure/` or `interface/`.

## Port / Adapter Pattern

Define abstract ports in `domain/ports.py`:

```python
from abc import ABC, abstractmethod

class ItemRepository(ABC):
    @abstractmethod
    async def find_by_id(self, item_id: str) -> Item | None: ...

    @abstractmethod
    async def save(self, item: Item) -> Item: ...
```

Implement the adapter in `infrastructure/mongo_repository.py`:

```python
class MongoItemRepository(ItemRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    async def find_by_id(self, item_id: str) -> Item | None:
        doc = await self._col.find_one({"_id": item_id})
        return Item(**doc) if doc else None
```

## Event Pattern

Contexts communicate through domain events, not direct imports.

```python
# In the publishing context's application service:
await event_bus.publish(OrderPlaced(order_id=order.id))

# In the subscribing context (registered at startup):
event_bus.subscribe(OrderPlaced, handle_order_placed)
```

## Dependency Injection Pattern

Wire the context in a `depends.py` or directly in the router:

```python
def get_item_service(request: Request) -> ItemService:
    registry = request.app.state.registry
    repo = MongoItemRepository(registry.db["items"])
    return ItemService(repo)
```

Use `Depends(get_item_service)` in route handlers.

## File Constraints

| Constraint                | Limit  |
|---------------------------|--------|
| Max lines per file        | 800    |
| Max lines per function    | 50     |
| Max nesting depth         | 4      |
| Preferred file size       | 200-400 lines |

If a file exceeds these limits, extract a new module.

## New Context Checklist

- [ ] Create the four-layer directory structure
- [ ] Define domain entities and repository ports
- [ ] Implement infrastructure adapters
- [ ] Write application service (use cases)
- [ ] Create FastAPI router and schemas
- [ ] Add dependency injection wiring
- [ ] Register router in `src/app_name/api/`
- [ ] Write unit tests for the application service
- [ ] Write integration tests for the router
- [ ] Verify no cross-context imports exist
