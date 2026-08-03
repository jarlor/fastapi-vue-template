# Contributing

This repository uses a human-governed, AI-assisted development model. AI may accelerate implementation and review, but it does not own product intent, risk acceptance, or release authority.

## Four Authorities

| Authority | Accountable owner | Repository evidence |
|---|---|---|
| Intent | Human decision owner | Issue change contract and acceptance examples |
| Implementation | Human contributor or AI agent | Pull-request diff and implementation tests |
| Verification | Repository-owned harness and CI | Expected CI summary and contract results |
| Release | Human maintainer | Pull-request merge record |

One person may participate in more than one activity, but implementation never becomes its own independent approval. AI-generated review is advisory and cannot replace the human decision owner or maintainer.

## Agent Method and Repository Authority

AI-led development uses [Superpowers](https://github.com/obra/superpowers) as the standard working method. Its skills
provide the behavioral workflow: clarify intent, design and plan when appropriate, implement with tests, debug from
evidence, review changes, verify fresh results, and prepare a branch for delivery.

The repository remains the authority over outcomes. Superpowers does not replace the change contract, risk model,
architecture invariants, repository commands, CI, human review, or release decision. In particular:

| Concern | Authority |
|---|---|
| How the agent plans, implements, debugs, and checks its work | Applicable Superpowers skills |
| Product intent, acceptance examples, non-goals, and risk acceptance | Human-confirmed change contract |
| Architecture, contracts, security, and other enforceable invariants | Repository files, `uv run poe verify`, and the pinned central CI Harness |
| Completion-stage advisory code review | Repository local review lane when supported; otherwise Superpowers review; optional PR review |
| Merge and release readiness | Human maintainer |

Do not duplicate every Superpowers checklist in repository documentation or turn its prescribed rituals into Harness
checks. Conversely, do not cite completion of a Superpowers workflow as proof that repository checks passed. A host
without Superpowers may use the lifecycle below as a fallback, but the contributor must disclose that the standard
agent method was unavailable.

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
3. Use the applicable Superpowers skills to design or plan at the scale of the change, implement the smallest coherent
   solution, add focused tests, and debug failures from evidence. Use `uv run poe check` for fast feedback while
   editing, and commit coherent branch checkpoints when useful.
4. Use Superpowers verification-before-completion with `uv run poe verify` as the required fresh command before
   handoff or pull-request updates. This remains the local deterministic oracle.
5. Superpowers process reviews may be used for risky intermediate changes. At final completion in Codex, avoid an
   additional generic AI review of the same diff and allow the trusted project Stop hook to provide the standard final
   pass: when it sees a new repository fingerprint, let it verify the pinned OCR command and request a review-only
   continuation with exact branch/workspace commands. In a host without that trusted completion hook, use the
   applicable Superpowers review skill before handoff instead.
6. Triage each material local finding against the confirmed intent and contracts. The review continuation reports
   findings but does not edit, commit, or push. Apply an accepted fix only in a subsequent implementation pass; ask
   the human decision owner first if it broadens scope or exposes an R2 choice.
7. After a fix, use `check` while iterating, then rerun `verify`. The changed fingerprint triggers another local
   review request before handoff.
8. Push the branch and open or update a pull request to `main` using the repository template. Draft pull requests are
   encouraged for unresolved human decisions.
9. Resolve the expected deterministic CI, human review, and—when separately enabled—the automatic PR advisory
   review. Do not weaken an oracle merely to fit the implementation.
10. Use the Superpowers branch-finishing workflow only to prepare or update the pull request. It does not authorize a
    local merge, branch discard, direct push to `main`, release, or deployment. A human maintainer squash-merges with
    a Conventional Commit pull-request title only after expected evidence and approvals are complete. Treat `main`
    as releasable even when the GitHub plan does not enforce that convention.

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

## GitHub Flow and the Soft PR Gate

The lifecycle above is the repository's GitHub Flow: normal product work reaches `main` through a short-lived branch
and pull request. `uv run pre-commit install` installs a local pre-push guard that rejects the usual direct push to
`main`. Contributors and AI agents must not use `--no-verify` to bypass it without explicit human authorization for
that exception.

On a pull request, CI validates the Conventional Commit title and invokes the central Harness Action at a full commit
SHA. That action runs `uv run poe verify` and the centrally owned architecture, frontend-boundary, security, and
supply-chain checks against this repository. `CI / required` is the single stable summary result maintainers inspect
before squash-merging. The local OpenCodeReview pass and optional PR OpenCodeReview pass are advisory; human review
still owns intent, risk, and merge readiness.

These are repository conventions, not a security boundary. A developer can bypass local hooks, and without GitHub
branch protection or a Ruleset the hosting service can still accept a direct push or merge with failing CI. The
template states that limitation plainly and does not add a brittle CI job that tries to infer a direct push after it
has already happened.

## Optional Server-Side Enforcement

Server-side enforcement is outside the default template. If the repository's GitHub plan and team model support it,
the existing `uv run poe repo-bootstrap bootstrap ...` command can preview and apply CODEOWNERS, merge settings, and
a `main` Ruleset. `--apply` mutates external repository state and always requires explicit human authorization for
the exact repository, profile, and maintainers. Teams that do not enable it continue to use the soft PR gate above.

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
the confirmed change scope, must rerun `uv run poe verify`, and needs new human confirmation if it exposes an R2
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
uv run poe verify      # complete local verification before handoff
```

`uv run poe harness` remains a compatibility alias for `verify`; new automation and documentation must use the
explicit command names. Central checker implementation and its self-tests live behind the pinned
`jarlor/fastapi-vue-harness` CI Action, so generated repositories do not inherit the checker test suite or a Harness
application dependency.

The local advisory review is Stop-hook driven and intentionally has no Poe task; it remains outside these
deterministic commands.

`repo-bootstrap` is an optional GitHub-governance entrypoint, not part of the baseline setup. Targeted Poe tasks and
scripts may evolve; CI and contributor documentation should call the stable interfaces.
