#!/usr/bin/env python3
"""Enforce deterministic supply-chain rules for the template."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PINNED_ACTION_RE = re.compile(r"^[^@\s]+@[a-f0-9]{40}$")
FRONTEND_LOCKFILE = "src/frontend/package-lock.json"
OPEN_CODE_REVIEW_ACTION = "alibaba/open-code-review"
OPEN_CODE_REVIEW_REF = f"{OPEN_CODE_REVIEW_ACTION}@5829539379ecc3c2e43c36061b73469f7a261f8d"
OPEN_CODE_REVIEW_CONDITION = " ".join(
    (
        "vars.OCR_ENABLED == 'true'",
        "&& github.event.pull_request.user.login != 'dependabot[bot]'",
        "&& github.event.pull_request.draft == false",
        "&& github.event.pull_request.head.repo.full_name == github.repository",
    )
)
OPEN_CODE_REVIEW_GUIDANCE = ".opencodereview/review-rules.md"
OPEN_CODE_REVIEW_JOB = "advisory-review"
OPEN_CODE_REVIEW_RULE = ".opencodereview/rule.json"
OPEN_CODE_REVIEW_WORKFLOW = ".github/workflows/open-code-review.yml"
PRE_COMMIT_CONFIG = ".pre-commit-config.yaml"
PRE_PUSH_POLICY_ENTRY = "uv run python scripts/governance/check_push_policy.py"
PRE_PUSH_POLICY_HOOK = "protect-main-push"
PRE_PUSH_POLICY_SCRIPT = "scripts/governance/check_push_policy.py"
LOCAL_REVIEW_HOOK_CONFIG = ".codex/hooks.json"
LOCAL_REVIEW_HOOK_SCRIPT = ".codex/hooks/stop_review.py"
LOCAL_REVIEW_GIT_ATTRIBUTES = (
    "/.codex/hooks/stop_review.py text eol=lf",
    "/.opencodereview/rule.json text eol=lf",
    "/.opencodereview/review-rules.md text eol=lf",
)
LOCAL_REVIEW_HOOK_DESCRIPTION = (
    "Require one local OpenCodeReview delegation pass before Codex hands off a changed repository state."
)
LOCAL_REVIEW_HOOK_STATUS = "Preparing local OpenCodeReview delegation"
LOCAL_REVIEW_HOOK_TIMEOUT = 30
LOCAL_REVIEW_INTEGRITY_FAILURE = (
    "Trusted local review artifacts failed integrity checks. Inspect .codex/hooks/stop_review.py and "
    ".opencodereview/, then re-trust the exact hook with /hooks."
)
OPEN_CODE_REVIEW_PERMISSIONS = {"contents": "read", "pull-requests": "write"}
OPEN_CODE_REVIEW_EVENTS = {"opened", "synchronize", "reopened", "ready_for_review"}
OPEN_CODE_REVIEW_RULE_CONFIG = {
    "include": [
        ".gitattributes",
        ".pre-commit-config.yaml",
        ".github/CODEOWNERS",
        ".github/CODEOWNERS.template",
        ".github/pull_request_template.md",
        ".opencodereview/review-rules.md",
        "AGENTS.md",
        "ARCHITECTURE.md",
        "CONTRIBUTING.md",
        "README.md",
        "docs/adr/**/*.md",
        "scripts/governance/**/*.py",
        "tests/**/*.py",
        "harness_tests/**/*.py",
        "**/*.test.{js,jsx,ts,tsx}",
        "**/*.spec.{js,jsx,ts,tsx}",
        "**/__tests__/**",
    ],
    "exclude": [
        "contracts/openapi.json",
        "src/frontend/src/api/generated/**",
    ],
    "rules": [
        {
            "path": "**",
            "rule": OPEN_CODE_REVIEW_GUIDANCE,
            "merge_system_rule": True,
        }
    ],
}
OPEN_CODE_REVIEW_INPUTS = {
    "llm_url": "${{ secrets.OCR_LLM_URL }}",
    "llm_auth_token": "${{ secrets.OCR_LLM_AUTH_TOKEN }}",
    "llm_model": "${{ vars.OCR_LLM_MODEL }}",
    "llm_use_anthropic": "${{ vars.OCR_LLM_USE_ANTHROPIC }}",
    "github_token": "${{ github.token }}",
    "ocr_version": "1.8.5",
    "language": "中文",
    "llm_timeout": "120",
    "review_concurrency": "4",
    "background": "${{ github.event.pull_request.title }}",
    "upload_artifacts": "false",
    "sticky_summary": "true",
    "incremental": "false",
    "incremental_overlap_threshold": "0.6",
    "review_comment_batch_size": "25",
    "route_severity_below": "low",
    "route_categories": "style,documentation",
}
OPEN_CODE_REVIEW_PUBLICATION_CONDITION = " ".join(
    (
        "always()",
        "&& steps.ocr.outcome == 'success'",
        "&& steps.ocr.outputs.comments_failed != ''",
        "&& steps.ocr.outputs.comments_failed != '0'",
    )
)
OPEN_CODE_REVIEW_PUBLICATION_COMMAND = "\n".join(
    (
        'echo "::error::OpenCodeReview could not publish ${FAILED_COMMENT_COUNT} generated comment(s)."',
        "exit 1",
    )
)
UNSUPPORTED_FRONTEND_LOCKFILES = (
    "src/frontend/yarn.lock",
    "src/frontend/pnpm-lock.yaml",
    "src/frontend/bun.lock",
    "src/frontend/bun.lockb",
)


@dataclass(frozen=True)
class Violation:
    """A supply-chain baseline violation."""

    path: Path
    message: str

    def format(self, root: Path) -> str:
        return f"{self.path.relative_to(root)}: {self.message}"


def expected_local_review_commands(
    script_digest: str,
    guidance_digest: str,
    rule_digest: str,
) -> tuple[str, str]:
    """Return isolated bootstrap commands bound to the three trusted artifacts."""
    expected = {
        LOCAL_REVIEW_HOOK_SCRIPT: script_digest,
        OPEN_CODE_REVIEW_GUIDANCE: guidance_digest,
        OPEN_CODE_REVIEW_RULE: rule_digest,
    }
    program = "\n".join(
        (
            "import hashlib,io,json,runpy,sys",
            "from pathlib import Path",
            f"failure={LOCAL_REVIEW_INTEGRITY_FAILURE!r}",
            f"expected={expected!r}",
            "raw=sys.stdin.read()",
            "try:",
            " data=json.loads(raw)",
            " cwd=Path(data.get('cwd') or Path.cwd()).resolve(strict=True)",
            " root=next((p for p in (cwd,*cwd.parents) if (p/'.git').exists()),None)",
            " if root is None: raise RuntimeError('root')",
            " actual={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in expected}",
            " if actual!=expected: raise RuntimeError('digest')",
            " sys.stdin=io.StringIO(raw)",
            " runpy.run_path(str(root/'.codex/hooks/stop_review.py'),run_name='__main__')",
            "except Exception:",
            " print(json.dumps({'continue':False,'stopReason':failure},separators=(',',':')))",
        )
    )
    source = f"exec({program!r})"
    return (
        f"python3 -I -S -c {shlex.quote(source)}",
        subprocess.list2cmdline(["py", "-3", "-I", "-S", "-c", source]),
    )


def load_yaml(path: Path) -> Any:
    """Load a YAML file."""
    return yaml.safe_load(path.read_text())


def check_lockfiles(root: Path) -> list[Violation]:
    """Require the selected package-manager lockfiles and reject drift."""
    violations: list[Violation] = []
    if not (root / "uv.lock").is_file():
        violations.append(Violation(root / "uv.lock", "required lockfile is missing"))

    if not (root / FRONTEND_LOCKFILE).is_file():
        violations.append(Violation(root / FRONTEND_LOCKFILE, "npm package-lock.json is required"))

    unsupported = [relative for relative in UNSUPPORTED_FRONTEND_LOCKFILES if (root / relative).exists()]
    if unsupported:
        violations.append(
            Violation(
                root / "src/frontend",
                "this template uses npm; remove unsupported lockfiles: " + ", ".join(unsupported),
            )
        )

    package_json = root / "src/frontend/package.json"
    if not package_json.is_file():
        violations.append(Violation(package_json, "package.json is required for the frontend lockfile"))
        return violations

    package_data = json.loads(package_json.read_text())
    package_manager = package_data.get("packageManager", "")
    if not package_manager:
        violations.append(Violation(package_json, "packageManager must pin the frontend package manager version"))
    elif not package_manager.startswith("npm@"):
        violations.append(Violation(package_json, "packageManager must match the committed frontend lockfile"))

    return violations


def iter_workflow_files(root: Path) -> list[Path]:
    """Return GitHub workflow files."""
    workflows = root / ".github/workflows"
    return sorted(workflows.glob("*.yml")) + sorted(workflows.glob("*.yaml"))


def workflow_events(workflow: Any) -> Any:
    """Return a workflow's event mapping despite PyYAML's YAML 1.1 `on` coercion."""
    if not isinstance(workflow, dict):
        return None
    return workflow.get("on", workflow.get(True))


def iter_open_code_review_steps(workflow: Any) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Return jobs and steps that invoke the OpenCodeReview action."""
    matches: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    jobs = workflow.get("jobs", {}) if isinstance(workflow, dict) else {}
    if not isinstance(jobs, dict):
        return matches
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            if str(step.get("uses", "")).startswith(f"{OPEN_CODE_REVIEW_ACTION}@"):
                matches.append((str(job_id), job, step))
    return matches


