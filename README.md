# app_name

A production-ready full-stack template built with **FastAPI** (backend) and **Vue 3 + Arco Design + Vite** (frontend). It includes a `dev`/`main` Git model, full-stack CI, Conventional Commit governance, semantic-release, and opt-in deployment workflows.

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

### 1. Generate a project

```bash
copier copy --trust <template-url-or-path> my-project
cd my-project
```

Copier records your answers in `.copier-answers.yml` so future template updates can be applied deliberately with `copier update`.

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
│   ├── check_context_boundaries.py
│   ├── render_copier_backend.py
│   └── template_smoke.py
├── docs/                    # architecture & development guides
├── src/
│   ├── app_name/            # Python backend (FastAPI)
│   │   ├── main.py          # FastAPI app + lifespan
│   │   ├── run_api.py       # uvicorn entry point
│   │   ├── config.py        # pydantic-settings + YAML merge
│   │   ├── core/            # registry, service_factory, logging, timezone
│   │   ├── api/             # deps.py + versioned route modules
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
└── AGENTS.md                # Repository instructions for AI coding agents
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
| `poe api`         | Start backend (port 8665)                |
| `poe frontend`    | Start Vite dev server (port 8006)        |
| `poe lint`        | Run Ruff linter                          |
| `poe fmt`         | Run Ruff formatter                       |
| `poe test`        | Run pytest with coverage                 |
| `poe harness`     | Run the repository quality gate          |

## Git and CI/CD

The template uses a `dev`/`main` model:

- `dev` is the integration branch.
- `main` is the production truth branch.
- `test` and `staging` are environments, not branches.
- Feature and fix branches open PRs into `dev`.
- Release PRs flow from `dev` into `main`.
- Hotfix branches start from `main` and are backmerged into `dev`.

GitHub Actions are included under `.github/workflows`:

| Workflow | Default behavior |
|---|---|
| `ci.yml` | Backend lint/test, frontend build/test, shell syntax checks |
| `pr-governance.yml` | Conventional Commit PR title checks |
| `commit-governance.yml` | Landed commit subject checks on `dev` and `main` |
| `deploy-test.yml` | Skipped unless `TEST_DEPLOY_ENABLED=true` |
| `release.yml` | Skipped unless `RELEASE_ENABLED=true`; production deploy is also opt-in |
| `backmerge-main-to-dev.yml` | Manual recovery backmerge |

Deployment profiles:

| Profile | Variables | Behavior |
|---|---|---|
| CI only | none | Full-stack CI and governance only |
| Production only | `RELEASE_ENABLED=true`, optional `PROD_DEPLOY_ENABLED=true` | Release from `main`; deploy only when production vars/secrets exist |
| Test and production | `TEST_DEPLOY_ENABLED=true`, `RELEASE_ENABLED=true`, optional `PROD_DEPLOY_ENABLED=true` | Deploy test from `dev`; release and optionally deploy production from `main` |

See [docs/git-workflow.md](docs/git-workflow.md) and [docs/ci-cd.md](docs/ci-cd.md).

## Template Defaults

- `src/app_name/main.py` exposes a `create_app()` factory. The dev runner uses `uvicorn` factory mode instead of importing a module-level app singleton.
- Successful API responses use the shared `APIResponse` envelope: `{ code, success, data, message }`.
- The template uses a single versioned API prefix: `/api/v1`.
- `config.yaml` uses `cors.allow_origins` and `frontend.base_url`. Legacy keys are still accepted for compatibility, but new code should use the canonical names.

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
| [configuration-guide.md](docs/configuration-guide.md) | Config system (.env / yaml) + logging management |
| [database-patterns.md](docs/database-patterns.md) | Database integration guide (MongoDB / PostgreSQL) |
| [git-workflow.md](docs/git-workflow.md) | Branch, PR, release, and hotfix rules |
| [ci-cd.md](docs/ci-cd.md) | GitHub Actions, deployment profiles, variables, and secrets |
| [harness-engineering.md](docs/harness-engineering.md) | Repository-owned agent workflow and quality gates |
| [template-engine.md](docs/template-engine.md) | Copier migration plan for safe project generation and updates |

AI coding agents should start with [AGENTS.md](AGENTS.md). Keep required agent workflow in repository-owned instructions and harness checks, not tool-specific adapter files.

## Using as a GitHub Template

Use Copier for new projects:

```bash
copier copy --trust gh:jarlor/fastapi-vue-template my-project
cd my-project
uv sync
npm --prefix src/frontend ci
uv run poe harness
```

Use `copier update` inside generated projects when this template evolves.
