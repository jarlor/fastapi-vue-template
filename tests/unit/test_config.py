"""Tests for explicit settings precedence and caching."""

from __future__ import annotations

from app.config import Settings, get_settings


def test_explicit_nested_settings_are_typed() -> None:
    settings = Settings(cors={"allow_origins": ["https://example.com"]})

    assert settings.cors.allow_origins == ["https://example.com"]


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()

    assert get_settings() is get_settings()

    get_settings.cache_clear()
