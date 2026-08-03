# AI Agent Operating Contract

This file is the single repository contract for AI coding agents. It applies whether the agent is implementing, reviewing, testing, or documenting a change.

The allocation of human, implementation, verification, and release authority is defined in [CONTRIBUTING.md](CONTRIBUTING.md). Code boundaries are defined in [ARCHITECTURE.md](ARCHITECTURE.md). Do not duplicate or reinterpret those policies here.

## Working Method

Use the installed [Superpowers](https://github.com/obra/superpowers) plugin as the standard method for shaping,
planning, implementing, debugging, reviewing, and finishing development work. Invoke its applicable skills rather
than improvising an equivalent workflow. If Superpowers is unavailable in the current host, say so and follow the
fallback lifecycle in `CONTRIBUTING.md`; do not claim that a Superpowers gate ran.

Superpowers governs method, not authority or evidence. This repository contract takes precedence when the two
intersect:

- the confirmed change contract and R0/R1/R2 decision determine scope and required human decisions;
- `ARCHITECTURE.md`, repository-owned contracts, tests, and harness checks determine acceptable artifacts;
- `uv run poe harness` supplies completion evidence; a Superpowers verification step must use it before handoff;
- when the trusted repository completion-review hook is available, it is the default final code review; otherwise use
  the applicable Superpowers review skill before handoff. Do not stack equivalent reviews over the same final diff
  unless the risk or a concrete finding justifies it;
- only a human maintainer may approve, merge, release, accept protected risk, or authorize an irreversible action.

Superpowers never grants permission to broaden intent, weaken an oracle, push directly to `main`, merge, deploy, or
perform an R2 action. When a Superpowers instruction conflicts with one of those boundaries, preserve the boundary
and report the conflict instead of silently choosing a weaker rule.

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
- Push a short-lived branch and use a pull request for changes to `main`. Never push directly to `main` or bypass
  the local pre-push guard unless the human decision owner explicitly authorizes that exact exception.
- When the trusted project Stop hook sees a new changed-work fingerprint, let it prepare the applicable committed
  branch, workspace, and deletion scopes and follow its requested read-only Codex review. The review continuation may
  inspect and report; it must not edit, commit, push, or fix its own findings. Handle an accepted finding in a
  subsequent implementation pass, rerun the harness, and let the changed result request another review.
- An enabled, non-Draft pull request triggers the repository's separate CI OpenCodeReview workflow. Do not move either
  probabilistic review lane into `check` or `harness`, and do not treat its output as approval.
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
- the disposition of material findings from the local Codex/OpenCodeReview delegate pass and any OpenCodeReview
  findings already present on the pull request, without silently fixing a finding that broadens intent or crosses an
  unconfirmed R2 boundary;
- remaining uncertainty, decisions, or follow-ups that require a human.

The agent's handoff is evidence for review, not approval to merge.
