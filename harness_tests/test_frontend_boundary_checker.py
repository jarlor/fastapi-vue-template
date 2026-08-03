"""Tests for the TypeScript/Vue AST frontend boundary checker."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "harness" / "check_frontend_boundaries.mjs"


def write_frontend_file(root: Path, relative: str, content: str) -> Path:
    """Write a frontend checker fixture."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def run_checker(frontend_src: Path) -> subprocess.CompletedProcess[str]:
    """Run the Node checker against an isolated source tree."""
    return subprocess.run(
        ["node", str(CHECKER_PATH), "--frontend-src", str(frontend_src)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )


class TestFrontendBoundaryChecker:
    def test_allows_api_layer_to_own_http_client(self, tmp_path: Path) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        write_frontend_file(
            frontend_src,
            "api/index.ts",
            'import axios from "axios";\nfetch("/health");\nnew EventSource("/events");\n',
        )

        result = run_checker(frontend_src)

        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("suffix", ["js", "jsx", "ts", "tsx"])
    def test_scans_javascript_and_typescript_source_kinds(self, tmp_path: Path, suffix: str) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        write_frontend_file(frontend_src, f"pages/Tasks.{suffix}", 'const load = () => fetch("/tasks");\n')

        result = run_checker(frontend_src)

        assert result.returncode == 1
        assert "HTTP clients must be used through src/frontend/src/api" in result.stderr

    def test_blocks_vue_script_setup_clients_but_ignores_template_text(self, tmp_path: Path) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        write_frontend_file(
            frontend_src,
            "pages/Tasks.vue",
            """<template>
  <!-- Calling fetch() here would be wrong. -->
  <p>Never import from \"axios\" in a component.</p>
</template>
<script setup lang="ts">
new EventSource("/events");
</script>
""",
        )

        result = run_checker(frontend_src)

        assert result.returncode == 1
        assert result.stderr.count("HTTP clients must be used through src/frontend/src/api") == 1
        assert ":6:" in result.stderr

    def test_blocks_computed_global_fetch_alias(self, tmp_path: Path) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        write_frontend_file(
            frontend_src,
            "pages/Task.tsx",
            'const request = globalThis["fetch"];\nrequest("/tasks");\nexport const view = <div />;\n',
        )

        result = run_checker(frontend_src)

        assert result.returncode == 1
        assert ":1: HTTP clients must be used through" in result.stderr

    def test_checks_expressions_inside_template_literal_interpolation(self, tmp_path: Path) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        write_frontend_file(frontend_src, "stores/tasks.ts", 'const value = `result: ${fetch("/tasks")}`;\n')

        result = run_checker(frontend_src)

        assert result.returncode == 1
        assert "HTTP clients must be used through src/frontend/src/api" in result.stderr

    def test_ignores_comments_plain_strings_jsx_text_and_type_references(self, tmp_path: Path) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        write_frontend_file(
            frontend_src,
            "pages/Notes.tsx",
            """// fetch('/not-code') and new EventSource('/not-code')
const guidance = `Do not import from "axios" or set responseType: "stream" here`;
type BrowserStream = EventSource;
export const note = <p>fetch('/not-code')</p>;
""",
        )

        result = run_checker(frontend_src)

        assert result.returncode == 0, result.stderr

    def test_blocks_static_and_dynamic_axios_imports(self, tmp_path: Path) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        write_frontend_file(frontend_src, "stores/static.ts", 'import client from "axios";\nvoid client;\n')
        write_frontend_file(frontend_src, "stores/dynamic.ts", 'const client = import("axios");\nvoid client;\n')

        result = run_checker(frontend_src)

        assert result.returncode == 1
        assert result.stderr.count("HTTP clients must be used through src/frontend/src/api") == 2

    def test_blocks_axios_stream_response_type_in_api_layer(self, tmp_path: Path) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        write_frontend_file(
            frontend_src,
            "api/chat.ts",
            'api.post("/chat", body, { responseType: "stream" });\noptions["responseType"] = "stream";\n',
        )

        result = run_checker(frontend_src)

        assert result.returncode == 1
        assert result.stderr.count("Browser streaming must not use Axios responseType stream") == 2

    def test_blocks_xml_http_request_in_classic_vue_script(self, tmp_path: Path) -> None:
        frontend_src = tmp_path / "src" / "frontend" / "src"
        write_frontend_file(
            frontend_src,
            "pages/Legacy.vue",
            """<script lang="js">
export default { created() { new window["XMLHttpRequest"](); } };
</script>
""",
        )

        result = run_checker(frontend_src)

        assert result.returncode == 1
        assert "HTTP clients must be used through src/frontend/src/api" in result.stderr
