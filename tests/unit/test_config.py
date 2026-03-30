"""Tests for settings normalization and compatibility helpers."""

from __future__ import annotations

from app_name.config import Settings


class TestSettingsCompatibility:
    def test_accepts_legacy_cors_origins_key(self) -> None:
        settings = Settings(cors={"origins": ["http://localhost:8006"]})

        assert settings.cors.allow_origins == ["http://localhost:8006"]

    def test_accepts_legacy_frontend_host_and_dev_port(self) -> None:
        settings = Settings(frontend={"host": "0.0.0.0", "dev_port": 8006})

        assert settings.frontend.base_url == "http://localhost:8006"
