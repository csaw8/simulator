"""Relic model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Relic:
    """Narratively important non-character object."""

    relic_id: str
    name: str
    relic_type: str
    current_region_id: str
    holder_ref: str
    significance: str = "high"
    danger: str = "medium"
    activation_state: str = "dormant"
    origin_mode: str = "legacy"
    construction_state: str = "unknown"
    sponsor_ref: str | None = None
    contractor_ref: str | None = None
    financier_ref: str | None = None
    opposition_ref: str | None = None
    story_tags: list[str] = field(default_factory=list)
    linked_events: list[str] = field(default_factory=list)
    contest_state: str = "forming"
    contest_summary: str = ""
    contesting_refs: list[str] = field(default_factory=list)
