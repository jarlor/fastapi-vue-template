# Template Engine

This template will migrate from broad string replacement to Copier.

## Goal

Generated projects should be:

- reproducible from explicit answers
- updateable when this template evolves
- safe from accidental placeholder replacement
- verifiable by the repository harness

## Current State

`uv run poe init [name]` calls `scripts/init.sh`. The script replaces `app_name` across many file types, renames `src/app_name`, then repairs reserved config keys that should not have been replaced.

That flow works for the current skeleton, but it is not a strong enough foundation for a production template. It is especially risky as the harness adds more scripts, docs, examples, generated clients, and deployment files.

## Target State

Copier becomes the canonical project generation and update path:

```bash
copier copy <template-url> my-project
copier update
```

The generated project keeps a Copier answers file so future template updates can be applied deliberately.

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

## Compatibility

Keep `scripts/init.sh` during migration. It should be deprecated after Copier can:

- generate a project from the template
- run backend tests in the generated project
- run frontend build/test in the generated project
- run the generated project's `uv run poe harness`
- prove no unresolved template-only placeholders remain

## Harness Requirements

Add a template smoke test before removing `scripts/init.sh`:

1. Generate a temporary project with Copier.
2. Install Python and frontend dependencies.
3. Run `uv run poe harness`.
4. Assert the generated project contains the Copier answers file.
5. Check for forbidden unresolved placeholders.

This smoke test is the gate that makes template generation a repository-owned guarantee instead of a manual convention.

Initial gate mode:

- Add `uv run poe template-smoke` in the first Copier implementation PR.
- Run it locally and document its output in the PR.
- Add a dedicated CI job with `continue-on-error: true` if runtime is acceptable.
- Do not add it to `uv run poe harness` until it is stable enough to be a required gate.

This keeps the canonical `harness` signal strong while the generated-project smoke path is still being tuned.

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

## Next Implementation PR

The next PR should add the first working Copier path without removing `scripts/init.sh`.

Add:

- `copier.yml` with the initial variables listed above
- a template smoke script under `scripts/`
- a `poe template-smoke` task
- a report-only CI job if the smoke runtime is acceptable

The smoke script should:

1. create a temporary directory
2. run Copier against the local repository with deterministic answers
3. run the generated project's Python tests
4. run the generated project's frontend build/test if dependencies are available
5. assert the Copier answers file exists
6. scan the generated project for unresolved sentinel tokens that should have been rendered

Keep the first implementation narrow. Do not introduce optional database, auth, observability, or deployment profiles in the Copier PR.

## Implementation Sequence

Use small PRs with explicit scope:

1. Copier infrastructure and compatibility smoke.
   - Add `copier.yml`, the Copier answers-file template, `poe template-smoke`, and report-only CI.
   - The smoke may call `scripts/init.sh` only as a migration bridge.
   - Do not describe this stage as a pure Copier-generated project path.
2. Minimal pure Copier backend path.
   - Render the Python package path, imports, `pyproject.toml`, tests, and Poe tasks with Copier/Jinja.
   - Remove the `init.sh` call from `scripts/template_smoke.py`.
   - Prove `uv run poe architecture` and `uv run poe test` pass in the generated project.
3. Configuration and frontend variables.
   - Render frontend package metadata, backend and frontend ports, API prefix, config defaults, and README startup examples.
   - Add targeted assertions that the generated values actually appear where expected.
4. Full generated-project smoke.
   - Run generated frontend install/build/test in CI after runtime and flake rate are acceptable.
   - Promote `template-smoke` from report-only to required only after it is stable.
5. Deprecate and remove `scripts/init.sh`.
   - First replace it with a compatibility warning or thin Copier wrapper.
   - Delete it only after docs, tests, and generated-project checks no longer depend on it.

Copier owns template rendering and generated-project updateability. Harness scripts, Poe tasks, CI, and project skills own deterministic verification and workflow policy.
