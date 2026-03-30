# app_name

A production-ready project template built with **FastAPI** (backend) and **Vue 3 + Arco Design + Vite** (frontend), using **MongoDB** for persistence.

## Tech Stack

| Layer     | Technology                              |
|-----------|-----------------------------------------|
| Backend   | FastAPI, Motor (async MongoDB), Pydantic Settings, Loguru |
| Frontend  | Vue 3, Arco Design Web Vue, Vite, Pinia |
| Auth      | PyJWT (access + refresh tokens)         |
| Scheduler | Croniter                                |
| Python    | >= 3.13, managed by **uv**              |
| Tasks     | poethepoet                              |
| Linting   | Ruff                                    |
| Testing   | pytest, pytest-asyncio, pytest-cov      |

## Quick Start

### 1. Initialise the project

```bash
# Clone this template, then rename the placeholder:
./init.sh my_project_name    # must be a valid Python identifier (snake_case)
```

### 2. Backend

```bash
uv sync                      # install Python dependencies
cp .env.example .env         # add your secrets
poe api                      # start FastAPI on port 8665
```

### 3. Frontend

```bash
cd src/frontend
npm install
cd ../..
poe frontend                 # start Vite dev server on port 8006
```

## Directory Structure

```
.
├── config.yaml              # non-sensitive defaults
├── .env.example             # secret template
├── pyproject.toml           # Python project & poe tasks
├── init.sh                  # one-time project renaming script
├── docs/                    # architecture & development guides
├── src/
│   ├── app_name/            # Python backend (FastAPI)
│   │   ├── config/          # pydantic-settings + YAML merge
│   │   ├── core/            # logging, security, events
│   │   ├── api/             # route modules (public / internal)
│   │   ├── contexts/        # bounded contexts (domain modules)
│   │   │   └── <context>/
│   │   │       ├── domain/       # entities, value objects, ports
│   │   │       ├── application/  # use cases, DTOs
│   │   │       ├── infrastructure/ # adapters (Mongo repos, clients)
│   │   │       └── interface/    # FastAPI routers
│   │   ├── shared/          # cross-cutting: base classes, utils
│   │   ├── registry.py      # AppRegistry for DI
│   │   ├── main.py          # FastAPI app factory
│   │   └── run_api.py       # uvicorn entry point
│   └── frontend/            # Vue 3 + Arco Design + Vite
├── tests/
│   ├── unit/
│   └── integration/
└── CLAUDE.md                # Claude Code instructions
```

## Bounded Contexts

Each domain module lives under `src/app_name/contexts/<context_name>/` with four layers:

| Layer          | Responsibility                          |
|----------------|----------------------------------------|
| domain/        | Entities, value objects, repository ports (abstract) |
| application/   | Use cases, DTOs, orchestration          |
| infrastructure/| Concrete adapters (MongoDB, HTTP, etc.) |
| interface/     | FastAPI routers, request/response models|

Contexts **never** import from each other directly. Cross-context communication goes through the event bus or the application layer.

See `docs/module-development.md` for the full guide.

## Poe Tasks

| Task          | Command                                  |
|---------------|------------------------------------------|
| `poe api`     | Start backend (port 8665)                |
| `poe frontend`| Start Vite dev server (port 8006)        |
| `poe lint`    | Run Ruff linter                          |
| `poe fmt`     | Run Ruff formatter                       |
| `poe test`    | Run pytest with coverage                 |

## Using as a GitHub Template

1. Click **Use this template** on GitHub (or fork).
2. Clone the new repository.
3. Run `./init.sh your_project_name`.
4. Commit the result and start building.

To mark this repo as a template on GitHub: **Settings > General > Template repository** (check the box).