def find_unpinned_actions(path: Path, workflow: Any) -> list[Violation]:
    """Return workflow action references that are not pinned to full SHAs."""
    violations: list[Violation] = []
    jobs = workflow.get("jobs", {}) if isinstance(workflow, dict) else {}
    if not isinstance(jobs, dict):
        return [Violation(path, "workflow jobs must be a mapping")]
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue

        reusable_workflow = job.get("uses")
        if reusable_workflow:
            reference = str(reusable_workflow)
            if not reference.startswith("./") and not PINNED_ACTION_RE.match(reference):
                violations.append(Violation(path, f"{job_id} uses unpinned reusable workflow: {reference}"))
            if not reference.startswith("./") and job.get("secrets") == "inherit":
                violations.append(Violation(path, f"{job_id} must pass explicit secrets to a remote reusable workflow"))

        steps = job.get("steps", [])
        if not isinstance(steps, list):
            violations.append(Violation(path, f"{job_id} steps must be a list"))
            continue
        for step in steps:
            if not isinstance(step, dict) or "uses" not in step:
                continue
            action = str(step["uses"])
            if action.startswith("./"):
                continue
            if not PINNED_ACTION_RE.match(action):
                violations.append(Violation(path, f"{job_id} uses unpinned action: {action}"))
    return violations


