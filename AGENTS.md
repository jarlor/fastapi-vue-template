# AGENTS.md -- Repository Instructions for AI Coding Agents

## What This Repository Is

This is a production-oriented FastAPI + Vue template that is being evolved for Vibe Coding and Harness Engineering.

The repository is the source of truth. Keep required workflow in repository-owned instructions, skills, scripts, and CI. Do not add tool-specific adapter files unless they enforce or document a repository-owned harness capability that cannot live in those shared locations.

## Operating Model

Use the repository harness as the authority:

1. Read this file first.
2. Read task-relevant docs under `docs/`.
3. Make focused changes on a feature branch from `dev`.
4. Run the smallest relevant checks while working.
5. Run `uv run poe harness` before opening or updating a PR.
6. Put test and harness evidence in the PR description.

Agent instructions, skills, and playbooks guide the work. Deterministic checks in scripts, pre-commit, and CI decide whether the work is acceptable.

## Core Architecture Rules

- Backend code lives under `src/app_name`.
- Frontend code lives under `src/frontend`.
- Backend features should be built as bounded contexts under `src/app_name/contexts/<context_name>/`.
- Contexts must not import each other directly. Use events or ports.
- Keep route handlers thin. Business logic belongs in application services.
- Keep `create_app()` as the app factory. Do not reintroduce a module-level FastAPI app singleton.
- Avoid module-level side effects such as creating settings, opening files, connecting to databases, or making network calls.
- Frontend components should not call `axios` or `fetch` directly. Use the API layer under `src/frontend/src/api`.

## Harness Workflow

Run these commands from the repository root:

```bash
uv run poe lint
uv run poe harness-test
uv run poe architecture
uv run poe security
uv run poe api-contracts
uv run poe frontend-harness
uv run poe runtime-harness
uv run poe test
npm --prefix src/frontend run build
npm --prefix src/frontend run test
uv run poe harness
```

`uv run poe harness` is the local aggregate gate. New deterministic checks should be added there before they become required in CI.
Poe task names are the public entrypoints; Python files under `scripts/harness/` are implementation details for repository-owned gates.

## Documentation Expectations

Update docs when behavior, architecture, workflow, configuration, or public contracts change.

Use these entry points:

- `docs/architecture.md` for backend structure and DI.
- `docs/module-development.md` for new bounded contexts.
- `docs/context-contracts.md` for inter-context contracts.
- `docs/api-conventions.md` for API behavior.
- `docs/frontend-standards.md` for Vue and API-client patterns.
- `docs/harness-engineering.md` for agent and harness policy.

## Pull Request Expectations

Every PR should state:

- What changed.
- Why it changed.
- Which checks were run.
- Whether API contracts, context contracts, config, secrets, or deployment behavior changed.
- Any known follow-up work.

Use `.github/pull_request_template.md` when opening a PR.
