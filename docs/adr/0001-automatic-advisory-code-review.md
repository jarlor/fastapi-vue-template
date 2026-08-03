# ADR 0001: Automatic Advisory Code Review in the Development Completion Flow

- **Status:** Accepted
- **Date:** 2026-08-03
- **Human decision owner:** @jarlor (upstream template decision only)
- **Risk class and triggers:** R2 — development hook, external tooling and model service, credentials, CI permissions,
  and verification authority
- **Related issue / pull request:** [#78](https://github.com/jarlor/fastapi-vue-template/pull/78)

## Context

The template must make AI-assisted development more reliable without allowing the implementation agent to become
its own verifier, approver, and release authority. The deterministic repository harness catches enforceable facts,
but it cannot reliably identify every omission, inconsistent assumption, or cross-file risk. A probabilistic review
can search for those issues both before local handoff and after work is offered in a pull request.

Running a model inside `poe harness` would make the required gate depend on network access, provider availability,
credentials, quota, cost, and probabilistic output. A prose-only local review instruction can be forgotten. Conversely,
a CI-only review arrives after local implementation is already complete and requires a separate provider decision.

## Decision

Keep `uv run poe harness` and `CI / required` deterministic and blocking. Add two advisory review lanes that share the
repository-owned OpenCodeReview rules but have different execution and trust boundaries.

The local completion lane:

- uses the project `.codex/hooks.json` Stop hook and repository-owned `.codex/hooks/stop_review.py` handler;
- runs only after the developer trusts the project and exact hook definition through `/hooks`;
- recognizes a new changed-work fingerprint and prepares whichever scopes apply: committed branch changes from
  `origin/main` to `HEAD` (with a local `main` fallback), tracked or untracked workspace changes, and deleted paths;
- validates pinned OpenCodeReview 1.8.5, then gives the Codex continuation exact delegate commands with
  `OCR_NO_UPDATE=1`; delegate mode selects files and resolves rules but does not call an OCR-hosted LLM;
- asks the current Codex session to perform a review-only continuation without editing, committing, pushing, or
  automatically fixing its findings, and uses a loop guard to avoid reviewing an unchanged fingerprint repeatedly;
- requires an accepted fix to happen in a later implementation pass, rerun deterministic checks, and request another
  review; any new R2 choice still stops for the human decision owner.

This local lane uses the already active Codex reviewer and therefore needs no separate OCR LLM endpoint, model name,
or API token. “Local” describes workstation orchestration, not offline inference; the active Codex account and
organization data controls still govern source/context processing. It remains outside Poe tasks and the deterministic
harness.

The pull-request lane uses a separate OpenCodeReview workflow:

- it runs automatically for enabled, non-Draft, same-repository pull requests targeting `main`, excluding Dependabot;
- it uses `pull_request_target`, reads the trusted base branch, fetches PR Git objects, and does not execute PR code;
- it posts a sticky summary and a complete inline-comment pass for each eligible update using `COMMENT`, never
  `APPROVE` or `REQUEST_CHANGES`;
- it cannot modify code, fix findings, merge, release, or change repository administration;
- its check is advisory and is not a dependency of `CI / required` or a Ruleset-required status;
- project-owned rules focus the review on the architecture, contracts, tests, security, and harness boundaries;
- the action commit and OCR CLI version are pinned, and the CLI background updater is disabled;
- generated repositories keep the workflow disabled until a human accepts the provider's data policy, configures a
  limited credential, and sets `OCR_ENABLED=true`.

The deterministic supply-chain checker verifies that this automatic review lane remains present with its narrow
permissions, repository-owned auto-discovered rules, explicit enable switch, and immutable outer action reference. It
also verifies the checked-in local hook contract, pinned delegate version, and disabled updater. It does not test or
assert model findings from either lane.

## Alternatives Considered

- **Run OCR inside `poe harness`.** This would mix probabilistic external behavior into the required deterministic
  oracle and make ordinary local development require secrets and paid network access.
- **Make OCR a required merge check.** This would block delivery on provider outages without making findings
  authoritative; OpenCodeReview exits successfully when it reports findings.
- **Use only the automatic PR workflow.** This preserves durable PR evidence but provides no automatic review before
  local handoff and requires a separately approved external provider.
- **Use only local Codex delegation.** This avoids a second provider, but the developer can disable or bypass a local
  hook and the current Codex context is not an independent human approval. The optional PR lane provides a later,
  separately configured pass.
- **Start a second local OCR model.** This would add credentials, data transfer, cost, and another provider boundary
  without changing the fact that all AI findings remain advisory.
- **Vendor the complete action.** This could pin every transitive action and binary checksum, but adds substantial
  maintenance. It remains an option for a future high-assurance profile.

## Consequences

Developers using a trusted Codex project hook receive an automatic, read-only review request for each new changed-work
fingerprint. Reviewing the applicable branch, workspace, and supplemental deletion scopes avoids ignoring committed,
uncommitted, or removed work. Requiring fixes to occur in a later implementation pass preserves a visible boundary
between finding and changing code, but does not make the current Codex context an independent authority.

The project hook is executable project configuration and runs outside the Codex sandbox. A developer must inspect and
trust its exact definition, and a Codex user or administrator may disable it. Development through another client may
bypass it entirely. It is therefore a strong workflow default, not a security boundary, required status, or merge
control. The loop guard records only that a continuation returned with an unchanged fingerprint; it cannot attest that
the agent followed the instructions or produced complete findings. The pinned OCR version and disabled updater reduce
drift; they do not cryptographically authenticate an executable supplied by the developer's `PATH`. The handler
rejects repository-local OCR executables, and the checked-in handler, rule-selection, and review-guidance digests
force a new `/hooks` trust decision when any artifact changes. These controls do not remove the need to review hook
changes. The default trusts workstation Python/Git/OCR/Node binaries, `PATH`, Git configuration and filters, and Git
metadata; hostile-checkout isolation would be a separate R2 design, not more code in this template hook.

Every enabled PR update receives an automatic second-pass review after the contributor marks the work ready. Humans
get line-level findings without delegating approval. OpenCodeReview 1.8.5 excludes deleted files, so deletion
consequences remain owned by deterministic checks and human diff review. Low-severity, style, and documentation
findings are routed to the summary to limit review noise. Generated repositories leave this CI lane disabled by
default.

Enabling the workflow sends changed code and repository context to the selected LLM provider and consumes its quota.
It therefore requires a provider approved for the repository's confidentiality level and a dedicated, limited
credential. External fork PRs and Dependabot PRs are not reviewed automatically to prevent untrusted quota spending.

Pinning the outer OpenCodeReview action and CLI does not make the current upstream composite action fully hermetic:
version 1.8.5 internally references mutable major tags for GitHub-maintained actions and installs the CLI through npm.
The advisory status, GitHub-hosted ephemeral runner, disabled updater, and narrow token permissions contain but do not
eliminate that residual supply-chain risk.

## Architecture and Contract Impact

The four-authority model is unchanged. The harness and CI retain verification authority over deterministic facts;
the local Codex pass and CI OpenCodeReview supply advisory evidence; the human decision owner accepts intent and risk;
the maintainer retains merge and release authority. The Codex continuation runs the local delegate and reads diffs
without intentionally executing product code; the out-of-sandbox hook itself only fingerprints Git state and checks
the OCR version under the trusted-workstation assumption. The PR workflow may write only pull-request comments and
read repository contents.

## Verification

Harness tests cover the local hook definition and handler behavior as deterministic artifacts, plus the workflow's
immutable action reference, fixed CLI version, trusted rules, enable guard, trigger, and exact permission set. They do
not assert probabilistic review findings. The complete repository harness must remain green. A local trial verifies
the branch, workspace, and deletion scopes, one-request-per-fingerprint loop guard, and review-only continuation.
After a generated repository configures its provider, a trial pull request verifies that a sticky summary and any
inline comments are posted without executing PR code or affecting `CI / required`.

## Rollback or Reversal

Set `OCR_ENABLED=false` to stop CI provider calls immediately. Disabling or declining trust for the project Stop hook
stops the local advisory lane without changing the deterministic delivery path, but is an explicit bypass of the team
default. A later R2 pull request may remove either lane, its rules, documentation, and checker invariant. No
application data migration is required.

## Human Approval

For the upstream template, @jarlor approved the trusted local Codex Stop-hook review and the separately enabled PR
OpenCodeReview workflow as advisory completion-stage lanes. Pull request #78 is that upstream approval and
residual-risk record. A generated repository inherits the design, not this authority: its maintainers must inspect and
trust the local executable hook for their environment and separately own and record the R2 provider/data decision
before enabling the CI lane.
