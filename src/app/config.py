"""Typed application settings.

Precedence is explicit init values, environment variables, ``.env``, then
non-secret defaults from ``config.yaml``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


class CORSConfig(BaseModel):
    allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    allow_credentials: bool = True
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8665
    reload: bool = True


class FrontendConfig(BaseModel):
    base_url: str = "http://localhost:5173"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    log_dir: str = "logs"
    retention_days: int = 30
    error_retention_days: int = 90
    rotation: str = "00:00"
    compression: str = "gz"


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """Load non-secret defaults from the repository-owned YAML file."""

    yaml_path = Path("config.yaml")

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        value = self._load().get(field_name)
        return value, field_name, False

    def __call__(self) -> dict[str, Any]:
        return self._load()

    def _load(self) -> dict[str, Any]:
        if not self.yaml_path.exists():
            return {}
        with self.yaml_path.open(encoding="utf-8") as file:
            return yaml.safe_load(file) or {}


class Settings(BaseSettings):
    """Root settings object. Secrets belong in environment variables."""

    model_config = {
        "env_nested_delimiter": "__",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    app_name: str = "FastAPI Vue App"
    debug: bool = False
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
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one lazily constructed settings object per process."""
    return Settings()