def check_workflow_permissions(root: Path, path: Path, workflow: Any) -> list[Violation]:
    """Require least-privilege workflow permissions."""
    permissions = workflow.get("permissions") if isinstance(workflow, dict) else None
    violations: list[Violation] = []

    if permissions not in ({}, {"contents": "read"}):
        violations.append(Violation(path, "top-level permissions must be empty or contents: read"))

    jobs = workflow.get("jobs", {}) if isinstance(workflow, dict) else {}
    if not isinstance(jobs, dict):
        return violations
    for job_id, job in jobs.items():
        if not isinstance(job, dict) or "permissions" not in job:
            continue
        job_permissions = job["permissions"]
        steps = job.get("steps", [])
        is_narrow_review_publisher = (
            path.relative_to(root).as_posix() == OPEN_CODE_REVIEW_WORKFLOW
            and job_permissions == OPEN_CODE_REVIEW_PERMISSIONS
            and isinstance(steps, list)
            and any(
                str(step.get("uses", "")).startswith(f"{OPEN_CODE_REVIEW_ACTION}@")
                for step in steps
                if isinstance(step, dict)
            )
        )
        has_write_permission = job_permissions == "write-all" or (
            isinstance(job_permissions, dict) and any(value == "write" for value in job_permissions.values())
        )
        if has_write_permission and not is_narrow_review_publisher:
            violations.append(Violation(path, f"{job_id} has prohibited write permissions: {job_permissions}"))
        elif not isinstance(job_permissions, dict) and job_permissions not in {"read-all", "write-all"}:
            violations.append(Violation(path, f"{job_id} has invalid permissions: {job_permissions}"))

    return violations


