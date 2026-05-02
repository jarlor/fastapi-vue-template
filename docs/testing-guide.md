# Testing Guide

This document explains the repository's test surfaces.

## Commands

Application tests:

```bash
uv run poe test
```

Harness/tool self-tests:

```bash
uv run poe harness-test
```

The aggregate gate:

```bash
uv run poe harness
```

## Directory Boundaries

- `tests/` validates application behavior and shared runtime utilities.
- `harness_tests/` validates harness checkers and template tooling.
- `scripts/harness/` contains implementation details for Poe/CI gates.

The application test gate requires at least 80% source coverage. Do not move business tests into `harness_tests/` to avoid coverage or application-test failures.
