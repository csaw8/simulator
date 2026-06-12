"""Region node model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RegionNode:
    """A concrete facility or control point inside a region."""

    node_id: str
    name: str
    node_type: str
    region_id: str
    linked_project_id: str | None = None
    linked_supply_id: str | None = None
    linked_relic_id: str | None = None
    controller_ref: str | None = None
    contention_state: str = "forming"
    pressure: str = "medium"
    visibility: str = "public"
    tags: list[str] = field(default_factory=list)
    recent_notes: list[str] = field(default_factory=list)
    state_summary: str = ""
    blockers: list[str] = field(default_factory=list)
