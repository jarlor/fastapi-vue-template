#!/usr/bin/env python3
"""Block high-confidence secret leaks in tracked and unignored files.

Python security patterns are owned by Ruff's standard ``S`` rules so this
scanner can remain small and focused on repository-wide text artifacts.
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "htmlcov",
    "node_modules",
}
IGNORED_FILE_NAMES = {
    ".coverage",
    "package-lock.json",
    "uv.lock",
}
ALLOWED_ENV_FILES = {".env.example"}
BLOCKED_ENV_FILE_RE = re.compile(r"^\.env(?:$|[._-].*)")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")
SECRET_ASSIGNMENT_RE = re.compile(
    r"""
    (?P<key>
        [a-z0-9_.-]*
        (?:api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|private[_-]?key|credential)
        [a-z0-9_.-]*
    )
    \s*(?:=|:)\s*
    (?P<quote>["']?)
    (?P<value>[^"'\s#]+)
    (?P=quote)
    """,
    re.IGNORECASE | re.VERBOSE,
)
KNOWN_TOKEN_RES = [
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bASIA[0-9A-Z]{16}\b"),
    re.compile(r"\bghp_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    re.compile(r"\bsk-(?:live|proj)-[A-Za-z0-9_-]{20,}\b"),
]
PLACEHOLDER_VALUES = {
    "...",
    "change-me",
    "changeme",
    "dummy",
    "example",
    "fake",
    "generated",
    "placeholder",
    "sample",
    "todo",
    "xxxx",
}
PLACEHOLDER_PREFIXES = ("<", "${", "dummy-", "example-", "fake-", "local-", "sample-", "test-", "your_")


@dataclass(frozen=True)
class Violation:
    """A security baseline violation."""

    path: Path
    line: int
    message: str

    def format(self, root: Path) -> str:
        rel_path = self.path.relative_to(root)
        return f"{rel_path}:{self.line}: {self.message}"


def should_skip_path(path: Path, root: Path) -> bool:
    """Return True for generated, vendored, cache, or binary-ish paths."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True

    if any(part in IGNORED_DIRS for part in relative.parts):
        return True

    return path.name in IGNORED_FILE_NAMES


def iter_files(root: Path) -> list[Path]:
    """Return tracked and unignored candidate files that should be scanned."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        msg = "security scan requires a Git work tree so ignore rules and candidate files are authoritative"
        raise RuntimeError(msg)

    paths: list[Path] = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = root / os.fsdecode(raw_path)
        if path.is_file() and not path.is_symlink() and not should_skip_path(path, root):
            paths.append(path)
    return sorted(paths)


def read_text(path: Path) -> str | None:
    """Read a text file, returning None for binary or undecodable files."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None

    if b"\x00" in raw:
        return None

    try:
        return raw.decode()
    except UnicodeDecodeError:
        return None


def is_blocked_env_file(path: Path) -> bool:
    """Return True when a candidate path is a prohibited environment file."""
    name = path.name
    return name not in ALLOWED_ENV_FILES and BLOCKED_ENV_FILE_RE.match(name) is not None


def shannon_entropy(value: str) -> float:
    """Calculate a small entropy signal for generic secret-looking values."""
    if not value:
        return 0.0

    counts = {char: value.count(char) for char in set(value)}
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def looks_like_placeholder(value: str) -> bool:
    """Return True for documented placeholders and intentionally fake values."""
    lowered = value.lower().strip()
    return lowered in PLACEHOLDER_VALUES or lowered.endswith(">") or lowered.startswith(PLACEHOLDER_PREFIXES)


def looks_like_live_secret(value: str) -> bool:
    """Return True for high-confidence live secret values."""
    stripped = value.strip().strip(",;")
    if not stripped or looks_like_placeholder(stripped):
        return False

    if any(pattern.search(stripped) for pattern in KNOWN_TOKEN_RES):
        return True

    if len(stripped) < 24:
        return False

    has_alpha = any(char.isalpha() for char in stripped)
    has_digit = any(char.isdigit() for char in stripped)
    has_secret_charset = re.fullmatch(r"[A-Za-z0-9_./+=:-]+", stripped) is not None
    return has_alpha and has_digit and has_secret_charset and shannon_entropy(stripped) >= 3.5


def find_text_violations(path: Path, text: str) -> list[Violation]:
    """Scan a text file for high-confidence secret material."""
    violations: list[Violation] = []
    if is_blocked_env_file(path):
        violations.append(Violation(path=path, line=1, message="tracked or unignored .env file is prohibited"))

    for line_number, line in enumerate(text.splitlines(), start=1):
        if PRIVATE_KEY_RE.search(line):
            violations.append(Violation(path=path, line=line_number, message="private key material is prohibited"))

        for pattern in KNOWN_TOKEN_RES:
            match = pattern.search(line)
            if match and not looks_like_placeholder(match.group(0)):
                violations.append(Violation(path=path, line=line_number, message="live-looking token is prohibited"))
                break

        assignment = SECRET_ASSIGNMENT_RE.search(line)
        if assignment and looks_like_live_secret(assignment.group("value")):
            violations.append(
                Violation(
                    path=path,
                    line=line_number,
                    message=f"live-looking secret assignment is prohibited ({assignment.group('key')})",
                )
            )

    return violations


def check_security_baseline(root: Path = PROJECT_ROOT) -> list[Violation]:
    """Check the repository for security baseline violations."""
    root = root.resolve()
    violations: list[Violation] = []
    for path in iter_files(root):
        text = read_text(path)
        if text is None:
            continue

        violations.extend(find_text_violations(path, text))

    return violations


def main() -> int:
    """CLI entry point."""
    try:
        violations = check_security_baseline()
    except RuntimeError as exc:
        print(f"security baseline failed: {exc}", file=sys.stderr)
        return 1
    if not violations:
        return 0

    for violation in violations:
        print(violation.format(PROJECT_ROOT), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
