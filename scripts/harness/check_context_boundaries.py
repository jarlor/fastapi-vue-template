#!/usr/bin/env python3
"""Enforce bounded-context import boundaries.

The checker parses Python imports with ``ast`` and reports violations as:

    path:line: message
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

IGNORED_CONTEXT_DIRS = {"__pycache__"}
LAYER_NAMES = {"domain", "application", "infrastructure", "interface"}
LAYER_IMPORT_RULES = {
    "domain": {"domain"},
    "application": {"domain", "application"},
    "infrastructure": {"domain", "infrastructure"},
    "interface": {"domain", "application", "interface"},
}
EXTERNAL_IO_MODULES = {
    "aiohttp",
    "aiokafka",
    "anthropic",
    "asyncpg",
    "boto3",
    "httpx",
    "motor",
    "openai",
    "psycopg",
    "pymongo",
    "redis",
    "requests",
    "sqlalchemy",
    "stripe",
}
STANDARD_LIBRARY_IO_MODULES = {
    "ftplib",
    "shutil",
    "smtplib",
    "socket",
    "sqlite3",
    "subprocess",
    "tempfile",
}
STANDARD_LIBRARY_IO_PREFIXES = {"http.client", "http.server", "pathlib.Path", "urllib.request"}
OS_IO_METHODS = {
    "chmod",
    "chown",
    "execv",
    "execve",
    "fork",
    "kill",
    "listdir",
    "makedirs",
    "mkdir",
    "open",
    "popen",
    "read",
    "remove",
    "removedirs",
    "rename",
    "replace",
    "rmdir",
    "scandir",
    "stat",
    "system",
    "unlink",
    "walk",
    "write",
}
TRANSPORT_FRAMEWORK_MODULES = {
    "django",
    "fastapi",
    "flask",
    "litestar",
    "starlette",
}
COMPOSITION_ROOT_MODULES = {"app.bootstrap", "app.container", "app.integrations", "app.main"}


@dataclass(frozen=True)
class ImportReference:
    """A parsed import reference with its source line number."""

    module: str
    line: int
    level: int = 0


@dataclass(frozen=True)
class Violation:
    """An architecture boundary violation."""

    path: Path
    line: int
    message: str

    def format(self, root: Path) -> str:
        rel_path = self.path.relative_to(root)
        return f"{rel_path}:{self.line}: {self.message}"


@dataclass(frozen=True)
class ContextFile:
    """A Python file inside a real bounded context."""

    path: Path
    package_name: str
    contexts_root: Path
    context: str
    layer: str | None


def discover_context_roots(project_root: Path = PROJECT_ROOT) -> list[tuple[str, Path]]:
    """Discover Python packages that contain a contexts directory."""
    src_root = project_root / "src"
    if not src_root.exists():
        return []

    roots: list[tuple[str, Path]] = []
    for package_path in sorted(src_root.iterdir()):
        contexts_root = package_path / "contexts"
        if package_path.is_dir() and contexts_root.is_dir():
            roots.append((package_path.name, contexts_root))
    return roots


def iter_context_files(package_name: str, contexts_root: Path) -> list[ContextFile]:
    """Return Python files under real bounded contexts."""
    if not contexts_root.exists():
        return []

    files: list[ContextFile] = []
    for path in sorted(contexts_root.rglob("*.py")):
        relative = path.relative_to(contexts_root)
        if len(relative.parts) < 2:
            continue

        context = relative.parts[0]
        layer = relative.parts[1] if relative.parts[1] in LAYER_NAMES else None
        files.append(
            ContextFile(
                path=path,
                package_name=package_name,
                contexts_root=contexts_root,
                context=context,
                layer=layer,
            )
        )

    return files


def imported_modules(path: Path) -> list[ImportReference]:
    """Parse import statements from a Python file."""
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: list[ImportReference] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(ImportReference(alias.name, node.lineno) for alias in node.names)
            continue

        if isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(ImportReference(node.module, node.lineno, node.level))
            imports.extend(
                ImportReference(
                    f"{node.module}.{alias.name}" if node.module else alias.name,
                    node.lineno,
                    node.level,
                )
                for alias in node.names
            )

    return imports


def module_for_file(context_file: ContextFile) -> str:
    """Return the module path for a context file."""
    relative = context_file.path.relative_to(context_file.contexts_root)
    parts = [*relative.parts[:-1], relative.stem]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join((context_file.package_name, "contexts", *parts))


def resolve_relative_import(context_file: ContextFile, import_ref: ImportReference) -> str:
    """Resolve a relative import to an absolute module path."""
    if import_ref.level == 0:
        return import_ref.module

    current_module = module_for_file(context_file)
    package_parts = current_module.split(".")
    if context_file.path.name != "__init__.py":
        package_parts = package_parts[:-1]
    if import_ref.level > len(package_parts):
        return import_ref.module

    base_parts = package_parts[: len(package_parts) - import_ref.level + 1]
    return ".".join((*base_parts, import_ref.module))


def imported_context(package_name: str, module: str) -> tuple[str, str | None, str] | None:
    """Return imported context metadata for package contexts imports."""
    context_prefix = f"{package_name}.contexts."
    if not module.startswith(context_prefix):
        return None

    remainder = module.removeprefix(context_prefix)
    parts = remainder.split(".")
    if not parts or not parts[0]:
        return None

    context = parts[0]
    layer = parts[1] if len(parts) > 1 and parts[1] in LAYER_NAMES else None
    context_remainder = ".".join(parts[1:])
    return context, layer, context_remainder


def check_file(context_file: ContextFile) -> list[Violation]:
    """Check one context file for boundary violations."""
    violations: list[Violation] = []
    seen: set[tuple[int, str]] = set()

    def add_violation(line: int, message: str) -> None:
        key = (line, message.split(" (", maxsplit=1)[0])
        if key in seen:
            return

        seen.add(key)
        violations.append(Violation(path=context_file.path, line=line, message=message))

    if context_file.layer is None:
        relative = context_file.path.relative_to(context_file.contexts_root / context_file.context)
        is_empty_context_marker = relative.parts == ("__init__.py",) and is_empty_package_marker(context_file.path)
        if not is_empty_context_marker:
            add_violation(
                1,
                "context source must live under domain, application, infrastructure, or interface",
            )

    for import_ref in imported_modules(context_file.path):
        module = resolve_relative_import(context_file, import_ref)
        if imports_io_dependency(module) and not context_file_allows_external_io(context_file):
            add_violation(
                import_ref.line,
                (f"I/O dependency '{module.split('.', maxsplit=1)[0]}' must live under infrastructure"),
            )
            continue

        if imports_transport_framework(module) and context_file.layer != "interface":
            add_violation(
                import_ref.line,
                f"transport framework '{module.split('.', maxsplit=1)[0]}' must live under interface",
            )
            continue

        composition_root = next(
            (root for root in COMPOSITION_ROOT_MODULES if module == root or module.startswith(f"{root}.")),
            None,
        )
        if composition_root is not None:
            add_violation(
                import_ref.line,
                f"context code must not import composition-root module '{composition_root}'",
            )
            continue

        imported = imported_context(context_file.package_name, module)
        if imported is None:
            continue

        imported_ctx, imported_layer, imported_remainder = imported
        if imported_ctx != context_file.context:
            add_violation(
                import_ref.line,
                (f"context '{context_file.context}' must not import context '{imported_ctx}' ({module})"),
            )
            continue

        if context_file.layer is None or imported_layer is None:
            continue

        if context_file.layer == "infrastructure" and (
            imported_remainder == "application.ports" or imported_remainder.startswith("application.ports.")
        ):
            continue

        allowed_layers = LAYER_IMPORT_RULES[context_file.layer]
        if imported_layer in allowed_layers:
            continue

        add_violation(
            import_ref.line,
            (f"layer '{context_file.layer}' must not import layer '{imported_layer}' ({module})"),
        )

    if not context_file_allows_external_io(context_file):
        for line in explicit_stdlib_io_calls(context_file.path):
            add_violation(line, "direct file or process I/O must live behind an infrastructure port implementation")

    return violations


def is_empty_package_marker(path: Path) -> bool:
    """Return whether a context marker contains only an optional docstring."""
    tree = ast.parse(path.read_text(), filename=str(path))
    return not tree.body or (
        len(tree.body) == 1
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    )


def imports_io_dependency(module: str) -> bool:
    """Return whether an import references a known external or standard-library I/O API."""
    head = module.split(".", maxsplit=1)[0]
    return head in EXTERNAL_IO_MODULES | STANDARD_LIBRARY_IO_MODULES or any(
        module == prefix or module.startswith(f"{prefix}.") for prefix in STANDARD_LIBRARY_IO_PREFIXES
    )


def imports_transport_framework(module: str) -> bool:
    """Return whether an import references a transport framework owned by interface code."""
    head = module.split(".", maxsplit=1)[0]
    return head in TRANSPORT_FRAMEWORK_MODULES


def explicit_stdlib_io_calls(path: Path) -> list[int]:
    """Return high-confidence built-in, os, and qualified pathlib I/O references."""
    tree = ast.parse(path.read_text(), filename=str(path))
    imported_names: dict[str, str] = {}
    pathlib_modules: set[str] = set()
    bound_open = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
                imported_names[local_name] = alias.name
                if alias.name == "pathlib":
                    pathlib_modules.add(local_name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local_name = alias.asname or alias.name
                imported_names[local_name] = f"{node.module}.{alias.name}"
        elif (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == "open") or (
            isinstance(node, ast.arg) and node.arg == "open"
        ):
            bound_open = True
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "open" for target in targets):
                bound_open = True

    lines: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "Path"
            and isinstance(node.value, ast.Name)
            and node.value.id in pathlib_modules
        ):
            lines.add(node.lineno)
            continue
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            qualified = imported_names.get(node.func.id, "")
            if (node.func.id == "open" and not bound_open) or (
                qualified.startswith("os.") and qualified.removeprefix("os.") in OS_IO_METHODS
            ):
                lines.add(node.lineno)
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if isinstance(node.func.value, ast.Name):
            module = imported_names.get(node.func.value.id)
            if module == "os" and node.func.attr in OS_IO_METHODS:
                lines.add(node.lineno)
    return sorted(lines)


def context_file_allows_external_io(context_file: ContextFile) -> bool:
    """Return whether a context file is in an external I/O implementation layer."""
    return context_file.layer == "infrastructure"


def check_context_boundaries(
    context_roots: list[tuple[str, Path]] | None = None,
) -> list[Violation]:
    """Check all bounded-context Python files."""
    if context_roots is None:
        context_roots = discover_context_roots()

    violations: list[Violation] = []
    for package_name, contexts_root in context_roots:
        violations.extend(check_context_scaffolds(contexts_root))
        for context_file in iter_context_files(package_name, contexts_root):
            violations.extend(check_file(context_file))
    return violations


def check_context_scaffolds(contexts_root: Path) -> list[Violation]:
    """Return violations for real contexts that only contain package markers."""
    if not contexts_root.exists():
        return []

    violations: list[Violation] = []
    for context_path in sorted(contexts_root.iterdir()):
        if not context_path.is_dir() or context_path.name in IGNORED_CONTEXT_DIRS:
            continue

        python_files = [path for path in context_path.rglob("*.py") if path.is_file()]
        if not python_files:
            continue
        has_source_file = any(path.name != "__init__.py" or not is_empty_package_marker(path) for path in python_files)
        if has_source_file:
            continue

        violations.append(
            Violation(
                path=context_path / "__init__.py",
                line=1,
                message=(
                    f"context '{context_path.name}' only contains empty package scaffolding; "
                    "add real domain, application, interface, or infrastructure source before committing it"
                ),
            )
        )
    return violations


def main() -> int:
    """CLI entry point."""
    violations = check_context_boundaries()
    if not violations:
        return 0

    for violation in violations:
        print(violation.format(PROJECT_ROOT), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
