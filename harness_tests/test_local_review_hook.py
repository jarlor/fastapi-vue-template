"""Process tests for the local OpenCodeReview Stop hook."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".codex" / "hooks" / "stop_review.py"


def run(*command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, check=True, text=True)


def git(repo: Path, *arguments: str) -> str:
    return run("git", "-C", str(repo), *arguments, cwd=repo).stdout.strip()


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def seed_repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    run("git", "init", "--initial-branch=main", str(repo), cwd=tmp_path)
    git(repo, "config", "user.email", "hook-tests@example.invalid")
    git(repo, "config", "user.name", "Hook Tests")
    write(repo / "app.py", "VALUE = 1\n")
    write(repo / ".gitattributes", (ROOT / ".gitattributes").read_text())
    handler = repo / ".codex" / "hooks" / "stop_review.py"
    handler.parent.mkdir(parents=True, exist_ok=True)
    handler.write_bytes(HOOK.read_bytes())
    write(repo / ".opencodereview" / "rule.json", (ROOT / ".opencodereview" / "rule.json").read_text())
    write(repo / ".opencodereview" / "review-rules.md", (ROOT / ".opencodereview" / "review-rules.md").read_text())
    git(repo, "add", ".")
    git(repo, "commit", "-m", "seed")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


def make_fake_ocr(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "ocr.jsonl"
    executable = bin_dir / "ocr"
    executable.write_text(
        f"#!{sys.executable}\n"
        + """import json
import os
import sys

with open(os.environ["FAKE_OCR_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps({
        "args": sys.argv[1:],
        "git_config_count": os.getenv("GIT_CONFIG_COUNT"),
        "git_dir": os.getenv("GIT_DIR"),
        "ocr_no_update": os.getenv("OCR_NO_UPDATE"),
    }) + "\\n")

mode = os.getenv("FAKE_OCR_MODE", "ok")
if mode == "update-hint":
    print("\\033[33m[ocr] A new version (v1.9.0) is available. Run to update:\\033[0m", file=sys.stderr)
    print("  npm i -g @alibaba-group/open-code-review@1.9.0", file=sys.stderr)
if mode == "wrong-version":
    print("open-code-review v9.9.9 (deadbeef0) fake/test")
else:
    print("open-code-review v1.8.5 (582953937) fake/test")