def check_open_code_review_workflow(root: Path) -> list[Violation]:
    """Require the automatic advisory review lane and its security boundary."""
    path = root / OPEN_CODE_REVIEW_WORKFLOW
    if not path.is_file():
        return [Violation(path, "automatic advisory OpenCodeReview workflow is required")]

    workflow = load_yaml(path)
    if not isinstance(workflow, dict):
        return [Violation(path, "OpenCodeReview workflow must be a YAML mapping")]

    violations: list[Violation] = []
    expected_workflow_fields = {"name", True, "concurrency", "permissions", "jobs"}
    if set(workflow) != expected_workflow_fields or workflow.get("name") != "OpenCodeReview":
        violations.append(Violation(path, "OpenCodeReview workflow may define only the reviewed top-level fields"))
    if workflow.get("permissions") != {}:
        violations.append(Violation(path, "OpenCodeReview top-level permissions must be empty"))

    events = workflow_events(workflow)
    if not isinstance(events, dict) or set(events) != {"pull_request_target"}:
        violations.append(Violation(path, "OpenCodeReview must use only the pull_request_target trigger"))
    target = events.get("pull_request_target") if isinstance(events, dict) else None
    if not isinstance(target, dict):
        violations.append(Violation(path, "OpenCodeReview must use pull_request_target"))
    else:
        if set(target) != {"branches", "types"}:
            violations.append(Violation(path, "OpenCodeReview trigger may define only branches and types"))
        if target.get("branches") != ["main"]:
            violations.append(Violation(path, "OpenCodeReview must target only the main base branch"))
        event_types = target.get("types", [])
        if (
            not isinstance(event_types, list)
            or not all(isinstance(event, str) for event in event_types)
            or set(event_types) != OPEN_CODE_REVIEW_EVENTS
        ):
            violations.append(
                Violation(path, f"OpenCodeReview pull request events must be {sorted(OPEN_CODE_REVIEW_EVENTS)}")
            )
    expected_concurrency = {
        "group": "open-code-review-${{ github.event.pull_request.number }}",
        "cancel-in-progress": True,
    }
    if workflow.get("concurrency") != expected_concurrency:
        violations.append(Violation(path, "OpenCodeReview must cancel superseded reviews for the same pull request"))

    jobs = workflow.get("jobs", {})
    if not isinstance(jobs, dict) or set(jobs) != {OPEN_CODE_REVIEW_JOB}:
        violations.append(Violation(path, f"OpenCodeReview must define only the {OPEN_CODE_REVIEW_JOB} job"))

    matches = iter_open_code_review_steps(workflow)
    if len(matches) != 1:
        violations.append(Violation(path, "exactly one pinned OpenCodeReview action step is required"))
        return violations

    job_id, job, step = matches[0]
    expected_job_fields = {"name", "if", "runs-on", "timeout-minutes", "permissions", "env", "steps"}
    if set(job) != expected_job_fields:
        violations.append(Violation(path, f"{job_id} may define only the reviewed job fields"))
    if job.get("name") != "Advisory review":
        violations.append(Violation(path, f"{job_id} must keep the Advisory review check name"))
    if job.get("permissions") != OPEN_CODE_REVIEW_PERMISSIONS:
        violations.append(Violation(path, f"{job_id} permissions must be exactly {OPEN_CODE_REVIEW_PERMISSIONS}"))
    if job.get("runs-on") != "ubuntu-24.04":
        violations.append(Violation(path, f"{job_id} must use the GitHub-hosted ubuntu-24.04 runner"))
    timeout = job.get("timeout-minutes")
    if type(timeout) is not int or timeout < 1 or timeout > 30:
        violations.append(Violation(path, f"{job_id} timeout-minutes must be between 1 and 30"))
    job_env = job.get("env", {})
    if job_env != {"OCR_NO_UPDATE": "1"}:
        violations.append(Violation(path, f"{job_id} must disable the OCR background updater with OCR_NO_UPDATE=1"))

    condition = re.sub(r"\s+", " ", str(job.get("if", ""))).strip()
    if condition != OPEN_CODE_REVIEW_CONDITION:
        violations.append(Violation(path, f"{job_id} must keep the exact reviewed activation guard"))

    steps = job.get("steps")
    if not isinstance(steps, list) or len(steps) != 2 or steps[0] is not step:
        violations.append(Violation(path, f"{job_id} must contain only the reviewed action and publication check"))

    expected_action_fields = {"name", "id", "uses", "with"}
    if set(step) != expected_action_fields:
        violations.append(Violation(path, "OpenCodeReview action step may define only name, id, uses, and with"))
    if step.get("name") != "Review PR without executing its code" or step.get("id") != "ocr":
        violations.append(Violation(path, "OpenCodeReview action step must keep its reviewed name and ocr id"))

    action = str(step.get("uses", ""))
    if action != OPEN_CODE_REVIEW_REF:
        violations.append(
            Violation(path, f"OpenCodeReview action must use the vetted reference {OPEN_CODE_REVIEW_REF}")
        )

    inputs = step.get("with", {})
    if not isinstance(inputs, dict):
        violations.append(Violation(path, "OpenCodeReview action inputs must be a mapping"))
        return violations

    for name, expected in OPEN_CODE_REVIEW_INPUTS.items():
        if inputs.get(name) != expected:
            violations.append(Violation(path, f"OpenCodeReview input {name} must be {expected!r}"))
    unexpected_inputs = sorted(set(inputs) - set(OPEN_CODE_REVIEW_INPUTS))
    if unexpected_inputs:
        violations.append(Violation(path, f"OpenCodeReview has unreviewed action inputs: {unexpected_inputs}"))

    if isinstance(steps, list) and len(steps) == 2 and isinstance(steps[1], dict):
        publication = steps[1]
        expected_publication_fields = {"name", "if", "env", "run"}
        publication_condition = re.sub(r"\s+", " ", str(publication.get("if", ""))).strip()
        if (
            set(publication) != expected_publication_fields
            or publication.get("name") != "Surface incomplete comment publication"
            or publication_condition != OPEN_CODE_REVIEW_PUBLICATION_CONDITION
            or publication.get("env") != {"FAILED_COMMENT_COUNT": "${{ steps.ocr.outputs.comments_failed }}"}
            or str(publication.get("run", "")).strip() != OPEN_CODE_REVIEW_PUBLICATION_COMMAND
        ):
            violations.append(Violation(path, "OpenCodeReview publication failure check must remain fail-closed"))
    return violations


