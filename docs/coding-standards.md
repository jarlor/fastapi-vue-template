# Coding Standards

## Python

### Naming

| Element | Convention | Example |
|---------|-----------|---------|
| Files, functions, variables | `snake_case` | `user_service.py`, `get_user()` |
| Classes | `PascalCase` | `UserService`, `AuthToken` |
| Constants | `UPPER_CASE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |

### Type Hints

Type hints are required on all public functions and methods. Use `from __future__ import annotations` at the top of every module for forward reference support.

```python
from __future__ import annotations

def get_user_by_email(email: str) -> User | None:
    ...
```

### Docstrings

Required on all public classes and any function with non-obvious behavior. Use Google-style docstrings.

```python
def calculate_score(weights: list[float], values: list[float]) -> float:
    """Calculate weighted score from parallel weight and value lists.

    Args:
        weights: Normalized weights summing to 1.0.
        values: Raw score values corresponding to each weight.

    Returns:
        Weighted sum of values.

    Raises:
        ValueError: If weights and values have different lengths.
    """
```

### String Formatting

Use f-strings. Avoid `.format()` and `%` formatting.

```python
# Correct
logger.info(f"User {user_id} logged in from {ip}")

# Wrong
logger.info("User {} logged in from {}".format(user_id, ip))
```

### Imports

- Use absolute imports only.
- Group imports: stdlib, third-party, local -- separated by blank lines.
- Use ruff for automatic import sorting (`ruff check --select I`).

```python
import os
from datetime import datetime

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection

from app_name.contexts.auth.application.services.auth_service import AuthService
```

## File Organization

- Many small files over few large files.
- **200-400 lines** typical, **800 lines** maximum.
- **Functions under 50 lines.** Extract helpers if longer.
- **Nesting depth under 4 levels.** Use early returns, guard clauses, and extraction to flatten.

## Immutability

Prefer creating new objects over mutating existing ones. This prevents hidden side effects and makes debugging easier.

```python
# Correct - return new dict
def with_status(user: dict, status: str) -> dict:
    return {**user, "status": status}

# Wrong - mutate in place
def set_status(user: dict, status: str) -> None:
    user["status"] = status
```

For Pydantic models, use `model.model_copy(update={"field": value})` instead of direct attribute assignment.

## Error Handling

- Handle errors explicitly at every level.
- Never swallow exceptions silently.
- Log context (what operation, what input) alongside the error.
- User-facing error messages are generic; server-side logs are detailed.

```python
try:
    result = await collection.find_one({"_id": doc_id})
except PyMongoError as e:
    logger.error(f"Failed to fetch document {doc_id}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")
```

## TypeScript / Vue

### General

- Use `<script setup lang="ts">` exclusively. No Options API.
- Type all props and emits with TypeScript interfaces.
- No `any` type except at system boundaries (e.g., third-party library returns). Document why with a comment.

### Composables

Extract reusable logic into composables following the `useXxx` pattern:

```typescript
// composables/useAuth.ts
export function useAuth() {
  const token = ref<string | null>(null)
  const isAuthenticated = computed(() => token.value !== null)
  // ...
  return { token, isAuthenticated, login, logout }
}
```

### State Management

Use Pinia stores with the composition API (setup function), not the options API:

```typescript
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const isAuthenticated = computed(() => token.value !== null)

  function setToken(newToken: string) {
    token.value = newToken
  }

  return { token, isAuthenticated, setToken }
})
```

## Code Quality Checklist

Before marking work complete:

- [ ] Code is readable and well-named
- [ ] Functions are small (< 50 lines)
- [ ] Files are focused (< 800 lines)
- [ ] No deep nesting (> 4 levels)
- [ ] Proper error handling
- [ ] No hardcoded values (use constants or config)
- [ ] Immutable patterns used where possible
- [ ] Type hints on all public Python functions
- [ ] TypeScript has no untyped `any`
