"""Event stream storage and iteration."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.events.models import Event


@dataclass(slots=True)
class EventStream:
    """In-memory structured event stream."""

    events: list[Event] = field(default_factory=list)
    _next_index: int = 1

    def new_event_id(self) -> str:
        """Return a unique event identifier."""
        event_id = f"event_{self._next_index:05d}"
        self._next_index += 1
        return event_id

    def append(self, event: Event) -> None:
        """Append an event to the stream."""
        self.events.append(event)

    def extend(self, events: list[Event]) -> None:
        """Append multiple events to the stream."""
        self.events.extend(events)

    def recent(self, limit: int = 10) -> list[Event]:
        """Return the most recent events."""
        return self.events[-limit:]
