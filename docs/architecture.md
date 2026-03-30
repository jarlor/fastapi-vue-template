# Architecture

## Layered Architecture

The backend follows a **four-layer architecture** within each bounded context:

```
┌─────────────────────────────────────────────┐
│  Interface Layer  (FastAPI routers, schemas) │
├─────────────────────────────────────────────┤
│  Application Layer (use cases, DTOs, events)│
├─────────────────────────────────────────────┤
│  Domain Layer     (entities, value objects,  │
│                    repository ports)         │
├─────────────────────────────────────────────┤
│  Infrastructure   (Mongo repos, HTTP clients,│
│                    adapters)                 │
└─────────────────────────────────────────────┘
```

**Dependency rule**: outer layers depend on inner layers, never the reverse. Infrastructure implements ports defined in the domain layer.

## Bounded Context Pattern

Each feature area is a **bounded context** under `src/app_name/contexts/`:

```
contexts/
├── users/
│   ├── domain/           # entities, ports (abstract repos)
│   ├── application/      # use cases, DTOs
│   ├── infrastructure/   # MongoUserRepository, etc.
│   └── interface/        # router.py, schemas.py
├── catalog/
│   └── ...
```

Contexts are isolated. They never import from each other directly. Cross-context communication uses the event bus or is orchestrated at the application layer.

## Dependency Injection

### AppRegistry

A single `AppRegistry` dataclass (in `src/app_name/registry.py`) holds all shared infrastructure: database client, settings, event bus. It is created once during the FastAPI lifespan and stored in `app.state`.

### FastAPI Depends

Route handlers receive use cases via `Depends()`. Each dependency function reads from `AppRegistry` and constructs the required service with its adapters:

```python
def get_user_service(request: Request) -> UserService:
    registry: AppRegistry = request.app.state.registry
    repo = MongoUserRepository(registry.db["users"])
    return UserService(repo)
```

This keeps routers thin and services testable (swap the repo with a mock).

## Event Bus

An in-process async event bus lives in `src/app_name/core/events.py`. It provides:

- `publish(event)` -- emit a domain event
- `subscribe(event_type, handler)` -- register a handler

Events are fire-and-forget within the same process. For distributed workloads, replace with a message broker adapter.

## Configuration Management

Configuration merges two sources (lower number = higher priority):

1. **Environment variables** (`.env` file, loaded via `python-dotenv`)
2. **config.yaml** (non-sensitive defaults)

Pydantic Settings reads both and validates them into typed models. Secrets always come from `.env`; non-sensitive values live in `config.yaml`.

## API Route Organisation

| Prefix              | Purpose                         |
|---------------------|---------------------------------|
| `/api/v1/<context>` | Public REST endpoints           |
| `/internal/`        | Health, metrics, admin (no auth)|
| `/health`           | Liveness probe                  |

All public routes require a valid JWT. Internal routes are protected by network policy (not exposed externally).
