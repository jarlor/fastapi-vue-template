"""Tests for the branch workflow checker."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "harness" / "check_branch_workflow.py"


def load_checker_module() -> ModuleType:
    """Load the checker script as a module without making scripts a package."""
    spec = importlib.util.spec_from_file_location("check_branch_workflow", CHECKER_PATH)
    if spec is None or spec.loader is None:
        msg = f"Could not load {CHECKER_PATH}"
        raise RuntimeError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = load_checker_module()
check_branch_workflow = checker.check_branch_workflow
agent_start_message = checker.agent_start_message
clean_agent_handoff = checker.clean_agent_handoff


def git(root: Path, *args: str) -> None:
    """Run git in a test repository."""
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def seed_repo(root: Path, branch: str = "main") -> None:
    """Create a git repository with a baseline commit."""
    git(root, "init", "-b", branch)
    git(root, "config", "user.name", "Test User")
    git(root, "config", "user.email", "test@example.com")
    (root / "README.md").write_text("# Test\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "chore: initialize from template")


def test_allows_clean_baseline_branch(tmp_path: Path) -> None:
    seed_repo(tmp_path)

    assert check_branch_workflow(tmp_path) == []


def test_allows_generated_files_before_baseline_commit(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    (tmp_path / "src" / "example").mkdir(parents=True)
    (tmp_path / "src" / "example" / "feature.py").write_text("VALUE = 1\n")

    assert check_branch_workflow(tmp_path) == []


def test_blocks_product_changes_on_baseline_branch(tmp_path: Path) -> None:
    seed_repo(tmp_path)
    (tmp_path / "src" / "example").mkdir(parents=True)
    (tmp_path / "src" / "example" / "feature.py").write_text("VALUE = 1\n")

    violations = check_branch_workflow(tmp_path)

    assert len(violations) == 1
    assert "baseline branch 'main'" in violations[0]
    assert "src/example/feature.py" in violations[0]


def test_agent_start_prompts_for_feature_branch_on_clean_baseline(tmp_path: Path) -> None:
    seed_repo(tmp_path)

    exit_code, message = agent_start_message(tmp_path)

    assert exit_code == 0
    assert "## main" in message
    assert "git switch -c feat/<short-task-name>" in message


def test_agent_start_fails_after_baseline_branch_product_edit(tmp_path: Path) -> None:
    seed_repo(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'example'\n")

    exit_code, message = agent_start_message(tmp_path)

    assert exit_code == 1
    assert "product/template changes detected on baseline branch 'main'" in message
    assert "pyproject.toml" in message


def test_agent_start_passes_on_feature_branch(tmp_path: Path) -> None:
    seed_repo(tmp_path)
    git(tmp_path, "switch", "-c", "feat/chat")

    exit_code, message = agent_start_message(tmp_path)

    assert exit_code == 0
    assert "Agent startup gate passed" in message


def test_allows_product_changes_on_feature_branch(tmp_path: Path) -> None:
    seed_repo(tmp_path)
    git(tmp_path, "switch", "-c", "feat/chat")
    (tmp_path / "src" / "example").mkdir(parents=True)
    (tmp_path / "src" / "example" / "feature.py").write_text("VALUE = 1\n")

    assert check_branch_workflow(tmp_path) == []


def test_ignores_non_product_local_files_on_baseline_branch(tmp_path: Path) -> None:
    seed_repo(tmp_path)
    (tmp_path / "scratch.txt").write_text("local note\n")

    assert check_branch_workflow(tmp_path) == []


def test_agent_handoff_clean_removes_rebuildable_dependency_trees(tmp_path: Path) -> None:
    for relative in (".venv/lib/site.py", "src/frontend/node_modules/pkg/index.js", "src/frontend/dist/index.html"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated\n")
    source_file = tmp_path / "src" / "frontend" / "src" / "main.ts"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("source\n")

    removed = clean_agent_handoff(tmp_path)

    assert removed == [".venv", "src/frontend/node_modules", "src/frontend/dist"]
    assert not (tmp_path / ".venv").exists()
    assert not (tmp_path / "src" / "frontend" / "node_modules").exists()
    assert not (tmp_path / "src" / "frontend" / "dist").exists()
    assert source_file.exists()
