#!/usr/bin/env python3
"""Require product edits to happen on a focused feature branch."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_BRANCHES = {"main", "master", "dev"}
PRODUCT_PATH_PREFIXES = (
    ".env.example",
    ".github/",
    ".pre-commit-config.yaml",
    "AGENTS.md",
    "README.md",
    "config.yaml",
    "contracts/",
    "docs/",
    "harness_tests/",
    "pyproject.toml",
    "scripts/",
    "src/",
    "tests/",
    "uv.lock",
)


def run_git(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command and return its result."""
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def inside_work_tree(root: Path) -> bool:
    """Return whether root is inside a git work tree."""
    result = run_git(["rev-parse", "--is-inside-work-tree"], root)
    return result.returncode == 0 and result.stdout.strip() == "true"


def current_branch(root: Path) -> str | None:
    """Return the current branch name, or None for detached HEAD/unknown."""
    result = run_git(["branch", "--show-current"], root)
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return branch or None


def has_commits(root: Path) -> bool:
    """Return whether the repository has at least one commit."""
    result = run_git(["rev-parse", "--verify", "HEAD"], root)
    return result.returncode == 0


def changed_paths(root: Path) -> list[str]:
    """Return changed tracked and untracked paths."""
    result = run_git(["status", "--short", "--untracked-files=all"], root)
    if result.returncode != 0:
        return []

    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        paths.append(path)
    return paths


def is_product_path(path: str) -> bool:
    """Return whether a changed path is part of repository-owned product/template code."""
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in PRODUCT_PATH_PREFIXES)


def check_branch_workflow(root: Path = PROJECT_ROOT) -> list[str]:
    """Return branch workflow violations."""
    root = root.resolve()
    if not inside_work_tree(root):
        return []

    if not has_commits(root):
        return []

    branch = current_branch(root)
    if branch not in BASELINE_BRANCHES:
        return []

    changed_product_paths = [path for path in changed_paths(root) if is_product_path(path)]
    if not changed_product_paths:
        return []

    sample = ", ".join(changed_product_paths[:5])
    if len(changed_product_paths) > 5:
        sample = f"{sample}, ..."
    return [
        f"product/template changes detected on baseline branch '{branch}': {sample}. "
        "Create a focused feature branch before editing product code."
    ]


def main() -> int:
    """CLI entry point."""
    violations = check_branch_workflow()
    if violations:
        print("Branch workflow violations:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print("Branch workflow passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
