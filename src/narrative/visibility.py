"""Visibility policies for observer-facing outputs."""

from __future__ import annotations

PLAYER_VIEW = "player"
TRUTH_VIEW = "truth"
SUPPORTED_VIEWS = {PLAYER_VIEW, TRUTH_VIEW}


def normalize_view(raw_view: str | None, *, default: str = TRUTH_VIEW) -> str:
    """Normalize a raw view token to a supported view."""
    if raw_view is None:
        return default
    lowered = raw_view.strip().lower()
    if lowered in SUPPORTED_VIEWS:
        return lowered
    return default


def is_player_view(view: str) -> bool:
    """Return True when the current output should be redacted for player observation."""
    return normalize_view(view) == PLAYER_VIEW
