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

## Local Development Lifecycle

The end-to-end path uses GitHub Flow while keeping intent, deterministic verification, AI review, and release
authority separate:

1. Confirm the change contract, acceptance examples, non-goals, risk class, and human decision owner. Stop for
   explicit human approval before any R2 implementation.
2. Update local `main`, then create a short-lived branch such as `feat/<topic>`, `fix/<topic>`, or `chore/<topic>`.
3. Make the smallest coherent change and add focused tests. Use `uv run poe check` for fast feedback while editing,
   and commit coherent branch checkpoints when useful.
4. Run `uv run poe harness` before handoff or pull-request updates. This remains the local deterministic oracle.
5. When Codex reaches a stopping point with a new repository fingerprint, allow the trusted project Stop hook to
   verify the pinned OCR command and request a review-only continuation with exact branch/workspace commands.
6. Triage each material local finding against the confirmed intent and contracts. The review continuation reports
   findings but does not edit, commit, or push. Apply an accepted fix only in a subsequent implementation pass; ask
   the human decision owner first if it broadens scope or exposes an R2 choice.
7. After a fix, use `check` while iterating, then rerun `harness`. The changed fingerprint triggers another local
   review request before handoff.
8. Push the branch and open or update a pull request to `main` using the repository template. Draft pull requests are
   encouraged for unresolved human decisions.
9. Resolve the required deterministic CI, human review, and—when separately enabled—the automatic PR advisory
   review. Do not weaken an oracle merely to fit the implementation.
10. A human maintainer squash-merges with a Conventional Commit pull-request title only after required evidence and
    approvals are complete. `main` remains protected and releasable.

### Local Codex Completion Review

Install OpenCodeReview 1.8.5 and trust the exact project hook through `/hooks` as described in
[README.md](README.md#create-a-repository). For each new changed-work fingerprint, `.codex/hooks.json` invokes the
repository-owned Stop handler. It emits exact OpenCodeReview commands for whichever scopes apply:

- committed branch changes from `origin/main` to `HEAD`, falling back to local `main` when necessary;
- the current workspace, including tracked and untracked changes.

Because OCR 1.8.5 excludes deleted files from its reviewable list, the continuation also receives root-anchored Git
commands that enumerate and inspect deletions directly.

The delegate selects reviewable files and auto-discovers `.opencodereview` rules; it does not call an OCR-hosted model.
The current Codex session is the read-only reviewer, so this lane needs no separate OCR LLM URL, model name, or API
token. It is workstation-orchestrated rather than offline: the active Codex account and organization data controls
still apply to source/context processing. The handler validates the pinned CLI, and the continuation uses
`OCR_NO_UPDATE=1`; unchanged fingerprints are not requested again. Deterministic checks still run independently.

The Stop hook executes only in a trusted project and after the developer trusts its exact definition. Codex or an
administrator can disable it, and development outside that configured client can bypass it. It is therefore a team
workflow guardrail—not a security boundary, required merge check, independent approval, or substitute for human R2
decisions. Its loop guard records that the continuation returned for an unchanged fingerprint; it cannot prove that
the agent followed the review instructions or that the findings were complete. A zero-finding review is useful
evidence, not approval.

This default assumes a trusted developer workstation. The hook does not deliberately invoke project build, test, or
application commands, but it fingerprints through Git outside the Codex sandbox. The selected Python, Git, OCR and
Node installations, `PATH`, system/global/local Git configuration and filters, and the worktree's Git metadata are
therefore machine prerequisites, not security boundaries enforced by this template.

## GitHub Flow

The lifecycle above is the repository's GitHub Flow: all product work reaches protected `main` through a short-lived
branch and pull request. The local review improves the work before it is offered for review; required CI and human
merge authority remain on GitHub.

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

## Automatic Advisory Review

`.github/workflows/open-code-review.yml` is the optional CI heuristic lane in the completion flow. It is distinct from
the local Codex Stop-hook review and is disabled by default in generated repositories. When `OCR_ENABLED=true`,
opening, reopening, marking ready, or updating a non-Draft same-repository PR against `main` triggers OpenCodeReview.
Dependabot and external fork PRs are excluded from automatic model spending. Required CI and the advisory review may
run concurrently after work is offered for review; OpenCodeReview is deliberately not executed by the local
deterministic harness.

The workflow reads the trusted base branch, fetches the proposed Git objects without executing PR code, and sends the
diff plus relevant repository context to the configured LLM provider. Enabling it is an R2 data and provider decision:
use a provider approved for the repository's confidentiality level and a dedicated credential with an appropriate
quota. GitHub Actions cannot reuse the developer's Codex session or local OCR setup. Configuration names and
activation order are documented in [README.md](README.md#enable-automatic-pr-advisory-review).

OpenCodeReview submits `COMMENT` reviews and a sticky summary. It does not approve, request changes, fix code, or own a
merge decision. Findings do not fail the check, and provider or action availability is not part of `CI / required`.
Each eligible PR update publishes a new pass over files OCR considers reviewable; OCR 1.8.5 excludes deleted files,
so removal consequences remain part of deterministic checks and human diff review. Earlier inline comments remain as
review history rather than suppressing a new finding merely because it touches the same lines.
The human reviewer validates each material finding against intent, contracts, and risk. A valid fix remains subject to
the confirmed change scope, must rerun `uv run poe harness`, and needs new human confirmation if it exposes an R2
decision. A false positive may be resolved with a concise explanation; zero findings is evidence, not approval.

The `team` and `high-assurance` governance profiles require review-thread resolution, so their normal human workflow
also closes or explains OpenCodeReview inline threads. This does not turn the bot into an eligible approving reviewer.
Set `OCR_ENABLED=false` to stop external model calls without weakening deterministic CI.

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

The local advisory review is Stop-hook driven and intentionally has no Poe task; it remains outside these
deterministic commands.

`repo-bootstrap` is the stable GitHub-governance entrypoint described above. Targeted Poe tasks and scripts may evolve; CI and contributor documentation should call the stable interfaces.
