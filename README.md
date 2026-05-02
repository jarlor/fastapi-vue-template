# app_name

A production-ready full-stack template built with **FastAPI** (backend) and **Vue 3 + Arco Design + Vite** (frontend). It includes a `dev`/`main` Git model, full-stack CI, Conventional Commit governance, semantic-release, and opt-in deployment workflows.

## AI Agent Entry

If you are an AI coding agent working in this repository, do this before broad exploration or edits:

1. Read [PROJECT_MAP.md](PROJECT_MAP.md).
2. Read [AGENTS.md](AGENTS.md).
3. Run `uv run poe agent-start`.

Use `uv run poe ...` task names as the public command interface.

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

If you delegate implementation to an AI coding agent, tell it to start from [00-START-HERE.md](00-START-HERE.md). The agent-facing execution path is [PROJECT_MAP.md](PROJECT_MAP.md), then [AGENTS.md](AGENTS.md), then `uv run poe agent-start`.

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
│   ├── harness/             # implementation for poe harness tasks
│   ├── render_copier_backend.py
│   └── template_smoke.py
├── .agents/skills/          # reusable agent workflows
├── harness_tests/           # tests for harness scripts and template tools
├── PROJECT_MAP.md           # short source map for agents and humans
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
├── 00-START-HERE.md         # First file for AI coding agents
├── 00-START-HERE/           # Mirrored startup sentinel for broad scans
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

Normal feature work follows [.agents/skills/project-development/SKILL.md](.agents/skills/project-development/SKILL.md).

## Poe Tasks

All tasks run via `uv run poe <task>`:

| Task              | Command                                  |
|-------------------|------------------------------------------|
| `poe api`         | Start backend (port 8665)                |
| `poe frontend`    | Start Vite dev server (port 8006)        |
| `poe agent-start` | Agent startup gate for init and branch state |
| `poe lint`        | Run Ruff linter                          |
| `poe fmt`         | Run Ruff formatter                       |
| `poe harness-test` | Test harness scripts and template tools |
| `poe governance-harness` | Check repository governance consistency |
| `poe supply-chain` | Check supply-chain and CI dependency policy |
| `poe architecture` | Check bounded-context boundaries        |
| `poe security`    | Run deterministic security baseline      |
| `poe api-contracts` | Check OpenAPI and frontend type drift   |
| `poe frontend-harness` | Check frontend source boundaries     |
| `poe runtime-harness` | Check app factory, lifespan, and health baseline |
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

Agent-facing branch and PR rules live in [AGENTS.md](AGENTS.md) and [.agents/skills/template-maintenance/SKILL.md](.agents/skills/template-maintenance/SKILL.md).

## Template Defaults

- `src/app_name/main.py` exposes a `create_app()` factory. The dev runner uses `uvicorn` factory mode instead of importing a module-level app singleton.
- Successful API responses use the shared `APIResponse` envelope: `{ code, success, data, message }`.
- The template uses a single versioned API prefix: `/api/v1`.
- `config.yaml` uses `cors.allow_origins` and `frontend.base_url`. Legacy keys are still accepted for compatibility, but new code should use the canonical names.

## Agent Workflows

AI coding agents should start with [00-START-HERE.md](00-START-HERE.md), [PROJECT_MAP.md](PROJECT_MAP.md), then [AGENTS.md](AGENTS.md). Normal feature work uses [.agents/skills/project-development/SKILL.md](.agents/skills/project-development/SKILL.md); template and harness work uses [.agents/skills/template-maintenance/SKILL.md](.agents/skills/template-maintenance/SKILL.md). Keep required workflow in repository-owned instructions and harness checks, not tool-specific adapter files.

## Using as a GitHub Template

Use Copier for new projects:

```bash
copier copy --trust gh:jarlor/fastapi-vue-template my-project
cd my-project
uv sync
npm --prefix src/frontend ci
uv run poe harness
uv run poe agent-handoff
```

Use `copier update` inside generated projects when this template evolves.
