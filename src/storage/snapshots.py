"""State snapshot helpers."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.events.models import Event
from src.events.stream import EventStream
from src.world.ai_audit import AIProposalAudit
from src.world.character import Character
from src.world.civilization import Civilization
from src.world.dynamic_structure import DynamicStructure
from src.world.faction import Faction
from src.world.frame import StructureTemplate
from src.world.pressure_thread import PressureThread
from src.world.project import ProjectNetwork
from src.world.presence import normalize_relic_state
from src.world.relation import Relation
from src.world.region import Region
from src.world.region_node import RegionNode
from src.world.relic import Relic
from src.world.state import WorldState
from src.world.supply import SupplyLine

DEFAULT_SNAPSHOT_PATH = Path("data/world_snapshot.json")


def snapshot_exists(path: Path = DEFAULT_SNAPSHOT_PATH) -> bool:
    """Return whether a snapshot file exists."""
    return path.exists()


def save_world_state(world: WorldState, path: Path = DEFAULT_SNAPSHOT_PATH) -> None:
    """Persist a world state to a JSON snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": world.seed,
        "current_tick": world.current_tick,
        "current_granularity": world.current_granularity,
        "civilizations": {key: asdict(value) for key, value in world.civilizations.items()},
        "regions": {key: asdict(value) for key, value in world.regions.items()},
        "characters": {key: asdict(value) for key, value in world.characters.items()},
        "factions": {key: asdict(value) for key, value in world.factions.items()},
        "relics": {key: asdict(value) for key, value in world.relics.items()},
        "projects": {key: asdict(value) for key, value in world.projects.items()},
        "supply_lines": {key: asdict(value) for key, value in world.supply_lines.items()},
        "region_nodes": {key: asdict(value) for key, value in world.region_nodes.items()},
        "dynamic_structures": {key: asdict(value) for key, value in world.dynamic_structures.items()},
        "ai_proposal_audits": {key: asdict(value) for key, value in world.ai_proposal_audits.items()},
        "pressure_threads": {key: asdict(value) for key, value in world.pressure_threads.items()},
        "relations": {key: asdict(value) for key, value in world.relations.items()},
        "event_stream": {
            "events": [asdict(event) for event in world.event_stream.events],
            "next_index": world.event_stream._next_index,
        },
        "active_event_ids": list(world.active_event_ids),
        "structure_template": asdict(world.structure_template),
        "world_tags": list(world.world_tags),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_world_state(path: Path = DEFAULT_SNAPSHOT_PATH) -> WorldState:
    """Load a world state from a JSON snapshot."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    world = WorldState(
        seed=int(payload["seed"]),
        current_tick=int(payload["current_tick"]),
        current_granularity=str(payload["current_granularity"]),
        active_event_ids=list(payload.get("active_event_ids", [])),
        structure_template=StructureTemplate(**payload.get("structure_template", {})),
        world_tags=list(payload.get("world_tags", [])),
    )
    world.civilizations = {
        key: Civilization(**value) for key, value in payload["civilizations"].items()
    }
    world.regions = {key: Region(**value) for key, value in payload["regions"].items()}
    world.characters = {
        key: Character(**value) for key, value in payload["characters"].items()
    }
    world.factions = {key: Faction(**value) for key, value in payload["factions"].items()}
    world.relics = {key: Relic(**value) for key, value in payload["relics"].items()}
    world.projects = {
        key: ProjectNetwork(**value) for key, value in payload.get("projects", {}).items()
    }
    world.supply_lines = {
        key: SupplyLine(**value) for key, value in payload.get("supply_lines", {}).items()
    }
    world.region_nodes = {
        key: RegionNode(**value) for key, value in payload.get("region_nodes", {}).items()
    }
    world.dynamic_structures = {
        key: DynamicStructure(**value) for key, value in payload.get("dynamic_structures", {}).items()
    }
    world.ai_proposal_audits = {
        key: AIProposalAudit(**value) for key, value in payload.get("ai_proposal_audits", {}).items()
    }
    world.pressure_threads = {
        key: PressureThread(**value) for key, value in payload.get("pressure_threads", {}).items()
    }
    for relic in world.relics.values():
        normalize_relic_state(relic)
    world.relations = {
        key: Relation(**value) for key, value in payload.get("relations", {}).items()
    }

    stream_payload = payload.get("event_stream", {})
    world.event_stream = EventStream(
        events=[Event(**event) for event in stream_payload.get("events", [])],
        _next_index=int(stream_payload.get("next_index", 1)),
    )
    return world
