# Human-Governed FastAPI + Vue Team Template

A human-governed, AI-assisted team template built with **FastAPI**, **Vue 3**, **Arco Design**, and **Vite**.

The template is designed for teams that want AI to accelerate implementation without delegating product intent, verification, approval, or release authority to AI. Repository-owned checks enforce code and contract invariants; humans remain accountable for requirements, risk acceptance, and merge decisions.

## Operating Model

Work separates intent, implementation, verification, and release authority so that an AI implementation cannot approve itself. The authoritative collaboration and risk model is defined in [CONTRIBUTING.md](CONTRIBUTING.md).

## Technology

| Surface | Technology |
|---|---|
| Backend | FastAPI, Pydantic Settings, Loguru |
| Frontend | Vue 3, Arco Design, Vite, Pinia |
| Python | Python 3.13+, managed by `uv` |
| Node | Node 22.12+, selected by `.node-version`; npm lockfile is authoritative |
| Task interface | Poe, invoked through `uv run poe` |
| Quality gates | Ruff, pytest, architecture and contract checks, frontend tests |
| Advisory review | OpenCodeReview on enabled, non-Draft pull requests |

## Create a Repository

Prerequisites: Git, Python 3.13+, `uv`, Node.js 22.12+, and npm 10.9.x. The repository's `.node-version`
and lockfiles define the reproducible toolchain and dependencies.

Create a repository with GitHub's **Use this template** action, then clone it locally:

```bash
git clone REPOSITORY_URL
cd REPOSITORY_NAME
uv sync --frozen
npm --prefix src/frontend ci
uv run pre-commit install
```

The template intentionally does not choose a software license for the generated product. Select and add the product's
license before distributing it outside your organization; absence of a license is not an open-source grant.

Preview the GitHub control plane before applying it:

```bash
uv run poe repo-bootstrap bootstrap \
  --repository OWNER/REPOSITORY \
  --profile solo-safe \
  --maintainer @MAINTAINER \
  --dry-run
```

After the human maintainer confirms the plan, let `CI / required` run once on `main`, then rerun the command with
`--apply` and an authorized `GH_TOKEN`. A read-only preflight verifies repository access, CODEOWNER identities and
write permissions, reviewer capacity, Rulesets availability, and the real GitHub Actions integration behind the
required check before anything is changed. The command then renders CODEOWNERS and converges the protected `main`
Ruleset. Team profiles, token permissions, and recovery behavior are documented in
[CONTRIBUTING.md](CONTRIBUTING.md).

### Enable Automatic Advisory Review

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

Use the public repository commands instead of invoking scripts under `scripts/harness/` directly:

```bash
uv run poe check       # fast feedback while editing
uv run poe harness     # complete required verification before a PR
```

Command semantics and the GitHub Flow are maintained in [CONTRIBUTING.md](CONTRIBUTING.md).

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
- `main` is the protected, releasable branch. Work reaches it through short-lived branches and pull requests.
- Dependabot keeps `uv`, npm, and pinned GitHub Actions dependencies visible through reviewable pull requests.

For the reasons behind these boundaries, see [ARCHITECTURE.md](ARCHITECTURE.md).