def check_open_code_review_rules(root: Path) -> list[Violation]:
    """Require the reviewed repository-owned rule selection and guidance."""
    path = root / OPEN_CODE_REVIEW_RULE
    if not path.is_file():
        return [Violation(path, "repository-owned OpenCodeReview rules are required")]

    try:
        config = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        return [Violation(path, f"invalid OpenCodeReview rule JSON: {error.msg}")]
    if not isinstance(config, dict):
        return [Violation(path, "OpenCodeReview rule configuration must be a JSON object")]

    violations: list[Violation] = []
    if config != OPEN_CODE_REVIEW_RULE_CONFIG:
        violations.append(Violation(path, "OpenCodeReview rule selection must match the reviewed repository policy"))

    guidance = (root / OPEN_CODE_REVIEW_GUIDANCE).resolve()
    if not guidance.is_relative_to(root) or not guidance.is_file() or not guidance.read_text().strip():
        violations.append(Violation(path, f"OpenCodeReview guidance is missing: {OPEN_CODE_REVIEW_GUIDANCE}"))
    return violations


def check_pre_push_policy(root: Path) -> list[Violation]:
    """Require the versioned, locally installed soft guard for main pushes."""
    config_path = root / PRE_COMMIT_CONFIG
    script_path = root / PRE_PUSH_POLICY_SCRIPT
    if not config_path.is_file() or config_path.is_symlink():
        return [Violation(config_path, "local pre-commit configuration is required")]
    if not script_path.is_file() or script_path.is_symlink():
        return [Violation(script_path, "local main-push policy script is required")]

    config = load_yaml(config_path)
    if not isinstance(config, dict):
        return [Violation(config_path, "pre-commit configuration must be a mapping")]

    install_types = config.get("default_install_hook_types", [])
    repositories = config.get("repos", [])
    if not isinstance(install_types, list) or not isinstance(repositories, list):
        return [Violation(config_path, "must install the reviewed local pre-push guard for main")]
    hooks = [
        hook
        for repository in repositories
        if isinstance(repository, dict) and repository.get("repo") == "local"
        for hook in (repository.get("hooks", []) if isinstance(repository.get("hooks", []), list) else [])
        if isinstance(hook, dict) and hook.get("id") == PRE_PUSH_POLICY_HOOK
    ]
    expected_hook = {
        "id": PRE_PUSH_POLICY_HOOK,
        "entry": PRE_PUSH_POLICY_ENTRY,
        "language": "system",
        "stages": ["pre-push"],
        "always_run": True,
        "pass_filenames": False,
    }
    valid_hook = len(hooks) == 1 and all(hooks[0].get(key) == value for key, value in expected_hook.items())
    if {"pre-commit", "pre-push"}.issubset(install_types) and valid_hook:
        return []
    return [Violation(config_path, "must install the reviewed local pre-push guard for main")]


