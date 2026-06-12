"""Civilization model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Civilization:
    """Macro-level civilization state."""

    civ_id: str
    name: str
    origin_region_id: str
    status: str
    stage: str
    trajectory: list[str] = field(default_factory=list)
    governance_mode: str = "hybrid_governance"
    cohesion: str = "medium"
    cohesion_trend: str = "steady"
    expansion_pressure: str = "medium"
    expansion_trend: str = "steady"
    scarcity_pressure: str = "medium"
    scarcity_trend: str = "steady"
    tech_profile: list[str] = field(default_factory=list)
    belief_profile: list[str] = field(default_factory=list)
    military_posture: str = "guarded"
    legitimacy: str = "medium"
    legitimacy_trend: str = "steady"
    external_relations: dict[str, str] = field(default_factory=dict)
    key_regions: list[str] = field(default_factory=list)
    key_factions: list[str] = field(default_factory=list)
    key_characters: list[str] = field(default_factory=list)
    key_relics: list[str] = field(default_factory=list)
    key_projects: list[str] = field(default_factory=list)
    key_supply_lines: list[str] = field(default_factory=list)
    summary_tags: list[str] = field(default_factory=list)
    strategic_posture: str = "balanced_competition"
    strategic_memory: list[str] = field(default_factory=list)
    strategic_bias_trace: list[str] = field(default_factory=list)
    strategic_posture_pending: str = "none"
    strategic_posture_pending_hits: int = 0
    strategic_posture_stability: str = "forming"
