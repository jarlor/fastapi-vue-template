#!/usr/bin/env python3
"""Enforce frontend boundary rules that are too project-specific for TypeScript alone."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = PROJECT_ROOT / "src" / "frontend" / "src"
API_ROOT = FRONTEND_SRC / "api"
IGNORED_DIRS = {"node_modules", "dist", ".vite", "coverage"}
HTTP_PATTERNS = (
    re.compile(r"""from\s+["']axios["']"""),
    re.compile(r"""import\s+axios\b"""),
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\bXMLHttpRequest\b"),
)
SCRIPT_TAG_RE = re.compile(r"<script\b([^>]*)>", re.IGNORECASE)
STYLE_TAG_RE = re.compile(r"<style\b([^>]*)>", re.IGNORECASE)
STATIC_INLINE_STYLE_RE = re.compile(r"\sstyle\s*=")
MAX_VUE_LINES = 300


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
        if any(pattern.search(line) for pattern in HTTP_PATTERNS):
            violations.append(
                Violation(
                    path=path,
                    line=line_number,
                    message="HTTP clients must be used through src/frontend/src/api",
                )
            )
    return violations


def check_vue_file(path: Path, lines: list[str]) -> list[Violation]:
    """Check Vue single-file component rules."""
    violations: list[Violation] = []
    if len(lines) > MAX_VUE_LINES:
        violations.append(
            Violation(
                path=path,
                line=MAX_VUE_LINES + 1,
                message=f"Vue components must stay at or below {MAX_VUE_LINES} lines",
            )
        )

    for line_number, line in enumerate(lines, start=1):
        script = SCRIPT_TAG_RE.search(line)
        if script and ("setup" not in script.group(1) or 'lang="ts"' not in script.group(1)):
            violations.append(
                Violation(
                    path=path,
                    line=line_number,
                    message='Vue components must use <script setup lang="ts">',
                )
            )

        style = STYLE_TAG_RE.search(line)
        if style and "scoped" not in style.group(1):
            violations.append(
                Violation(
                    path=path,
                    line=line_number,
                    message="Vue component styles must be scoped",
                )
            )

        if STATIC_INLINE_STYLE_RE.search(line):
            violations.append(
                Violation(
                    path=path,
                    line=line_number,
                    message="static inline styles are prohibited; use classes or dynamic :style",
                )
            )
    return violations


def check_file(path: Path) -> list[Violation]:
    """Check one frontend source file."""
    lines = path.read_text().splitlines()
    violations = check_http_boundary(path, lines)
    if path.suffix == ".vue":
        violations.extend(check_vue_file(path, lines))
    return violations


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
