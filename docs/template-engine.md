# Template Engine

This repository uses Copier as the canonical project generation and update path.

```bash
copier copy --trust <template-url-or-path> my-project
cd my-project
copier update
```

`--trust` is required because this template runs a repository-owned Copier task to render backend package paths while keeping the template repository itself runnable.

The legacy broad replacement initializer was removed. Do not reintroduce `init.sh` or broad search-and-replace generation.

## Variables

| Variable | Purpose |
|---|---|
| `project_name` | Human-facing project name |
| `package_name` | Python package name under `src/` |
| `frontend_name` | Frontend package name |
| `backend_port` | FastAPI development port |
| `frontend_port` | Vite development port |
| `api_prefix` | Versioned API prefix |

`project_name` is the value users normally type. Other values are derived unless explicitly overridden.

## Generated Project Gate

Run:

```bash
uv run poe template-smoke
```

CI runs the full generated-project gate:

```bash
uv run poe template-smoke --full
```

The smoke test generates a temporary project, installs dependencies, runs that project's harness, checks the Copier answers file, and fails on forbidden unresolved template sentinels.

Keep template smoke outside `uv run poe harness` so the everyday local aggregate gate remains fast. Treat the CI template-smoke job as required because generated-project validity is the core guarantee of a template repository.

## Authoring Rules

- Prefer Copier variables and repository-owned render scripts over ad hoc replacement.
- Do not scan for every literal `app_name`; some occurrences are semantic field names.
- Add explicit sentinel tokens for values that must never survive generation.
- Keep Copier tasks deterministic and covered by `uv run poe template-smoke`.