""",
    )
    executable.chmod(0o755)
    return bin_dir, log_path


def fake_environment(bin_dir: Path, log_path: Path, *, mode: str = "ok") -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join((str(bin_dir), env.get("PATH", "")))
    env["FAKE_OCR_LOG"] = str(log_path)
    env["FAKE_OCR_MODE"] = mode
    return env


def invoke_hook(
    repo: Path,
    *,
    env: dict[str, str],
    active: bool = False,
    cwd: Path | None = None,
    session_id: str = "test-session",
) -> dict[str, Any]:
    value = {
        "hook_event_name": "Stop",
        "cwd": str(cwd or repo),
        "stop_hook_active": active,
        "session_id": session_id,
    }
    result = subprocess.run(
        [sys.executable, str(repo / ".codex" / "hooks" / "stop_review.py")],
        cwd=repo,
        env=env,
        input=json.dumps(value),
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    records = result.stdout.splitlines()
    assert len(records) == 1
    parsed = json.loads(records[0])
    assert isinstance(parsed, dict)
    return parsed


def ocr_calls(log_path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in log_path.read_text().splitlines()] if log_path.exists() else []


def clear_log(log_path: Path) -> None:
    if log_path.exists():
        log_path.unlink()


def test_clean_repository_allows_without_ocr(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    bin_dir, log_path = make_fake_ocr(tmp_path)

    assert invoke_hook(repo, env=fake_environment(bin_dir, log_path)) == {"continue": True}
    assert ocr_calls(log_path) == []


def test_changed_branch_and_workspace_request_exact_review_commands(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    git(repo, "switch", "-c", "feature")
    write(repo / "app.py", "VALUE = 2\n")
    git(repo, "add", "app.py")
    git(repo, "commit", "-m", "feature")
    write(repo / "workspace.py", "WORKSPACE = True\n")
    bin_dir, log_path = make_fake_ocr(tmp_path)

    response = invoke_hook(repo, env=fake_environment(bin_dir, log_path))

    assert response.get("decision") == "block"
    reason = response["reason"]
    assert '"--from", "origin/main", "--to", "HEAD"' in reason
    assert '"delegate", "preview", "--repo"' in reason
    assert '"delegate", "rule", "--repo"' in reason
    assert '"--no-ext-diff", "--no-textconv"' in reason
    assert '"--diff-filter=D", "--name-only", "-z"' in reason
    assert [call["args"] for call in ocr_calls(log_path)] == [["version"]]


def test_active_continuation_completes_and_deduplicates_same_state(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    write(repo / "workspace.py", "WORKSPACE = True\n")
    bin_dir, log_path = make_fake_ocr(tmp_path)
    env = fake_environment(bin_dir, log_path)
    assert invoke_hook(repo, env=env).get("decision") == "block"
    clear_log(log_path)

    active = invoke_hook(repo, env=env, active=True)
    assert "quality is not mechanically verified" in active.get("systemMessage", "")
    assert invoke_hook(repo, env=env) == {"continue": True}
    assert ocr_calls(log_path) == []


def test_changed_state_during_review_remains_unreviewed(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    workspace = repo / "workspace.py"
    write(workspace, "WORKSPACE = 1\n")
    bin_dir, log_path = make_fake_ocr(tmp_path)
    env = fake_environment(bin_dir, log_path)
    assert invoke_hook(repo, env=env).get("decision") == "block"

    write(workspace, "WORKSPACE = 2\n")
    assert "remains unreviewed" in invoke_hook(repo, env=env, active=True).get("systemMessage", "")
    assert invoke_hook(repo, env=env).get("decision") == "block"


def test_other_session_cannot_complete_pending_review(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    write(repo / "workspace.py", "WORKSPACE = True\n")
    bin_dir, log_path = make_fake_ocr(tmp_path)
    env = fake_environment(bin_dir, log_path)
    assert invoke_hook(repo, env=env, session_id="a").get("decision") == "block"

    unrelated = invoke_hook(repo, env=env, active=True, session_id="b")
    assert "No review request" in unrelated.get("systemMessage", "")
    assert invoke_hook(repo, env=env, active=True, session_id="a").get("continue") is True


@pytest.mark.skipif(os.name == "nt", reason="executable mode is not portable on Windows")
def test_untracked_content_and_mode_changes_retrigger(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    workspace = repo / "workspace.py"
    write(workspace, "WORKSPACE = 1\n")
    bin_dir, log_path = make_fake_ocr(tmp_path)
    env = fake_environment(bin_dir, log_path)
    assert invoke_hook(repo, env=env).get("decision") == "block"
    assert invoke_hook(repo, env=env, active=True).get("continue") is True

    write(workspace, "WORKSPACE = 2\n")
    assert invoke_hook(repo, env=env).get("decision") == "block"
    assert invoke_hook(repo, env=env, active=True).get("continue") is True
    workspace.chmod(0o755)
    assert invoke_hook(repo, env=env).get("decision") == "block"


def test_nested_cwd_still_anchors_commands_to_root(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    nested = repo / "src" / "package"
    write(nested / "new.py", "NEW = True\n")
    bin_dir, log_path = make_fake_ocr(tmp_path)

    response = invoke_hook(repo, cwd=nested, env=fake_environment(bin_dir, log_path))

    assert response.get("decision") == "block"
    assert json.dumps(str(repo.resolve())) in response["reason"]
    assert f'"-C", "{repo.resolve()}"' in response["reason"]


def test_missing_or_wrong_ocr_fails_closed(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    write(repo / "workspace.py", "WORKSPACE = True\n")
    installed_git = shutil.which("git")
    assert installed_git
    git_only = tmp_path / "git-only"
    git_only.mkdir()
    (git_only / Path(installed_git).name).symlink_to(installed_git)
    env = os.environ.copy()
    env["PATH"] = str(git_only)
    assert "OpenCodeReview is missing" in invoke_hook(repo, env=env).get("stopReason", "")

    bin_dir, log_path = make_fake_ocr(tmp_path)
    wrong = invoke_hook(repo, env=fake_environment(bin_dir, log_path, mode="wrong-version"))
    assert "must be exactly v1.8.5" in wrong.get("stopReason", "")


def test_cached_update_hint_is_accepted_without_updating(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    write(repo / "workspace.py", "WORKSPACE = True\n")
    bin_dir, log_path = make_fake_ocr(tmp_path)

    response = invoke_hook(repo, env=fake_environment(bin_dir, log_path, mode="update-hint"))

    assert response.get("decision") == "block"
    assert [call["args"] for call in ocr_calls(log_path)] == [["version"]]


def test_repo_local_ocr_is_not_used(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    write(repo / "workspace.py", "WORKSPACE = True\n")
    bin_dir, log_path = make_fake_ocr(repo)
    installed_git = shutil.which("git")
    assert installed_git
    git_only = tmp_path / "git-only"
    git_only.mkdir()
    (git_only / Path(installed_git).name).symlink_to(installed_git)
    env = fake_environment(bin_dir, log_path)
    env["PATH"] = os.pathsep.join((str(bin_dir), str(git_only)))

    response = invoke_hook(repo, env=env)

    assert response.get("continue") is False
    assert "OpenCodeReview is missing" in response.get("stopReason", "")
    assert ocr_calls(log_path) == []


@pytest.mark.skipif(os.name == "nt", reason="unprivileged Windows users may not create symlinks")
def test_untracked_symlink_fails_closed(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    outside = tmp_path / "outside.py"
    write(outside, "SECRET = True\n")
    (repo / "linked.py").symlink_to(outside)
    bin_dir, log_path = make_fake_ocr(tmp_path)

    response = invoke_hook(repo, env=fake_environment(bin_dir, log_path))

    assert response.get("continue") is False
    assert "untracked links" in response.get("stopReason", "")
    assert ocr_calls(log_path) == []


@pytest.mark.skipif(os.name == "nt", reason="executable external-diff fixture is POSIX-only")
def test_external_diff_and_fsmonitor_are_not_executed(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    marker = tmp_path / "git-extension-ran"
    helper = tmp_path / "git-extension"
    helper.write_text(f"#!{sys.executable}\nfrom pathlib import Path\nPath({str(marker)!r}).touch()\n")
    helper.chmod(0o755)
    git(repo, "config", "diff.external", str(helper))
    git(repo, "config", "core.fsmonitor", str(helper))
    write(repo / "workspace.py", "WORKSPACE = True\n")
    bin_dir, log_path = make_fake_ocr(tmp_path)

    assert invoke_hook(repo, env=fake_environment(bin_dir, log_path)).get("decision") == "block"
    assert not marker.exists()


def test_git_environment_cannot_redirect_state(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    other_parent = tmp_path / "other"
    other_parent.mkdir()
    other = seed_repository(other_parent)
    write(repo / "workspace.py", "WORKSPACE = True\n")
    bin_dir, log_path = make_fake_ocr(tmp_path)
    env = fake_environment(bin_dir, log_path)
    env["GIT_DIR"] = str(other / ".git")
    env["GIT_WORK_TREE"] = str(other)

    assert invoke_hook(repo, env=env).get("decision") == "block"
    assert not (other / ".git" / "codex-local-review").exists()
    assert all(call["git_dir"] is None and call["git_config_count"] == "1" for call in ocr_calls(log_path))


def test_invalid_policy_fails_before_ocr(tmp_path: Path) -> None:
    repo = seed_repository(tmp_path)
    write(repo / "workspace.py", "WORKSPACE = True\n")
    write(repo / ".opencodereview" / "rule.json", "not json\n")
    bin_dir, log_path = make_fake_ocr(tmp_path)

    response = invoke_hook(repo, env=fake_environment(bin_dir, log_path))

    assert response.get("continue") is False
    assert "policy is missing or invalid" in response.get("stopReason", "")
    assert ocr_calls(log_path) == []
