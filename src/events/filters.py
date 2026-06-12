"""Event filtering and priority selection."""

from __future__ import annotations

from src.events.models import Event


def select_chronicle_events(events: list[Event], limit: int = 5) -> list[Event]:
    """Select a small set of events worth turning into a chronicle note."""
    if not events:
        return []

    def score(event: Event) -> tuple[int, int]:
        scope_score = {
            "civilization": 3,
            "character": 2,
            "region": 1,
        }.get(event.event_scope, 0)
        severity_score = {
            "high": 3,
            "medium": 2,
            "low": 1,
        }.get(event.severity, 1)
        return (scope_score + severity_score, event.tick)

    ranked = sorted(events, key=score, reverse=True)
    return ranked[:limit]
