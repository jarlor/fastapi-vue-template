"""Tests for the repository governance baseline checker."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "harness" / "check_governance_baseline.py"


def load_checker_module() -> ModuleType:
    """Load the checker script as a module without making scripts a package."""
    spec = importlib.util.spec_from_file_location("check_governance_baseline", CHECKER_PATH)
    if spec is None or spec.loader is None:
        msg = f"Could not load {CHECKER_PATH}"
        raise RuntimeError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = load_checker_module()
check_governance_baseline = checker.check_governance_baseline


def write_file(root: Path, relative: str, content: str = "") -> Path:
    """Write a file in a temporary repository."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def seed_repo(root: Path) -> None:
    """Create the minimum files needed by the governance checker."""
    required_tasks = (
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
    poe_entries = "\n".join(f'{task} = "echo {task}"' for task in required_tasks)
    harness_entries = "\n".join(f'    {{ cmd = "uv run poe {task}" }},' for task in required_tasks)
    command_entries = "\n".join([*(f"uv run poe {task}" for task in required_tasks), "uv run poe template-smoke"])
    agents_entries = "\n".join(
        [
            command_entries,
            "00-START-HERE.md",
            "uv run poe agent-start",
            "git status --short --branch",
            "git switch -c feat/<short-task-name>",
            "create a focused feature branch before changing product code",
            "exclude `.git/`, `.venv/`, `node_modules/`, `.ruff_cache/`, `.pytest_cache/`, logs, "
            "and generated coverage files",
        ]
    )

    write_file(
        root,
        "pyproject.toml",
        f"""
[tool.poe.tasks]
{poe_entries}
template-smoke = "python scripts/template_smoke.py"
harness = [
{harness_entries}
]
""",
    )
    write_file(
        root,
        ".github/workflows/ci.yml",
        """
jobs:
  template-harness:
    steps:
      - run: uv run poe harness
  template-smoke:
    steps:
      - run: uv run poe template-smoke --full
""",
    )
    start_here_text = "Run `uv run poe agent-start`, then follow AGENTS.md. Exclude .venv/.\n"
    write_file(root, "AGENTS.md", agents_entries)
    write_file(root, "00-START-HERE.md", start_here_text)
    write_file(root, "00-START-HERE/README.md", start_here_text)
    write_file(root, ".github/pull_request_template.md", command_entries)
    write_file(
        root,
        ".agents/skills/template-maintenance/SKILL.md",
        "Skills provide reusable workflow. Poe tasks provide hard constraints.",
    )


def messages_for(root: Path) -> list[str]:
    """Run the checker and return formatted messages."""
    return [violation.format(root.resolve()) for violation in check_governance_baseline(root)]


class TestGovernanceBaseline:
    def test_accepts_seeded_repository(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)

        assert messages_for(tmp_path) == []

    def test_blocks_product_specific_agent_adapters(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        write_file(tmp_path, "CLAUDE.md", "# Claude-only instructions\n")

        messages = messages_for(tmp_path)

        assert len(messages) == 1
        assert "CLAUDE.md: product-specific agent adapter is prohibited" in messages[0]

    def test_requires_new_task_to_be_in_aggregate_harness(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(pyproject.read_text().replace('    { cmd = "uv run poe governance-harness" },\n', ""))

        messages = messages_for(tmp_path)

        assert len(messages) == 1
        assert "aggregate harness must run: uv run poe governance-harness" in messages[0]

    def test_requires_ci_to_use_public_poe_entrypoints(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        write_file(
            tmp_path,
            ".github/workflows/ci.yml",
            """
jobs:
  direct-script:
    steps:
      - run: python scripts/template_smoke.py --full
""",
        )

        messages = messages_for(tmp_path)

        assert any("CI must run public Poe entrypoint: uv run poe harness" in message for message in messages)
        assert any(
            "CI must run public Poe entrypoint: uv run poe template-smoke --full" in message for message in messages
        )

    def test_requires_pr_template_aggregate_evidence(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        write_file(tmp_path, ".github/pull_request_template.md", "uv run poe lint\n")

        messages = messages_for(tmp_path)

        assert any("missing required evidence command: uv run poe harness" in message for message in messages)
        assert any("missing required evidence command: uv run poe template-smoke" in message for message in messages)

    def test_requires_agent_branch_guidance(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        agents = tmp_path / "AGENTS.md"
        agents.write_text(agents.read_text().replace("git switch -c feat/<short-task-name>\n", ""))

        messages = messages_for(tmp_path)

        assert any(
            "missing agent workflow guidance: git switch -c feat/<short-task-name>" in message for message in messages
        )

    def test_requires_agent_startup_sentinel(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        (tmp_path / "00-START-HERE.md").unlink()

        messages = messages_for(tmp_path)

        assert any("00-START-HERE.md: missing agent startup sentinel" in message for message in messages)
