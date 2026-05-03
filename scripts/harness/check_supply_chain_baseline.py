#!/usr/bin/env python3
"""Enforce deterministic supply-chain rules for the template."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FULL_SHA_RE = re.compile(r"^[a-f0-9]{40}$")
PINNED_ACTION_RE = re.compile(r"^[^@\s]+@[a-f0-9]{40}$")
FRONTEND_LOCKFILES = (
    "src/frontend/package-lock.json",
    "src/frontend/yarn.lock",
    "src/frontend/pnpm-lock.yaml",
    "src/frontend/bun.lock",
    "src/frontend/bun.lockb",
)
WRITE_PERMISSION_ALLOWED_JOBS = {
    ".github/workflows/backmerge-main-to-dev.yml": {"backmerge"},
    ".github/workflows/release.yml": {"release", "backmerge"},
}


@dataclass(frozen=True)
class Violation:
    """A supply-chain baseline violation."""

    path: Path
    message: str

    def format(self, root: Path) -> str:
        return f"{self.path.relative_to(root)}: {self.message}"


def load_yaml(path: Path) -> Any:
    """Load a YAML file."""
    return yaml.safe_load(path.read_text())


def check_lockfiles(root: Path) -> list[Violation]:
    """Require the selected package-manager lockfiles and reject drift."""
    violations: list[Violation] = []
    if not (root / "uv.lock").is_file():
        violations.append(Violation(root / "uv.lock", "required lockfile is missing"))

    present_frontend_lockfiles = [relative for relative in FRONTEND_LOCKFILES if (root / relative).exists()]
    if not present_frontend_lockfiles:
        violations.append(Violation(root / "src/frontend", "one frontend package-manager lockfile is required"))
    if len(present_frontend_lockfiles) > 1:
        violations.append(
            Violation(
                root / "src/frontend",
                "only one frontend package-manager lockfile is allowed: " + ", ".join(present_frontend_lockfiles),
            )
        )

    if "src/frontend/package-lock.json" not in present_frontend_lockfiles:
        return violations

    package_json = root / "src/frontend/package.json"
    package_data = json.loads(package_json.read_text())
    package_manager = package_data.get("packageManager", "")
    if package_manager and not package_manager.startswith("npm@"):
        violations.append(Violation(package_json, "packageManager must match the committed frontend lockfile"))

    return violations


def iter_workflow_files(root: Path) -> list[Path]:
    """Return GitHub workflow files."""
    workflows = root / ".github/workflows"
    return sorted(workflows.glob("*.yml")) + sorted(workflows.glob("*.yaml"))


def find_unpinned_actions(path: Path, workflow: Any) -> list[Violation]:
    """Return workflow action references that are not pinned to full SHAs."""
    violations: list[Violation] = []
    jobs = workflow.get("jobs", {}) if isinstance(workflow, dict) else {}
    for job_id, job in jobs.items():
        steps = job.get("steps", []) if isinstance(job, dict) else []
        for step in steps:
            if not isinstance(step, dict) or "uses" not in step:
                continue
            action = str(step["uses"])
            if action.startswith("./"):
                continue
            if not PINNED_ACTION_RE.match(action):
                violations.append(Violation(path, f"{job_id} uses unpinned action: {action}"))
    return violations


def check_workflow_permissions(root: Path, path: Path, workflow: Any) -> list[Violation]:
    """Require least-privilege workflow permissions."""
    relative = str(path.relative_to(root))
    permissions = workflow.get("permissions") if isinstance(workflow, dict) else None
    violations: list[Violation] = []

    if permissions != {"contents": "read"}:
        violations.append(Violation(path, "top-level permissions must be contents: read"))

    jobs = workflow.get("jobs", {}) if isinstance(workflow, dict) else {}
    allowed_jobs = WRITE_PERMISSION_ALLOWED_JOBS.get(relative, set())
    for job_id, job in jobs.items():
        if not isinstance(job, dict) or "permissions" not in job:
            continue
        job_permissions = job["permissions"]
        if job_permissions == {"contents": "write"} and job_id in allowed_jobs:
            continue
        violations.append(Violation(path, f"{job_id} has prohibited job permissions: {job_permissions}"))

    return violations


def check_workflow_commands(path: Path, workflow_text: str) -> list[Violation]:
    """Block mutable dependency installation commands in workflows."""
    violations: list[Violation] = []
    for line_number, line in enumerate(workflow_text.splitlines(), start=1):
        stripped = line.strip()
        if re.search(r"\bnpm install\b", stripped):
            violations.append(Violation(path, f"line {line_number} must use npm ci, not npm install"))
        if re.search(r"\buv sync\b", stripped) and "--frozen" not in stripped:
            violations.append(Violation(path, f"line {line_number} must use uv sync --frozen"))
    return violations


def check_workflows(root: Path) -> list[Violation]:
    """Check all workflow supply-chain rules."""
    violations: list[Violation] = []
    for path in iter_workflow_files(root):
        workflow_text = path.read_text()
        workflow = load_yaml(path)
        violations.extend(find_unpinned_actions(path, workflow))
        violations.extend(check_workflow_permissions(root, path, workflow))
        violations.extend(check_workflow_commands(path, workflow_text))
    return violations


def check_supply_chain_baseline(root: Path = PROJECT_ROOT) -> list[Violation]:
    """Check the repository supply-chain baseline."""
    root = root.resolve()
    violations: list[Violation] = []
    violations.extend(check_lockfiles(root))
    violations.extend(check_workflows(root))
    return violations


def main() -> int:
    """CLI entry point."""
    violations = check_supply_chain_baseline()
    if violations:
        print("Supply-chain baseline violations:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation.format(PROJECT_ROOT)}", file=sys.stderr)
        return 1

    print("Supply-chain baseline passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
