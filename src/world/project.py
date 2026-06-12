"""Project network model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ProjectNetwork:
    """Mid-layer project structure for live engineering and control fronts."""

    project_id: str
    name: str
    project_type: str
    status: str
    pressure: str = "medium"
    sponsor_refs: list[str] = field(default_factory=list)
    contractor_refs: list[str] = field(default_factory=list)
    financier_refs: list[str] = field(default_factory=list)
    opposition_refs: list[str] = field(default_factory=list)
    linked_regions: list[str] = field(default_factory=list)
    linked_presence_refs: list[str] = field(default_factory=list)
    linked_factions: list[str] = field(default_factory=list)
    linked_civs: list[str] = field(default_factory=list)
    linked_characters: list[str] = field(default_factory=list)
    front_tags: list[str] = field(default_factory=list)
    recent_notes: list[str] = field(default_factory=list)
    progress_state: str = "forming"
    progress_summary: str = ""
    progress_blockers: list[str] = field(default_factory=list)
