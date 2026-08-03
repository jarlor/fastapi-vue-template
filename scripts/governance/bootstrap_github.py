#!/usr/bin/env python3
"""Render or apply the GitHub control plane for a generated repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CODEOWNERS_TEMPLATE = PROJECT_ROOT / ".github" / "CODEOWNERS.template"
DEFAULT_CODEOWNERS_OUTPUT = PROJECT_ROOT / ".github" / "CODEOWNERS"
DEFAULT_API_URL = "https://api.github.com"
DEFAULT_RULESET_NAME = "main-protection"
GITHUB_ACTIONS_APP_SLUG = "github-actions"
MAINTAINERS_MARKER = "__MAINTAINERS__"
REQUIRED_CHECK_CONTEXT = "required"
WRITE_PERMISSIONS = frozenset({"admin", "maintain", "push", "write"})
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
OWNER_RE = re.compile(r"^@?[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:/[A-Za-z0-9_.-]+)?$")
CONVENTIONAL_TITLE_RE = re.compile(
    r"^(?:feat|fix|perf|docs|refactor|test|chore|ci|build|style|revert)"
    r"(?:\([A-Za-z0-9._/-]+\))?!?: .+"
)


@dataclass(frozen=True)
class GovernanceProfile:
    """Pull-request policy inputs for a GitHub ruleset."""

    approvals: int
    dismiss_stale_reviews: bool
    require_code_owner_review: bool
    require_last_push_approval: bool
    require_review_thread_resolution: bool
    minimum_eligible_reviewers: int


PROFILES: Mapping[str, GovernanceProfile] = {
    "solo-safe": GovernanceProfile(
        approvals=0,
        dismiss_stale_reviews=False,
        require_code_owner_review=False,
        require_last_push_approval=False,
        require_review_thread_resolution=False,
        minimum_eligible_reviewers=1,
    ),
    "team": GovernanceProfile(
        approvals=1,
        dismiss_stale_reviews=False,
        require_code_owner_review=True,
        require_last_push_approval=True,
        require_review_thread_resolution=True,
        minimum_eligible_reviewers=2,
    ),
    "high-assurance": GovernanceProfile(
        approvals=2,
        dismiss_stale_reviews=True,
        require_code_owner_review=True,
        require_last_push_approval=True,
        require_review_thread_resolution=True,
        minimum_eligible_reviewers=3,
    ),
}


class GitHubAPIError(RuntimeError):
    """A GitHub API request failed."""

    def __init__(self, *, method: str, path: str, status: int | None, detail: str) -> None:
        self.method = method
        self.path = path
        self.status = status
        self.detail = detail
        status_text = f"HTTP {status}" if status is not None else "network error"
        super().__init__(f"GitHub API {method} {path} failed with {status_text}: {detail}")


class PreflightError(RuntimeError):
    """A read-only GitHub preflight rejected an unsafe apply."""


class ApplyStageError(RuntimeError):
    """A staged apply failed and may have completed earlier stages."""

    def __init__(
        self,
        *,
        failed_stage: str,
        completed: Sequence[Mapping[str, str]],
        not_completed: Sequence[str],
        cause: Exception,
    ) -> None:
        self.failed_stage = failed_stage
        self.completed = tuple(dict(item) for item in completed)
        self.not_completed = tuple(not_completed)
        self.cause = cause
        super().__init__(str(cause))

    def as_dict(self) -> dict[str, Any]:
        """Return a machine-readable partial-apply report."""
        cause = actionable_api_error(self.cause, stage=self.failed_stage)
        return {
            "error": "github bootstrap apply failed",
            "failed_stage": self.failed_stage,
            "completed": list(self.completed),
            "not_completed": list(self.not_completed),
            "cause": cause,
            "recovery": (
                "No automatic rollback was attempted. Inspect the completed stages, correct the cause, "
                "then rerun the same --apply command; every remote operation is convergent."
            ),
        }


@dataclass(frozen=True)
class PreflightResult:
    """Read-only state captured before an apply starts mutating anything."""

    repository: Mapping[str, Any]
    current_ruleset: Mapping[str, Any] | None
    required_check_integration_id: int
    validated_codeowners: tuple[Mapping[str, Any], ...]


class GitHubClient:
    """Small stdlib-only client for the repository settings and ruleset APIs."""

    def __init__(self, *, token: str, api_url: str = DEFAULT_API_URL) -> None:
        if not token:
            msg = "A GitHub token is required for --apply (set GH_TOKEN or GITHUB_TOKEN)."
            raise ValueError(msg)
        parsed_url = urllib.parse.urlparse(api_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            msg = "GitHub API URL must be an absolute HTTP or HTTPS URL."
            raise ValueError(msg)
        self.token = token
        self.api_url = api_url.rstrip("/")

    def request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> Any:
        """Send one JSON request to GitHub."""
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(  # noqa: S310 - api_url scheme validated in __init__
            f"{self.api_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "fastapi-vue-template-governance-bootstrap",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - validated in __init__
                body = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise GitHubAPIError(method=method, path=path, status=exc.code, detail=detail) from exc
        except urllib.error.URLError as exc:
            raise GitHubAPIError(method=method, path=path, status=None, detail=str(exc.reason)) from exc
        return None if not body else json.loads(body)


def validate_repository(repository: str) -> str:
    """Validate and return an owner/repository identifier."""
    if not REPOSITORY_RE.fullmatch(repository):
        msg = f"Invalid repository {repository!r}; expected owner/repository."
        raise ValueError(msg)
    return repository


def normalize_maintainers(maintainers: Sequence[str]) -> tuple[str, ...]:
    """Return stable, unique CODEOWNERS handles."""
    normalized: list[str] = []
    seen: set[str] = set()
    for value in maintainers:
        candidate = value.strip()
        if not candidate or not OWNER_RE.fullmatch(candidate):
            msg = f"Invalid maintainer {value!r}; use a GitHub user or org/team handle."
            raise ValueError(msg)
        handle = candidate if candidate.startswith("@") else f"@{candidate}"
        identity = handle.casefold()
        if identity not in seen:
            normalized.append(handle)
            seen.add(identity)
    if not normalized:
        msg = "At least one --maintainer is required."
        raise ValueError(msg)
    return tuple(normalized)


def validate_reviewer_capacity(
    profile_name: str,
    maintainers: Sequence[str],
    eligible_reviewers: int | None,
) -> int:
    """Return a declared reviewer count after rejecting self-locking profiles."""
    try:
        profile = PROFILES[profile_name]
    except KeyError as exc:
        msg = f"Unknown profile {profile_name!r}."
        raise ValueError(msg) from exc

    normalized = normalize_maintainers(maintainers)
    if eligible_reviewers is not None and eligible_reviewers < 1:
        msg = "--eligible-reviewers must be at least 1."
        raise ValueError(msg)
    if profile.minimum_eligible_reviewers == 1:
        return eligible_reviewers or len(normalized)
    if eligible_reviewers is None:
        msg = (
            f"Profile {profile_name!r} requires an explicit --eligible-reviewers declaration of at least "
            f"{profile.minimum_eligible_reviewers}."
        )
        raise ValueError(msg)
    if eligible_reviewers < profile.minimum_eligible_reviewers:
        msg = (
            f"Profile {profile_name!r} requires at least {profile.minimum_eligible_reviewers} eligible reviewers; "
            f"received {eligible_reviewers}."
        )
        raise ValueError(msg)

    has_team_owner = any("/" in owner.removeprefix("@") for owner in normalized)
    if not has_team_owner and len(normalized) < profile.minimum_eligible_reviewers:
        msg = (
            f"Profile {profile_name!r} requires at least {profile.minimum_eligible_reviewers} distinct personal "
            "CODEOWNERS so a maintainer-authored PR cannot self-lock. Add maintainers or use an @org/team owner "
            "with an explicit eligible reviewer declaration."
        )
        raise ValueError(msg)
    return eligible_reviewers


def has_write_permission(payload: Mapping[str, Any]) -> bool:
    """Return whether a collaborator/team repository response grants write access."""
    permission = str(payload.get("permission") or payload.get("role_name") or "").lower()
    if permission in WRITE_PERMISSIONS:
        return True
    permissions = payload.get("permissions")
    return isinstance(permissions, Mapping) and any(
        bool(permissions.get(name)) for name in ("admin", "maintain", "push")
    )


def actionable_api_error(error: Exception, *, stage: str) -> str:
    """Return an actionable GitHub API error without hiding partial progress."""
    if not isinstance(error, GitHubAPIError):
        return str(error)
    detail = error.detail.strip() or "no response detail"
    if error.status == 401:
        return (
            f"{stage} failed with HTTP 401. GH_TOKEN/GITHUB_TOKEN is invalid or expired; authenticate again and rerun. "
            f"GitHub response: {detail}"
        )
    if error.status == 403:
        if "rate limit" in detail.lower():
            return (
                f"{stage} failed because the GitHub API rate limit was exceeded. Wait or use another token, then rerun."
            )
        rulesets_hint = ""
        if "/rulesets" in error.path:
            rulesets_hint = (
                " Rulesets require a public repository on GitHub Free or a private repository on GitHub Pro, "
                "Team, or Enterprise."
            )
        return (
            f"{stage} failed with HTTP 403. Use a token with repository Metadata: read and Administration: write. "
            "For @org/team CODEOWNERS, also grant organization Members: read (classic tokens need repo + read:org). "
            f"{rulesets_hint} GitHub response: {detail}"
        )
    if error.status == 404 and "/rulesets" in error.path:
        return (
            f"{stage} could not read Rulesets (HTTP 404). Confirm repository admin access and plan support: Rulesets "
            "work for public repositories on GitHub Free and for private repositories on GitHub Pro, Team, or "
            f"Enterprise. GitHub response: {detail}"
        )
    if error.status == 404:
        return (
            f"{stage} failed with HTTP 404. Verify the repository, main branch, CODEOWNER handle/team, and token "
            f"visibility for that resource. GitHub response: {detail}"
        )
    return str(error)


def preflight_request(
    client: GitHubClient,
    *,
    stage: str,
    method: str,
    path: str,
) -> Any:
    """Make one read-only preflight request with actionable failures."""
    if method != "GET":
        msg = f"Preflight attempted non-read-only method {method!r}."
        raise PreflightError(msg)
    try:
        return client.request(method, path)
    except GitHubAPIError as exc:
        raise PreflightError(actionable_api_error(exc, stage=stage)) from exc


def render_codeowners(template: str, maintainers: Sequence[str]) -> str:
    """Render a CODEOWNERS template with normalized maintainer handles."""
    if MAINTAINERS_MARKER not in template:
        msg = f"CODEOWNERS template is missing marker {MAINTAINERS_MARKER!r}."
        raise ValueError(msg)
    owners = " ".join(normalize_maintainers(maintainers))
    return template.replace(MAINTAINERS_MARKER, owners).rstrip() + "\n"


def validate_pr_title(title: str) -> bool:
    """Return whether a PR title can become a Conventional Commit squash title."""
    return CONVENTIONAL_TITLE_RE.fullmatch(title.strip()) is not None


def repository_settings() -> dict[str, Any]:
    """Return repository settings for a main-only, squash-merge workflow."""
    return {
        "default_branch": "main",
        "allow_merge_commit": False,
        "allow_rebase_merge": False,
        "allow_squash_merge": True,
        "delete_branch_on_merge": True,
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "PR_BODY",
    }


def repository_settings_diff(current: Mapping[str, Any], desired: Mapping[str, Any]) -> dict[str, Any]:
    """Return only repository settings that differ from GitHub state."""
    return {key: value for key, value in desired.items() if current.get(key) != value}


def build_ruleset(
    profile_name: str,
    *,
    ruleset_name: str = DEFAULT_RULESET_NAME,
    required_check_integration_id: int | None = None,
) -> dict[str, Any]:
    """Build the canonical default-branch ruleset for a profile."""
    try:
        profile = PROFILES[profile_name]
    except KeyError as exc:
        msg = f"Unknown profile {profile_name!r}."
        raise ValueError(msg) from exc

    if required_check_integration_id is not None and required_check_integration_id < 1:
        msg = "required_check_integration_id must be a positive integer."
        raise ValueError(msg)

    pull_request_parameters = {
        "allowed_merge_methods": ["squash"],
        "dismiss_stale_reviews_on_push": profile.dismiss_stale_reviews,
        "require_code_owner_review": profile.require_code_owner_review,
        "require_last_push_approval": profile.require_last_push_approval,
        "required_approving_review_count": profile.approvals,
        "required_review_thread_resolution": profile.require_review_thread_resolution,
    }
    required_check: dict[str, Any] = {"context": REQUIRED_CHECK_CONTEXT}
    if required_check_integration_id is not None:
        required_check["integration_id"] = required_check_integration_id

    return {
        "name": ruleset_name,
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "required_linear_history"},
            {"type": "pull_request", "parameters": pull_request_parameters},
            {
                "type": "required_status_checks",
                "parameters": {
                    "do_not_enforce_on_create": True,
                    "required_status_checks": [required_check],
                    "strict_required_status_checks_policy": True,
                },
            },
        ],
    }


def ruleset_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Project a GitHub response onto fields controlled by this bootstrap."""
    conditions = payload.get("conditions")
    conditions = conditions if isinstance(conditions, Mapping) else {}
    ref_name = conditions.get("ref_name")
    ref_name = ref_name if isinstance(ref_name, Mapping) else {}

    bypass_actors = payload.get("bypass_actors") or []
    projected_bypass = [
        {
            "actor_id": actor.get("actor_id"),
            "actor_type": actor.get("actor_type"),
            "bypass_mode": actor.get("bypass_mode", "always"),
        }
        for actor in bypass_actors
        if isinstance(actor, Mapping)
    ]
    projected_bypass.sort(
        key=lambda actor: (
            str(actor.get("actor_type") or ""),
            int(actor.get("actor_id") or -1),
            str(actor.get("bypass_mode") or ""),
        )
    )

    projected_rules: list[dict[str, Any]] = []
    for rule in payload.get("rules") or []:
        if not isinstance(rule, Mapping):
            continue
        rule_type = rule.get("type")
        projected_rule: dict[str, Any] = {"type": rule_type}
        parameters = rule.get("parameters")
        parameters = parameters if isinstance(parameters, Mapping) else {}
        if rule_type == "pull_request":
            managed_keys = (
                "allowed_merge_methods",
                "dismiss_stale_reviews_on_push",
                "require_code_owner_review",
                "require_last_push_approval",
                "required_approving_review_count",
                "required_review_thread_resolution",
            )
            projected_rule["parameters"] = {key: parameters.get(key) for key in managed_keys}
        elif rule_type == "required_status_checks":
            checks = [
                {
                    "context": check.get("context"),
                    "integration_id": check.get("integration_id"),
                }
                for check in parameters.get("required_status_checks") or []
                if isinstance(check, Mapping)
            ]
            checks.sort(key=lambda check: (str(check["context"] or ""), int(check["integration_id"] or -1)))
            projected_rule["parameters"] = {
                "do_not_enforce_on_create": parameters.get("do_not_enforce_on_create"),
                "required_status_checks": checks,
                "strict_required_status_checks_policy": parameters.get("strict_required_status_checks_policy"),
            }
        projected_rules.append(projected_rule)
    projected_rules.sort(key=lambda rule: str(rule.get("type") or ""))

    return {
        "name": payload.get("name"),
        "target": payload.get("target"),
        "enforcement": payload.get("enforcement"),
        "bypass_actors": projected_bypass,
        "conditions": {
            "ref_name": {
                "include": sorted(ref_name.get("include") or []),
                "exclude": sorted(ref_name.get("exclude") or []),
            }
        },
        "rules": projected_rules,
    }


