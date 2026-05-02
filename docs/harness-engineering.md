# Harness Engineering

This template is being shaped for Vibe Coding: humans describe intent, AI agents implement large parts of the change, and the repository harness decides whether the result is acceptable.

## Policy

Repository-tracked files are the authority:

- `AGENTS.md` defines shared agent behavior.
- `.agents/skills/` contains reusable, repository-owned agent workflows.
- Required workflow belongs in repository-owned instructions, not tool-specific adapter files.
- `poe` tasks, scripts, pre-commit, and CI enforce rules.
- Pull requests record evidence that the harness passed.

Do not rely on one AI product's private hooks or rules for required behavior. Product-specific integrations may improve local ergonomics, but do not commit adapter files unless they add repository-owned value that cannot live in `AGENTS.md`, skills, scripts, or docs.

## Harness Layers

| Layer | Purpose | Authority |
|---|---|---|
| Instructions | Guide agents and humans through the workflow | Advisory |
| Skills / playbooks | Reusable task procedures | Advisory |
| Local commands | Fast deterministic checks | Enforcing locally |
| Pre-commit | Lightweight checks before commit | Enforcing locally |
| CI | Shared gate for PRs and branches | Enforcing remotely |
| PR template | Required review evidence | Governance |

## Current Gate

Run the aggregate local gate before opening or updating a PR:

```bash
uv run poe harness
```

The first version intentionally uses stable existing checks:

- backend lint
- backend tests
- frontend build
- frontend tests

## Roadmap

1. Architecture harness: enforce bounded-context and layer import rules.
2. Security harness: scan for committed secrets and dangerous code patterns.
3. API contract harness: export OpenAPI and generate frontend types.
4. Frontend harness: add lint rules and smoke tests for main user paths.
5. Runtime harness: add readiness, liveness, metrics, tracing, and structured logs.
6. Template harness: replace broad string replacement init with a template engine.

New checks should start narrow or report-only when false positives are likely. Promote them to required CI checks after they are stable.

## PR Evidence

Every PR should state:

- commands run and results
- affected contracts or public interfaces
- configuration and secret impact
- security considerations
- follow-up harness gaps
