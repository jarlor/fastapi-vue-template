# Harness Engineering

This template is being shaped for Vibe Coding: humans describe intent, AI agents implement large parts of the change, and the repository harness provides strong constraints around whether the resulting repository change is acceptable.

## Policy

Repository-tracked files are the authority:

- `AGENTS.md` defines shared agent behavior.
- `.agents/skills/` contains reusable, repository-owned agent workflows.
- Docs provide soft constraints: intent, rationale, conventions, examples, and review expectations.
- Required workflow belongs in repository-owned instructions, not tool-specific adapter files.
- `poe` tasks, scripts, pre-commit, and CI provide hard constraints that enforce repository quality gates.
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
- harness script and template-tool tests
- governance consistency checks for public Poe gates, CI entrypoints, PR evidence, and prohibited product-specific agent adapters
- supply-chain checks for SHA-pinned actions, dependency update coverage, least-privilege workflow permissions, lockfiles, and reproducible install commands
- architecture boundary checks
- security baseline checks
- API contract drift checks
- frontend source boundary checks
- runtime app factory, lifespan, and health baseline checks
- backend tests
- frontend build
- frontend tests

Poe task names are the stable local and CI entrypoints. Scripts under `scripts/harness/` implement those gates and are not a separate public script API. Use `tests/` for application behavior and utility coverage; use `harness_tests/` for checker and template-tool self-tests; use harness tasks for repository workflow, architectural boundaries, generated-template guarantees, and other constraints that AI coding agents must not bypass.

`uv run poe governance-harness` is the bridge between soft and hard constraints. It does not review prose quality. It checks mechanical repository facts that should not drift: required Poe tasks exist, the aggregate harness calls them through public Poe entrypoints, CI uses public Poe entrypoints for required gates, PR evidence lists required commands, and product-specific agent adapter files are not reintroduced.

## Roadmap

1. Frontend harness: add smoke tests for main user paths and promote more rules only when false positives are low.
2. Runtime harness: extend the current app factory, lifespan, and health baseline only when deployment conventions justify readiness, metrics, tracing, or structured logs.
3. Template engine: keep Copier generation and generated-project smoke tests as repository-owned guarantees.
4. Security harness: expand the baseline only when new rules are deterministic enough to avoid noisy false positives.
5. API contract harness: expand from type generation to generated clients only if the frontend needs it.

New checks should start narrow or report-only when false positives are likely. Promote them to required CI checks after they are stable.

## PR Evidence

Every PR should state:

- commands run and results
- affected contracts or public interfaces
- configuration and secret impact
- security considerations
- follow-up harness gaps
