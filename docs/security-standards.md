# Security Standards

Baseline security requirements for all code in this project.

## Security Rules

### 1. SSL Verification Required

Never use `verify=False` in HTTP clients (httpx, requests, aiohttp) in production code. If disabled for local development, it must be gated behind a `DEBUG` setting and logged as a warning.

### 2. SHA-256 for Identity Hashing

Use SHA-256 (or stronger) for any security-related hashing: tokens, passwords (via bcrypt/argon2), signatures. MD5 is acceptable only for non-security cache keys where collision resistance is irrelevant.

### 3. Regex Injection Prevention

Always call `re.escape()` on user-supplied strings before using them in MongoDB `$regex` queries or any regular expression construction.

```python
# Correct
import re
pattern = re.escape(user_input)
query = {"name": {"$regex": pattern, "$options": "i"}}

# Wrong - allows regex injection
query = {"name": {"$regex": user_input}}
```

### 4. Secret Key Requirements

- Production `secret_key` must be at least 32 characters.
- The application must refuse to start if the secret key matches the default value in production mode.
- Generate keys with `secrets.token_urlsafe(32)` or equivalent.

### 5. No Empty Except Blocks

Every `except` clause must catch a specific exception type and log it. Bare `except:` and `except Exception: pass` are prohibited.

```python
# Correct
try:
    result = await fetch_data()
except httpx.TimeoutException:
    logger.warning("Fetch timed out", exc_info=True)
    raise

# Wrong
try:
    result = await fetch_data()
except:
    pass
```

### 6. No Module-Level Side Effects

Module-level code must not instantiate `Settings()`, open database connections, perform file I/O, or make network calls. All initialization happens explicitly during application startup (e.g., FastAPI lifespan).

### 7. Input Validation

- All request bodies must use Pydantic models.
- All path and query parameters must use `Path()` / `Query()` with type constraints.
- Validate at the boundary, trust internally.

### 8. Bearer Token Authentication

Any endpoint that requires authentication must use `Authorization: Bearer <token>` and be documented explicitly. The base template does not pre-classify routes as public vs internal.

### 9. No Hardcoded Credentials

No API keys, passwords, tokens, or connection strings in source code. Use environment variables or a secrets manager. Run `grep -r` checks for common patterns (`password=`, `secret=`, `token=`, `api_key=`) before committing.

### 10. Safe Error Messages

Error responses to clients must not include stack traces, database names, collection names, file paths, or internal IP addresses. Log full details server-side; return generic messages to callers.

```python
# Correct
raise HTTPException(status_code=500, detail="Internal server error")

# Wrong
raise HTTPException(status_code=500, detail=str(e))
```

### 11. Explicit Logout

Logout endpoints must invalidate or clear all auth artifacts: access tokens, refresh tokens, session cookies, and any server-side session state.

## Pre-Commit Security Checklist

Before every commit, verify:

- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] No `verify=False` in HTTP clients
- [ ] No bare `except:` or `except Exception: pass`
- [ ] No module-level side effects (Settings(), DB connections, file I/O)
- [ ] All user input validated via Pydantic or Path/Query
- [ ] All regex built from user input uses `re.escape()`
- [ ] Error responses do not leak internal details
- [ ] Auth is enforced on every endpoint that is meant to be protected
- [ ] No MD5 used for security purposes
- [ ] Secret key length >= 32 chars and not default
- [ ] `.env` and credential files are in `.gitignore`

## Secret Management

### Environment Variables

All secrets are provided via environment variables, loaded from `.env` files in development:

```
MONGODB_URL=mongodb://...
SECRET_KEY=<generated-32+-char-key>
OPENAI_API_KEY=sk-...
```

### Rules

- `.env` files are listed in `.gitignore` and never committed.
- `.env.example` contains variable names with placeholder values only.
- Required secrets are validated at application startup; the app fails fast if any are missing.
- Secrets are never logged, even at DEBUG level.
- Rotate any secret that has been exposed in logs, error messages, or version control history.
