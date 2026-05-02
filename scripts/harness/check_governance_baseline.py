#!/usr/bin/env python3
"""Enforce repository governance rules for agent-driven changes.

This checker keeps soft guidance aligned with hard gates. It is intentionally
narrow: every rule should be stable enough to block a PR without interpretation.
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_HARNESS_TASKS = (
    "lint",
    "harness-test",
    "branch-harness",
    "governance-harness",
    "supply-chain",
    "architecture",
    "security",
    "api-contracts",
    "frontend-harness",
    "runtime-harness",
    "test",
)
REQUIRED_NON_AGGREGATE_TASKS = (
    "agent-start",
    "agent-handoff",
    "template-smoke",
)
REQUIRED_EVIDENCE_COMMANDS = (
    "harness",
    "template-smoke",
)
REQUIRED_AGENT_GUIDANCE = (
    "PROJECT_MAP.md",
    "uv run poe agent-start",
    "uv run poe agent-handoff",
    "create a focused feature branch before changing product code",
    "exclude `.git/`, `.venv/`, `node_modules/`, `.ruff_cache/`, `.pytest_cache/`, logs, and generated coverage files",
)
REQUIRED_CI_POE_TASKS = (
    "harness",
    "template-smoke --full",
)
REQUIRED_README_AGENT_GUIDANCE = (
    "## AI Agent Entry",
    "If you are an AI coding agent working in this repository",
    "Read [PROJECT_MAP.md](PROJECT_MAP.md)",
    "Read [AGENTS.md](AGENTS.md)",
    "Run `uv run poe agent-start`",
    "uv run poe agent-handoff",
)
PROHIBITED_AGENT_ADAPTERS = (
    "CLAUDE.md",
    ".claude",
    ".cursor",
    ".cursorrules",
    ".windsurf",
    ".windsurfrules",
)


@dataclass(frozen=True)
class Violation:
    """A repository governance violation."""

    path: Path
    message: str

    def format(self, root: Path) -> str:
        rel_path = self.path.relative_to(root)
        return f"{rel_path}: {self.message}"


def read_text(root: Path, relative: str) -> str:
    """Read a required repository text file."""
    return (root / relative).read_text()


def find_prohibited_adapters(root: Path) -> list[Violation]:
    """Return committed product-specific agent adapter paths."""
    violations: list[Violation] = []
    for adapter in PROHIBITED_AGENT_ADAPTERS:
        path = root / adapter
        if path.exists():
            violations.append(Violation(path=path, message="product-specific agent adapter is prohibited"))
    return violations


def extract_task_commands(task: object) -> list[str]:
    """Return command strings from a Poe task definition."""
    if isinstance(task, str):
        return [task]
    if isinstance(task, dict):
        command = task.get("cmd")
        return [command] if isinstance(command, str) else []
    if isinstance(task, list):
        commands: list[str] = []
        for item in task:
            commands.extend(extract_task_commands(item))
        return commands
    return []


def find_missing_poe_tasks(root: Path, pyproject_text: str) -> list[Violation]:
    """Return missing public Poe tasks and aggregate harness entries."""
    violations: list[Violation] = []
    pyproject = root / "pyproject.toml"
    poe_tasks = tomllib.loads(pyproject_text).get("tool", {}).get("poe", {}).get("tasks", {})
    harness_commands = extract_task_commands(poe_tasks.get("harness"))

    for task in REQUIRED_HARNESS_TASKS:
        if task not in poe_tasks:
            violations.append(Violation(path=pyproject, message=f"missing Poe task: {task}"))
        if f"uv run poe {task}" not in harness_commands:
            violations.append(Violation(path=pyproject, message=f"aggregate harness must run: uv run poe {task}"))

    for task in REQUIRED_NON_AGGREGATE_TASKS:
        if task not in poe_tasks:
            violations.append(Violation(path=pyproject, message=f"missing Poe task: {task}"))

    return violations


def find_missing_ci_entries(root: Path, ci_text: str) -> list[Violation]:
    """Return missing CI hard-gate Poe commands."""
    ci_path = root / ".github" / "workflows" / "ci.yml"
    violations: list[Violation] = []
    for task in REQUIRED_CI_POE_TASKS:
        command = f"uv run poe {task}"
        if command not in ci_text:
            violations.append(Violation(path=ci_path, message=f"CI must run public Poe entrypoint: {command}"))

    if "continue-on-error" in ci_text:
        violations.append(Violation(path=ci_path, message="required CI workflow must not use continue-on-error"))

    return violations


def find_missing_evidence_entries(root: Path, text: str, relative: str) -> list[Violation]:
    """Return missing required harness evidence entries in an instruction file."""
    path = root / relative
    violations: list[Violation] = []
    for task in REQUIRED_EVIDENCE_COMMANDS:
        command = f"uv run poe {task}"
        if command not in text:
            violations.append(Violation(path=path, message=f"missing required evidence command: {command}"))
    return violations


def find_missing_agent_guidance(root: Path, agents_text: str) -> list[Violation]:
    """Return missing workflow guidance that keeps agents on the intended path."""
    path = root / "AGENTS.md"
    violations: list[Violation] = []
    for relative in ("00-START-HERE.md", "00-START-HERE/README.md"):
        start_here = root / relative
        if not start_here.is_file():
            violations.append(Violation(path=start_here, message="missing agent startup sentinel"))
            continue

        start_text = start_here.read_text()
        for expected in (
            "uv run poe agent-start",
            "uv run poe agent-handoff",
            "AGENTS.md",
            "PROJECT_MAP.md",
            ".venv/",
        ):
            if expected not in start_text:
                violations.append(Violation(path=start_here, message=f"missing startup sentinel guidance: {expected}"))

    project_map = root / "PROJECT_MAP.md"
    if not project_map.is_file():
        violations.append(Violation(path=project_map, message="missing repository source map"))
    else:
        project_map_text = project_map.read_text()
        for expected in (
            "uv run poe agent-start",
            "uv run poe agent-handoff",
            "AGENTS.md",
            "src/app_name/",
            "src/frontend/",
            "harness_tests/",
            "scripts/harness/",
            ".venv/",
            "node_modules/",
            "uv run poe harness",
        ):
            if expected not in project_map_text:
                violations.append(Violation(path=project_map, message=f"missing source map guidance: {expected}"))

    for skill in (
        ".agents/skills/project-development/SKILL.md",
        ".agents/skills/template-maintenance/SKILL.md",
    ):
        if not (root / skill).is_file():
            violations.append(Violation(path=root / skill, message="missing agent workflow skill"))

    for expected in REQUIRED_AGENT_GUIDANCE:
        if expected not in agents_text:
            violations.append(Violation(path=path, message=f"missing agent workflow guidance: {expected}"))
    return violations


def find_missing_readme_agent_guidance(root: Path) -> list[Violation]:
    """Return missing README first-screen guidance for agents that read README first."""
    path = root / "README.md"
    text = read_text(root, "README.md")
    violations: list[Violation] = []
    for expected in REQUIRED_README_AGENT_GUIDANCE:
        if expected not in text:
            violations.append(Violation(path=path, message=f"missing README agent entry guidance: {expected}"))
    return violations


def check_governance_baseline(root: Path = PROJECT_ROOT) -> list[Violation]:
    """Check repository governance invariants."""
    root = root.resolve()
    pyproject_text = read_text(root, "pyproject.toml")
    ci_text = read_text(root, ".github/workflows/ci.yml")
    agents_text = read_text(root, "AGENTS.md")
    pr_template_text = read_text(root, ".github/pull_request_template.md")

    violations: list[Violation] = []
    violations.extend(find_prohibited_adapters(root))
    violations.extend(find_missing_poe_tasks(root, pyproject_text))
    violations.extend(find_missing_ci_entries(root, ci_text))
    violations.extend(find_missing_evidence_entries(root, agents_text, "AGENTS.md"))
    violations.extend(find_missing_evidence_entries(root, pr_template_text, ".github/pull_request_template.md"))
    violations.extend(find_missing_agent_guidance(root, agents_text))
    violations.extend(find_missing_readme_agent_guidance(root))

    return violations


def main() -> int:
    """CLI entry point."""
    violations = check_governance_baseline()
    if violations:
        print("Governance baseline violations:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation.format(PROJECT_ROOT)}", file=sys.stderr)
        return 1

    print("Governance baseline passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
