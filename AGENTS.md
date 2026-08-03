# AI Agent Operating Contract

This file is the single repository contract for AI coding agents. It applies whether the agent is implementing, reviewing, testing, or documenting a change.

The allocation of human, implementation, verification, and release authority is defined in [CONTRIBUTING.md](CONTRIBUTING.md). Code boundaries are defined in [ARCHITECTURE.md](ARCHITECTURE.md). Do not duplicate or reinterpret those policies here.

## Before Editing

1. Read the linked issue or pull request and identify its intent, acceptance examples, non-goals, risk class, and human decision owner.
2. Read only the relevant sections of `ARCHITECTURE.md` and the task-relevant source and tests.
3. Inspect the current branch and working tree. Preserve unrelated user changes.
4. If the change contract is missing, ambiguous, or has an unconfirmed protected-risk trigger, ask the human decision owner before implementation.

Do not execute a repository-wide discovery ritual. Ignore dependency trees, virtual environments, caches, build output, logs, coverage output, and `.git` as source context.

## Agent Authority

An agent may:

- inspect repository-owned files relevant to the task;
- propose a plan and identify uncertainty or risk;
- edit code, tests, contracts, and documentation within the confirmed scope;
- run repository checks and report their exact results;
- suggest follow-up work without silently expanding the current change.

An agent must not:

- invent or silently broaden product intent, acceptance criteria, or risk tolerance;
- weaken acceptance tests, contracts, CI, security controls, or harness checks merely to make its implementation pass;
- treat its own review as human approval;
- approve, merge, deploy, apply GitHub control-plane changes, rotate secrets, migrate production data, or exercise a human maintainer's release authority;
- perform destructive or irreversible operations without explicit authority for the exact target and impact.

Any protected-risk trigger listed in `CONTRIBUTING.md` requires explicit human confirmation before implementation continues. A proposed change to an architecture invariant also requires an ADR.

## Repository Interface

Use Poe tasks as the public interface. Scripts under `scripts/harness/` are implementation details.

- Run `uv run poe check` for fast feedback while editing.
- Run `uv run poe harness` before handing work to a reviewer or updating a pull request.
- A configured, non-Draft pull request triggers the repository's separate OpenCodeReview workflow. Do not move that
  probabilistic external review into `check` or `harness`, and do not treat its output as approval.
- Use `uv run poe repo-bootstrap bootstrap ... --dry-run` only when GitHub governance is in scope. Running it with `--apply` changes external repository state and requires explicit human authorization for the exact repository, profile, and maintainers.

If a command fails, fix the product change or report the blocker. Do not bypass the command or modify its gate unless governance itself is explicitly in scope and human-approved.

## Implementation Rules

- Make the smallest coherent change that satisfies the confirmed acceptance examples.
- Treat contracts and acceptance tests as the independent oracle, not as implementation scaffolding.
- Add focused tests for new behavior and regressions.
- Preserve compatibility unless the change contract explicitly authorizes a break.
- Follow `ARCHITECTURE.md`; do not introduce a new architecture convention inside a feature patch.
- Never commit credentials, local environment values, generated dependency trees, or build output.

## Handoff

Report:

- what changed and why;
- acceptance examples covered;
- architecture, contract, security, data, dependency, deployment, or harness impact;
- commands run and their results;
- the disposition of material OpenCodeReview findings already present on the pull request, without silently fixing a
  finding that broadens intent or crosses an unconfirmed R2 boundary;
- remaining uncertainty, decisions, or follow-ups that require a human.

The agent's handoff is evidence for review, not approval to merge.