def check_local_review_hook(root: Path) -> list[Violation]:
    """Require the trusted Codex Stop hook and bind it to the reviewed handler bytes."""
    config_path = root / LOCAL_REVIEW_HOOK_CONFIG
    script_path = root / LOCAL_REVIEW_HOOK_SCRIPT
    attributes_path = root / ".gitattributes"
    violations: list[Violation] = []

    try:
        attributes = tuple(line.rstrip() for line in attributes_path.read_text().splitlines())
    except OSError:
        attributes = ()
    missing_attributes = [entry for entry in LOCAL_REVIEW_GIT_ATTRIBUTES if entry not in attributes]
    if missing_attributes:
        violations.append(
            Violation(
                attributes_path,
                "local review handler must keep LF-normalized bytes for its trusted digest",
            )
        )

    if not script_path.is_file() or script_path.is_symlink():
        violations.append(Violation(script_path, "repository-owned local review handler is required"))
        return violations
    script_content = script_path.read_text()
    required_handler_guards = (
        "STATE_VERSION = 2",
        'OCR_VERSION = "1.8.5"',
        'OCR_COMMIT = "582953937"',
        '"OCR_NO_UPDATE": "1"',
        'if value.get("stop_hook_active") is True:',
        '"--no-ext-diff"',
        '"--no-textconv"',
        '"delegate", "preview"',
        '"delegate", "rule"',
    )
    missing_guards = [guard for guard in required_handler_guards if guard not in script_content]
    if missing_guards:
        violations.append(Violation(script_path, "local review handler is missing a reviewed safety guard"))

    if not config_path.is_file() or config_path.is_symlink():
        violations.append(Violation(config_path, "repository-owned Codex Stop hook is required"))
        return violations
    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError as error:
        violations.append(Violation(config_path, f"invalid Codex hook JSON: {error.msg}"))
        return violations

    guidance_path = root / OPEN_CODE_REVIEW_GUIDANCE
    guidance_digest = hashlib.sha256(guidance_path.read_bytes()).hexdigest() if guidance_path.is_file() else ""
    rule_path = root / OPEN_CODE_REVIEW_RULE
    rule_digest = hashlib.sha256(rule_path.read_bytes()).hexdigest() if rule_path.is_file() else ""
    script_digest = hashlib.sha256(script_path.read_bytes()).hexdigest()
    posix_command, windows_command = expected_local_review_commands(script_digest, guidance_digest, rule_digest)
    expected_config = {
        "description": LOCAL_REVIEW_HOOK_DESCRIPTION,
        "hooks": {
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": posix_command,
                            "commandWindows": windows_command,
                            "timeout": LOCAL_REVIEW_HOOK_TIMEOUT,
                            "statusMessage": LOCAL_REVIEW_HOOK_STATUS,
                        }
                    ]
                }
            ]
        },
    }
    if config != expected_config:
        violations.append(
            Violation(
                config_path,
                "Codex Stop hook must match the reviewed command, timeout, and trusted artifact integrity digests",
            )
        )
    return violations


