---
name: project-development
description: Use when implementing normal generated-project features, including backend bounded contexts, FastAPI routes, API contracts, frontend API calls, configuration changes, security-sensitive code, and application tests.
---

# Project Development

Use this skill for feature, fix, refactor, and test work in a project generated from this template.

## Workflow

1. Start from `AGENTS.md` and run `uv run poe agent-start` before the first edit.
2. Complete the init workflow if this is a fresh checkout or generated project. After the template baseline commit, create a focused feature branch before editing product code.
3. Identify the touched surface: backend context, API contract, frontend API boundary, configuration, security, or tests.
4. Read only the matching docs routed from `AGENTS.md`; do not inspect `.git/`, `.venv/`, `node_modules/`, caches, logs, or generated coverage files as source context.
5. Keep changes inside the smallest bounded context or frontend module that owns the behavior.
6. Run the narrow Poe check for the touched surface while editing.
7. Run `uv run poe harness` before opening or updating a PR.

## Development Rules

- Backend features live under the generated backend package's `contexts/<context_name>/` directory.
- Contexts do not import each other directly. Use events or ports.
- Route handlers stay thin; application services own behavior.
- Keep `create_app()` as the app factory and avoid module-level side effects.
- Frontend code calls HTTP only through `src/frontend/src/api`.
- Generated API artifacts are refreshed through `uv run poe api-contracts-write`, not edited by hand.
- Put application behavior tests in `tests/`.
- Put harness checker and template-tool tests in `harness_tests/`.
- Do not add a major dependency only to satisfy wording. Use it in the implementation and cover its behavior, or do not add it.
- When implementing browser streaming over HTTP, put the streaming client in `src/frontend/src/api`. Vue components must not call `fetch`, `EventSource`, `axios`, or `XMLHttpRequest` directly.
- For POST-based SSE or streamed responses in browsers, prefer `fetch` with `ReadableStream` inside the API layer. Do not use Axios `responseType: "stream"` for browser streaming.
- For SSE over GET, `EventSource` may be used only inside the API layer.

## Dependency Additions

When adding a runtime dependency:

1. Add it through the package manager (`uv add ...` or the frontend package manager).
2. Use the dependency in code, not only in lockfiles.
3. Add or update tests that exercise the behavior the dependency provides.
4. Mention the dependency's concrete call sites in the PR summary.

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
