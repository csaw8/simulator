"""Dynamic relationship model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Relation:
    """A lightweight dynamic relationship between two world entities."""

    relation_id: str
    source_ref: str
    target_ref: str
    relation_type: str
    strength: str = "medium"
    status: str = "active"
    updated_tick: int = 0
    last_event_id: str = ""
    notes: str = ""
    tags: list[str] = field(default_factory=list)
