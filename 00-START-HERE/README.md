# Start Here

Before broad repository exploration or code edits, run:

```bash
uv run poe agent-start
```

Then read `PROJECT_MAP.md` for the source map and follow `AGENTS.md`.

Exclude `.git/`, `.venv/`, `node_modules/`, caches, logs, coverage output, and build output from source-context scans.

If a baseline commit already exists and dependency trees are present, `uv run poe agent-handoff-clean` can remove rebuildable trees before agent work.
