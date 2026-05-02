---
name: harness-engineering
description: Use when changing this repository's agent workflow, project template guardrails, CI quality gates, PR process, or Vibe Coding and Harness Engineering documentation.
---

# Harness Engineering

Use this skill for repository changes that affect how humans and AI agents make, verify, and review changes.

This repository treats Harness Engineering as the pairing of soft and hard constraints:

- `AGENTS.md`, skills, and focused docs guide agents before they edit.
- `uv run poe ...` tasks, scripts, pre-commit, CI, and PR evidence enforce what must not drift.
- `scripts/harness/` contains implementation details; Poe task names are the public interface.

## Workflow

1. Start from `AGENTS.md`.
2. Read only the task-relevant docs or skills routed from `AGENTS.md`.
3. Inspect current Poe, CI, pre-commit, and PR evidence before adding new policy.
4. Prefer repository-tracked, deterministic checks over tool-specific hooks.
5. Do not add product-specific agent adapters unless the repository cannot express that capability through shared instructions, skills, scripts, docs, or CI.
6. Add new deterministic checks as Poe tasks before making them required in CI.
7. Include stable checks in `uv run poe harness`; keep slow generated-project checks in `uv run poe template-smoke`.
8. For new rules, document the expected behavior and the command that verifies it.

## Decision Rules

- Use `AGENTS.md` for shared agent behavior.
- Use this skill for reusable repository workflow guidance.
- Use docs for rationale, roadmap, and examples.
- Use `poe` tasks, scripts, pre-commit, and CI for enforceable rules.
- Do not bind required behavior to a specific AI product.
- Do not turn every convention into a hard gate. Promote only rules that are broadly useful, deterministic, and owned by the template.
- Keep downstream product, database, deployment, UI style, and infrastructure choices out of default gates unless the template owns that behavior.
- Use `tests/` for application behavior. Use `harness_tests/` for harness checker and template-tool self-tests.
- Delete or shorten docs that are not tied to current template behavior, a task route in `AGENTS.md`, or a hard harness gate.

## Validation

Before finishing harness changes, run the narrow checks for touched areas and then run:

```bash
uv run poe harness
```

If a new rule is not deterministic enough to block PRs yet, make it report-only first and document the path to hard enforcement.
