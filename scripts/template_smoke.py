#!/usr/bin/env python3
"""Smoke-test the Copier template path by generating a temporary project."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMOKE_PROJECT_NAME = "sample-project"
SMOKE_PACKAGE_NAME = "sample_project"
SMOKE_FRONTEND_NAME = "sample-frontend"
SMOKE_BACKEND_PORT = 8765
SMOKE_FRONTEND_PORT = 8016
SMOKE_API_PREFIX = "/api/smoke"
SENTINELS = (
    "__PROJECT_NAME__",
    "__PACKAGE_NAME__",
    "__FRONTEND_NAME__",
    "__BACKEND_PORT__",
    "__FRONTEND_PORT__",
    "__API_PREFIX__",
    "{{package_name}}",
    "{{ package_name }}",
    "{{project_name}}",
    "{{ project_name }}",
    "{{frontend_name}}",
    "{{ frontend_name }}",
)
SENTINEL_ALLOWLIST = {
    "docs/template-engine.md",
    "scripts/template_smoke.py",
}
TEMPLATE_ONLY_FILES = {
    "harness_tests/test_render_copier_backend.py",
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
        if relative_path in TEMPLATE_ONLY_FILES:
            matches.append(relative_path)
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


def assert_contains(path: Path, expected: str) -> None:
    """Fail if a generated text file does not contain expected content."""
    content = path.read_text()
    if expected not in content:
        msg = f"{path} does not contain expected text: {expected}"
        raise RuntimeError(msg)


def assert_not_contains(path: Path, unexpected: str) -> None:
    """Fail if a generated text file contains stale template text."""
    content = path.read_text()
    if unexpected in content:
        msg = f"{path} contains unexpected text: {unexpected}"
        raise RuntimeError(msg)


def assert_generated_variables(generated: Path) -> None:
    """Assert that Copier variables affected concrete generated files."""
    assert_contains(generated / ".copier-answers.yml", f"project_name: {SMOKE_PROJECT_NAME}")
    assert_contains(generated / ".copier-answers.yml", f"package_name: {SMOKE_PACKAGE_NAME}")
    assert_contains(generated / ".copier-answers.yml", f"frontend_name: {SMOKE_FRONTEND_NAME}")
    assert_contains(generated / ".copier-answers.yml", f"backend_port: {SMOKE_BACKEND_PORT}")
    assert_contains(generated / ".copier-answers.yml", f"frontend_port: {SMOKE_FRONTEND_PORT}")
    assert_contains(generated / ".copier-answers.yml", f"api_prefix: {SMOKE_API_PREFIX}")

    assert_contains(generated / ".ignore", ".venv/")
    assert_contains(generated / ".ignore", "node_modules/")
    assert_contains(generated / ".ignore", ".git/")
    assert_contains(generated / "00-START-HERE.md", "uv run poe agent-start")
    assert_contains(generated / "00-START-HERE.md", "AGENTS.md")
    assert_contains(generated / "00-START-HERE.md", "PROJECT_MAP.md")
    assert_contains(generated / "00-START-HERE.md", ".venv/")
    assert_contains(generated / "00-START-HERE" / "README.md", "uv run poe agent-start")
    assert_contains(generated / "00-START-HERE" / "README.md", "AGENTS.md")
    assert_contains(generated / "00-START-HERE" / "README.md", "PROJECT_MAP.md")
    assert_contains(generated / "00-START-HERE" / "README.md", ".venv/")
    assert_contains(generated / "PROJECT_MAP.md", f"src/{SMOKE_PACKAGE_NAME}/")
    assert_contains(generated / "PROJECT_MAP.md", "src/frontend/")
    assert_contains(generated / "PROJECT_MAP.md", "harness_tests/")
    assert_contains(generated / "PROJECT_MAP.md", "scripts/harness/")
    assert_contains(generated / "PROJECT_MAP.md", "uv run poe agent-start")
    assert_contains(generated / "PROJECT_MAP.md", "uv run poe harness")
    assert_contains(generated / "PROJECT_MAP.md", ".venv/")
    assert_contains(generated / "PROJECT_MAP.md", "node_modules/")
    assert_contains(generated / "pyproject.toml", f'name = "{SMOKE_PROJECT_NAME}"')
    assert_contains(generated / "pyproject.toml", f"src/{SMOKE_PACKAGE_NAME}")
    assert_contains(generated / "README.md", f"# {SMOKE_PROJECT_NAME}")
    assert_contains(generated / "README.md", f"src/{SMOKE_PACKAGE_NAME}")
    assert_contains(generated / "README.md", f"├── {SMOKE_PACKAGE_NAME}/")
    assert_contains(generated / "AGENTS.md", f"src/{SMOKE_PACKAGE_NAME}")
    assert_contains(generated / "AGENTS.md", "PROJECT_MAP.md")
    assert_contains(generated / "AGENTS.md", "git init")
    assert_contains(generated / "AGENTS.md", "uv run poe agent-start")
    assert_contains(generated / "AGENTS.md", "git status --short --branch")
    assert_contains(generated / "AGENTS.md", 'git commit -m "chore: initialize from template"')
    assert_contains(generated / "AGENTS.md", "git switch -c feat/<short-task-name>")
    assert_contains(generated / "AGENTS.md", "Run `git init` only when `.git/` does not exist yet.")
    assert_contains(generated / "AGENTS.md", "create the template baseline commit before feature work")
    assert_contains(generated / "AGENTS.md", "create a focused feature branch before changing product code")
    assert_contains(generated / "AGENTS.md", "Do not continue implementation work on the baseline branch.")
    assert_contains(
        generated / "AGENTS.md",
        "exclude `.git/`, `.venv/`, `node_modules/`, `.ruff_cache/`, `.pytest_cache/`, logs, "
        "and generated coverage files",
    )
    assert_not_contains(generated / "AGENTS.md", "src/app_name")
    assert_contains(generated / "config.yaml", f"port: {SMOKE_BACKEND_PORT}")
    assert_contains(generated / "config.yaml", f"http://localhost:{SMOKE_FRONTEND_PORT}")
    assert_contains(generated / "src" / "frontend" / "package.json", f'"name": "{SMOKE_FRONTEND_NAME}"')
    assert_contains(generated / "contracts" / "openapi.json", f'"title": "{SMOKE_PROJECT_NAME}"')
    assert_contains(generated / "contracts" / "openapi.json", f'"{SMOKE_API_PREFIX}/health"')
    assert_contains(
        generated / "src" / "frontend" / "vite.config.ts",
        f'APP_FRONTEND_PORT || "{SMOKE_FRONTEND_PORT}"',
    )
    assert_contains(
        generated / "src" / "frontend" / "vite.config.ts",
        f'APP_BACKEND_URL || "http://127.0.0.1:{SMOKE_BACKEND_PORT}"',
    )
    assert_contains(generated / "src" / "frontend" / "src" / "api" / "index.ts", f'baseURL: "{SMOKE_API_PREFIX}"')
    assert_contains(generated / "src" / "frontend" / "src" / "api" / "generated" / "openapi.ts", SMOKE_API_PREFIX)


def run_smoke(*, keep: bool = False, full: bool = False) -> Path:
    """Generate a project and run its core checks.

    The generated project must pass backend checks through the Copier path.
    """
    tmp = Path(tempfile.mkdtemp(prefix="fastapi-vue-template-"))
    generated = tmp / SMOKE_PROJECT_NAME
    env = build_env()

    try:
        run(
            [
                "uv",
                "run",
                "copier",
                "copy",
                "--trust",
                "--vcs-ref=HEAD",
                "--defaults",
                "--data",
                f"project_name={SMOKE_PROJECT_NAME}",
                "--data",
                f"package_name={SMOKE_PACKAGE_NAME}",
                "--data",
                f"frontend_name={SMOKE_FRONTEND_NAME}",
                "--data",
                f"backend_port={SMOKE_BACKEND_PORT}",
                "--data",
                f"frontend_port={SMOKE_FRONTEND_PORT}",
                "--data",
                f"api_prefix={SMOKE_API_PREFIX}",
                str(PROJECT_ROOT),
                str(generated),
            ],
            cwd=PROJECT_ROOT,
            env=env,
        )

        answers_file = generated / ".copier-answers.yml"
        if not answers_file.exists():
            msg = "Copier answers file was not generated"
            raise RuntimeError(msg)

        generated_package = generated / "src" / SMOKE_PACKAGE_NAME
        if not generated_package.is_dir():
            msg = "Generated backend package directory was not rendered"
            raise RuntimeError(msg)
        if (generated / "src" / "app_name").exists():
            msg = "Template backend package directory survived generation"
            raise RuntimeError(msg)
        assert_generated_variables(generated)

        sentinel_matches = scan_for_sentinels(generated)
        if sentinel_matches:
            msg = "Unresolved template sentinel tokens remain in: " + ", ".join(sentinel_matches)
            raise RuntimeError(msg)

        run(["uv", "run", "poe", "architecture"], cwd=generated, env=env)
        run(["npm", "--prefix", "src/frontend", "ci", "--no-audit", "--no-fund"], cwd=generated, env=env)
        run(["uv", "run", "poe", "harness-test"], cwd=generated, env=env)
        run(["uv", "run", "poe", "governance-harness"], cwd=generated, env=env)
        run(["uv", "run", "poe", "supply-chain"], cwd=generated, env=env)
        run(["uv", "run", "poe", "api-contracts"], cwd=generated, env=env)
        run(["uv", "run", "poe", "frontend-harness"], cwd=generated, env=env)
        run(["uv", "run", "poe", "runtime-harness"], cwd=generated, env=env)
        run(["uv", "run", "poe", "test"], cwd=generated, env=env)
        if full:
            run(["npm", "--prefix", "src/frontend", "run", "build"], cwd=generated, env=env)
            run(["npm", "--prefix", "src/frontend", "run", "test"], cwd=generated, env=env)

        print(f"Generated project smoke passed: {generated}", flush=True)
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
        help="Also run generated frontend build/test. Slower; intended for the required CI template smoke gate.",
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
