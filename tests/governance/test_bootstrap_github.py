"""Pure-function tests for the GitHub governance bootstrap."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from scripts.governance.bootstrap_github import (
    PROFILES,
    ApplyStageError,
    GitHubAPIError,
    GitHubClient,
    PreflightError,
    PreflightResult,
    actionable_api_error,
    apply_control_plane,
    bind_plan_to_preflight,
    build_ruleset,
    has_write_permission,
    normalize_maintainers,
    preflight_control_plane,
    render_codeowners,
    render_plan,
    repository_settings,
    repository_settings_diff,
    ruleset_action,
    validate_pr_title,
    validate_repository,
    validate_reviewer_capacity,
)


def test_github_client_rejects_non_http_api_url() -> None:
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        GitHubClient(token=__name__, api_url="file:///tmp/fake-api")


class FakeGitHubClient:
    """Deterministic request/response fake for read-only preflight and apply tests."""

    def __init__(self, responses: dict[tuple[str, str], Any]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, Any]] = []

    def request(self, method: str, path: str, payload: Any = None) -> Any:
        self.calls.append((method, path, payload))
        response = self.responses[(method, path)]
        if isinstance(response, Exception):
            raise response
        return deepcopy(response)


def render_test_plan(
    tmp_path: Path,
    *,
    profile: str = "solo-safe",
    maintainers: list[str] | None = None,
    eligible_reviewers: int | None = None,
) -> dict[str, Any]:
    template = tmp_path / "CODEOWNERS.template"
    template.write_text("* __MAINTAINERS__\n")
    return render_plan(
        repository="acme/service",
        profile=profile,
        maintainers=maintainers or ["alice"],
        eligible_reviewers=eligible_reviewers,
        template_path=template,
        ruleset_name="main-protection",
    )


def user_preflight_responses(*, maintainers: tuple[str, ...] = ("alice",)) -> dict[tuple[str, str], Any]:
    repository = "acme/service"
    main_sha = "abc123"
    responses: dict[tuple[str, str], Any] = {
        ("GET", f"/repos/{repository}"): {
            "owner": {"login": "acme", "type": "Organization"},
            "permissions": {"admin": True, "push": True},
            "archived": False,
            "disabled": False,
            **repository_settings(),
        },
        ("GET", f"/repos/{repository}/branches/main"): {"commit": {"sha": main_sha}},
        (
            "GET",
            f"/repos/{repository}/commits/{main_sha}/check-runs?check_name=required&filter=latest&per_page=100",
        ): {
            "check_runs": [
                {
                    "name": "required",
                    "conclusion": "success",
                    "app": {"slug": "github-actions", "id": 4242},
                }
            ]
        },
        (
            "GET",
            f"/repos/{repository}/rulesets?includes_parents=false&targets=branch&per_page=100",
        ): [],
    }
    for identity, maintainer in enumerate(maintainers, start=1):
        responses[("GET", f"/users/{maintainer}")] = {"id": identity, "login": maintainer, "type": "User"}
        responses[("GET", f"/repos/{repository}/collaborators/{maintainer}/permission")] = {"permission": "write"}
    return responses


def pull_request_parameters(profile: str) -> dict[str, object]:
    """Return pull-request parameters from a rendered ruleset."""
    ruleset = build_ruleset(profile)
    return next(rule["parameters"] for rule in ruleset["rules"] if rule["type"] == "pull_request")


@pytest.mark.parametrize(
    "title",
    [
        "feat(api): add task endpoint",
        "fix!: remove unsafe fallback",
        "docs: explain local setup",
        "chore(deps): update FastAPI",
        "revert: restore stable router",
    ],
)
def test_validate_pr_title_accepts_conventional_titles(title: str) -> None:
    assert validate_pr_title(title)


@pytest.mark.parametrize(
    "title",
    [
        "Add task endpoint",
        "feat missing separator",
        "feature(api): unsupported type",
        "feat(): empty scope",
        "feat: ",
    ],
)
def test_validate_pr_title_rejects_non_conventional_titles(title: str) -> None:
    assert not validate_pr_title(title)


def test_normalize_maintainers_adds_prefix_and_deduplicates() -> None:
    assert normalize_maintainers(["alice", "@alice", "@ALICE", "acme/platform"]) == (
        "@alice",
        "@acme/platform",
    )


@pytest.mark.parametrize("maintainers", [[], [""], ["bad handle"], ["@org/"]])
def test_normalize_maintainers_rejects_invalid_input(maintainers: list[str]) -> None:
    with pytest.raises(ValueError, match=r"maintainer|required"):
        normalize_maintainers(maintainers)


def test_render_codeowners_replaces_every_marker() -> None:
    template = "* __MAINTAINERS__\n/.github/ __MAINTAINERS__\n"

    rendered = render_codeowners(template, ["alice", "acme/platform"])

    assert rendered == "* @alice @acme/platform\n/.github/ @alice @acme/platform\n"


def test_render_codeowners_requires_marker() -> None:
    with pytest.raises(ValueError, match="missing marker"):
        render_codeowners("* @alice\n", ["alice"])


def test_profiles_have_monotonically_stronger_human_review() -> None:
    assert PROFILES["solo-safe"].approvals == 0
    assert PROFILES["team"].approvals == 1
    assert PROFILES["high-assurance"].approvals == 2

    solo = pull_request_parameters("solo-safe")
    team = pull_request_parameters("team")
    high_assurance = pull_request_parameters("high-assurance")

    assert not solo["require_code_owner_review"]
    assert team["require_code_owner_review"]
    assert team["require_last_push_approval"]
    assert team["required_review_thread_resolution"]
    assert high_assurance["dismiss_stale_reviews_on_push"]


def test_solo_safe_infers_one_eligible_reviewer() -> None:
    assert validate_reviewer_capacity("solo-safe", ["alice"], None) == 1


@pytest.mark.parametrize(
    ("profile", "maintainers", "eligible_reviewers", "message"),
    [
        ("team", ["alice", "bob"], None, "explicit --eligible-reviewers"),
        ("team", ["alice", "bob"], 1, "at least 2"),
        ("team", ["alice"], 2, "distinct personal CODEOWNERS"),
        ("high-assurance", ["alice", "bob", "carol"], 2, "at least 3"),
        ("high-assurance", ["alice", "bob"], 3, "distinct personal CODEOWNERS"),
    ],
)
def test_reviewer_capacity_rejects_self_locking_profiles(
    profile: str,
    maintainers: list[str],
    eligible_reviewers: int | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_reviewer_capacity(profile, maintainers, eligible_reviewers)


@pytest.mark.parametrize(
    ("profile", "maintainers", "eligible_reviewers"),
    [
        ("team", ["alice", "bob"], 2),
        ("high-assurance", ["alice", "bob", "carol"], 3),
        ("team", ["acme/platform"], 2),
        ("high-assurance", ["acme/platform"], 3),
    ],
)
def test_reviewer_capacity_accepts_individuals_or_declared_team_membership(
    profile: str,
    maintainers: list[str],
    eligible_reviewers: int,
) -> None:
    assert validate_reviewer_capacity(profile, maintainers, eligible_reviewers) == eligible_reviewers


@pytest.mark.parametrize("profile", sorted(PROFILES))
def test_ruleset_protects_default_branch_with_one_stable_check(profile: str) -> None:
    ruleset = build_ruleset(profile)
    rule_types = {rule["type"] for rule in ruleset["rules"]}

    assert ruleset["conditions"] == {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}}
    assert {"deletion", "non_fast_forward", "required_linear_history", "pull_request"} <= rule_types
    required = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
    assert required["parameters"]["required_status_checks"] == [{"context": "required"}]
    assert required["parameters"]["strict_required_status_checks_policy"] is True


def test_ruleset_action_ignores_github_response_metadata() -> None:
    desired = build_ruleset("team")
    current = deepcopy(desired)
    current.update({"id": 42, "source": "acme/example", "source_type": "Repository"})

    assert ruleset_action(None, desired) == "create"
    assert ruleset_action(current, desired) == "unchanged"

    current["enforcement"] = "disabled"
    assert ruleset_action(current, desired) == "update"


def test_ruleset_action_ignores_server_pull_request_defaults_but_compares_integration() -> None:
    desired = build_ruleset("team", required_check_integration_id=4242)
    current = deepcopy(desired)
    current.update({"id": 42, "source": "acme/service", "source_type": "Repository"})
    pull_request_rule = next(rule for rule in current["rules"] if rule["type"] == "pull_request")
    pull_request_rule["parameters"].update(
        {
            "dismissal_restriction": {"enabled": False, "allowed_actors": []},
            "ignore_approvals_from_contributors": False,
            "required_reviewers": [],
        }
    )

    assert ruleset_action(current, desired) == "unchanged"

    required_rule = next(rule for rule in current["rules"] if rule["type"] == "required_status_checks")
    required_rule["parameters"]["required_status_checks"][0]["integration_id"] = 9999
    assert ruleset_action(current, desired) == "update"


def test_ruleset_binds_required_check_only_when_discovered() -> None:
    unbound = build_ruleset("solo-safe")
    bound = build_ruleset("solo-safe", required_check_integration_id=4242)

    unbound_required = next(rule for rule in unbound["rules"] if rule["type"] == "required_status_checks")
    bound_required = next(rule for rule in bound["rules"] if rule["type"] == "required_status_checks")

    assert unbound_required["parameters"]["required_status_checks"] == [{"context": "required"}]
    assert bound_required["parameters"]["required_status_checks"] == [{"context": "required", "integration_id": 4242}]


def test_repository_settings_are_main_only_and_squash_only() -> None:
    assert repository_settings() == {
        "default_branch": "main",
        "allow_merge_commit": False,
        "allow_rebase_merge": False,
        "allow_squash_merge": True,
        "delete_branch_on_merge": True,
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "PR_BODY",
    }


def test_repository_settings_diff_returns_only_changes() -> None:
    desired = repository_settings()
    current = {**desired, "allow_merge_commit": True}

    assert repository_settings_diff(current, desired) == {"allow_merge_commit": False}


@pytest.mark.parametrize("repository", ["owner/repo", "acme-inc/service.api"])
def test_validate_repository_accepts_owner_and_name(repository: str) -> None:
    assert validate_repository(repository) == repository


@pytest.mark.parametrize("repository", ["repo", "owner/repo/extra", "owner /repo", ""])
def test_validate_repository_rejects_invalid_identifier(repository: str) -> None:
    with pytest.raises(ValueError, match="owner/repository"):
        validate_repository(repository)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"permission": "write"}, True),
        ({"permission": "admin"}, True),
        ({"permissions": {"maintain": True}}, True),
        ({"permission": "read", "permissions": {"push": False}}, False),
    ],
)
def test_has_write_permission_handles_user_and_team_responses(payload: dict[str, Any], expected: bool) -> None:
    assert has_write_permission(payload) is expected


def test_api_preflight_validates_users_and_discovers_actions_source(tmp_path: Path) -> None:
    plan = render_test_plan(tmp_path)
    client = FakeGitHubClient(user_preflight_responses())

    result = preflight_control_plane(client, plan)
    bound = bind_plan_to_preflight(plan, result)

    assert result.required_check_integration_id == 4242
    assert result.validated_codeowners == ({"handle": "@alice", "id": 1, "kind": "user", "permission": "write"},)
    assert all(method == "GET" and payload is None for method, _path, payload in client.calls)
    required = next(rule for rule in bound["ruleset"]["rules"] if rule["type"] == "required_status_checks")
    assert required["parameters"]["required_status_checks"] == [{"context": "required", "integration_id": 4242}]


def test_api_preflight_validates_visible_team_with_write_access(tmp_path: Path) -> None:
    plan = render_test_plan(
        tmp_path,
        profile="team",
        maintainers=["acme/platform"],
        eligible_reviewers=2,
    )
    responses = user_preflight_responses(maintainers=())
    responses[("GET", "/orgs/acme/teams/platform")] = {
        "id": 77,
        "slug": "platform",
        "privacy": "closed",
    }
    responses[("GET", "/orgs/acme/teams/platform/repos/acme/service")] = {"permission": "maintain"}
    client = FakeGitHubClient(responses)

    result = preflight_control_plane(client, plan)

    assert result.validated_codeowners == (
        {"handle": "@acme/platform", "id": 77, "kind": "team", "permission": "maintain"},
    )


def test_api_preflight_rejects_codeowner_without_write_access(tmp_path: Path) -> None:
    plan = render_test_plan(tmp_path)
    responses = user_preflight_responses()
    responses[("GET", "/repos/acme/service/collaborators/alice/permission")] = {"permission": "read"}
    client = FakeGitHubClient(responses)

    with pytest.raises(PreflightError, match="does not have explicit write access"):
        preflight_control_plane(client, plan)

    assert all(method == "GET" for method, _path, _payload in client.calls)


def test_api_preflight_rejects_two_handles_resolving_to_one_person(tmp_path: Path) -> None:
    plan = render_test_plan(
        tmp_path,
        profile="team",
        maintainers=["alice", "alice-renamed"],
        eligible_reviewers=2,
    )
    responses = user_preflight_responses(maintainers=("alice", "alice-renamed"))
    responses[("GET", "/users/alice-renamed")]["id"] = 1
    client = FakeGitHubClient(responses)

    with pytest.raises(PreflightError, match="duplicate GitHub user"):
        preflight_control_plane(client, plan)


def test_api_preflight_refuses_to_guess_required_check_source(tmp_path: Path) -> None:
    plan = render_test_plan(tmp_path)
    responses = user_preflight_responses()
    check_path = "/repos/acme/service/commits/abc123/check-runs?check_name=required&filter=latest&per_page=100"
    responses[("GET", check_path)] = {"check_runs": []}
    client = FakeGitHubClient(responses)

    with pytest.raises(PreflightError, match="will not guess"):
        preflight_control_plane(client, plan)

    assert all(method == "GET" for method, _path, _payload in client.calls)


def test_rulesets_403_has_actionable_preflight_guidance(tmp_path: Path) -> None:
    plan = render_test_plan(tmp_path)
    responses = user_preflight_responses()
    rulesets_path = "/repos/acme/service/rulesets?includes_parents=false&targets=branch&per_page=100"
    responses[("GET", rulesets_path)] = GitHubAPIError(
        method="GET",
        path=rulesets_path,
        status=403,
        detail="Resource not accessible by personal access token",
    )
    client = FakeGitHubClient(responses)

    with pytest.raises(PreflightError, match="Administration: write"):
        preflight_control_plane(client, plan)


def test_rulesets_404_mentions_plan_support() -> None:
    error = GitHubAPIError(
        method="GET",
        path="/repos/acme/service/rulesets",
        status=404,
        detail="Not Found",
    )

    message = actionable_api_error(error, stage="Rulesets access preflight")

    assert "plan support" in message
    assert "private repositories on GitHub Pro" in message


def test_apply_failure_reports_completed_and_pending_stages(tmp_path: Path) -> None:
    plan = render_test_plan(tmp_path)
    preflight = PreflightResult(
        repository={
            "owner": {"login": "acme", "type": "Organization"},
            "permissions": {"admin": True},
            **repository_settings(),
            "allow_merge_commit": True,
        },
        current_ruleset=None,
        required_check_integration_id=4242,
        validated_codeowners=({"handle": "@alice", "id": 1, "kind": "user", "permission": "write"},),
    )
    bound = bind_plan_to_preflight(plan, preflight)
    ruleset_error = GitHubAPIError(
        method="POST",
        path="/repos/acme/service/rulesets",
        status=403,
        detail="Resource not accessible by personal access token",
    )
    client = FakeGitHubClient(
        {
            ("PATCH", "/repos/acme/service"): {},
            ("POST", "/repos/acme/service/rulesets"): ruleset_error,
        }
    )
    writes: list[tuple[Path, str]] = []

    with pytest.raises(ApplyStageError) as captured:
        apply_control_plane(
            client,
            plan=bound,
            preflight=preflight,
            codeowners_output=tmp_path / "CODEOWNERS",
            writer=lambda path, content: writes.append((path, content)),
        )

    report = captured.value.as_dict()
    assert writes
    assert report["failed_stage"] == "ruleset"
    assert report["completed"] == [
        {"stage": "preflight", "result": "passed"},
        {"stage": "codeowners", "result": str(tmp_path / "CODEOWNERS")},
        {"stage": "repository-settings", "result": "updated"},
    ]
    assert report["not_completed"] == ["ruleset"]
    assert "Administration: write" in report["cause"]
