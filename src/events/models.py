"""Event data structures."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Event:
    """A structured world event."""

    event_id: str
    tick: int
    time_granularity: str
    event_type: str
    event_scope: str
    title: str
    summary: str
    region_refs: list[str] = field(default_factory=list)
    civ_refs: list[str] = field(default_factory=list)
    actor_refs: list[str] = field(default_factory=list)
    faction_refs: list[str] = field(default_factory=list)
    relic_refs: list[str] = field(default_factory=list)
    project_refs: list[str] = field(default_factory=list)
    supply_refs: list[str] = field(default_factory=list)
    node_refs: list[str] = field(default_factory=list)
    cause_tags: list[str] = field(default_factory=list)
    result_tags: list[str] = field(default_factory=list)
    severity: str = "medium"
    novelty: str = "low"
    consequence_score: str = "medium"
    narrative_priority: str = "low"
    visibility: str = "visible"
