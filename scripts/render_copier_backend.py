#!/usr/bin/env python3
"""Render backend package names after Copier copies the dual-use template."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

TEMPLATE_PACKAGE = "app_name"
TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".vue",
    ".yaml",
    ".yml",
}
IGNORED_PARTS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "node_modules",
    "__pycache__",
}


def validate_package_name(package_name: str) -> None:
    """Validate the generated Python package name."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*", package_name):
        msg = f"Invalid package_name: {package_name!r}"
        raise ValueError(msg)


def should_process(path: Path, root: Path) -> bool:
    """Return whether a file is safe to process as project text."""
    relative = path.relative_to(root)
    if any(part in IGNORED_PARTS for part in relative.parts):
        return False
    if path.name in {".gitignore", ".pre-commit-config.yaml", ".python-version"}:
        return True
    return path.suffix in TEXT_SUFFIXES or ".env" in path.name


def render_text(text: str, *, package_name: str, project_name: str) -> str:
    """Render backend package references without renaming semantic app_name fields."""
    replacements = {
        f"src/{TEMPLATE_PACKAGE}": f"src/{package_name}",
        f"from {TEMPLATE_PACKAGE}": f"from {package_name}",
        f"import {TEMPLATE_PACKAGE}": f"import {package_name}",
        f"{TEMPLATE_PACKAGE}.": f"{package_name}.",
        f"{TEMPLATE_PACKAGE}.main:create_app": f"{package_name}.main:create_app",
        'name = "app_name"': f'name = "{project_name}"',
        'title="app_name"': f'title="{project_name}"',
        'logger.info("Starting app_name v{}"': f'logger.info("Starting {project_name} v{{}}"',
        'app_name: str = "app_name"': 'app_name: str = "app_name"',
        'app_name="app_name_test"': f'app_name="{package_name}_test"',
        'TEST_PACKAGE = "app_name"': f'TEST_PACKAGE = "{package_name}"',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def render_files(root: Path, *, package_name: str, project_name: str) -> list[Path]:
    """Render package references in text files and return changed paths."""
    changed: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not should_process(path, root):
            continue

        try:
            original = path.read_text()
        except UnicodeDecodeError:
            continue

        rendered = render_text(original, package_name=package_name, project_name=project_name)
        if rendered != original:
            path.write_text(rendered)
            changed.append(path.relative_to(root))
    return changed


def move_package(root: Path, *, package_name: str) -> None:
    """Move the backend package directory into its generated package name."""
    source = root / "src" / TEMPLATE_PACKAGE
    destination = root / "src" / package_name
    if package_name == TEMPLATE_PACKAGE:
        return
    if not source.exists():
        msg = f"Expected backend package directory does not exist: {source}"
        raise FileNotFoundError(msg)
    if destination.exists():
        msg = f"Generated backend package directory already exists: {destination}"
        raise FileExistsError(msg)
    shutil.move(str(source), str(destination))


def render_backend(root: Path, *, project_name: str, package_name: str) -> list[Path]:
    """Render backend package paths and imports in a copied project."""
    validate_package_name(package_name)
    changed = render_files(root, package_name=package_name, project_name=project_name)
    move_package(root, package_name=package_name)
    return changed


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--package-name", required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    try:
        changed = render_backend(
            args.root.resolve(),
            project_name=args.project_name,
            package_name=args.package_name,
        )
    except Exception as exc:
        print(f"backend rendering failed: {exc}", file=sys.stderr)
        return 1

    print(f"Rendered backend package '{args.package_name}' in {len(changed)} files.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
