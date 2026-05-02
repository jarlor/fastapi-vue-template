# Start Here

Before broad repository exploration or code edits, run:

```bash
uv run poe agent-start
```

Then read `PROJECT_MAP.md` for the source map and follow `AGENTS.md`.

Exclude `.git/`, `.venv/`, `node_modules/`, caches, logs, coverage output, and build output from source-context scans.

After the baseline commit, run `uv run poe agent-handoff` before agent work so the agent starts on a focused branch without rebuildable dependency trees.
