# Git Workflow

This template uses a small `dev`/`main` model that works for solo projects, small teams, and production projects with optional test/staging infrastructure.

`test` and `staging` are environments, not required branches.

## Branches

| Branch | Purpose | Merge rule |
|---|---|---|
| `main` | Production truth branch | PR only |
| `dev` | Integration branch | PR only |
| `feature/*` | New work | PR to `dev` |
| `fix/*` | Non-production bug fixes | PR to `dev` |
| `hotfix/*` | Urgent production fixes | Branch from `main`, PR to `main` |

## Normal Feature Flow

```bash
git switch dev
git pull --ff-only origin dev
git switch -c feature/task-board

git add .
git commit -m "feat(tasks): add task board"
git push -u origin feature/task-board
gh pr create --base dev --title "feat(tasks): add task board"
```

Merge feature PRs into `dev` with squash merge. The squash title becomes the landed commit subject, so it must follow Conventional Commit format.

## Release Flow

```bash
git switch dev
git pull --ff-only origin dev
gh pr create --base main --head dev --title "feat: release integrated changes"
```

PRs into `main` must use a release-triggering Conventional Commit type:

- `feat:`
- `fix:`
- `perf:`

After `main` receives a release-triggering commit, `release.yml` can run semantic-release when `RELEASE_ENABLED=true`. Production deployment remains disabled unless `PROD_DEPLOY_ENABLED=true`.

## Hotfix Flow

```bash
git switch main
git pull --ff-only origin main
git switch -c hotfix/repair-login

git add .
git commit -m "fix(auth): repair login callback"
git push -u origin hotfix/repair-login
gh pr create --base main --title "fix(auth): repair login callback"
```

After the hotfix lands on `main`, backmerge `main` into `dev`. The release workflow does this automatically after a successful release/deploy path. Use `backmerge-main-to-dev.yml` manually if recovery is needed.

## Commit Format

Use Conventional Commits:

```text
feat(api): add task endpoint
fix(frontend): repair dashboard loading state
docs: update deployment guide
test(api): add config tests
ci: add release workflow
```

Allowed types:

- `feat`
- `fix`
- `perf`
- `docs`
- `refactor`
- `test`
- `chore`
- `ci`
- `build`
- `style`
- `revert`

## Pull Requests

PR titles must also use Conventional Commit format:

```text
feat(api): add task endpoint
fix(frontend): repair dashboard loading state
```

Keep PRs small enough to review. Put manual verification notes in the PR body when the change affects runtime behavior.

## Protected Branches

Recommended branch protection for `main` and `dev`:

- Require pull requests.
- Require CI checks.
- Restrict direct pushes.
- Use squash merge into `dev`.
- Use merge commit or squash merge into `main`, depending on whether the project wants to preserve a release PR merge commit.

Do not force-push `main` or `dev`.
