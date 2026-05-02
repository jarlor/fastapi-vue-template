"""Tests for the one-time project initialization script."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLACEHOLDER_NAME = "app" "_name"
SOURCE_PACKAGE_DIR = next(
    path
    for path in (ROOT / "src").iterdir()
    if path.is_dir() and path.name != "frontend"
)


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_init_script_preserves_reserved_config_keys(tmp_path: Path) -> None:
    project_root = tmp_path / "sample-project"
    project_root.mkdir()
    (project_root / "scripts").mkdir()
    (project_root / "src" / SOURCE_PACKAGE_DIR.name).mkdir(parents=True)
    (project_root / "tests").mkdir()

    shutil.copy2(ROOT / "scripts" / "init.sh", project_root / "scripts" / "init.sh")
    shutil.copy2(
        SOURCE_PACKAGE_DIR / "config.py",
        project_root / "src" / SOURCE_PACKAGE_DIR.name / "config.py",
    )
    shutil.copy2(ROOT / "tests" / "conftest.py", project_root / "tests" / "conftest.py")
    shutil.copy2(ROOT / "pyproject.toml", project_root / "pyproject.toml")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_executable(fake_bin / "uv", "#!/bin/sh\nexit 0\n")
    _write_executable(fake_bin / "npm", "#!/bin/sh\nexit 0\n")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:/usr/bin:/bin"

    result = subprocess.run(
        ["bash", "scripts/init.sh", "my_project"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert (project_root / "src" / "my_project").is_dir()
    assert not (project_root / "src" / SOURCE_PACKAGE_DIR.name).exists()

    config_text = (project_root / "src" / "my_project" / "config.py").read_text()
    assert f'{PLACEHOLDER_NAME}: str = "my_project"' in config_text
    assert 'my_project: str = "my_project"' not in config_text

    conftest_text = (project_root / "tests" / "conftest.py").read_text()
    assert f'{PLACEHOLDER_NAME}="my_project_test"' in conftest_text
    assert 'my_project="my_project_test"' not in conftest_text

    pyproject_text = (project_root / "pyproject.toml").read_text()
    assert 'test = "python -m pytest tests/ -v --cov=src/my_project --cov-report=term-missing"' in pyproject_text
