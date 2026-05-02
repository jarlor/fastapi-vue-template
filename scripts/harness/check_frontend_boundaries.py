#!/usr/bin/env python3
"""Enforce frontend boundary rules that are too project-specific for TypeScript alone."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = PROJECT_ROOT / "src" / "frontend" / "src"
API_ROOT = FRONTEND_SRC / "api"
IGNORED_DIRS = {"node_modules", "dist", ".vite", "coverage"}
HTTP_PATTERNS = (
    'from "axios"',
    "from 'axios'",
    "import axios",
    "fetch(",
    "XMLHttpRequest",
)


@dataclass(frozen=True)
class Violation:
    """A frontend harness violation."""

    path: Path
    line: int
    message: str

    def format(self, root: Path) -> str:
        return f"{self.path.relative_to(root)}:{self.line}: {self.message}"


def should_skip(path: Path) -> bool:
    """Return True for generated, vendored, or irrelevant frontend paths."""
    relative = path.relative_to(FRONTEND_SRC)
    return any(part in IGNORED_DIRS for part in relative.parts)


def is_under(path: Path, parent: Path) -> bool:
    """Return True when path is inside parent."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def iter_frontend_files(root: Path | None = None) -> list[Path]:
    """Return frontend source files checked by the harness."""
    if root is None:
        root = FRONTEND_SRC

    if not root.exists():
        return []

    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix in {".ts", ".vue"} and not should_skip(path)
    ]


def check_http_boundary(path: Path, lines: list[str]) -> list[Violation]:
    """Ensure HTTP clients are only imported/called from the API layer."""
    if is_under(path, API_ROOT):
        return []

    violations: list[Violation] = []
    for line_number, line in enumerate(lines, start=1):
        compact_line = line.replace(" ", "")
        if any(pattern in line or pattern.replace(" ", "") in compact_line for pattern in HTTP_PATTERNS):
            violations.append(
                Violation(
                    path=path,
                    line=line_number,
                    message="HTTP clients must be used through src/frontend/src/api",
                )
            )
    return violations


def check_file(path: Path) -> list[Violation]:
    """Check one frontend source file."""
    lines = path.read_text().splitlines()
    return check_http_boundary(path, lines)


def check_frontend_boundaries() -> list[Violation]:
    """Check all frontend source files."""
    violations: list[Violation] = []
    for path in iter_frontend_files():
        violations.extend(check_file(path))
    return violations


def main() -> int:
    """CLI entry point."""
    violations = check_frontend_boundaries()
    if not violations:
        return 0

    for violation in violations:
        print(violation.format(PROJECT_ROOT), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
