"""Character model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Character:
    """Character state used by scheduler and resolver."""

    char_id: str
    name: str
    character_level: str
    current_region_id: str
    affiliation: list[str] = field(default_factory=list)
    role_tags: list[str] = field(default_factory=list)
    capability_tags: list[str] = field(default_factory=list)
    desire_tags: list[str] = field(default_factory=list)
    fear_tags: list[str] = field(default_factory=list)
    loyalty_map: dict[str, str] = field(default_factory=dict)
    relationship_refs: list[str] = field(default_factory=list)
    status: str = "active"
    notoriety: str = "low"
    initiative: str = "medium"
    memory_summary: str = ""
    recent_goal: str = ""
    last_intent: dict[str, object] = field(default_factory=dict)
    active_goal_summary: str = ""
    active_goal_target_ref: str = "none"
    active_goal_status: str = "forming"
    active_goal_blockers: list[str] = field(default_factory=list)
    active_goal_recent_result: str = ""
    frontier_history: list[str] = field(default_factory=list)
    frontier_theme: str = "none"
    frontier_theme_trace: list[str] = field(default_factory=list)
    frontier_theme_strength: str = "none"
    frontier_theme_shift: str = "steady"
    frontier_previous_theme: str = "none"
    frontier_focus_ref: str = "none"
    frontier_focus_type: str = "none"
    frontier_focus_shift: str = "steady"
    frontier_focus_trace: list[str] = field(default_factory=list)
    frontier_focus_reason: str = "none"
    wake_priority_seed: int = 0
    observation_trace: int = 0
    agency_mode: str = "reactive"
