"""Supply line model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SupplyLine:
    """A lightweight cross-region supply corridor."""

    supply_id: str
    name: str
    origin_region_id: str
    destination_region_id: str
    status: str
    pressure: str = "medium"
    controlling_faction_ref: str | None = None
    linked_civ_refs: list[str] = field(default_factory=list)
    front_tags: list[str] = field(default_factory=list)
    recent_notes: list[str] = field(default_factory=list)
    corridor_state: str = "forming"
    corridor_summary: str = ""
    corridor_blockers: list[str] = field(default_factory=list)
