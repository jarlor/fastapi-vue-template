"""
Application configuration using Pydantic Settings V2.

Source priority (highest wins): environment variables -> .env -> config.yaml
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


# ---------------------------------------------------------------------------
# Nested config sections
# ---------------------------------------------------------------------------

class MongoConfig(BaseModel):
    url: str = "mongodb://localhost:27017"
    database: str = "app_name"
    min_pool_size: int = 5
    max_pool_size: int = 50


class OpenAIConfig(BaseModel):
    """Optional -- only needed when the project uses LLM features."""
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.0


class AuthConfig(BaseModel):
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


class CORSConfig(BaseModel):
    allow_origins: list[str] = ["http://localhost:5173"]
    allow_credentials: bool = True
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


class FrontendConfig(BaseModel):
    base_url: str = "http://localhost:5173"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    log_dir: str = "logs"


# ---------------------------------------------------------------------------
# YAML source
# ---------------------------------------------------------------------------

class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """Load non-secret configuration from a YAML file."""

    _yaml_path: Path = Path("config.yaml")

    def get_field_value(
        self, field: Any, field_name: str
    ) -> tuple[Any, str, bool]:
        data = self._load_yaml()
        value = data.get(field_name)
        return value, field_name, False

    def _load_yaml(self) -> dict[str, Any]:
        if self._yaml_path.exists():
            with open(self._yaml_path, "r") as fh:
                return yaml.safe_load(fh) or {}
        return {}

    def __call__(self) -> dict[str, Any]:
        return self._load_yaml()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """Root settings object merging env, dotenv, and YAML sources."""

    model_config = {
        "env_nested_delimiter": "__",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    app_name: str = "app_name"
    debug: bool = False

    mongo: MongoConfig = MongoConfig()
    openai: OpenAIConfig = OpenAIConfig()
    auth: AuthConfig = AuthConfig()
    cors: CORSConfig = CORSConfig()
    server: ServerConfig = ServerConfig()
    frontend: FrontendConfig = FrontendConfig()
    logging: LoggingConfig = LoggingConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            init_settings,
        )


# ---------------------------------------------------------------------------
# Lazy singleton
# ---------------------------------------------------------------------------

class _LazySettings:
    """Thread-safe, lazy proxy for the Settings singleton.

    Allows ``get_settings()`` to be called at import time without
    immediately reading env / files. The real Settings object is
    created on first attribute access.
    """

    def __init__(self) -> None:
        self._instance: Settings | None = None
        self._lock = threading.Lock()

    def _resolve(self) -> Settings:
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = Settings()
        return self._instance

    def __getattr__(self, name: str) -> Any:
        return getattr(self._resolve(), name)

    def initialize(self, **overrides: Any) -> Settings:
        """Force (re-)initialization with explicit overrides."""
        with self._lock:
            self._instance = Settings(**overrides)
        return self._instance


_lazy = _LazySettings()


def get_settings() -> Settings:
    """Return the application settings singleton."""
    return _lazy._resolve()  # noqa: SLF001
