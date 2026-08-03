#!/usr/bin/env python3
"""Provide the template's local, bypassable direct-push guard."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping

MAIN_REF = "refs/heads/main"


def check_push_policy(environment: Mapping[str, str]) -> str | None:
    """Return an actionable message when a push targets main directly."""
    if environment.get("PRE_COMMIT_REMOTE_BRANCH") != MAIN_REF:
        return None

    return (
        "Direct pushes to main are outside this template's normal workflow. "
        "Push a short-lived branch and merge it through a pull request after CI and human review. "
        "This is a local soft guard; bypassing hooks is an explicit human exception, not approval."
    )


def main() -> int:
    """Run the policy against the pre-commit pre-push environment."""
    message = check_push_policy(os.environ)
    if message is None:
        return 0

    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
