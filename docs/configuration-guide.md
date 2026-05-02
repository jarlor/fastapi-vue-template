# Configuration Guide

This document exists for changes to configuration, environment variables, or logging.

## Sources

Configuration is loaded with Pydantic Settings V2.

Priority, highest first:

1. Environment variables
2. `.env`
3. `config.yaml`
4. Code defaults

Use `config.yaml` for non-sensitive defaults. Use `.env` or a secret manager for credentials, tokens, connection strings, and production overrides. Do not commit `.env`.

Nested environment variables use `__`:

```bash
SERVER__PORT=9000
LOGGING__LEVEL=DEBUG
```

## Default Sections

- `server`: host, port, reload
- `cors`: allowed origins, credentials, methods, headers
- `frontend`: base URL
- `logging`: level, directory, retention, rotation, compression

When adding a new config section:

1. Add a typed model in `src/app_name/config.py`.
2. Register it on `Settings`.
3. Add safe defaults to `config.yaml`.
4. Put sensitive values in `.env.example` as empty placeholders when developers need to know the key exists.
5. Add tests when parsing, defaults, or compatibility behavior matters.

## Logging

Use Loguru through the configured application logging setup.

```python
from loguru import logger

logger.info("Processed item {}", item_id)
logger.bind(request_id=request_id).warning("Slow request")
```

Request handlers can use the request context middleware helpers when they need a request id in logs.

Production projects should set `SERVER__RELOAD=false` and choose log retention/rotation that matches their infrastructure.
