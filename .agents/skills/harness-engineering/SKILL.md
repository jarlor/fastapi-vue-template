---
name: harness-engineering
description: Use when changing this repository's agent workflow, project template guardrails, CI quality gates, PR process, or Vibe Coding and Harness Engineering documentation.
---

# Harness Engineering

Use this skill for repository changes that affect how humans and AI agents make, verify, and review changes.

## Workflow

1. Start from `AGENTS.md`.
2. Inspect the relevant project docs and current CI/pre-commit tasks.
3. Prefer repository-tracked, deterministic checks over tool-specific hooks.
4. Keep tool-specific adapters thin. They should point back to repository-owned instructions.
5. Add new checks to `uv run poe harness` before making them required in CI.
6. For new rules, document the expected behavior and the command that verifies it.

## Decision Rules

- Use `AGENTS.md` for shared agent behavior.
- Use this skill for reusable repository workflow guidance.
- Use docs for rationale, roadmap, and examples.
- Use `poe` tasks, scripts, pre-commit, and CI for enforceable rules.
- Do not bind required behavior to a specific AI product.

## Validation

Before finishing harness changes, run the narrow checks for touched areas and then run:

```bash
uv run poe harness
```

If a new rule is not deterministic enough to block PRs yet, make it report-only first and document the path to hard enforcement.
