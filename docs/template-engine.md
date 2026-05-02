# Template Engine

This template will migrate from broad string replacement to Copier.

## Goal

Generated projects should be:

- reproducible from explicit answers
- updateable when this template evolves
- safe from accidental placeholder replacement
- verifiable by the repository harness

## Current State

Copier is the canonical project generation path. The previous `scripts/init.sh` broad replacement flow has been removed because generated projects are now rendered through Copier variables and verified by generated-project smoke tests.

## Target State

Copier becomes the canonical project generation and update path:

```bash
copier copy --trust <template-url> my-project
copier update
```

The generated project keeps a Copier answers file so future template updates can be applied deliberately.

`--trust` is required because this template runs a repository-owned Copier task during `copy` to render dual-use backend package paths while keeping the template repository itself runnable.

## Template Variables

The first Copier implementation should cover:

| Variable | Default / Derivation | Validation | Purpose |
|---|---|---|---|
| `project_name` | target directory name | non-empty kebab/snake/display text, no path separators | Human-facing repository/project name |
| `package_name` | `project_name` normalized to lowercase snake_case | Python identifier: `^[a-z][a-z0-9_]*$` | Python package name under `src/` |
| `frontend_name` | `project_name` normalized to npm package style | npm-safe lowercase name: `^[a-z0-9][a-z0-9._-]*$` | Frontend package metadata |
| `backend_port` | `8665` | integer, `1024..65535` | FastAPI development port |
| `frontend_port` | `8006` | integer, `1024..65535`, not equal to `backend_port` | Vite development port |
| `api_prefix` | `/api/v1` | starts with `/`, no trailing slash unless `/` | Default versioned API prefix |

Do not add optional feature toggles until the base generation path is tested.

`project_name` is the only value users should normally type. The first Copier PR should derive `package_name` and `frontend_name` unless users override them explicitly.

## Removed Legacy Path

The old broad replacement initializer has been removed. Copier is the only supported generation path because it can:

- generate a project from the template
- run backend tests in the generated project
- run frontend build/test in the generated project
- run the generated project's `uv run poe harness`
- prove no unresolved template-only placeholders remain

## Harness Requirements

The template smoke test must:

1. Generate a temporary project with Copier.
2. Install Python and frontend dependencies.
3. Run `uv run poe harness`.
4. Assert the generated project contains the Copier answers file.
5. Check for forbidden unresolved placeholders.

This smoke test is the gate that makes template generation a repository-owned guarantee instead of a manual convention.

Current gate mode:

- `uv run poe template-smoke` runs backend generated-project checks.
- `uv run poe template-smoke` installs generated frontend dependencies because the generated API contract check uses frontend type generation.
- `uv run poe template-smoke --full` also runs generated frontend build/test.
- CI requires full template smoke to pass.
- Keep it outside `uv run poe harness` so the everyday local aggregate gate remains fast, but treat the dedicated CI job as a required template-generation gate.

This keeps the canonical `harness` signal focused while still making generated-project validity a hard CI constraint.

## Placeholder Policy

Do not scan for every literal `app_name`. Some occurrences are semantic field names and must remain stable, such as the `Settings.app_name` configuration key.

The smoke test should scan only for template-only tokens that must never survive generation. The first Copier PR should introduce explicit sentinel tokens for templated values, for example:

- `__PROJECT_NAME__`
- `__PACKAGE_NAME__`
- `__FRONTEND_NAME__`
- `__BACKEND_PORT__`
- `__FRONTEND_PORT__`
- `__API_PREFIX__`

The smoke test should fail if any sentinel token remains outside documented examples. If a literal example is needed in docs, add a narrow allowlist entry in the smoke script.

## Implementation Sequence

Completed migration steps:

1. Copier infrastructure and generated-project smoke.
   - Add `copier.yml`, the Copier answers-file template, `poe template-smoke`, and CI.
2. Minimal pure Copier backend path.
   - Render the Python package path, imports, `pyproject.toml`, tests, and Poe tasks with Copier/Jinja.
   - Prove `uv run poe architecture` and `uv run poe test` pass in the generated project.
3. Configuration and frontend variables.
   - Render frontend package metadata, backend and frontend ports, API prefix, config defaults, and README startup examples.
   - Add targeted assertions that the generated values actually appear where expected.
4. Full generated-project smoke.
   - Run generated frontend install/build/test in CI.
   - Require `template-smoke` in CI after the generated-project path is stable.
5. Remove the legacy broad replacement initializer.
   - Removed after docs, tests, and generated-project checks no longer depended on it.

Copier owns template rendering and generated-project updateability. Harness scripts, Poe tasks, CI, and project skills own deterministic verification and workflow policy.

The source repository is also a working project. Avoid converting shared source files directly into non-runnable Jinja when a Copier task or narrow template file can preserve both roles. Any Copier task must be repository-owned, deterministic, and covered by `poe template-smoke`.
