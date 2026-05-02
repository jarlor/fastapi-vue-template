# Start Here

This repository is designed for agent-driven development with repository-owned guardrails.

Before inspecting broad file trees or editing code, run:

```bash
uv run poe agent-start
```

Then read `PROJECT_MAP.md` for the source map and follow `AGENTS.md`. The same startup instructions are mirrored in `00-START-HERE/README.md` so broad file scans can discover them.

Do not treat `.git/`, `.venv/`, `node_modules/`, caches, logs, coverage output, or build output as source context.
