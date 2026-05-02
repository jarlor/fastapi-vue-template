---
name: template-maintenance
description: Use when changing this template repository itself, including Copier generation, generated-project files, repository guardrails, Poe harness gates, CI quality checks, PR workflow, or agent instructions.
---

# Template Maintenance

Use this skill for changes to the template as a template. This includes generated-project shape, Copier behavior, repository-owned guardrails, and the soft/hard constraint system used by AI agents.

## Operating Model

This repository pairs soft and hard constraints:

- `AGENTS.md` routes agents to the right workflow and states shared rules.
- Skills provide task-specific procedures.
- Focused docs explain generated-project behavior when humans need stable reference material.
- `uv run poe ...` tasks, scripts, pre-commit, CI, and PR evidence enforce what must not drift.
- `scripts/harness/` contains implementation details; Poe task names are the public interface.

## Workflow

1. Start from `AGENTS.md`.
2. Decide whether the change affects generated projects, template mechanics, harness gates, or agent instructions.
3. Read only the relevant docs, skills, scripts, CI files, and tests.
4. Prefer repository-tracked deterministic checks over tool-specific hooks.
5. Keep required behavior in shared instructions, skills, scripts, Poe tasks, CI, or PR evidence.
6. Do not add product-specific agent adapters unless shared repository mechanisms cannot express the capability.
7. Add new deterministic checks as Poe tasks before making them required in CI.
8. Include stable fast checks in `uv run poe harness`; keep slow generated-project checks in `uv run poe template-smoke`.
9. Document only current template-owned behavior and the command that verifies it.

## Decision Rules

- Use `AGENTS.md` for shared agent behavior and routing.
- Use skills for reusable agent workflows.
- Use docs only for generated-project reference material or template-maintainer history that should not be in a workflow.
- Use Poe tasks, harness scripts, pre-commit, and CI for enforceable rules.
- Do not turn every convention into a hard gate. Promote only rules that are broadly useful, deterministic, and owned by the template.
- Keep downstream product, database, deployment, UI style, and infrastructure choices out of default gates unless the template owns that behavior.
- Use `tests/` for application behavior.
- Use `harness_tests/` for harness checker and template-tool self-tests.
- Delete or shorten docs that are not tied to current template behavior, a route in `AGENTS.md`, a skill workflow, or a hard harness gate.

## Template Engine

Copier is the canonical generation and update path. Do not reintroduce `init.sh` or broad search-and-replace generation.

Run generated-project smoke when changing Copier config, generated-project files, render scripts, template sentinels, or harness behavior:

```bash
uv run poe template-smoke
```

CI runs the full generated-project gate:

```bash
uv run poe template-smoke --full
```

Keep template smoke outside `uv run poe harness` so the everyday local aggregate gate remains fast.

## Validation

Run the narrow checks for touched areas, then run:

```bash
uv run poe harness
```

Also run `uv run poe template-smoke` when template generation or generated-project behavior changed.

If a new rule is not deterministic enough to block PRs yet, make it report-only first and document the path to hard enforcement.