def ruleset_action(current: Mapping[str, Any] | None, desired: Mapping[str, Any]) -> str:
    """Return create, update, or unchanged for one ruleset."""
    if current is None:
        return "create"
    if ruleset_projection(current) == ruleset_projection(desired):
        return "unchanged"
    return "update"


def write_atomic(path: Path, content: str) -> None:
    """Write text atomically without leaving a partial CODEOWNERS file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def validate_repository_preflight(repository: str, payload: Mapping[str, Any]) -> None:
    """Reject repositories that cannot safely accept governance mutations."""
    if payload.get("archived") or payload.get("disabled"):
        msg = f"Repository {repository} is archived or disabled; no governance changes were made."
        raise PreflightError(msg)
    permissions = payload.get("permissions")
    if not isinstance(permissions, Mapping) or not permissions.get("admin"):
        msg = (
            f"Token does not have admin access to {repository}. Use a fine-grained token with Metadata: read and "
            "Administration: write, or a classic token with repo scope. No governance changes were made."
        )
        raise PreflightError(msg)


def validate_codeowners_with_github(
    client: GitHubClient,
    *,
    repository: str,
    repository_payload: Mapping[str, Any],
    maintainers: Sequence[str],
) -> tuple[Mapping[str, Any], ...]:
    """Validate that every CODEOWNER exists and has explicit repository write access."""
    repository_owner = repository.split("/", maxsplit=1)[0]
    owner_payload = repository_payload.get("owner")
    owner_payload = owner_payload if isinstance(owner_payload, Mapping) else {}
    owner_type = str(owner_payload.get("type") or "")
    owner_login = str(owner_payload.get("login") or repository_owner)
    validated: list[Mapping[str, Any]] = []
    principal_ids: set[tuple[str, int]] = set()

    for handle in normalize_maintainers(maintainers):
        owner = handle.removeprefix("@")
        if "/" not in owner:
            identity = preflight_request(
                client,
                stage=f"CODEOWNER {handle} identity validation",
                method="GET",
                path=f"/users/{owner}",
            )
            if (
                not isinstance(identity, Mapping)
                or identity.get("type") != "User"
                or not isinstance(identity.get("id"), int)
            ):
                msg = f"CODEOWNER {handle} is not a GitHub user; use an individual user or @org/team handle."
                raise PreflightError(msg)
            principal = ("user", int(identity["id"]))
            if principal in principal_ids:
                msg = f"CODEOWNER {handle} resolves to a duplicate GitHub user and cannot increase reviewer capacity."
                raise PreflightError(msg)
            principal_ids.add(principal)
            permission = preflight_request(
                client,
                stage=f"CODEOWNER {handle} repository permission validation",
                method="GET",
                path=f"/repos/{repository}/collaborators/{owner}/permission",
            )
            if not isinstance(permission, Mapping) or not has_write_permission(permission):
                msg = f"CODEOWNER {handle} does not have explicit write access to {repository}."
                raise PreflightError(msg)
            validated.append(
                {
                    "handle": handle,
                    "id": identity["id"],
                    "kind": "user",
                    "permission": permission.get("permission"),
                }
            )
            continue

        organization, team_slug = owner.split("/", maxsplit=1)
        if owner_type != "Organization" or organization.casefold() != owner_login.casefold():
            msg = (
                f"CODEOWNER {handle} is a team, but {repository} is not owned by organization {organization!r}. "
                "GitHub teams can own code only in repositories owned by their organization."
            )
            raise PreflightError(msg)
        team = preflight_request(
            client,
            stage=f"CODEOWNER {handle} team validation",
            method="GET",
            path=f"/orgs/{organization}/teams/{team_slug}",
        )
        if (
            not isinstance(team, Mapping)
            or not isinstance(team.get("id"), int)
            or str(team.get("privacy") or "").lower() != "closed"
        ):
            msg = f"CODEOWNER team {handle} must exist and be visible, not secret."
            raise PreflightError(msg)
        principal = ("team", int(team["id"]))
        if principal in principal_ids:
            msg = f"CODEOWNER {handle} resolves to a duplicate GitHub team and cannot increase reviewer capacity."
            raise PreflightError(msg)
        principal_ids.add(principal)
        permission = preflight_request(
            client,
            stage=f"CODEOWNER {handle} repository permission validation",
            method="GET",
            path=f"/orgs/{organization}/teams/{team_slug}/repos/{repository}",
        )
        if not isinstance(permission, Mapping) or not has_write_permission(permission):
            msg = f"CODEOWNER team {handle} does not have explicit write access to {repository}."
            raise PreflightError(msg)
        validated.append(
            {
                "handle": handle,
                "id": team["id"],
                "kind": "team",
                "permission": permission.get("permission"),
            }
        )
    return tuple(validated)


def discover_required_check_integration_id(client: GitHubClient, *, repository: str, main_sha: str) -> int:
    """Discover the GitHub Actions App id from a real required check run on main."""
    payload = preflight_request(
        client,
        stage="required status-check source discovery",
        method="GET",
        path=(
            f"/repos/{repository}/commits/{main_sha}/check-runs"
            f"?check_name={REQUIRED_CHECK_CONTEXT}&filter=latest&per_page=100"
        ),
    )
    check_runs = payload.get("check_runs") if isinstance(payload, Mapping) else None
    candidates = []
    for check_run in check_runs or []:
        if not isinstance(check_run, Mapping) or check_run.get("name") != REQUIRED_CHECK_CONTEXT:
            continue
        app = check_run.get("app")
        if isinstance(app, Mapping) and app.get("slug") == GITHUB_ACTIONS_APP_SLUG:
            candidates.append(check_run)
    integration_ids = {
        int(check_run["app"]["id"])
        for check_run in candidates
        if isinstance(check_run.get("app"), Mapping) and isinstance(check_run["app"].get("id"), int)
    }
    if not integration_ids:
        msg = (
            "No GitHub Actions check run named 'required' exists on main. This bootstrap will not guess or leave the "
            "required context unbound. First merge the CI workflow, let 'CI / required' run on main, then rerun "
            "--dry-run and --apply. No governance changes were made."
        )
        raise PreflightError(msg)
    if len(integration_ids) != 1:
        msg = f"Required checks on main resolved to multiple GitHub Actions integration ids: {sorted(integration_ids)}."
        raise PreflightError(msg)
    return integration_ids.pop()


def preflight_control_plane(client: GitHubClient, plan: Mapping[str, Any]) -> PreflightResult:
    """Complete every available read-only validation before the first mutation."""
    repository = str(plan["repository"])
    repository_payload = preflight_request(
        client,
        stage="repository access preflight",
        method="GET",
        path=f"/repos/{repository}",
    )
    if not isinstance(repository_payload, Mapping):
        msg = f"Repository preflight for {repository} returned an invalid response."
        raise PreflightError(msg)
    validate_repository_preflight(repository, repository_payload)

    main_branch = preflight_request(
        client,
        stage="main branch preflight",
        method="GET",
        path=f"/repos/{repository}/branches/main",
    )
    main_commit = main_branch.get("commit") if isinstance(main_branch, Mapping) else None
    main_sha = main_commit.get("sha") if isinstance(main_commit, Mapping) else None
    if not isinstance(main_sha, str) or not main_sha:
        msg = f"Repository {repository} must already have a main branch before governance can be applied."
        raise PreflightError(msg)

    validated_codeowners = validate_codeowners_with_github(
        client,
        repository=repository,
        repository_payload=repository_payload,
        maintainers=plan["maintainers"],
    )
    integration_id = discover_required_check_integration_id(client, repository=repository, main_sha=main_sha)
    try:
        current_ruleset = find_repository_ruleset(client, repository, str(plan["ruleset"]["name"]))
    except GitHubAPIError as exc:
        raise PreflightError(actionable_api_error(exc, stage="Rulesets access preflight")) from exc

    return PreflightResult(
        repository=repository_payload,
        current_ruleset=current_ruleset,
        required_check_integration_id=integration_id,
        validated_codeowners=validated_codeowners,
    )


def bind_plan_to_preflight(plan: Mapping[str, Any], preflight: PreflightResult) -> dict[str, Any]:
    """Return the exact apply plan with the discovered Actions integration bound."""
    ruleset_name = str(plan["ruleset"]["name"])
    bound = dict(plan)
    bound["ruleset"] = build_ruleset(
        str(plan["profile"]),
        ruleset_name=ruleset_name,
        required_check_integration_id=preflight.required_check_integration_id,
    )
    bound["status_check_source"] = {
        "app_slug": GITHUB_ACTIONS_APP_SLUG,
        "binding": "bound",
        "context": REQUIRED_CHECK_CONTEXT,
        "integration_id": preflight.required_check_integration_id,
    }
    return bound


def apply_repository_settings(
    client: GitHubClient,
    repository: str,
    desired: Mapping[str, Any],
    current: Mapping[str, Any],
) -> str:
    """Update repository merge settings only when they differ."""
    changes = repository_settings_diff(current, desired)
    if not changes:
        return "unchanged"
    client.request("PATCH", f"/repos/{repository}", changes)
    return "updated"


def find_repository_ruleset(client: GitHubClient, repository: str, name: str) -> Mapping[str, Any] | None:
    """Return a full repository-owned ruleset with the requested name."""
    summaries = client.request(
        "GET",
        f"/repos/{repository}/rulesets?includes_parents=false&targets=branch&per_page=100",
    )
    matches = [item for item in summaries if item.get("name") == name and item.get("source_type") == "Repository"]
    if len(matches) > 1:
        msg = f"Multiple repository rulesets are named {name!r}; resolve the duplicate before applying."
        raise ValueError(msg)
    if not matches:
        return None
    ruleset_id = matches[0]["id"]
    return client.request("GET", f"/repos/{repository}/rulesets/{ruleset_id}?includes_parents=false")


def apply_ruleset(
    client: GitHubClient,
    repository: str,
    desired: Mapping[str, Any],
    current: Mapping[str, Any] | None,
) -> tuple[str, int | None]:
    """Create or update one named ruleset without creating duplicates."""
    action = ruleset_action(current, desired)
    if action == "unchanged":
        return (action, int(current["id"]))
    if action == "create":
        response = client.request("POST", f"/repos/{repository}/rulesets", desired)
    else:
        response = client.request("PUT", f"/repos/{repository}/rulesets/{current['id']}", desired)
    return (action, int(response["id"]))


def render_plan(
    *,
    repository: str,
    profile: str,
    maintainers: Sequence[str],
    eligible_reviewers: int | None,
    template_path: Path,
    ruleset_name: str,
    required_check_integration_id: int | None = None,
) -> dict[str, Any]:
    """Render the complete deterministic GitHub bootstrap plan."""
    validated_repository = validate_repository(repository)
    normalized_maintainers = normalize_maintainers(maintainers)
    declared_eligible_reviewers = validate_reviewer_capacity(profile, normalized_maintainers, eligible_reviewers)
    codeowners = render_codeowners(template_path.read_text(), normalized_maintainers)
    return {
        "repository": validated_repository,
        "profile": profile,
        "maintainers": list(normalized_maintainers),
        "eligible_reviewers": declared_eligible_reviewers,
        "repository_settings": repository_settings(),
        "ruleset": build_ruleset(
            profile,
            ruleset_name=ruleset_name,
            required_check_integration_id=required_check_integration_id,
        ),
        "status_check_source": {
            "app_slug": GITHUB_ACTIONS_APP_SLUG,
            "binding": "bound" if required_check_integration_id is not None else "discover-on-apply",
            "context": REQUIRED_CHECK_CONTEXT,
            "integration_id": required_check_integration_id,
        },
        "codeowners": codeowners,
    }


def token_from_environment() -> str:
    """Return the first supported GitHub token environment variable."""
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap", help="Render or apply repository settings and the main ruleset.")
    bootstrap.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY"),
        required="GITHUB_REPOSITORY" not in os.environ,
        help="GitHub owner/repository (defaults to GITHUB_REPOSITORY).",
    )
    bootstrap.add_argument("--profile", choices=sorted(PROFILES), default="solo-safe")
    bootstrap.add_argument(
        "--maintainer",
        action="append",
        default=[],
        help="CODEOWNERS user or org/team handle; repeat for multiple owners.",
    )
    bootstrap.add_argument(
        "--eligible-reviewers",
        type=int,
        help=(
            "Declared humans eligible to approve PRs; required for team (>=2) and high-assurance (>=3). "
            "The declaration is mandatory when an @org/team CODEOWNER hides individual membership."
        ),
    )
    bootstrap.add_argument("--ruleset-name", default=DEFAULT_RULESET_NAME)
    bootstrap.add_argument("--codeowners-template", type=Path, default=DEFAULT_CODEOWNERS_TEMPLATE)
    bootstrap.add_argument("--codeowners-output", type=Path, default=DEFAULT_CODEOWNERS_OUTPUT)
    bootstrap.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", DEFAULT_API_URL))
    mode = bootstrap.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the desired plan and pending Actions-source binding without writing or calling GitHub.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Run read-only preflight, then write CODEOWNERS and converge GitHub settings.",
    )

    validate_title = subparsers.add_parser(
        "validate-pr-title",
        help="Validate a PR title for Conventional Commit squash merging.",
    )
    validate_title.add_argument("--title", required=True)
    return parser.parse_args()


APPLY_STAGES = ("preflight", "codeowners", "repository-settings", "ruleset")


def apply_control_plane(
    client: GitHubClient,
    *,
    plan: Mapping[str, Any],
    preflight: PreflightResult,
    codeowners_output: Path,
    writer: Callable[[Path, str], None] = write_atomic,
) -> dict[str, Any]:
    """Apply a preflighted plan and report the exact result of every stage."""
    completed: list[dict[str, str]] = [{"stage": "preflight", "result": "passed"}]
    pending = ["codeowners", "repository-settings", "ruleset"]

    try:
        writer(codeowners_output, str(plan["codeowners"]))
    except Exception as exc:
        raise ApplyStageError(
            failed_stage="codeowners",
            completed=completed,
            not_completed=pending,
            cause=exc,
        ) from exc
    completed.append({"stage": "codeowners", "result": str(codeowners_output)})
    pending.pop(0)

    try:
        settings_result = apply_repository_settings(
            client,
            str(plan["repository"]),
            plan["repository_settings"],
            preflight.repository,
        )
    except Exception as exc:
        raise ApplyStageError(
            failed_stage="repository-settings",
            completed=completed,
            not_completed=pending,
            cause=exc,
        ) from exc
    completed.append({"stage": "repository-settings", "result": settings_result})
    pending.pop(0)

    try:
        ruleset_result, ruleset_id = apply_ruleset(
            client,
            str(plan["repository"]),
            plan["ruleset"],
            preflight.current_ruleset,
        )
    except Exception as exc:
        raise ApplyStageError(
            failed_stage="ruleset",
            completed=completed,
            not_completed=pending,
            cause=exc,
        ) from exc
    completed.append({"stage": "ruleset", "result": ruleset_result})

    return {
        "codeowners": str(codeowners_output),
        "repository_settings": settings_result,
        "ruleset": ruleset_result,
        "ruleset_id": ruleset_id,
        "status_check_source": plan["status_check_source"],
        "validated_codeowners": list(preflight.validated_codeowners),
        "stages": completed,
    }


def run_bootstrap(
    args: argparse.Namespace,
    *,
    client_factory: Callable[..., GitHubClient] = GitHubClient,
) -> int:
    """Render or apply a bootstrap plan."""
    plan = render_plan(
        repository=args.repository,
        profile=args.profile,
        maintainers=args.maintainer,
        eligible_reviewers=args.eligible_reviewers,
        template_path=args.codeowners_template.resolve(),
        ruleset_name=args.ruleset_name,
    )
    if args.dry_run:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    try:
        client = client_factory(token=token_from_environment(), api_url=args.api_url)
        preflight = preflight_control_plane(client, plan)
    except Exception as exc:
        raise ApplyStageError(
            failed_stage="preflight",
            completed=(),
            not_completed=APPLY_STAGES,
            cause=exc,
        ) from exc

    bound_plan = bind_plan_to_preflight(plan, preflight)
    result = apply_control_plane(
        client,
        plan=bound_plan,
        preflight=preflight,
        codeowners_output=args.codeowners_output.resolve(),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    try:
        if args.command == "validate-pr-title":
            if validate_pr_title(args.title):
                print("PR title follows Conventional Commit format.")
                return 0
            print(
                "PR title must follow Conventional Commit format, for example 'feat(api): add task endpoint'.",
                file=sys.stderr,
            )
            return 1
        return run_bootstrap(args)
    except ApplyStageError as exc:
        print(json.dumps(exc.as_dict(), indent=2, sort_keys=True), file=sys.stderr)
        return 1
    except (GitHubAPIError, OSError, PreflightError, ValueError) as exc:
        print(f"github bootstrap failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
