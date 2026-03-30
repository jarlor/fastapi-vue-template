# CLAUDE.md -- Project Instructions for Claude Code

## Project

FastAPI backend + Vue 3 / Arco Design / Vite frontend project template.
Uses "app_name" as the placeholder; run `init.sh` to replace it with the real project name.

## Tech Stack

- **Backend**: FastAPI, Motor (async MongoDB), Pydantic Settings, Loguru, PyJWT
- **Frontend**: Vue 3, Arco Design Web Vue, Vite, Pinia
- **Python**: >= 3.13, managed by uv, tasks via poethepoet
- **Database**: MongoDB

## Key File Locations

| File / Dir                           | Purpose                               |
|--------------------------------------|---------------------------------------|
| `src/app_name/main.py`              | FastAPI app factory, `__version__`    |
| `src/app_name/run_api.py`           | Uvicorn entry point                   |
| `src/app_name/config/settings.py`   | Pydantic Settings + config.yaml merge |
| `src/app_name/core/logging.py`      | Loguru setup (call once at startup)   |
| `src/app_name/core/security.py`     | JWT helpers                           |
| `src/app_name/core/events.py`       | In-process async event bus            |
| `src/app_name/registry.py`          | AppRegistry (DI container)            |
| `src/app_name/contexts/`            | Bounded contexts (domain modules)     |
| `src/app_name/shared/`              | Cross-cutting base classes & utils    |
| `src/app_name/api/`                 | Top-level API router registration     |
| `src/frontend/`                     | Vue 3 + Arco Design + Vite            |
| `config.yaml`                       | Non-sensitive defaults                |
| `.env` / `.env.example`             | Secrets (never committed)             |

## Module Decoupling Rules

- Bounded contexts live under `src/app_name/contexts/<name>/`.
- Each context has four layers: domain, application, infrastructure, interface.
- Contexts NEVER import from each other. Cross-context communication uses the event bus.
- Only the application layer orchestrates domain and infrastructure.

## Poe Tasks

```bash
poe api        # Start backend on port 8665
poe frontend   # Start Vite dev server on port 8006
poe lint       # Ruff linter
poe fmt        # Ruff formatter
poe test       # pytest with coverage
```

## Config Files

- `.env` -- secrets (MONGODB__URL, AUTH__SECRET_KEY, OPENAI__API_KEY, etc.)
- `config.yaml` -- non-sensitive defaults (server port, CORS origins, log dir)
- Pydantic Settings merges both; env vars take precedence over YAML.

## Known Patterns

- **Immutability**: return new objects, do not mutate in place.
- **Repository pattern**: abstract ports in `domain/ports.py`, concrete adapters in `infrastructure/`.
- **DI via AppRegistry**: created in lifespan, stored in `app.state`, injected via `Depends()`.
- **File limits**: 800 lines max per file, 50 lines max per function, 4 levels max nesting.
- **Testing**: TDD (RED-GREEN-IMPROVE), 80 %+ coverage target, pytest-asyncio for async tests.
