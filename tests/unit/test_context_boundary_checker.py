"""Tests for bounded-context import boundary checks."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
CHECKER_PATH = ROOT / "scripts" / "harness" / "check_context_boundaries.py"
TEST_PACKAGE = "app_name"


def load_checker_module() -> ModuleType:
    """Load the checker script as a module without making scripts a package."""
    spec = importlib.util.spec_from_file_location("check_context_boundaries", CHECKER_PATH)
    if spec is None or spec.loader is None:
        msg = f"Could not load {CHECKER_PATH}"
        raise RuntimeError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = load_checker_module()
check_context_boundaries = checker.check_context_boundaries


def check_test_contexts(contexts_root: Path):
    """Run the checker against the temporary test package."""
    return check_context_boundaries([(TEST_PACKAGE, contexts_root)])


def write_context_file(contexts_root: Path, relative: str, content: str) -> Path:
    """Write a test Python file under a temporary contexts root."""
    path = contexts_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class TestContextBoundaryChecker:
    def test_passes_when_no_contexts_exist(self, tmp_path: Path) -> None:
        violations = check_test_contexts(tmp_path / "contexts")

        assert violations == []

    def test_ignores_template_context(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "_template/domain/entities.py",
            f"from {TEST_PACKAGE}.contexts.other.application.services import OtherService\n",
        )

        violations = check_test_contexts(contexts_root)

        assert violations == []

    def test_allows_same_context_allowed_imports(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/services/create_order.py",
            f"from {TEST_PACKAGE}.contexts.orders.domain.entities import Order\n",
        )
        write_context_file(
            contexts_root,
            "orders/interface/api/router.py",
            f"from {TEST_PACKAGE}.contexts.orders.application.services.create_order import CreateOrder\n",
        )

        violations = check_test_contexts(contexts_root)

        assert violations == []

    def test_fails_cross_context_import(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/services/create_order.py",
            f"from {TEST_PACKAGE}.contexts.users.domain.entities import User\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert "must not import context 'users'" in violations[0].message

    def test_fails_domain_to_application_import(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/domain/entities.py",
            f"from {TEST_PACKAGE}.contexts.orders.application.services.create_order import CreateOrder\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "layer 'domain' must not import layer 'application'" in violations[0].message

    def test_fails_application_to_infrastructure_import(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/services/create_order.py",
            f"from {TEST_PACKAGE}.contexts.orders.infrastructure.repositories.order_repo import OrderRepository\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "layer 'application' must not import layer 'infrastructure'" in violations[0].message

    def test_fails_context_package_alias_import(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/services/create_order.py",
            f"from {TEST_PACKAGE}.contexts import users\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "must not import context 'users'" in violations[0].message

    def test_fails_same_context_layer_package_alias_import(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/domain/entities.py",
            f"from {TEST_PACKAGE}.contexts.orders import application\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "layer 'domain' must not import layer 'application'" in violations[0].message

    def test_fails_relative_domain_to_application_import(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/domain/entities.py",
            "from ..application.services.create_order import CreateOrder\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert f"{TEST_PACKAGE}.contexts.orders.application.services.create_order" in violations[0].message

    def test_fails_relative_cross_context_import(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/services/create_order.py",
            "from ....users.domain.entities import User\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "must not import context 'users'" in violations[0].message

    def test_allows_infrastructure_to_application_ports_import(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/infrastructure/repositories/order_repo.py",
            f"from {TEST_PACKAGE}.contexts.orders.application.ports.repositories import OrderRepositoryPort\n",
        )

        violations = check_test_contexts(contexts_root)

        assert violations == []

    def test_reports_multiple_violations_with_paths_and_lines(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        path = write_context_file(
            contexts_root,
            "orders/domain/entities.py",
            "\n"
            f"from {TEST_PACKAGE}.contexts.orders.application.services.create_order import CreateOrder\n"
            f"import {TEST_PACKAGE}.contexts.users.domain.entities\n",
        )

        violations = check_test_contexts(contexts_root)
        formatted = [violation.format(tmp_path) for violation in violations]

        assert len(violations) == 2
        assert formatted[0].startswith(f"{path.relative_to(tmp_path)}:2:")
        assert formatted[1].startswith(f"{path.relative_to(tmp_path)}:3:")
