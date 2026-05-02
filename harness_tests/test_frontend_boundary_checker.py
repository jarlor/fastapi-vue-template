"""Tests for frontend boundary harness checks."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "harness" / "check_frontend_boundaries.py"


def load_checker_module() -> ModuleType:
    """Load the checker script as a module without making scripts a package."""
    spec = importlib.util.spec_from_file_location("check_frontend_boundaries", CHECKER_PATH)
    if spec is None or spec.loader is None:
        msg = f"Could not load {CHECKER_PATH}"
        raise RuntimeError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = load_checker_module()


def write_frontend_file(root: Path, relative: str, content: str) -> Path:
    """Write a frontend test fixture."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class TestFrontendBoundaryChecker:
    def test_allows_api_layer_to_own_http_client(self, tmp_path: Path, monkeypatch) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        monkeypatch.setattr(checker, "FRONTEND_SRC", frontend_src)
        monkeypatch.setattr(checker, "API_ROOT", frontend_src / "api")
        write_frontend_file(frontend_src, "api/index.ts", 'import axios from "axios";\nfetch("/health");\n')

        assert checker.check_frontend_boundaries() == []

    def test_blocks_http_client_outside_api_layer(self, tmp_path: Path, monkeypatch) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        monkeypatch.setattr(checker, "FRONTEND_SRC", frontend_src)
        monkeypatch.setattr(checker, "API_ROOT", frontend_src / "api")
        write_frontend_file(
            frontend_src,
            "pages/Dashboard.vue",
            '<script setup lang="ts">\nfetch("/health");\n</script>\n',
        )

        violations = checker.check_frontend_boundaries()

        assert len(violations) == 1
        assert "HTTP clients must be used through src/frontend/src/api" in violations[0].message

    def test_allows_vue_component_style_choices(self, tmp_path: Path, monkeypatch) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        monkeypatch.setattr(checker, "FRONTEND_SRC", frontend_src)
        monkeypatch.setattr(checker, "API_ROOT", frontend_src / "api")
        write_frontend_file(
            frontend_src,
            "components/Legacy.vue",
            (
                '<script lang="ts">\n</script>\n<template>\n'
                '  <div style="margin-top: 16px" />\n</template>\n'
                "<style>\n.x { color: red; }\n</style>\n"
            ),
        )

        assert checker.check_frontend_boundaries() == []
