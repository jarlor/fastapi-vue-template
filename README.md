# Human-Governed FastAPI + Vue Team Template

A human-governed, AI-assisted team template built with **FastAPI**, **Vue 3**, **Arco Design**, and **Vite**.

The template is designed for teams that want AI to accelerate implementation without delegating product intent, verification, approval, or release authority to AI. Repository-owned checks enforce code and contract invariants; humans remain accountable for requirements, risk acceptance, and merge decisions.

## Operating Model

Work separates intent, implementation, verification, and release authority so that an AI implementation cannot approve itself. The authoritative collaboration and risk model is defined in [CONTRIBUTING.md](CONTRIBUTING.md).

[Superpowers](https://github.com/obra/superpowers) is the standard behavioral workflow for AI-led development. It
drives planning, implementation, debugging, verification, and branch completion; the repository Harness determines
whether the resulting artifacts satisfy this project's architecture, contracts, security, and test expectations.
Superpowers is installed in the developer's code-agent host rather than vendored into every generated repository.

## Technology

| Surface | Technology |
|---|---|
| Backend | FastAPI, Pydantic Settings, Loguru |
| Frontend | Vue 3, Arco Design, Vite, Pinia |
| Python | Python 3.13+, managed by `uv` |
| Node | Node 22.12+, selected by `.node-version`; npm lockfile is authoritative |
| Task interface | Poe, invoked through `uv run poe` |
| Quality gates | Ruff, pytest, architecture and contract checks, frontend tests |
| Local advisory review | Trusted Codex Stop hook with OpenCodeReview delegation |
| PR advisory review | Optional OpenCodeReview on enabled, non-Draft pull requests |

## Create a Repository

Prerequisites: Git 2.41+, Python 3.13+, `uv`, Node.js 22.12+, and npm 10.9.x. The repository's `.node-version`
and lockfiles define the reproducible toolchain and dependencies.

Create a repository with GitHub's **Use this template** action, then clone it locally:

```bash
git clone REPOSITORY_URL
cd REPOSITORY_NAME
uv sync --frozen
npm --prefix src/frontend ci
uv run pre-commit install
```

Install Superpowers in each code-agent host used for AI-led development:

- **Codex App or CLI:** open `/plugins`, search for `Superpowers`, and install the official plugin.
- **Claude Code:** run `/plugin install superpowers@claude-plugins-official`.

Restart or reload the host if it requests that step, then confirm that the Superpowers skills are available. Project
files cannot install or trust a user-level plugin on someone else's behalf. If a contributor's host cannot run
Superpowers, the repository lifecycle remains usable as a fallback, but the contributor must disclose that fact in
the handoff or pull request.

The last command installs both the normal commit checks and a local pre-push guard. The guard rejects the usual
direct push to `main` and tells the contributor to use a short-lived branch and pull request instead.

Install the pinned OpenCodeReview delegate once on each development machine:

```bash
npm install -g @alibaba-group/open-code-review@1.8.5
OCR_NO_UPDATE=1 ocr version
```

In PowerShell, verify with `$env:OCR_NO_UPDATE = "1"; ocr version` instead. The hook rejects an `ocr` executable that
resolves inside the repository; the developer-managed executable on `PATH` remains a trusted machine prerequisite,
and its version output is a drift check rather than cryptographic provenance.

The version output must start with `open-code-review v1.8.5 (582953937)`. In a Codex host that supports project hooks,
open the repository, run `/hooks`, inspect the Stop hook and its three bound artifacts, and trust that exact
definition. The published setup path is the current Codex CLI; for another host, first confirm that `/hooks` shows
this project Stop hook. Project hooks execute outside the Codex sandbox, and generated repositories do not inherit
the template maintainer's trust decision. Changes to the handler, rule selection, or review guidance change the
trusted digests and require another inspection and `/hooks` trust decision.

The template intentionally does not choose a software license for the generated product. Select and add the product's
license before distributing it outside your organization; absence of a license is not an open-source grant.

The default template does not change GitHub repository permissions, Rulesets, or branch protection. Its Git policy is
deliberately soft: local hooks can be bypassed, and a green `CI / required` result is evidence that maintainers agree
to require before merging rather than a GitHub-enforced merge lock. This keeps the baseline useful for free and
private repositories without pretending that repository files can enforce server-side permissions. Optional
server-side enforcement is described in [CONTRIBUTING.md](CONTRIBUTING.md#optional-server-side-enforcement).

### Enable Automatic PR Advisory Review

The template includes a safe-by-default OpenCodeReview workflow, but generated repositories leave it disabled until
a human approves the model provider and its data policy. GitHub Actions cannot reuse a local Codex session; configure
these under **Settings → Secrets and variables → Actions**:

| Kind | Name | Value |
|---|---|---|
| Secret | `OCR_LLM_URL` | Approved LLM API endpoint |
| Secret | `OCR_LLM_AUTH_TOKEN` | Dedicated, limited provider credential |
| Variable | `OCR_LLM_MODEL` | Provider model name |
| Variable | `OCR_LLM_USE_ANTHROPIC` | `true` for Anthropic; `false` for an OpenAI-compatible API |
| Variable | `OCR_ENABLED` | Set to `true` only after the four values above are ready |

Once enabled, every non-Draft, non-Dependabot, same-repository PR opened or updated against `main` is reviewed
automatically. Source diffs and repository context are sent to the configured provider. The bot posts advisory
comments only: it cannot fix, approve, merge, or release the change, and its check is not part of `CI / required`. See
the review boundary in
[CONTRIBUTING.md](CONTRIBUTING.md#automatic-advisory-review) and the accepted trade-offs in
[ADR 0001](docs/adr/0001-automatic-advisory-code-review.md).

## Develop

```bash
cp .env.example .env
uv run poe api
uv run poe frontend
```

Use the public repository commands for local product feedback:

```bash
uv run poe check       # fast feedback while editing
uv run poe verify      # complete verification before handoff or a PR update
```

GitHub Actions invokes `jarlor/fastapi-vue-harness` at a full commit SHA. The central Action reruns `verify` and adds
architecture, frontend-boundary, security, and supply-chain checks without copying their implementation or self-tests
into repositories created from this template.

After changed work reaches a stopping point, the trusted Stop hook fingerprints the committed-branch and workspace
state, verifies the pinned OCR command, and gives Codex exact read-only preview, rule, diff, and deletion commands.
Codex runs those commands in its normal sandbox; OCR delegate mode selects reviewable files and resolves
repository-owned rules. This local lane needs no separate OCR model endpoint or API token. A new fingerprint gets one
automatic review-continuation request; unchanged state is not requested again. “Local” describes workstation
orchestration, not offline inference: the active Codex account and organization data controls still govern source and
context processing. Use `check` while fixing accepted findings, then rerun `verify` and request another review.

The hook is a visible, bypassable workflow guardrail, not a security boundary, required status, human approval, or
merge authority. It runs only after the repository and exact hook definition are trusted, can be disabled by the
developer or administrator, and can observe that a continuation returned but cannot prove review quality. It must
never replace deterministic checks or human R2 decisions. The hook does not intentionally run build, test, or
application commands, but its out-of-sandbox Git fingerprinting and OCR version check rely on trusted workstation
Python/Git/OCR binaries, `PATH`, Git configuration and filters, and uncompromised worktree/Git metadata. Adversarial
repository inspection belongs in a separately isolated R2 workflow, not this default hook. The complete lifecycle is in
[CONTRIBUTING.md](CONTRIBUTING.md#local-development-lifecycle).

## Repository Guides

Each concept has one authoritative guide:

| Guide | Authority |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Enforceable code, dependency, runtime, and contract boundaries |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Human/AI authority, risk classification, GitHub Flow, and governance changes |
| [AGENTS.md](AGENTS.md) | Operating contract for AI coding agents |
| [ADR template](docs/adr/0000-template.md) | Record for durable, high-impact technical decisions |

AI agents start with [AGENTS.md](AGENTS.md). Human contributors start with [CONTRIBUTING.md](CONTRIBUTING.md).

## Template Defaults

- Backend code lives under `src/app`; frontend code lives under `src/frontend`.
- `src/app/contexts/tasks` is a runnable reference context, not an empty directory blueprint.
- The API uses a `create_app()` factory and the versioned `/api/v1` prefix.
- Successful responses use the shared `{ code, success, data, message }` envelope.
- Non-sensitive defaults live in `config.yaml`; secrets belong in the environment.
- `main` is treated as the releasable branch. The local workflow sends changes through short-lived branches and pull
  requests; server-side protection is optional and is not configured by the template.
- Dependabot keeps `uv`, npm, and pinned GitHub Actions dependencies visible through reviewable pull requests.

For the reasons behind these boundaries, see [ARCHITECTURE.md](ARCHITECTURE.md).
