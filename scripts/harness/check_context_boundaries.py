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

IGNORED_CONTEXTS = {"_template"}
LAYER_NAMES = {"domain", "application", "infrastructure", "interface"}
LAYER_IMPORT_RULES = {
    "domain": {"domain"},
    "application": {"domain", "application"},
    "infrastructure": {"domain", "infrastructure"},
    "interface": {"domain", "application", "interface"},
}


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
        if context in IGNORED_CONTEXTS:
            continue

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

        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(ImportReference(node.module, node.lineno, node.level))
            imports.extend(
                ImportReference(f"{node.module}.{alias.name}", node.lineno, node.level) for alias in node.names
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
    package_parts = current_module.split(".")[:-1]
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

    for import_ref in imported_modules(context_file.path):
        module = resolve_relative_import(context_file, import_ref)
        imported = imported_context(context_file.package_name, module)
        if imported is None:
            continue

        imported_ctx, imported_layer, imported_remainder = imported
        if imported_ctx in IGNORED_CONTEXTS:
            continue

        if imported_ctx != context_file.context:
            add_violation(
                import_ref.line,
                (f"context '{context_file.context}' must not import context '{imported_ctx}' ({module})"),
            )
            continue

        if context_file.layer is None or imported_layer is None:
            continue

        if context_file.layer == "infrastructure" and imported_remainder.startswith("application.ports"):
            continue

        allowed_layers = LAYER_IMPORT_RULES[context_file.layer]
        if imported_layer in allowed_layers:
            continue

        add_violation(
            import_ref.line,
            (f"layer '{context_file.layer}' must not import layer '{imported_layer}' ({module})"),
        )

    return violations


def check_context_boundaries(
    context_roots: list[tuple[str, Path]] | None = None,
) -> list[Violation]:
    """Check all bounded-context Python files."""
    if context_roots is None:
        context_roots = discover_context_roots()

    violations: list[Violation] = []
    for package_name, contexts_root in context_roots:
        for context_file in iter_context_files(package_name, contexts_root):
            violations.extend(check_file(context_file))
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
