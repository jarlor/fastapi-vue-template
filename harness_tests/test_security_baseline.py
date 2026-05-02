"""Tests for the repository security baseline checker."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

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


def write_file(root: Path, relative: str, content: str) -> Path:
    """Write a file in a temporary repository."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def joined(*parts: str) -> str:
    """Build scanner fixture strings without committing complete secret patterns."""
    return "".join(parts)


def messages_for(root: Path) -> list[str]:
    """Run the checker and return formatted messages."""
    return [violation.format(root.resolve()) for violation in check_security_baseline(root)]


class TestSecurityBaseline:
    def test_allows_placeholder_env_example(self, tmp_path: Path) -> None:
        write_file(
            tmp_path,
            ".env.example",
            "OPENAI_API_KEY=sk-...\nSECRET_KEY=<generated-32+-char-key>\n",
        )

        assert messages_for(tmp_path) == []

    def test_blocks_committed_env_files(self, tmp_path: Path) -> None:
        write_file(tmp_path, ".env.local", "DEBUG=true\n")

        messages = messages_for(tmp_path)

        assert len(messages) == 1
        assert ".env.local:1: committed .env file is prohibited" in messages[0]

    def test_blocks_private_key_material(self, tmp_path: Path) -> None:
        write_file(
            tmp_path,
            "fixtures/key.txt",
            joined("-----BEGIN OPENSSH ", "PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----\n"),
        )

        messages = messages_for(tmp_path)

        assert len(messages) == 1
        assert "private key material is prohibited" in messages[0]

    def test_blocks_known_live_token_patterns(self, tmp_path: Path) -> None:
        token = joined("sk-proj-", "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789")
        write_file(tmp_path, "config.txt", f"OPENAI_API_KEY={token}\n")

        messages = messages_for(tmp_path)

        assert len(messages) == 2
        assert any("live-looking token is prohibited" in message for message in messages)
        assert any("live-looking secret assignment is prohibited" in message for message in messages)

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

    def test_blocks_bare_except(self, tmp_path: Path) -> None:
        write_file(
            tmp_path,
            "src/app.py",
            "try:\n    risky()\nexcept:\n    handle()\n",
        )

        messages = messages_for(tmp_path)

        assert len(messages) == 1
        assert "src/app.py:3: bare except is prohibited" in messages[0]

    def test_blocks_exception_pass(self, tmp_path: Path) -> None:
        write_file(
            tmp_path,
            "src/app.py",
            "try:\n    risky()\nexcept Exception:\n    pass\n",
        )

        messages = messages_for(tmp_path)

        assert len(messages) == 1
        assert "except Exception: pass is prohibited" in messages[0]

    def test_allows_specific_logged_exception(self, tmp_path: Path) -> None:
        write_file(
            tmp_path,
            "src/app.py",
            "try:\n    risky()\nexcept ValueError:\n    logger.warning('bad input', exc_info=True)\n    raise\n",
        )

        assert messages_for(tmp_path) == []

    def test_blocks_verify_false(self, tmp_path: Path) -> None:
        write_file(tmp_path, "src/client.py", "client.get('https://example.com', verify=False)\n")

        messages = messages_for(tmp_path)

        assert len(messages) == 1
        assert "TLS verification must not be disabled" in messages[0]

    def test_blocks_hashlib_md5(self, tmp_path: Path) -> None:
        write_file(tmp_path, "src/hash.py", "import hashlib\nhashlib.md5(b'value')\n")

        messages = messages_for(tmp_path)

        assert len(messages) == 1
        assert "hashlib.md5 is prohibited" in messages[0]
