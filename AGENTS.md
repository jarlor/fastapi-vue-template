# AGENTS.md -- AI Agent Operating Contract

If you arrived here from `00-START-HERE.md` or `PROJECT_MAP.md`, keep using `uv run poe ...` as the public command interface.

## Repository Role

This is a production-oriented FastAPI + Vue project template for Vibe Coding and Harness Engineering.

The repository-owned harness is the authority. Skills and these instructions guide work; Poe tasks, scripts, pre-commit, and CI decide whether a change is acceptable.

## Default Workflow

1. Read this file first. If you need a quick source map before editing, read `PROJECT_MAP.md`; do not infer source roots by sweeping the entire tree.
2. Run `uv run poe agent-start` as the first repository command. It prints `git status --short --branch` and tells you whether to finish init or create a feature branch before editing.
3. Read the task-relevant skill listed below. Do not sweep the repository by default, and exclude `.git/`, `.venv/`, `node_modules/`, `.ruff_cache/`, `.pytest_cache/`, logs, and generated coverage files from repository exploration.
4. Work on a focused feature branch before editing product code. If this generated project uses the template's default Git model, branch from `dev`; if `dev` does not exist yet, create it deliberately or follow the project's actual integration branch.
5. Run the smallest relevant Poe checks while editing.
6. Run `uv run poe harness` before opening or updating a PR.
7. Run `uv run poe template-smoke` when template generation, Copier config, generated-project files, or harness behavior changes.

## Init Workflow

After this repository is generated from the template, initialize the working tree before feature work:

```bash
git init
uv sync
npm --prefix src/frontend ci
uv run pre-commit install
uv run poe harness
git add .
git commit -m "chore: initialize from template"
uv run poe agent-handoff
```

Run `git init` only when `.git/` does not exist yet. If the repository has no commits after initialization, create the template baseline commit before feature work. Run `uv run poe agent-handoff` only after the baseline commit; it creates a focused feature branch when still on a baseline branch and removes rebuildable dependency trees such as `.venv/`, `src/frontend/node_modules/`, and `src/frontend/dist/` so agent context scans start from source files. Always create a focused feature branch before changing product code. Do not hand work to an agent on the baseline branch.

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
uv run poe agent-start
uv run poe agent-handoff
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

## Skill Routing

Use skills as task references, not as a mandatory reading set.

| Task | Read |
|---|---|
| Quick source map and ignored paths | `PROJECT_MAP.md` |
| Normal generated-project feature work | `.agents/skills/project-development/SKILL.md` |
| Template generation, Copier, generated project smoke, harness, CI, or agent instructions | `.agents/skills/template-maintenance/SKILL.md` |

## PR Expectations

Every PR should state what changed, why it changed, which checks ran, and whether API contracts, config, secrets, deployment behavior, or harness behavior changed.

Use `.github/pull_request_template.md` when opening a PR.
