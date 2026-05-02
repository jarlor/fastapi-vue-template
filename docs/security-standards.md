# Security Standards

This document describes the baseline enforced by `uv run poe security`.

## Enforced Baseline

The security harness blocks:

- committed `.env` files except `.env.example`
- private key material
- high-confidence live tokens and secret assignments
- `verify=False`
- bare `except:`
- `except Exception: pass`
- `hashlib.md5(...)`

Run:

```bash
uv run poe security
```

The aggregate gate `uv run poe harness` runs the same check.

## Guidance

- Keep secrets in environment variables or a secrets manager, never source code.
- Validate user input at request boundaries with Pydantic, `Path()`, or `Query()`.
- Return generic error messages to clients and log details server-side.
- Avoid module-level side effects such as constructing settings, opening files, connecting to databases, or making network calls.

Do not expand this document into an auth implementation guide. Authentication and authorization choices belong to the generated project.