def check_workflow_commands(path: Path, workflow_text: str) -> list[Violation]:
    """Block mutable dependency installation commands in workflows."""
    violations: list[Violation] = []
    for line_number, line in enumerate(workflow_text.splitlines(), start=1):
        stripped = line.strip()
        if re.search(r"\bnpm install\b", stripped):
            violations.append(Violation(path, f"line {line_number} must use npm ci, not npm install"))
        if re.search(r"\buv sync\b", stripped) and "--frozen" not in stripped:
            violations.append(Violation(path, f"line {line_number} must use uv sync --frozen"))
    return violations


def check_workflows(root: Path) -> list[Violation]:
    """Check all workflow supply-chain rules."""
    violations: list[Violation] = []
    workflow_files = iter_workflow_files(root)
    if not workflow_files:
        return [Violation(root / ".github/workflows", "at least one GitHub Actions workflow is required")]

    for path in workflow_files:
        workflow_text = path.read_text()
        workflow = load_yaml(path)
        violations.extend(find_unpinned_actions(path, workflow))
        violations.extend(check_workflow_permissions(root, path, workflow))
        violations.extend(check_workflow_commands(path, workflow_text))
    return violations


def check_dependency_updates(root: Path) -> list[Violation]:
    """Require update coverage for each repository-owned dependency ecosystem."""
    path = root / ".github/dependabot.yml"
    if not path.is_file():
        return [Violation(path, "Dependabot configuration is required")]

    config = load_yaml(path)
    updates = config.get("updates", []) if isinstance(config, dict) else []
    configured = {
        (entry.get("package-ecosystem"), entry.get("directory")) for entry in updates if isinstance(entry, dict)
    }
    required = {("uv", "/"), ("npm", "/src/frontend"), ("github-actions", "/")}
    missing = sorted(required - configured)
    if not missing:
        return []
    return [Violation(path, f"missing dependency update coverage: {missing}")]


def check_supply_chain_baseline(root: Path = PROJECT_ROOT) -> list[Violation]:
    """Check the repository supply-chain baseline."""
    root = root.resolve()
    violations: list[Violation] = []
    violations.extend(check_lockfiles(root))
    violations.extend(check_workflows(root))
    violations.extend(check_pre_push_policy(root))
    violations.extend(check_open_code_review_workflow(root))
    violations.extend(check_open_code_review_rules(root))
    violations.extend(check_local_review_hook(root))
    violations.extend(check_dependency_updates(root))
    return violations


def main() -> int:
    """CLI entry point."""
    violations = check_supply_chain_baseline()
    if violations:
        print("Supply-chain baseline violations:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation.format(PROJECT_ROOT)}", file=sys.stderr)
        return 1

    print("Supply-chain baseline passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
