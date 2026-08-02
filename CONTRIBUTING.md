# Contributing

This repository uses a human-governed, AI-assisted development model. AI may accelerate implementation and review, but it does not own product intent, risk acceptance, or release authority.

## Four Authorities

| Authority | Accountable owner | Repository evidence |
|---|---|---|
| Intent | Human decision owner | Issue change contract and acceptance examples |
| Implementation | Human contributor or AI agent | Pull-request diff and implementation tests |
| Verification | Repository-owned harness and CI | Required status checks and contract results |
| Release | Human maintainer | Protected-branch merge record |

One person may participate in more than one activity, but implementation never becomes its own independent approval. AI-generated review is advisory and cannot replace the human decision owner or maintainer.

## Change Contract

Start meaningful work with the [change issue form](.github/ISSUE_TEMPLATE/change.yml), or provide the same information in an existing issue:

- **Intent:** the problem and desired outcome;
- **Acceptance examples:** externally observable examples of success;
- **Non-goals:** behavior intentionally outside this change;
- **Risk:** the risk class, applicable triggers, and human decision owner.

AI may draft this contract. A human must confirm it before protected-risk implementation begins. Tests and implementation may elaborate approved examples, but must not silently redefine them.

## Risk Classes

### R0 — Mechanical

No intended runtime or public-contract behavior changes. Examples include formatting, typo fixes, and verified mechanical renames. Normal review and required checks are sufficient.

### R1 — Product Behavior

Behavior changes within existing architecture, security, data, deployment, and public-contract boundaries. The human decision owner confirms acceptance examples; implementation then proceeds through the normal pull-request flow.

### R2 — Protected

Explicit human approval is required before implementation when a change affects any of the following:

- a public API, shared contract, compatibility promise, or configuration contract;
- authentication, authorization, credentials, privacy, PII, payments, or security posture;
- persisted data shape, migration, retention, deletion, or other irreversible operation;
- a new external service, runtime dependency, provider, or infrastructure assumption;
- an architecture invariant or cross-context ownership boundary;
- removal or weakening of approved acceptance tests or contracts, or changes to CI, harness checks, branch protection, or other verification authority;
- deployment behavior, production resources, secrets, or release policy.

R2 changes require maintainer review. Use an ADR when the decision is durable, costly to reverse, or changes an invariant.

## GitHub Flow

`main` is protected and must remain releasable.

1. Confirm the change contract and risk class.
2. Create a short-lived branch from current `main`, such as `feat/<topic>`, `fix/<topic>`, or `chore/<topic>`.
3. Make the smallest coherent change. Use `uv run poe check` for fast local feedback.
4. Run `uv run poe harness` before requesting review.
5. Open a pull request to `main` using the repository template. Draft pull requests are encouraged for early human decisions.
6. Resolve required checks and human review without weakening the oracle to fit the implementation.
7. Squash-merge with a Conventional Commit pull-request title.

## GitHub Control Plane

`repo-bootstrap` renders CODEOWNERS and idempotently configures repository merge settings and the protected `main` ruleset. Select the governance profile that matches the actual team:

- `solo-safe` protects required checks and history without requiring an impossible self-approval;
- `team` requires code-owner review and approval from someone other than the last pusher. Declare at least two
  eligible human reviewers so a maintainer-authored pull request still has an independent reviewer;
- `high-assurance` requires two non-author approvals, code-owner review, and fresh reviews after changes. Declare at
  least three eligible humans so any one of them may author a pull request without locking the merge path.

For `team` and `high-assurance`, `--eligible-reviewers` is mandatory. When CODEOWNERS are individual users, the
command also requires at least two or three distinct `--maintainer` handles respectively. An organization team may
stand in for those individual handles, but its eligible reviewer count must be explicitly declared; preflight still
verifies that the team exists, is visible, and has write access to the repository.

Start with `solo-safe` unless the independent reviewer capacity already exists. Always inspect a dry-run first:

