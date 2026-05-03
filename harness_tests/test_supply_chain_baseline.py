"""Tests for the supply-chain baseline checker."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "harness" / "check_supply_chain_baseline.py"
PINNED_CHECKOUT = "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd"


def load_checker_module() -> ModuleType:
    """Load the checker script as a module without making scripts a package."""
    spec = importlib.util.spec_from_file_location("check_supply_chain_baseline", CHECKER_PATH)
    if spec is None or spec.loader is None:
        msg = f"Could not load {CHECKER_PATH}"
        raise RuntimeError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = load_checker_module()
check_supply_chain_baseline = checker.check_supply_chain_baseline


def write_file(root: Path, relative: str, content: str = "") -> Path:
    """Write a file in a temporary repository."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def seed_repo(root: Path) -> None:
    """Create a minimal compliant repository."""
    write_file(root, "uv.lock")
    write_file(
        root,
        "src/frontend/package.json",
        json.dumps({"name": "frontend", "packageManager": "npm@10.9.2"}),
    )
    write_file(root, "src/frontend/package-lock.json")
    write_file(
        root,
        ".github/workflows/ci.yml",
        f"""
name: CI
on: [push]
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: {PINNED_CHECKOUT}
      - run: uv sync --frozen --group dev
      - run: npm ci --no-audit --no-fund
""",
    )


def messages_for(root: Path) -> list[str]:
    """Run the checker and return formatted messages."""
    return [violation.format(root.resolve()) for violation in check_supply_chain_baseline(root)]


class TestSupplyChainBaseline:
    def test_accepts_seeded_repository(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)

        assert messages_for(tmp_path) == []

    def test_blocks_unpinned_actions(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.write_text(workflow.read_text().replace(PINNED_CHECKOUT, "actions/checkout@v6"))

        messages = messages_for(tmp_path)

        assert any("uses unpinned action: actions/checkout@v6" in message for message in messages)

    def test_requires_single_frontend_lockfile_policy(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        (tmp_path / "uv.lock").unlink()
        write_file(tmp_path, "src/frontend/yarn.lock")
        package_json = tmp_path / "src/frontend/package.json"
        package_json.write_text(json.dumps({"name": "frontend", "packageManager": "pnpm@10.0.0"}))

        messages = messages_for(tmp_path)

        assert any("uv.lock: required lockfile is missing" in message for message in messages)
        assert any("only one frontend package-manager lockfile is allowed" in message for message in messages)
        assert any("packageManager must match the committed frontend lockfile" in message for message in messages)

    def test_blocks_mutable_install_commands(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.write_text(workflow.read_text().replace("uv sync --frozen --group dev", "uv sync --group dev"))
        workflow.write_text(workflow.read_text().replace("npm ci --no-audit --no-fund", "npm install"))

        messages = messages_for(tmp_path)

        assert any("must use uv sync --frozen" in message for message in messages)
        assert any("must use npm ci, not npm install" in message for message in messages)

    def test_restricts_workflow_write_permissions(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.write_text(workflow.read_text().replace("contents: read", "contents: write"))

        messages = messages_for(tmp_path)

        assert any("top-level permissions must be contents: read" in message for message in messages)
