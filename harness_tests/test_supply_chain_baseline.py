"""Tests for the supply-chain baseline checker."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "harness" / "check_supply_chain_baseline.py"
PINNED_CHECKOUT = "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd"


def load_checker_module() -> ModuleType:
    """Load the checker script as a module without making scripts a package."""
    spec = importlib.util.spec_from_file_location("check_supply_chain_baseline", CHECKER_PATH)
    if spec is None or spec.loader is None:
        msg = f"Could not load {CHECKER_PATH}"
        raise RuntimeError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


checker = load_checker_module()
check_supply_chain_baseline = checker.check_supply_chain_baseline


def write_file(root: Path, relative: str, content: str = "") -> Path:
    """Write a file in a temporary repository."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def seed_repo(root: Path) -> None:
    """Create a minimal compliant repository."""
    write_file(root, "uv.lock")
    write_file(
        root,
        "src/frontend/package.json",
        json.dumps({"name": "frontend", "packageManager": "npm@10.9.2"}),
    )
    write_file(root, "src/frontend/package-lock.json")
    write_file(
        root,
        ".github/workflows/ci.yml",
        f"""
name: CI
on: [push]
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: {PINNED_CHECKOUT}
      - run: uv sync --frozen --group dev
      - run: npm ci --no-audit --no-fund
""",
    )
    for relative in (
        ".github/workflows/open-code-review.yml",
        ".opencodereview/review-rules.md",
        ".opencodereview/rule.json",
    ):
        write_file(root, relative, (ROOT / relative).read_text())
    write_file(
        root,
        ".github/dependabot.yml",
        """
version: 2
updates:
  - package-ecosystem: uv
    directory: /
    schedule: {interval: weekly}
  - package-ecosystem: npm
    directory: /src/frontend
    schedule: {interval: weekly}
  - package-ecosystem: github-actions
    directory: /
    schedule: {interval: weekly}
""",
    )


def messages_for(root: Path) -> list[str]:
    """Run the checker and return formatted messages."""
    return [violation.format(root.resolve()) for violation in check_supply_chain_baseline(root)]


