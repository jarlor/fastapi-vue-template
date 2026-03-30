# Testing Guide

## TDD Workflow

Follow the RED-GREEN-IMPROVE cycle for every change:

1. **RED** -- Write a failing test that describes the expected behaviour.
2. **GREEN** -- Write the minimal implementation to make the test pass.
3. **IMPROVE** -- Refactor while keeping all tests green.

Target **80 %+** code coverage.

## Tools

| Tool            | Purpose                          |
|-----------------|----------------------------------|
| pytest          | Test runner                      |
| pytest-asyncio  | Async test support               |
| pytest-cov      | Coverage reporting               |
| ruff            | Linting (not a test tool, but run before commits) |

Run all tests:

```bash
uv run poe test
```

> **Note**: All `poe` task commands should be prefixed with `uv run` (e.g. `uv run poe lint`, `uv run poe fmt`).

## Test Organisation

```
tests/
├── conftest.py          # shared fixtures (mock DB, test client)
├── unit/
│   └── <context>/       # mirrors src/app_name/contexts/
│       └── test_service.py
└── integration/
    └── <context>/
        └── test_router.py
```

- **Unit tests** cover application services and domain logic. They mock infrastructure (repositories, external clients).
- **Integration tests** cover FastAPI routers via `httpx.AsyncClient`. They use a real (or in-memory) database fixture.

## Mock Patterns for Motor

Use `AsyncMock` to mock Motor collections:

```python
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_collection():
    col = MagicMock()
    col.find_one = AsyncMock(return_value={"_id": "1", "name": "test"})
    col.insert_one = AsyncMock()
    col.update_one = AsyncMock()
    col.delete_one = AsyncMock()
    return col
```

For `find()` which returns a cursor, mock the cursor's `to_list`:

```python
cursor = MagicMock()
cursor.to_list = AsyncMock(return_value=[{"_id": "1"}, {"_id": "2"}])
col.find = MagicMock(return_value=cursor)
```

## conftest.py Pattern

The root `tests/conftest.py` provides three core fixtures:

1. **mock_db** -- A `MagicMock` that acts as a Motor database, returning mock collections via `__getitem__`.
2. **test_settings** -- A settings object with safe defaults for testing.
3. **test_client** -- An `httpx.AsyncClient` wired to the FastAPI app with mocked dependencies.

See `tests/conftest.py` for the full implementation.
