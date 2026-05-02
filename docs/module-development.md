# Module Development

This document exists for backend architecture changes and new bounded contexts.

## Runtime Shape

- `create_app()` is the FastAPI app factory.
- Shared runtime state is built during lifespan and stored on `app.state`.
- Route handlers stay thin; application services own behavior.
- Configuration comes from environment variables, `.env`, and `config.yaml`.

Run architecture checks with:

```bash
uv run poe architecture
```

## Directory Template

Create the following structure under `src/app_name/contexts/<context_name>/`:

```
<context_name>/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities.py          # domain entities & value objects
│   ├── value_objects.py     # immutable value types
│   └── events.py            # domain events
├── application/
│   ├── __init__.py
│   ├── ports/               # abstract interfaces (Protocol classes)
│   │   └── __init__.py
│   └── services/            # use cases / application services
│       └── __init__.py
├── infrastructure/
│   ├── __init__.py
│   ├── repositories/        # data persistence implementations
│   │   └── __init__.py
│   ├── gateways/            # external service integrations
│   │   └── __init__.py
│   └── adapters/            # port implementations
│       └── __init__.py
└── interface/
    ├── __init__.py
    └── api/                  # FastAPI routers and schemas
        ├── __init__.py
        └── router.py
```

## Import Rules

### Allowed

| From               | May import                                |
|--------------------|-------------------------------------------|
| interface/         | application/, domain/                     |
| application/       | domain/                                   |
| infrastructure/    | domain/, application/ports/               |
| any layer          | `shared/` (cross-cutting utilities)       |

### Forbidden

- Context A **never** imports from Context B.
- `domain/` never imports from `application/`, `infrastructure/`, or `interface/`.
- `application/` never imports from `infrastructure/` or `interface/`.

These rules are enforced by the repository architecture harness:

```bash
uv run poe architecture
```

The aggregate gate `uv run poe harness` also runs this check.

## Ports and Events

Use `Protocol` classes under `application/ports/` for dependencies that need adapters. Put concrete implementations under `infrastructure/`.

For external I/O such as HTTP clients, LLM SDKs, payment providers, email services, or search providers:

- Define the capability the application needs as a `Protocol` in `application/ports/`.
- Inject that port into the application service.
- Put the concrete SDK/client code under `infrastructure/gateways/` or `infrastructure/adapters/`.
- Wire the concrete implementation from dependency providers or registry setup.

Application services must not import concrete provider SDKs or network clients directly. The architecture harness enforces this boundary for known external I/O libraries.

## Event Pattern

Contexts communicate through domain events, not direct imports.

```python
# In the publishing context's application service:
await event_bus.publish(OrderPlaced(order_id=order.id))

# In the subscribing context (registered at startup):
event_bus.subscribe(OrderPlaced, handle_order_placed)
```

## Dependency Injection Pattern

Wire the context from dependency providers or registry setup. Routers should depend on provider functions; they should not construct concrete infrastructure clients inline.

```python
from typing import Protocol


class ItemRepositoryPort(Protocol):
    async def list_items(self) -> list[Item]: ...


class ItemService:
    def __init__(self, repo: ItemRepositoryPort) -> None:
        self._repo = repo


def get_item_service(request: Request) -> ItemService:
    registry = request.app.state.registry
    repo = MongoItemRepository(registry.db.get_collection("items"))  # infrastructure adapter
    return ItemService(repo)
```

Use `Depends(get_item_service)` in route handlers. If your project has not integrated a database or provider yet, keep the same dependency shape but substitute an in-memory or mocked adapter. Do not bypass the port just because the first version is small.

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
- [ ] Run `uv run poe architecture`
