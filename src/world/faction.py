"""Faction model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Faction:
    """Faction or organization state."""

    faction_id: str
    name: str
    faction_type: str
    parent_civ_id: str | None
    power_scope: str
    influence: str = "medium"
    influence_trend: str = "steady"
    cohesion: str = "medium"
    doctrine_tags: list[str] = field(default_factory=list)
    operational_style: str = "adaptive_network"
    operational_style_stability: str = "forming"
    operational_style_pending: str = "none"
    operational_style_pending_hits: int = 0
    operational_style_memory: list[str] = field(default_factory=list)
    operational_style_trace: list[str] = field(default_factory=list)
    strategic_objective: str = ""
    strategic_objective_target_ref: str = "none"
    strategic_objective_status: str = "forming"
    strategic_objective_blockers: list[str] = field(default_factory=list)
    strategic_objective_recent_result: str = ""
    controlled_regions: list[str] = field(default_factory=list)
    key_characters: list[str] = field(default_factory=list)
    rival_factions: list[str] = field(default_factory=list)
    allied_factions: list[str] = field(default_factory=list)
