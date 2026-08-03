# ADR 0001: Automatic Advisory Code Review in the PR Completion Flow

- **Status:** Accepted
- **Date:** 2026-08-03
- **Human decision owner:** @jarlor
- **Risk class and triggers:** R2 — external model service, credentials, CI permissions, and verification authority
- **Related issue / pull request:** [#78](https://github.com/jarlor/fastapi-vue-template/pull/78)

## Context

The template must make AI-assisted development more reliable without allowing the implementation agent to become
its own verifier, approver, and release authority. The deterministic repository harness catches enforceable facts,
but it cannot reliably identify every omission, inconsistent assumption, or cross-file risk. A separate AI review can
search for those issues after work is offered for review.

Running a model inside `poe harness` would make the required gate depend on network access, provider availability,
credentials, quota, cost, and probabilistic output. A local-only review instruction can also be forgotten or performed
by the same implementation context without independent evidence.

## Decision

Keep `uv run poe harness` and `CI / required` deterministic and blocking. Add a separate OpenCodeReview workflow to
the pull-request review stage:

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
does not test or assert model findings.

## Alternatives Considered

- **Run OCR inside `poe harness`.** This would mix probabilistic external behavior into the required deterministic
  oracle and make ordinary local development require secrets and paid network access.
- **Make OCR a required merge check.** This would block delivery on provider outages without making findings
  authoritative; OpenCodeReview exits successfully when it reports findings.
- **Use only a local Codex delegation review.** This is useful on demand but can be skipped and may leave the
  implementation model reviewing its own work.
- **Vendor the complete action.** This could pin every transitive action and binary checksum, but adds substantial
  maintenance. It remains an option for a future high-assurance profile.

## Consequences

Every enabled PR update receives an automatic second-pass review after the contributor marks the work ready. Humans
get line-level findings without delegating approval. Low-severity, style, and documentation findings are routed to the
summary to limit review noise.

Enabling the workflow sends changed code and repository context to the selected LLM provider and consumes its quota.
It therefore requires a provider approved for the repository's confidentiality level and a dedicated, limited
credential. External fork PRs and Dependabot PRs are not reviewed automatically to prevent untrusted quota spending.

Pinning the outer OpenCodeReview action and CLI does not make the current upstream composite action fully hermetic:
version 1.8.5 internally references mutable major tags for GitHub-maintained actions and installs the CLI through npm.
The advisory status, GitHub-hosted ephemeral runner, disabled updater, and narrow token permissions contain but do not
eliminate that residual supply-chain risk.

## Architecture and Contract Impact

The four-authority model is unchanged. The harness and CI retain verification authority over deterministic facts;
OpenCodeReview supplies advisory evidence; the human decision owner accepts intent and risk; the maintainer retains
merge and release authority. The new workflow may write only pull-request comments and read repository contents.

## Verification

Harness tests cover the workflow's immutable action reference, fixed CLI version, trusted rules, enable guard, trigger,
and exact permission set. The complete repository harness must remain green. After a generated repository configures
its provider, a trial pull request verifies that a sticky summary and any inline comments are posted without executing
PR code or affecting `CI / required`.

## Rollback or Reversal

Set `OCR_ENABLED=false` to stop model calls immediately without changing the deterministic delivery path. A later R2
pull request may remove the workflow, rules, documentation, and checker invariant. No application data migration is
required.

## Human Approval

@jarlor approved automatic OpenCodeReview integration as an advisory completion-stage review. Pull request #78 is the
durable approval and residual-risk record.
