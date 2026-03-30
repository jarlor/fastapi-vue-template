# app_name

A production-ready project template built with **FastAPI** (backend) and **Vue 3 + Arco Design + Vite** (frontend). Database integration is optional -- see [docs/database-patterns.md](docs/database-patterns.md).

## Tech Stack

| Layer     | Technology                              |
|-----------|-----------------------------------------|
| Backend   | FastAPI, Pydantic Settings V2, Loguru    |
| Frontend  | Vue 3, Arco Design Web Vue, Vite, Pinia |
| Scheduler | Croniter                                |
| Python    | >= 3.13, managed by **uv**              |
| Tasks     | poethepoet (via `uv run poe`)           |
| Linting   | Ruff                                    |
| Testing   | pytest, pytest-asyncio, pytest-cov      |

## Quick Start

### 1. Initialise the project

```bash
# Clone this template, then run init (auto-derives name from directory):
uv run poe init                    # my-project/ → my_project
# Or specify explicitly:
uv run poe init my_project_name
```

This single command: renames all `app_name` references, syncs Python deps, installs npm packages, and sets up pre-commit hooks.

### 2. Start developing

```bash
cp .env.example .env               # add your secrets
uv run poe api                     # start FastAPI on port 8665
uv run poe frontend                # start Vite dev server on port 8006
```

## Directory Structure

```
.
├── config.yaml              # non-sensitive defaults
├── .env.example             # secret template
├── pyproject.toml           # Python project & poe tasks
├── scripts/
│   └── init.sh              # one-time project renaming script (via poe init)
├── docs/                    # architecture & development guides
├── src/
│   ├── app_name/            # Python backend (FastAPI)
│   │   ├── main.py          # FastAPI app + lifespan
│   │   ├── run_api.py       # uvicorn entry point
│   │   ├── config.py        # pydantic-settings + YAML merge
│   │   ├── core/            # registry, service_factory, logging, timezone
│   │   ├── api/             # deps.py + route modules (public_v1 / internal_v1)
│   │   ├── contexts/        # bounded contexts (domain modules)
│   │   │   ├── _template/   # blank context template
│   │   │   └── <context>/
│   │   │       ├── domain/       # entities, value objects
│   │   │       ├── application/  # services, ports, use cases
│   │   │       ├── infrastructure/ # repositories, gateways, adapters
│   │   │       └── interface/    # FastAPI routers + schemas
│   │   ├── shared/          # events bus, constants
│   │   └── models/          # shared domain models
│   └── frontend/            # Vue 3 + Arco Design + Vite
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
└── CLAUDE.md                # Claude Code instructions
```

## Bounded Contexts

Each domain module lives under `src/app_name/contexts/<context_name>/` with four layers:

| Layer          | Responsibility                          |
|----------------|----------------------------------------|
| domain/        | Entities, value objects                 |
| application/   | Services, ports (Protocol), use cases   |
| infrastructure/| Concrete adapters (MongoDB, HTTP, etc.) |
| interface/     | FastAPI routers, request/response models|

Contexts **never** import from each other directly. Cross-context communication goes through the event bus or Ports.

See `docs/module-development.md` for the full guide, or `docs/walkthrough.md` for a step-by-step example.

## Poe Tasks

All tasks run via `uv run poe <task>`:

| Task              | Command                                  |
|-------------------|------------------------------------------|
| `poe init [name]` | One-time init: rename + deps + hooks (name auto-derived if omitted)|
| `poe api`         | Start backend (port 8665)                |
| `poe frontend`    | Start Vite dev server (port 8006)        |
| `poe lint`        | Run Ruff linter                          |
| `poe fmt`         | Run Ruff formatter                       |
| `poe test`        | Run pytest with coverage                 |

## Documentation

| Doc | Content |
|---|---|
| [architecture.md](docs/architecture.md) | Layered architecture, DI, event bus |
| [coding-standards.md](docs/coding-standards.md) | Naming, style, file constraints |
| [module-development.md](docs/module-development.md) | How to create new contexts |
| [context-contracts.md](docs/context-contracts.md) | Inter-context communication |
| [api-conventions.md](docs/api-conventions.md) | REST API design conventions |
| [frontend-standards.md](docs/frontend-standards.md) | Vue3 component/state/API standards |
| [security-standards.md](docs/security-standards.md) | 11 security rules + checklist |
| [testing-guide.md](docs/testing-guide.md) | TDD flow, pytest patterns |
| [walkthrough.md](docs/walkthrough.md) | End-to-end feature creation example |
| [database-patterns.md](docs/database-patterns.md) | Database integration guide (MongoDB / PostgreSQL) |

## Using as a GitHub Template

1. Push this repo to GitHub.
2. Go to **Settings > General > Template repository** (check the box).
3. Others (or yourself) can click **"Use this template"** to create a new repo.
4. Or via CLI: `gh repo create my-project --template yourname/fastapi-vue-template --private --clone`
5. Run `uv run poe init` in the new repo (auto-derives name from directory).
