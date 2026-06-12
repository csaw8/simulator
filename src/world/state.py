"""Aggregated world state."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.world.ai_audit import AIProposalAudit
from src.world.character import Character
from src.world.civilization import Civilization
from src.events.stream import EventStream
from src.world.faction import Faction
from src.world.frame import StructureTemplate
from src.world.dynamic_structure import DynamicStructure
from src.world.pressure_thread import PressureThread
from src.world.project import ProjectNetwork
from src.world.relation import Relation
from src.world.region import Region
from src.world.region_node import RegionNode
from src.world.relic import Relic
from src.world.supply import SupplyLine


@dataclass(slots=True)
class WorldState:
    """Top-level in-memory state container for the world."""

    seed: int
    current_tick: int = 0
    current_granularity: str = "week"
    civilizations: dict[str, Civilization] = field(default_factory=dict)
    regions: dict[str, Region] = field(default_factory=dict)
    characters: dict[str, Character] = field(default_factory=dict)
    factions: dict[str, Faction] = field(default_factory=dict)
    relics: dict[str, Relic] = field(default_factory=dict)
    projects: dict[str, ProjectNetwork] = field(default_factory=dict)
    supply_lines: dict[str, SupplyLine] = field(default_factory=dict)
    region_nodes: dict[str, RegionNode] = field(default_factory=dict)
    dynamic_structures: dict[str, DynamicStructure] = field(default_factory=dict)
    ai_proposal_audits: dict[str, AIProposalAudit] = field(default_factory=dict)
    pressure_threads: dict[str, PressureThread] = field(default_factory=dict)
    relations: dict[str, Relation] = field(default_factory=dict)
    event_stream: EventStream = field(default_factory=EventStream)
    active_event_ids: list[str] = field(default_factory=list)
    structure_template: StructureTemplate = field(default_factory=StructureTemplate)
    world_tags: list[str] = field(
        default_factory=lambda: ["realistic_future_tech", "text_first"]
    )

    def summary(self) -> dict[str, int | str]:
        """Return a compact summary of current world contents."""
        protagonist_count = sum(
            1 for char in self.characters.values() if char.character_level == "L3"
        )
        active_character_count = sum(
            1 for char in self.characters.values() if char.character_level == "L2"
        )
        return {
            "seed": self.seed,
            "tick": self.current_tick,
            "granularity": self.current_granularity,
            "civilizations": len(self.civilizations),
            "regions": len(self.regions),
            "factions": len(self.factions),
            "characters": len(self.characters),
            "protagonists": protagonist_count,
            "active_characters": active_character_count,
            "relics": len(self.relics),
            "projects": len(self.projects),
            "supply_lines": len(self.supply_lines),
            "region_nodes": len(self.region_nodes),
            "dynamic_structures": len(self.dynamic_structures),
            "ai_proposal_audits": len(self.ai_proposal_audits),
            "pressure_threads": len(self.pressure_threads),
            "relations": len(self.relations),
            "events": len(self.event_stream.events),
            "world_frame": self.structure_template.brief_signature(),
        }
