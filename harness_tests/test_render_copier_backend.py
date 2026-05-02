"""Tests for Copier backend package rendering."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_copier_backend",
    ROOT / "scripts" / "render_copier_backend.py",
)
assert SPEC and SPEC.loader
render_copier_backend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_copier_backend)
render_backend = render_copier_backend.render_backend
validate_package_name = render_copier_backend.validate_package_name


def write(path: Path, content: str) -> None:
    """Write test file content after creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_render_backend_moves_package_and_updates_backend_references(tmp_path: Path) -> None:
    write(
        tmp_path / "src" / "app_name" / "main.py",
        'from app_name.config import Settings\ntitle="app_name"\n',
    )
    write(tmp_path / "src" / "app_name" / "config.py", '    app_name: str = "app_name"\n')
    write(tmp_path / "src" / "app_name" / "run_api.py", '"app_name.main:create_app"\n')
    write(
        tmp_path / "config.yaml",
        'server:\n  port: 8665\nfrontend:\n  base_url: "http://localhost:8006"\n',
    )
    write(tmp_path / "src" / "frontend" / "package.json", '{\n  "name": "frontend"\n}\n')
    write(
        tmp_path / "src" / "frontend" / "vite.config.ts",
        'env.APP_FRONTEND_PORT || "8006"; env.APP_BACKEND_URL || "http://127.0.0.1:8665";\n',
    )
    write(tmp_path / "src" / "frontend" / "src" / "api" / "index.ts", 'baseURL: "/api/v1"\n')
    write(
        tmp_path / "contracts" / "openapi.json",
        '{"info":{"title":"app_name"},"paths":{"/api/v1/health":{"get":{"operationId":"health_api_v1_health_get"}}}}\n',
    )
    write(
        tmp_path / "src" / "frontend" / "src" / "api" / "generated" / "openapi.ts",
        '"/api/v1/health": { get: operations["health_api_v1_health_get"] };\n',
    )
    write(
        tmp_path / "pyproject.toml",
        "\n".join(
            [
                'name = "app_name"',
                'packages = ["src/app_name"]',
                'api = "python -m app_name.run_api"',
                'lint = "ruff check src/app_name scripts tests harness_tests"',
                'test = "python -m pytest tests/ -v --cov=src/app_name --cov-report=term-missing"',
            ]
        ),
    )
    write(tmp_path / "tests" / "conftest.py", 'from app_name.config import Settings\napp_name="app_name_test"\n')

    render_backend(
        tmp_path,
        project_name="sample-project",
        package_name="sample_project",
        frontend_name="sample-frontend",
        backend_port=8765,
        frontend_port=8016,
        api_prefix="/api/smoke",
    )

    assert not (tmp_path / "src" / "app_name").exists()
    assert (tmp_path / "src" / "sample_project").is_dir()

    main_text = (tmp_path / "src" / "sample_project" / "main.py").read_text()
    assert "from sample_project.config import Settings" in main_text
    assert 'title="sample-project"' in main_text

    config_text = (tmp_path / "src" / "sample_project" / "config.py").read_text()
    assert 'app_name: str = "app_name"' in config_text
    assert "sample_project: str" not in config_text

    pyproject_text = (tmp_path / "pyproject.toml").read_text()
    assert 'name = "sample-project"' in pyproject_text
    assert 'packages = ["src/sample_project"]' in pyproject_text
    assert 'api = "python -m sample_project.run_api"' in pyproject_text
    assert "--cov=src/sample_project" in pyproject_text

    config_text = (tmp_path / "config.yaml").read_text()
    assert "port: 8765" in config_text
    assert "http://localhost:8016" in config_text

    assert '"name": "sample-frontend"' in (tmp_path / "src" / "frontend" / "package.json").read_text()
    vite_text = (tmp_path / "src" / "frontend" / "vite.config.ts").read_text()
    assert 'APP_FRONTEND_PORT || "8016"' in vite_text
    assert 'APP_BACKEND_URL || "http://127.0.0.1:8765"' in vite_text
    assert 'baseURL: "/api/smoke"' in (tmp_path / "src" / "frontend" / "src" / "api" / "index.ts").read_text()
    openapi_text = (tmp_path / "contracts" / "openapi.json").read_text()
    assert '"/api/smoke/health"' in openapi_text
    assert '"title":"sample-project"' in openapi_text
    assert (
        "health_api_smoke_health_get"
        in (tmp_path / "src" / "frontend" / "src" / "api" / "generated" / "openapi.ts").read_text()
    )

    conftest_text = (tmp_path / "tests" / "conftest.py").read_text()
    assert "from sample_project.config import Settings" in conftest_text
    assert 'app_name="sample_project_test"' in conftest_text


def test_validate_package_name_rejects_invalid_names() -> None:
    with pytest.raises(ValueError, match="Invalid package_name"):
        validate_package_name("Bad-Name")


def test_render_backend_rejects_invalid_ports(tmp_path: Path) -> None:
    write(tmp_path / "src" / "app_name" / "__init__.py", "")

    with pytest.raises(ValueError, match="backend_port and frontend_port must differ"):
        render_backend(
            tmp_path,
            project_name="sample-project",
            package_name="sample_project",
            frontend_name="sample-frontend",
            backend_port=8765,
            frontend_port=8765,
            api_prefix="/api/smoke",
        )
