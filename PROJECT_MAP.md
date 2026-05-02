# Project Map

This is the short source map for agents and humans who need repository context without sweeping dependency trees.

## Start

1. Run `uv run poe agent-start`.
2. Read `AGENTS.md` for the workflow contract.
3. Read only the task-relevant skill or doc routed from `AGENTS.md`.

## Source Roots

| Path | Purpose |
|---|---|
| `src/app_name/` | FastAPI backend package |
| `src/frontend/` | Vue 3 frontend |
| `tests/` | Generated application behavior tests |
| `harness_tests/` | Tests for harness checkers and template tools |
| `scripts/harness/` | Poe task implementations; not public entrypoints |
| `.agents/skills/` | Reusable agent workflows |
| `docs/` | Focused reference docs routed by `AGENTS.md` |

## Ignore During Context Scans

Do not inspect `.git/`, `.venv/`, `node_modules/`, `.ruff_cache/`, `.pytest_cache/`, logs, coverage output, build output, or generated dependency files as source context.

After the baseline commit, `uv run poe agent-handoff-clean` removes rebuildable dependency trees so broad scans start from source files.

## Required Gates

Use public Poe tasks:

```bash
uv run poe agent-start
uv run poe harness
uv run poe agent-handoff-clean
```

Run `uv run poe template-smoke` only for template generation, Copier, generated-project files, sentinel files, or harness behavior.
