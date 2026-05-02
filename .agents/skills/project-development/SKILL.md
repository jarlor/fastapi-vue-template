---
name: project-development
description: Use when implementing normal generated-project features, including backend bounded contexts, FastAPI routes, API contracts, frontend API calls, configuration changes, security-sensitive code, and application tests.
---

# Project Development

Use this skill for feature, fix, refactor, and test work in a project generated from this template.

## Workflow

1. Start from `AGENTS.md` and complete its init workflow if this is a fresh checkout or generated project.
2. Identify the touched surface: backend context, API contract, frontend API boundary, configuration, security, or tests.
3. Read only the matching docs routed from `AGENTS.md`.
4. Keep changes inside the smallest bounded context or frontend module that owns the behavior.
5. Run the narrow Poe check for the touched surface while editing.
6. Run `uv run poe harness` before opening or updating a PR.

## Development Rules

- Backend features live under `src/app_name/contexts/<context_name>/`.
- Contexts do not import each other directly. Use events or ports.
- Route handlers stay thin; application services own behavior.
- Keep `create_app()` as the app factory and avoid module-level side effects.
- Frontend code calls HTTP only through `src/frontend/src/api`.
- Generated API artifacts are refreshed through `uv run poe api-contracts-write`, not edited by hand.
- Put application behavior tests in `tests/`.
- Put harness checker and template-tool tests in `harness_tests/`.

## Targeted Checks

Use the smallest relevant command first:

```bash
uv run poe architecture
uv run poe security
uv run poe api-contracts
uv run poe frontend-harness
uv run poe runtime-harness
uv run poe test
npm --prefix src/frontend run build
npm --prefix src/frontend run test
```

Use the aggregate gate before PR handoff:

```bash
uv run poe harness
```
