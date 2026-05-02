# API Conventions

This document exists for changes that touch FastAPI routes, response models, or committed API contracts.

## Contract Gate

Committed contract artifacts:

- `contracts/openapi.json`
- `src/frontend/src/api/generated/openapi.ts`

Refresh after API changes:

```bash
uv run poe api-contracts-write
```

Check drift:

```bash
uv run poe api-contracts
```

The aggregate gate `uv run poe harness` runs the same drift check. Do not edit generated contract artifacts by hand.

## Default API Shape

- Versioned API prefix: `/api/v1`
- Root health endpoint: `/health`
- Versioned health endpoint: `/api/v1/health`
- Successful and error responses use the shared `APIResponse` envelope: `{ code, success, data, message }`.

Use context-owned routers for feature APIs and mount them under the versioned prefix. Keep route handlers thin; application services own business behavior.
