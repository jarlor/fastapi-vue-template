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


def test_blocks_product_changes_on_baseline_branch(tmp_path: Path) -> None:
    seed_repo(tmp_path)
    (tmp_path / "src" / "example").mkdir(parents=True)
    (tmp_path / "src" / "example" / "feature.py").write_text("VALUE = 1\n")

    violations = check_branch_workflow(tmp_path)

    assert len(violations) == 1
    assert "baseline branch 'main'" in violations[0]
    assert "src/example/feature.py" in violations[0]


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
