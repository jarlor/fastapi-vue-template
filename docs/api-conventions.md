# API Conventions

## URL Structure

```
/api/{scope}/v1/{context}/{resource}
```

| Segment | Values | Description |
|---------|--------|-------------|
| `scope` | `public`, `internal` | `public` = no auth required; `internal` = bearer token required |
| `v1` | Version prefix | Increment for breaking changes |
| `context` | Bounded context name | e.g., `auth`, `models`, `pipeline` |
| `resource` | Plural noun | e.g., `users`, `tokens`, `tasks` |

Examples:
- `GET /api/public/v1/models/` -- list models (no auth)
- `POST /api/internal/v1/pipeline/tasks` -- create task (auth required)

## HTTP Methods

| Method | Purpose | Idempotent | Request Body |
|--------|---------|------------|--------------|
| GET | Read resource(s) | Yes | No |
| POST | Create resource or trigger action | No | Yes |
| PATCH | Partial update | Yes | Yes (partial) |
| DELETE | Remove resource | Yes | No |

Use POST for actions that do not map to CRUD (e.g., `POST /api/internal/v1/pipeline/run`).

## Status Codes

| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Successful GET, PATCH, or action POST |
| 201 | Created | Successful resource creation POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Malformed request syntax |
| 401 | Unauthorized | Missing or invalid auth token |
| 403 | Forbidden | Valid token but insufficient permissions |
| 404 | Not Found | Resource does not exist |
| 422 | Validation Error | Request body fails Pydantic validation |
| 500 | Internal Server Error | Unhandled server error |

## Response Format

### Success (single resource)

```json
{
  "data": { "id": "abc123", "name": "Example" },
  "message": "OK"
}
```

### Success (paginated list)

```json
{
  "data": [
    { "id": "abc123", "name": "Example" }
  ],
  "total": 100,
  "page": 1,
  "limit": 20
}
```

### Error

```json
{
  "detail": "Resource not found"
}
```

For validation errors (422), FastAPI returns its default format:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Authentication

- Primary: `Authorization: Bearer <token>` header.
- WebSocket fallback: `?token=<token>` query parameter (headers cannot be set on WebSocket connections from browsers).
- Tokens are opaque strings. The server validates them on every request.

## Pagination

Query parameters:

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `page` | int | 1 | -- | 1-based page number |
| `limit` | int | 20 | 100 | Items per page |

The response includes `total`, `page`, and `limit` fields alongside `data`.

## Filtering

Use query parameters matching field names:

```
GET /api/public/v1/models?status=approved&category=nlp
```

For date ranges, use `_from` and `_to` suffixes:

```
GET /api/internal/v1/pipeline/tasks?created_from=2024-01-01&created_to=2024-01-31
```

## Sorting

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sort_by` | string | `created_at` | Field name to sort by |
| `sort_order` | string | `desc` | `asc` or `desc` |

```
GET /api/public/v1/models?sort_by=name&sort_order=asc
```

## Versioning

Version is embedded in the URL path: `/v1`, `/v2`, etc. Increment the version only for breaking changes. Non-breaking additions (new optional fields, new endpoints) do not require a version bump.

## Router Organization

Each bounded context provides its own `FastAPI APIRouter`. Routers are mounted in the application factory:

```python
# Public routes (no auth)
app.include_router(models_public_router, prefix="/api/public/v1/models", tags=["models"])

# Internal routes (auth required)
app.include_router(pipeline_internal_router, prefix="/api/internal/v1/pipeline", tags=["pipeline"])
```

## Route Definition Rules

### Static routes before catch-alls

Static routes must be defined before parameterized `/{id}` routes to prevent shadowing:

```python
# Correct order
@router.get("/stats")
async def get_stats(): ...

@router.get("/{model_id}")
async def get_model(model_id: str): ...
```

### No trailing slashes

Do not include trailing slashes in route definitions. Trailing slashes cause 307 redirects that break some proxy configurations and API clients.

```python
# Correct
@router.get("/models")

# Wrong
@router.get("/models/")
```