class TestSupplyChainBaseline:
    def test_accepts_seeded_repository(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)

        assert messages_for(tmp_path) == []

    def test_blocks_unpinned_actions(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.write_text(workflow.read_text().replace(PINNED_CHECKOUT, "actions/checkout@v6"))

        messages = messages_for(tmp_path)

        assert any("uses unpinned action: actions/checkout@v6" in message for message in messages)

    def test_requires_a_workflow(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        (tmp_path / ".github/workflows/ci.yml").unlink()
        (tmp_path / ".github/workflows/open-code-review.yml").unlink()

        messages = messages_for(tmp_path)

        assert any("at least one GitHub Actions workflow is required" in message for message in messages)

    def test_requires_dependency_update_coverage(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        (tmp_path / ".github/dependabot.yml").unlink()

        messages = messages_for(tmp_path)

        assert any("Dependabot configuration is required" in message for message in messages)

    def test_blocks_unpinned_remote_reusable_workflows_and_inherited_secrets(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.write_text(
            """
name: CI
on: [push]
permissions: {}
jobs:
  delegated:
    uses: attacker/project/.github/workflows/ci.yml@main
    secrets: inherit
"""
        )

        messages = messages_for(tmp_path)

        assert any("uses unpinned reusable workflow" in message for message in messages)
        assert any("must pass explicit secrets" in message for message in messages)

    def test_requires_the_repository_owned_npm_lockfile(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        (tmp_path / "uv.lock").unlink()
        (tmp_path / "src/frontend/package-lock.json").unlink()
        write_file(tmp_path, "src/frontend/yarn.lock")
        package_json = tmp_path / "src/frontend/package.json"
        package_json.write_text(json.dumps({"name": "frontend", "packageManager": "pnpm@10.0.0"}))

        messages = messages_for(tmp_path)

        assert any("uv.lock: required lockfile is missing" in message for message in messages)
        assert any("npm package-lock.json is required" in message for message in messages)
        assert any("this template uses npm" in message for message in messages)

    def test_requires_package_manager_to_declare_npm(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        (tmp_path / "src/frontend/package-lock.json").unlink()
        package_json = tmp_path / "src/frontend/package.json"
        package_json.write_text(json.dumps({"name": "frontend", "packageManager": "yarn@4.0.0"}))

        messages = messages_for(tmp_path)

        assert any("packageManager must match the committed frontend lockfile" in message for message in messages)

    def test_blocks_mutable_install_commands(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.write_text(workflow.read_text().replace("uv sync --frozen --group dev", "uv sync --group dev"))
        workflow.write_text(workflow.read_text().replace("npm ci --no-audit --no-fund", "npm install"))

        messages = messages_for(tmp_path)

        assert any("must use uv sync --frozen" in message for message in messages)
        assert any("must use npm ci, not npm install" in message for message in messages)

    def test_restricts_workflow_write_permissions(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.write_text(workflow.read_text().replace("contents: read", "contents: write"))

        messages = messages_for(tmp_path)

        assert any("top-level permissions must be empty or contents: read" in message for message in messages)

    def test_accepts_an_explicitly_empty_permission_set(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.write_text(workflow.read_text().replace("permissions:\n  contents: read", "permissions: {}"))

        assert messages_for(tmp_path) == []

    def test_requires_the_automatic_advisory_review_lane(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        (tmp_path / ".github/workflows/open-code-review.yml").unlink()

        messages = messages_for(tmp_path)

        assert any("automatic advisory OpenCodeReview workflow is required" in message for message in messages)

    def test_allows_only_the_narrow_review_comment_permission(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/open-code-review.yml"
        workflow.write_text(workflow.read_text().replace("pull-requests: write", "contents: write"))

        messages = messages_for(tmp_path)

        assert any("has prohibited write permissions" in message for message in messages)
        assert any("permissions must be exactly" in message for message in messages)

    def test_blocks_pull_request_write_permission_outside_review_lane(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/ci.yml"
        workflow.write_text(
            workflow.read_text().replace(
                "runs-on: ubuntu-latest",
                "permissions:\n      pull-requests: write\n    runs-on: ubuntu-latest",
            )
        )

        messages = messages_for(tmp_path)

        assert any("test has prohibited write permissions" in message for message in messages)

    def test_requires_fixed_ocr_runtime_and_update_guard(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/open-code-review.yml"
        workflow.write_text(
            workflow.read_text()
            .replace('OCR_NO_UPDATE: "1"', 'OCR_NO_UPDATE: ""')
            .replace('ocr_version: "1.8.5"', "ocr_version: latest")
        )

        messages = messages_for(tmp_path)

        assert any("must disable the OCR background updater" in message for message in messages)
        assert any("input ocr_version must be '1.8.5'" in message for message in messages)

    def test_requires_trusted_repository_owned_review_rules(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        rule = tmp_path / ".opencodereview/rule.json"
        rule.write_text(
            json.dumps(
                {
                    "include": [],
                    "exclude": "generated/**",
                    "rules": [{"path": "**", "rule": "../../outside.md", "merge_system_rule": False}],
                }
            )
        )

        messages = messages_for(tmp_path)

        assert any("rule selection must match the reviewed repository policy" in message for message in messages)

    def test_requires_non_empty_repository_guidance(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        (tmp_path / ".opencodereview/review-rules.md").write_text("\n")

        messages = messages_for(tmp_path)

        assert any("OpenCodeReview guidance is missing" in message for message in messages)

    def test_reports_invalid_workflow_jobs_without_crashing(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/open-code-review.yml"
        workflow_text = workflow.read_text()
        workflow.write_text(f"{workflow_text[: workflow_text.index('jobs:')]}jobs: []\n")

        messages = messages_for(tmp_path)

        assert any("workflow jobs must be a mapping" in message for message in messages)
        assert any("must define only the advisory-review job" in message for message in messages)

    def test_blocks_guard_and_exclusion_fail_open_bypasses(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/open-code-review.yml"
        workflow.write_text(
            workflow.read_text().replace("vars.OCR_ENABLED == 'true'", "true || vars.OCR_ENABLED == 'true'")
        )
        rule = tmp_path / ".opencodereview/rule.json"
        config = json.loads(rule.read_text())
        config["exclude"] = ["**"]
        rule.write_text(json.dumps(config))

        messages = messages_for(tmp_path)

        assert any("must keep the exact reviewed activation guard" in message for message in messages)
        assert any("rule selection must match the reviewed repository policy" in message for message in messages)

    def test_blocks_unreviewed_ocr_inputs_and_step_mutation(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/open-code-review.yml"
        workflow.write_text(
            workflow.read_text()
            .replace(
                "          background: ${{ github.event.pull_request.title }}",
                "          background: ${{ github.event.pull_request.title }}\n"
                "          base_ref: main\n"
                "          head_sha: ${{ github.event.pull_request.base.sha }}",
            )
            .replace("        id: ocr", "        id: ocr\n        continue-on-error: true")
        )

        messages = messages_for(tmp_path)

        assert any("unreviewed action inputs" in message for message in messages)
        assert any("action step may define only" in message for message in messages)

    def test_blocks_silent_trigger_disable_and_boolean_timeout(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/open-code-review.yml"
        workflow.write_text(
            workflow.read_text()
            .replace(
                "    types: [opened, synchronize, reopened, ready_for_review]",
                "    types: [opened, synchronize, reopened, ready_for_review]\n"
                '    paths-ignore: ["**"]\n'
                "  pull_request_review:\n"
                "    types: [submitted]",
            )
            .replace("timeout-minutes: 30", "timeout-minutes: true")
        )

        messages = messages_for(tmp_path)

        assert any("must use only the pull_request_target trigger" in message for message in messages)
        assert any("trigger may define only branches and types" in message for message in messages)
        assert any("timeout-minutes must be between 1 and 30" in message for message in messages)

    def test_blocks_unreviewed_top_level_execution_settings(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/open-code-review.yml"
        workflow.write_text(
            workflow.read_text().replace(
                "permissions: {}",
                "env:\n"
                "  npm_config_registry: https://attacker.invalid\n"
                "defaults:\n"
                "  run:\n"
                '    shell: "true {0}"\n'
                "permissions: {}",
            )
        )

        messages = messages_for(tmp_path)

        assert any("may define only the reviewed top-level fields" in message for message in messages)

    def test_requires_fail_closed_comment_publication(self, tmp_path: Path) -> None:
        seed_repo(tmp_path)
        workflow = tmp_path / ".github/workflows/open-code-review.yml"
        workflow.write_text(workflow.read_text().replace("          exit 1", "          exit 0"))

        messages = messages_for(tmp_path)

        assert any("publication failure check must remain fail-closed" in message for message in messages)
