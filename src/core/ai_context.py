"""Small, bounded AI context builders."""

from __future__ import annotations

from src.events.visibility_rules import format_event_summary_for_view
from src.narrative.names import format_entity_ref
from src.world.relations import relations_for_ref
from src.world.state import WorldState


def build_dynamic_structure_context(
    world: WorldState,
    *,
    target_type: str,
    target_id: str,
    event_limit: int = 8,
) -> dict[str, object]:
    """Build a bounded context for dynamic-structure proposals."""
    if not _target_exists(world, target_id):
        return {"error": f"unknown target: {target_type} {target_id}"}

    recent_events = [
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "summary": format_event_summary_for_view(event, view="truth", world=world),
            "refs": _event_ref_ids(event),
        }
        for event in world.event_stream.recent(80)
        if target_id in _event_ref_ids(event)
    ][-event_limit:]
    pressure_threads = [
        {
            "theme": thread.theme,
            "status": thread.status,
            "intensity": thread.intensity,
            "summary": thread.summary,
        }
        for thread in world.pressure_threads.values()
        if thread.scope_ref == target_id and thread.status != "dormant"
    ][:6]
    relations = [
        {
            "source_ref": relation.source_ref,
            "target_ref": relation.target_ref,
            "relation_type": relation.relation_type,
            "strength": relation.strength,
            "status": relation.status,
            "notes": relation.notes,
        }
        for relation in relations_for_ref(world, target_id, limit=8)
    ]
    nearby_dynamic = [
        {
            "structure_id": structure.structure_id,
            "structure_type": structure.structure_type,
            "name": structure.name,
            "summary": structure.summary,
            "scope_refs": structure.scope_refs,
            "linked_refs": structure.linked_refs,
        }
        for structure in world.dynamic_structures.values()
        if target_id in structure.scope_refs or target_id in structure.linked_refs
    ][:6]
    return {
        "tick": world.current_tick,
        "target_type": target_type,
        "target_id": target_id,
        "target_label": format_entity_ref(world, target_id),
        "world_frame": world.structure_template.brief_signature(),
        "allowed_refs": _allowed_refs(world),
        "recent_events": recent_events,
        "pressure_threads": pressure_threads,
        "relations": relations,
        "nearby_dynamic_structures": nearby_dynamic,
    }


def dynamic_structure_context_signal(context: dict[str, object]) -> int:
    """Estimate whether a target has enough signal for dynamic proposal generation."""
    if context.get("error"):
        return 0
    score = min(len(context.get("recent_events", [])), 4)
    score += min(len(context.get("pressure_threads", [])), 3)
    score += min(len(context.get("relations", [])), 2)
    return score


def _event_ref_ids(event) -> list[str]:
    refs: list[str] = []
    for group in (
        event.region_refs,
        event.civ_refs,
        event.actor_refs,
        event.faction_refs,
        event.relic_refs,
        event.project_refs,
        event.supply_refs,
        event.node_refs,
        event.dynamic_structure_refs,
    ):
        for ref in group:
            if ref not in refs:
                refs.append(ref)
    return refs


def _allowed_refs(world: WorldState) -> list[str]:
    refs: list[str] = []
    for collection in (
        world.regions,
        world.civilizations,
        world.factions,
        world.characters,
        world.relics,
        world.projects,
        world.supply_lines,
        world.region_nodes,
        world.dynamic_structures,
    ):
        refs.extend(collection.keys())
    return sorted(refs)


def _target_exists(world: WorldState, target_id: str) -> bool:
    return target_id in set(_allowed_refs(world))
