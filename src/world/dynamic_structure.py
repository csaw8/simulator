"""AI-proposed dynamic structure model."""

from __future__ import annotations

from dataclasses import dataclass, field


ALLOWED_DYNAMIC_STRUCTURE_TYPES = {
    "local_group",
    "incident_site",
    "rumor_network",
    "proxy_cell",
    "anomaly_trace",
}


@dataclass(slots=True)
class DynamicStructure:
    """A bounded, AI-proposable structure that sits beside fixed world objects."""

    structure_id: str
    structure_type: str
    name: str
    summary: str
    origin: str
    status: str = "active"
    visibility: str = "visible"
    scope_refs: list[str] = field(default_factory=list)
    linked_refs: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    pressure: str = "medium"
    created_tick: int = 0
    updated_tick: int = 0
    source_event_refs: list[str] = field(default_factory=list)
    influence_refs: list[str] = field(default_factory=list)
