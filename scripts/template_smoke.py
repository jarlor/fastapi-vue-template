#!/usr/bin/env python3
"""Smoke-test the migration-period Copier template path."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SENTINELS = (
    "__PROJECT_NAME__",
    "__PACKAGE_NAME__",
    "__FRONTEND_NAME__",
    "__BACKEND_PORT__",
    "__FRONTEND_PORT__",
    "__API_PREFIX__",
)
SENTINEL_ALLOWLIST = {
    "docs/template-engine.md",
    "scripts/template_smoke.py",
}


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    """Run a subprocess and fail fast with useful context."""
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def scan_for_sentinels(project_root: Path) -> list[str]:
    """Return files that still contain template-only sentinel tokens."""
    matches: list[str] = []
    ignored_dirs = {
        ".git",
        ".venv",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "__pycache__",
    }

    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in ignored_dirs for part in path.parts):
            continue

        try:
            content = path.read_text()
        except UnicodeDecodeError:
            continue

        relative_path = str(path.relative_to(project_root))
        if relative_path in SENTINEL_ALLOWLIST:
            continue

        if any(sentinel in content for sentinel in SENTINELS):
            matches.append(relative_path)

    return matches


def build_env() -> dict[str, str]:
    """Build a subprocess environment with the current uv path first."""
    env = os.environ.copy()
    uv_path = shutil.which("uv")
    if uv_path:
        env["PATH"] = f"{Path(uv_path).parent}{os.pathsep}{env['PATH']}"
    return env


def run_smoke(*, keep: bool = False, full: bool = False) -> Path:
    """Generate a project and run its core checks.

    This is a compatibility smoke while Copier rendering is being introduced.
    The generated project still runs init.sh until package/module paths are
    fully rendered by Copier templates.
    """
    tmp = Path(tempfile.mkdtemp(prefix="fastapi-vue-template-"))
    generated = tmp / "sample-project"
    env = build_env()

    try:
        run(
            [
                "uv",
                "run",
                "copier",
                "copy",
                "--vcs-ref=HEAD",
                "--defaults",
                "--data",
                "project_name=sample-project",
                "--data",
                "package_name=sample_project",
                "--data",
                "frontend_name=sample-project",
                str(PROJECT_ROOT),
                str(generated),
            ],
            cwd=PROJECT_ROOT,
            env=env,
        )
        print("Running migration compatibility init bridge.", flush=True)
        run(["bash", "scripts/init.sh", "sample_project"], cwd=generated, env=env)

        answers_file = generated / ".copier-answers.yml"
        if not answers_file.exists():
            msg = "Copier answers file was not generated"
            raise RuntimeError(msg)

        sentinel_matches = scan_for_sentinels(generated)
        if sentinel_matches:
            msg = "Unresolved template sentinel tokens remain in: " + ", ".join(sentinel_matches)
            raise RuntimeError(msg)

        run(["uv", "run", "poe", "architecture"], cwd=generated, env=env)
        run(["uv", "run", "poe", "test"], cwd=generated, env=env)
        if full:
            run(["npm", "--prefix", "src/frontend", "run", "build"], cwd=generated, env=env)
            run(["npm", "--prefix", "src/frontend", "run", "test"], cwd=generated, env=env)

        print(f"Generated project compatibility smoke passed: {generated}", flush=True)
        return generated
    finally:
        if keep:
            print(f"Kept generated project at {generated}", flush=True)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true", help="Keep the generated project for inspection.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Also run generated frontend build/test. Slower; intended for CI report-only checks.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    try:
        run_smoke(keep=args.keep, full=args.full)
    except Exception as exc:
        print(f"template smoke failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
