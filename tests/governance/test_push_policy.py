"""Tests for the local Git push policy."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "governance" / "check_push_policy.py"


def load_policy_module() -> ModuleType:
    """Load the executable policy script without making scripts a package."""
    spec = importlib.util.spec_from_file_location("check_push_policy", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        msg = f"Could not load {SCRIPT_PATH}"
        raise RuntimeError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


policy = load_policy_module()
MAIN_REF = policy.MAIN_REF
check_push_policy = policy.check_push_policy


def test_allows_a_task_branch_push() -> None:
    assert check_push_policy({"PRE_COMMIT_REMOTE_BRANCH": "refs/heads/feat/example"}) is None


def test_allows_manual_invocation_without_push_context() -> None:
    assert check_push_policy({}) is None


def test_rejects_a_push_targeting_main() -> None:
    message = check_push_policy({"PRE_COMMIT_REMOTE_BRANCH": MAIN_REF})

    assert message is not None
    assert "pull request" in message
    assert "local soft guard" in message
