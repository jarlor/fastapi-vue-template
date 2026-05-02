#!/usr/bin/env python3
"""Export and verify committed API contract artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from app_name.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = PROJECT_ROOT / "contracts" / "openapi.json"
FRONTEND_TYPES_PATH = PROJECT_ROOT / "src" / "frontend" / "src" / "api" / "generated" / "openapi.ts"
FRONTEND_ROOT = PROJECT_ROOT / "src" / "frontend"


def normalized_json(data: dict[str, Any]) -> str:
    """Return stable JSON text for committed contract artifacts."""
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def export_openapi() -> str:
    """Build the FastAPI app and export its OpenAPI schema."""
    app = create_app()
    return normalized_json(app.openapi())


def run_openapi_typescript(openapi_path: Path, output_path: Path) -> None:
    """Generate TypeScript declarations from OpenAPI using frontend tooling."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "npm",
        "--prefix",
        str(FRONTEND_ROOT),
        "exec",
        "openapi-typescript",
        "--",
        str(openapi_path),
        "-o",
        str(output_path),
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def generate_types(openapi_text: str) -> str:
    """Generate frontend TypeScript types for an OpenAPI schema."""
    with tempfile.TemporaryDirectory(prefix="api-contracts-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        tmp_openapi = tmp_root / "openapi.json"
        tmp_types = tmp_root / "openapi.ts"
        tmp_openapi.write_text(openapi_text)
        run_openapi_typescript(tmp_openapi, tmp_types)
        return tmp_types.read_text()


def write_artifacts(openapi_text: str, types_text: str) -> None:
    """Write committed API contract artifacts."""
    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_TYPES_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_PATH.write_text(openapi_text)
    FRONTEND_TYPES_PATH.write_text(types_text)


def read_artifact(path: Path) -> str | None:
    """Read a committed artifact if it exists."""
    if not path.exists():
        return None
    return path.read_text()


def check_artifacts(openapi_text: str, types_text: str) -> list[str]:
    """Return artifact drift messages."""
    failures: list[str] = []
    current_openapi = read_artifact(OPENAPI_PATH)
    current_types = read_artifact(FRONTEND_TYPES_PATH)

    if current_openapi != openapi_text:
        failures.append(f"{relative_to_project(OPENAPI_PATH)} is out of date")
    if current_types != types_text:
        failures.append(f"{relative_to_project(FRONTEND_TYPES_PATH)} is out of date")

    return failures


def relative_to_project(path: Path) -> Path:
    """Return a stable display path for repository artifacts."""
    try:
        return path.relative_to(PROJECT_ROOT)
    except ValueError:
        return path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Refresh committed contract artifacts.")
    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    try:
        openapi_text = export_openapi()
        types_text = generate_types(openapi_text)
    except subprocess.CalledProcessError as exc:
        print(f"api contract generation failed: {' '.join(exc.cmd)}", file=sys.stderr)
        return exc.returncode
    except Exception as exc:
        print(f"api contract generation failed: {exc}", file=sys.stderr)
        return 1

    if args.write:
        write_artifacts(openapi_text, types_text)
        print("API contract artifacts updated.", flush=True)
        return 0

    failures = check_artifacts(openapi_text, types_text)
    if not failures:
        return 0

    print("API contract artifacts are stale. Run `uv run poe api-contracts-write`.", file=sys.stderr)
    for failure in failures:
        print(f"- {failure}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
