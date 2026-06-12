"""Region model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Region:
    """Region-level state and pressures."""

    region_id: str
    name: str
    civ_id: str | None
    region_type: str
    connectivity: str = "medium"
    security: str = "medium"
    security_trend: str = "steady"
    prosperity: str = "medium"
    prosperity_trend: str = "steady"
    scarcity: str = "medium"
    scarcity_trend: str = "steady"
    infrastructure: str = "medium"
    infrastructure_trend: str = "steady"
    tech_density: str = "medium"
    ecological_stress: str = "medium"
    ecological_stress_trend: str = "steady"
    political_tension: str = "medium"
    political_tension_trend: str = "steady"
    belief_temperature: str = "medium"
    population_profile: list[str] = field(default_factory=list)
    strategic_value: str = "medium"
    active_factions: list[str] = field(default_factory=list)
    active_characters: list[str] = field(default_factory=list)
    resident_relics: list[str] = field(default_factory=list)
    local_story_hooks: list[str] = field(default_factory=list)
