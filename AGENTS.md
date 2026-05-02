# AGENTS.md -- AI Agent Operating Contract

## Repository Role

This is a production-oriented FastAPI + Vue project template for Vibe Coding and Harness Engineering.

The repository-owned harness is the authority. Docs and skills guide work; Poe tasks, scripts, pre-commit, and CI decide whether a change is acceptable.

## Default Workflow

1. Read this file first.
2. Read only the task-relevant docs listed below. Do not sweep all of `docs/` by default.
3. Work on a focused branch. If this generated project uses the template's default Git model, branch from `dev`; if `dev` does not exist yet, create it deliberately or follow the project's actual integration branch.
4. Run the smallest relevant Poe checks while editing.
5. Run `uv run poe harness` before opening or updating a PR.
6. Run `uv run poe template-smoke` when template generation, Copier config, generated-project files, or harness behavior changes.

## Init Workflow

After this repository is generated from the template, initialize the working tree before feature work:

```bash
uv sync
npm --prefix src/frontend ci
uv run pre-commit install
uv run poe harness
```

Do not run `uv run poe template-smoke` for ordinary generated-project feature work. That gate is for template maintenance: Copier config, generated-project files, render scripts, template sentinels, and harness behavior.

For template maintenance, also run:

```bash
uv run poe template-smoke
```

Then choose the task workflow:

- Use `.agents/skills/template-maintenance/SKILL.md` for template mechanics, Copier, generated-project files, harness gates, CI, PR workflow, and agent instruction changes.
- Use `.agents/skills/project-development/SKILL.md` for normal generated-project feature work.

## Core Rules

- Backend code lives under `src/app_name`.
- Frontend code lives under `src/frontend`.
- Backend features should be built as bounded contexts under the generated backend package's `contexts/<context_name>/` directory.
- Contexts must not import each other directly. Use events or ports.
- Keep route handlers thin. Business logic belongs in application services.
- Keep `create_app()` as the app factory. Do not reintroduce a module-level FastAPI app singleton.
- Avoid module-level side effects such as creating settings, opening files, connecting to databases, or making network calls.
- Frontend components must not call `axios`, `fetch`, `EventSource`, or `XMLHttpRequest` directly. Use `src/frontend/src/api`.

## Commands

Use Poe task names as public entrypoints. Python files under `scripts/harness/` are implementation details.

```bash
uv run poe harness
uv run poe template-smoke
```

Targeted checks:

```bash
uv run poe lint
uv run poe harness-test
uv run poe governance-harness
uv run poe supply-chain
uv run poe architecture
uv run poe security
uv run poe api-contracts
uv run poe frontend-harness
uv run poe runtime-harness
uv run poe test
npm --prefix src/frontend run build
npm --prefix src/frontend run test
```

## Docs Routing

Use docs as task references, not as a mandatory reading set.

| Task | Read |
|---|---|
| Template generation, Copier, generated project smoke | `.agents/skills/template-maintenance/SKILL.md` and `docs/template-engine.md` |
| Harness policy, checks, PR evidence | `.agents/skills/template-maintenance/SKILL.md` |
| Backend structure or new bounded context | `docs/module-development.md` |
| API routes, response envelope, OpenAPI contract | `docs/api-conventions.md` |
| Frontend API boundary or generated API types | `docs/frontend-standards.md` |
| Config, env, logging | `docs/configuration-guide.md` |
| Tests and `tests/` vs `harness_tests/` | `docs/testing-guide.md` |
| CI, release, deploy workflows | `docs/ci-cd.md` and `docs/git-workflow.md` |
| Security baseline | `docs/security-standards.md` |

Historical template decisions live under `docs/adr/` in the template repository. Copier excludes them from generated projects.

## PR Expectations

Every PR should state what changed, why it changed, which checks ran, and whether API contracts, config, secrets, deployment behavior, or harness behavior changed.

Use `.github/pull_request_template.md` when opening a PR.
