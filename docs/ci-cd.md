# CI/CD

The template ships with full-stack GitHub Actions. CI and governance are always safe to keep enabled. Deployment and release automation are opt-in so the template works for projects with no server, one production server, or separate test and production environments.

## Workflows

| Workflow | Trigger | Default behavior |
|---|---|---|
| `ci.yml` | PR and push to `dev`/`main` | Backend lint/test, frontend build/test, shell syntax |
| `pr-governance.yml` | PR to `dev`/`main` | Validates Conventional Commit PR titles |
| `commit-governance.yml` | Push to `dev`/`main` | Validates landed first-parent commit subjects |
| `deploy-test.yml` | Push to `dev`, manual | Skipped unless `TEST_DEPLOY_ENABLED=true` |
| `release.yml` | Push to `main`, manual | Skipped unless `RELEASE_ENABLED=true`; production deploy is also opt-in |
| `backmerge-main-to-dev.yml` | Manual | Recovery workflow for `main -> dev` backmerge |

## Always-On Checks

`ci.yml` runs:

- Backend lint: `uv run poe lint`
- Backend tests: `uv run poe test`
- Frontend install: `npm ci --no-audit --no-fund`
- Frontend build: `npm run build`
- Frontend tests: `npm run test`
- Shell syntax checks for `scripts/cicd/*.sh` and `scripts/deploy/*.sh`

## Profiles

| Profile | Required variables | Result |
|---|---|---|
| CI only | none | No deployment or release automation runs |
| Production only | `RELEASE_ENABLED=true`; optionally `PROD_DEPLOY_ENABLED=true` | Release from `main`; deploy production only if enabled |
| Test and production | `TEST_DEPLOY_ENABLED=true`, `RELEASE_ENABLED=true`; optionally `PROD_DEPLOY_ENABLED=true` | Deploy test from `dev`; release and optionally deploy production from `main` |

Use CI-only mode until the target project has real infrastructure.

## Optional Test Deploy

Set `TEST_DEPLOY_ENABLED=true` only when the project has a separate test or staging host.

Secrets:

- `TEST_SSH_HOST`
- `TEST_SSH_USER`
- `TEST_SSH_KEY`

Variables:

- `TEST_DEPLOY_PATH`
- `TEST_SYSTEMD_SERVICE`
- `TEST_HEALTH_URL`
- `TEST_REPOSITORY_URL`

## Optional Production Deploy

Set `PROD_DEPLOY_ENABLED=true` only when production SSH deployment is configured.

Secrets:

- `PROD_SSH_HOST`
- `PROD_SSH_USER`
- `PROD_SSH_KEY`

Variables:

- `PROD_DEPLOY_PATH`
- `PROD_SYSTEMD_SERVICE`
- `PROD_HEALTH_URL`
- `PROD_REPOSITORY_URL`

## Optional Release Automation

Set `RELEASE_ENABLED=true` only after `RELEASE_TOKEN` can push release commits and tags to `main` under the repository ruleset.

Required secret:

- `RELEASE_TOKEN`

Required variable:

- `RELEASE_ENABLED`

If release automation is disabled, `release.yml` is skipped and `main` still receives CI and commit governance.
