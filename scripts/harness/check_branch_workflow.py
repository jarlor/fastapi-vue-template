#!/usr/bin/env python3
"""Require product edits to happen on a focused feature branch."""

from __future__ import annotations

import shutil
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
CLEANUP_PATHS = (
    ".venv",
    "src/frontend/node_modules",
    "src/frontend/dist",
)
DEFAULT_HANDOFF_BRANCH = "feat/agent-work"


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


def agent_start_message(root: Path = PROJECT_ROOT) -> tuple[int, str]:
    """Return the agent startup gate status and message."""
    root = root.resolve()
    if not inside_work_tree(root):
        return (
            0,
            "No git repository detected. If this is a fresh generated project, run the AGENTS.md init workflow first.",
        )

    branch = current_branch(root) or "<detached>"
    status_result = run_git(["status", "--short", "--branch"], root)
    status = status_result.stdout.strip() if status_result.returncode == 0 else f"## {branch}"

    if not has_commits(root):
        return (
            0,
            f"{status}\nNo baseline commit exists yet. Complete the AGENTS.md init workflow "
            "and commit the template baseline.",
        )

    violations = check_branch_workflow(root)
    if violations:
        return (
            1,
            f"{status}\n{violations[0]}",
        )

    if branch in BASELINE_BRANCHES:
        return (
            0,
            f"{status}\nBaseline branch detected. Before editing product code, run: "
            "git switch -c feat/<short-task-name>",
        )

    return (0, f"{status}\nAgent startup gate passed. Continue on this focused branch.")


def clean_agent_handoff(root: Path = PROJECT_ROOT) -> list[str]:
    """Remove rebuildable dependency trees before handing a repo to an agent."""
    removed: list[str] = []
    for relative in CLEANUP_PATHS:
        path = root / relative
        if path.exists():
            shutil.rmtree(path)
            removed.append(relative)
    return removed


def next_available_branch(root: Path, preferred: str) -> str:
    """Return preferred branch name, or a numbered variant when it already exists."""
    candidate = preferred
    suffix = 2
    while run_git(["show-ref", "--verify", "--quiet", f"refs/heads/{candidate}"], root).returncode == 0:
        candidate = f"{preferred}-{suffix}"
        suffix += 1
    return candidate


def prepare_agent_handoff(root: Path = PROJECT_ROOT, branch_name: str | None = None) -> tuple[int, str]:
    """Prepare a generated repository before handing it to an agent."""
    root = root.resolve()
    if not inside_work_tree(root):
        return (1, "No git repository detected. Complete the AGENTS.md init workflow before agent handoff.")

    if not has_commits(root):
        return (1, "No baseline commit exists yet. Commit the generated template baseline before agent handoff.")

    branch = current_branch(root) or "<detached>"
    if branch in BASELINE_BRANCHES:
        target_branch = next_available_branch(root, branch_name or DEFAULT_HANDOFF_BRANCH)
        switch_result = run_git(["switch", "-c", target_branch], root)
        if switch_result.returncode != 0:
            return (1, switch_result.stderr.strip() or f"Failed to create handoff branch: {target_branch}")
        branch = target_branch

    removed = clean_agent_handoff(root)
    message_lines = [f"Agent handoff ready on branch: {branch}"]
    if removed:
        message_lines.append("Removed rebuildable agent-handoff paths:")
        message_lines.extend(f"- {path}" for path in removed)
    else:
        message_lines.append("No rebuildable agent-handoff paths found.")
    return (0, "\n".join(message_lines))


def main() -> int:
    """CLI entry point."""
    if "--agent-start" in sys.argv:
        exit_code, message = agent_start_message()
        stream = sys.stderr if exit_code else sys.stdout
        print(message, file=stream)
        return exit_code

    if "--agent-handoff" in sys.argv:
        index = sys.argv.index("--agent-handoff")
        branch_name = sys.argv[index + 1] if len(sys.argv) > index + 1 else None
        exit_code, message = prepare_agent_handoff(branch_name=branch_name)
        stream = sys.stderr if exit_code else sys.stdout
        print(message, file=stream)
        return exit_code

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