```bash
uv run poe repo-bootstrap bootstrap \
  --repository OWNER/REPOSITORY \
  --profile solo-safe \
  --maintainer @MAINTAINER \
  --dry-run
```

A two-person team uses both personal CODEOWNERS and an explicit capacity declaration:

```bash
uv run poe repo-bootstrap bootstrap \
  --repository OWNER/REPOSITORY \
  --profile team \
  --maintainer @ALICE \
  --maintainer @BOB \
  --eligible-reviewers 2 \
  --dry-run
```

For an organization team, use `--maintainer @ORG/TEAM --eligible-reviewers 2` (or `3` for `high-assurance`). The
number is a human declaration of genuinely available reviewers, not a way to bypass GitHub permission checks.

Before applying, merge the CI workflow and let the `CI / required` check run on `main`. During `--apply`, bootstrap
discovers that check's actual GitHub Actions integration ID and binds the required status to it. If no such check run
exists, bootstrap stops during read-only preflight without writing CODEOWNERS or changing repository settings; it
never guesses a global App ID or leaves the required context open to another status provider.

Applying changes GitHub repository state and requires explicit human approval plus an authorized token. A
fine-grained token needs repository **Metadata: read** and **Administration: write**; organization-team CODEOWNERS
also need organization **Members: read**. A classic token needs `repo` and, for teams, `read:org`. Rulesets work for
public repositories on GitHub Free and for private repositories on GitHub Pro, Team, or Enterprise. Provide the token
through the environment without writing it into a command, file, or shell history:

```bash
uv run poe repo-bootstrap bootstrap \
  --repository OWNER/REPOSITORY \
  --profile solo-safe \
  --maintainer @MAINTAINER \
  --apply
```

All preflight calls are read-only. Mutation then proceeds in named stages: `codeowners`, `repository-settings`, and
`ruleset`. A failure prints machine-readable JSON listing completed and uncompleted stages; no cross-system rollback
is claimed. Inspect that report, correct the cause, and rerun the same convergent command.

Commit the rendered `.github/CODEOWNERS` through the normal pull-request flow. Rerun the command when the chosen
profile or maintainer set changes. Do not treat possession of a token as approval to apply the plan.

## Agent Identity Boundary

An AI agent should operate through a separate, least-privilege identity or stop at a local branch for a human to push.
An agent identity may update task branches and pull requests, but it must not have repository-administration, Ruleset
bypass, release-tag, production Environment approval, or production-secret permissions. If an agent uses a human
administrator's unrestricted credentials, GitHub cannot distinguish its actions from that administrator; repository
checks alone cannot restore that lost authority boundary.

## Review Responsibilities

Repository checks review deterministic facts: tests, contracts, dependencies, architecture imports, frontend boundaries, runtime construction, and security baselines.

AI review may search for omissions, inconsistent assumptions, and cross-file risks. Human review remains responsible for:

- whether the change solves the intended problem;
- whether acceptance examples and non-goals are correct;
- whether protected-risk trade-offs are acceptable;
- whether a test, contract, or gate change weakens independent verification;
- whether the result is ready to merge or release.

A green check is necessary but not sufficient approval. A human approval without required green checks is also insufficient.

## Changing the Harness

The harness governs artifacts, not contributor behavior. A new blocking rule must:

- be deterministic and tied to an observable repository invariant;
- have a low expected false-positive rate and an actionable failure message;
- include pass and fail tests for its checker;
- be owned by an explicit repository invariant or approved product contract, not one contributor's tool preference;
- avoid checking whether README, AGENTS, a PR, a human, or an AI repeated a prescribed sentence or ritual.

Trial uncertain rules as report-only checks. Promote them only after evidence shows they are reliable. When executable verification becomes authoritative, remove duplicate prose assertions and checklist evidence.

## Repository Commands

These are the stable public interfaces:

```bash
uv run poe check       # fast local feedback
uv run poe harness     # complete required verification
```

`repo-bootstrap` is the stable GitHub-governance entrypoint described above. Targeted Poe tasks and scripts may evolve; CI and contributor documentation should call the stable interfaces.
