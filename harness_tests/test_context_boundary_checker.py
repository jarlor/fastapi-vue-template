"""Tests for bounded-context import boundary checks."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "harness" / "check_context_boundaries.py"
TEST_PACKAGE = "app"


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

    def test_ignores_empty_untracked_context_directory(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        (contexts_root / "scratch").mkdir(parents=True)

        violations = check_test_contexts(contexts_root)

        assert violations == []

    def test_fails_context_with_only_package_markers(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        for relative in (
            "chat/__init__.py",
            "chat/domain/__init__.py",
            "chat/application/__init__.py",
            "chat/interface/api/__init__.py",
        ):
            write_context_file(contexts_root, relative, "")

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert "context 'chat' only contains empty package scaffolding" in violations[0].message

    def test_ignores_runtime_cache_directories(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(contexts_root, "__pycache__/__init__.py", "")

        violations = check_test_contexts(contexts_root)

        assert violations == []

    def test_allows_context_with_real_source_file(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(contexts_root, "chat/__init__.py", "")
        write_context_file(contexts_root, "chat/domain/models.py", "from dataclasses import dataclass\n")

        violations = check_test_contexts(contexts_root)

        assert violations == []

    def test_blocks_external_io_client_in_application_service(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(contexts_root, "chat/application/services/chat_service.py", "import httpx\n")

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert "I/O dependency 'httpx' must live under infrastructure" in violations[0].message

    def test_allows_external_io_client_in_infrastructure_gateway(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(contexts_root, "chat/infrastructure/gateways/provider_gateway.py", "import httpx\n")

        violations = check_test_contexts(contexts_root)

        assert violations == []

    def test_allows_database_client_in_infrastructure_repository(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(contexts_root, "chat/infrastructure/repositories/chat_repository.py", "import httpx\n")

        assert check_test_contexts(contexts_root) == []

    def test_allows_io_directly_under_infrastructure(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(contexts_root, "chat/infrastructure/email_sender.py", "import httpx\n")

        assert check_test_contexts(contexts_root) == []

    def test_blocks_external_provider_sdk_in_interface_layer(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(contexts_root, "chat/interface/api/router.py", "from anthropic import AsyncAnthropic\n")

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "I/O dependency 'anthropic'" in violations[0].message

    def test_blocks_transport_framework_in_domain(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(contexts_root, "orders/domain/model.py", "from fastapi import HTTPException\n")

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "transport framework 'fastapi' must live under interface" in violations[0].message

    def test_blocks_context_import_of_composition_root(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(contexts_root, "orders/interface/api/deps.py", "from app.container import AppContainer\n")

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "must not import composition-root module 'app.container'" in violations[0].message

    def test_blocks_context_import_of_outer_integration_adapter(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/services/create_order.py",
            "from app.integrations.orders_users import UserLookup\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "must not import composition-root module 'app.integrations'" in violations[0].message

    def test_blocks_standard_library_file_and_process_io_in_application(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/services/import_orders.py",
            "from pathlib import Path\nimport subprocess\nPath('orders.json').read_text()\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 2
        assert {"pathlib", "subprocess"} == {
            "pathlib" if "direct file or process I/O" in violation.message else violation.message.split("'")[1]
            for violation in violations
        }

    def test_blocks_direct_open_call_outside_infrastructure_implementation(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/domain/model.py",
            'payload = open("orders.json").read()\n',
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "direct file or process I/O" in violations[0].message

    def test_allows_pure_path_and_url_value_types(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/domain/model.py",
            "from http import HTTPStatus\nfrom pathlib import PurePath\nfrom urllib.parse import urlparse\n",
        )

        assert check_test_contexts(contexts_root) == []

    def test_allows_a_custom_open_callable(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/domain/model.py",
            "def open() -> str:\n    return 'state transition'\n\nresult = open()\n",
        )

        assert check_test_contexts(contexts_root) == []

    def test_allows_domain_methods_with_filesystem_like_names(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/domain/model.py",
            (
                "def normalize(title: str) -> str:\n"
                "    return title.replace('_', ' ')\n\n"
                "class Order:\n"
                "    def rename(self, name: str) -> None:\n"
                "        self.name = name\n\n"
                "Order().rename('next')\n"
            ),
        )

        assert check_test_contexts(contexts_root) == []

    def test_blocks_io_from_a_path_variable(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/services/load.py",
            "from pathlib import Path\npath = Path('orders.json')\npayload = path.read_text()\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert violations[0].line == 1

    def test_blocks_filesystem_query_from_path_constructor(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/services/discover.py",
            "from pathlib import Path\nentries = list(Path('.').iterdir())\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert violations[0].line == 1

    def test_blocks_path_type_annotation_outside_infrastructure(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/domain/model.py",
            ("from pathlib import Path\ndef load(path: Path) -> str:\n    return path.read_text()\n"),
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert violations[0].line == 1

    def test_blocks_qualified_path_reference_outside_infrastructure(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/ports/files.py",
            "import pathlib as paths\ndef load(path: paths.Path) -> str: ...\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert violations[0].line == 2

    def test_blocks_source_file_outside_a_named_layer(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/service.py",
            f"from {TEST_PACKAGE}.contexts.orders.infrastructure.repositories.order_repo import OrderRepository\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "context source must live under" in violations[0].message

    def test_blocks_code_hidden_in_unknown_layer_package_marker(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(contexts_root, "orders/helpers/__init__.py", "SIDE_EFFECT = True\n")

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "context source must live under" in violations[0].message

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

    def test_allows_explicit_top_level_integration_contract(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/services/create_order.py",
            f"from {TEST_PACKAGE}.contracts.order_events import OrderPlaced\n",
        )

        assert check_test_contexts(contexts_root) == []

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

    def test_fails_relative_package_alias_import(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/domain/entities.py",
            "from .. import application\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "layer 'domain' must not import layer 'application'" in violations[0].message

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

    def test_fails_relative_cross_context_package_alias_import(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/application/services/create_order.py",
            "from .... import users\n",
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

    def test_blocks_infrastructure_to_ports_lookalike_import(self, tmp_path: Path) -> None:
        contexts_root = tmp_path / "contexts"
        write_context_file(
            contexts_root,
            "orders/infrastructure/repositories/order_repo.py",
            f"from {TEST_PACKAGE}.contexts.orders.application.ports_evil import ConcreteService\n",
        )

        violations = check_test_contexts(contexts_root)

        assert len(violations) == 1
        assert "layer 'infrastructure' must not import layer 'application'" in violations[0].message

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
