"""Tests for the repository security baseline checker."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "harness" / "check_security_baseline.py"


def load_checker_module() -> ModuleType:
    """Load the checker script as a module without making scripts a package."""
    spec = importlib.util.spec_from_file_location("check_security_baseline", CHECKER_PATH)
    if spec is None or spec.loader is None:
        msg = f"Could not load {CHECKER_PATH}"
        raise RuntimeError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = load_checker_module()
check_security_baseline = checker.check_security_baseline


def git(root: Path, *args: str) -> None:
    """Run Git in a security scanner fixture repository."""
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def ensure_repo(root: Path) -> None:
    """Create a Git index for tracked-file scanner fixtures."""
    if not (root / ".git").exists():
        git(root, "init", "-b", "main")


def write_file(root: Path, relative: str, content: str) -> Path:
    """Write and track a file in a temporary repository."""
    ensure_repo(root)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    git(root, "add", "--force", relative)
    return path


def joined(*parts: str) -> str:
    """Build scanner fixture strings without committing complete secret patterns."""
    return "".join(parts)


def messages_for(root: Path) -> list[str]:
    """Run the checker and return formatted messages."""
    return [violation.format(root.resolve()) for violation in check_security_baseline(root)]


class TestSecurityBaseline:
    def test_requires_a_git_work_tree(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeError, match="requires a Git work tree"):
            check_security_baseline(tmp_path)

    def test_allows_placeholder_env_example(self, tmp_path: Path) -> None:
        write_file(
            tmp_path,
            ".env.example",
            "SERVICE_API_KEY=replace-with-provider-key\nSECRET_KEY=<generated-32+-char-key>\n",
        )

        assert messages_for(tmp_path) == []

    def test_blocks_tracked_env_files(self, tmp_path: Path) -> None:
        write_file(tmp_path, ".env.local", "DEBUG=true\n")

        messages = messages_for(tmp_path)

        assert len(messages) == 1
        assert ".env.local:1: tracked or unignored .env file is prohibited" in messages[0]

    def test_allows_ignored_untracked_env_files(self, tmp_path: Path) -> None:
        ensure_repo(tmp_path)
        write_file(tmp_path, ".gitignore", ".env\n")
        (tmp_path / ".env").write_text("SERVICE_API_KEY=local-development-value\n")

        assert messages_for(tmp_path) == []

    def test_blocks_private_key_material(self, tmp_path: Path) -> None:
        write_file(
            tmp_path,
            "fixtures/key.txt",
            joined("-----BEGIN OPENSSH ", "PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----\n"),
        )

        messages = messages_for(tmp_path)

        assert len(messages) == 1
        assert "private key material is prohibited" in messages[0]

    def test_scans_untracked_files_that_are_not_ignored(self, tmp_path: Path) -> None:
        ensure_repo(tmp_path)
        token = joined("sk-proj-", "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789")
        path = tmp_path / "new_source.py"
        path.write_text(f'API_KEY = "{token}"\n')

        assert any("live-looking token is prohibited" in message for message in messages_for(tmp_path))

    def test_blocks_known_live_token_patterns(self, tmp_path: Path) -> None:
        token = joined("sk-proj-", "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789")
        write_file(tmp_path, "config.txt", f"SERVICE_API_KEY={token}\n")

        messages = messages_for(tmp_path)

        assert len(messages) == 2
        assert any("live-looking token is prohibited" in message for message in messages)
        assert any("live-looking secret assignment is prohibited" in message for message in messages)

    def test_does_not_treat_test_substring_inside_token_as_a_placeholder(self, tmp_path: Path) -> None:
        token = joined("sk-proj-", "AbCdEftestGhIjKlMnOpQrStUvWxYz0123456789")
        write_file(tmp_path, "config.txt", f"SERVICE_API_KEY={token}\n")

        assert any("live-looking token is prohibited" in message for message in messages_for(tmp_path))

    def test_blocks_high_entropy_secret_assignments(self, tmp_path: Path) -> None:
        secret = joined("Zx9qLm2nP8v", "Rs4Tu7Wx0Yz3AbCdEfGh")
        write_file(tmp_path, "settings.ini", f"service_secret = {secret}\n")

        messages = messages_for(tmp_path)

        assert len(messages) == 1
        assert "live-looking secret assignment is prohibited (service_secret)" in messages[0]

    def test_ignores_vendor_and_generated_directories(self, tmp_path: Path) -> None:
        secret = joined("Zx9qLm2nP8v", "Rs4Tu7Wx0Yz3AbCdEfGh")
        write_file(tmp_path, "node_modules/pkg/index.js", f"const api_key = '{secret}'\n")
        write_file(tmp_path, ".venv/lib/site.py", "except:\n    pass\n")

        assert messages_for(tmp_path) == []
