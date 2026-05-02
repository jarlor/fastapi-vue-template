# Frontend Standards

This document exists for changes under `src/frontend`.

## Enforced Baseline

Run:

```bash
uv run poe frontend-harness
```

The aggregate gate `uv run poe harness` runs the same check.

The template default enforces only one frontend source rule: HTTP clients (`axios`, `fetch`, `EventSource`, `XMLHttpRequest`) are used through `src/frontend/src/api`.

Browser streaming must not use Axios `responseType: "stream"`. For POST streaming or SSE-like responses, use `fetch` with `ReadableStream` inside `src/frontend/src/api`. For GET SSE, `EventSource` is allowed inside the API layer.

Everything else in frontend structure and component style is advisory. Generated projects may adopt stricter rules when they own that product decision.

## API Contracts

Generated OpenAPI types live in `src/frontend/src/api/generated/`. Do not edit them by hand. Refresh them with:

```bash
uv run poe api-contracts-write
```

Frontend API wrappers should live under `src/frontend/src/api` and use generated schema types when available.
