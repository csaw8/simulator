"""Semi-independent emergent presence model."""

from __future__ import annotations

from dataclasses import dataclass, field


ALLOWED_EMERGENT_PRESENCE_TYPES = {
    "spore_bloom",
    "migrant_swarm",
    "mycelial_mat",
    "feral_cluster",
    "signal_biota",
}

ALLOWED_EMERGENT_LIFECYCLE_STAGES = {
    "forming",
    "spreading",
    "nesting",
    "adapting",
    "retreating",
    "dormant",
}

ALLOWED_EMERGENT_STATUSES = {
    "active",
    "contained",
    "dormant",
    "cooling",
    "archived",
}

ALLOWED_EMERGENT_SCALES = {
    "trace",
    "cluster",
    "colony",
    "swarm",
    "regional",
}

ALLOWED_EMERGENT_MOBILITY = {
    "fixed",
    "local",
    "migrating",
    "distributed",
}


@dataclass(slots=True)
class EmergentPresence:
    """A bounded semi-independent ecological/anomalous presence."""

    presence_id: str
    presence_type: str
    name: str
    summary: str
    origin: str
    status: str = "active"
    visibility: str = "visible"
    home_region_ref: str | None = None
    current_region_refs: list[str] = field(default_factory=list)
    linked_relic_refs: list[str] = field(default_factory=list)
    linked_dynamic_refs: list[str] = field(default_factory=list)
    linked_faction_refs: list[str] = field(default_factory=list)
    lifecycle_stage: str = "forming"
    population_scale: str = "trace"
    adaptation_level: str = "low"
    mobility: str = "local"
    pressure: str = "medium"
    behavior_tags: list[str] = field(default_factory=list)
    sensory_tags: list[str] = field(default_factory=list)
    ecological_tags: list[str] = field(default_factory=list)
    created_tick: int = 0
    updated_tick: int = 0
    source_event_refs: list[str] = field(default_factory=list)
    influence_refs: list[str] = field(default_factory=list)
