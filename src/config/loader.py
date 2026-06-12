"""Configuration loading helpers."""

from __future__ import annotations

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.config.models import AIConfig, AppConfig, WorldConfig


def load_default_app_config() -> AppConfig:
    """Build typed config objects from in-repo defaults."""
    return AppConfig(
        world=WorldConfig(**DEFAULT_WORLD_CONFIG),
        ai=AIConfig(**DEFAULT_AI_CONFIG),
    )
