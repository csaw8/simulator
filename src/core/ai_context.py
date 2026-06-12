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
    event_limit: int = 6,
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
        if structure.status != "archived"
        and (target_id in structure.scope_refs or target_id in structure.linked_refs)
    ][:6]
    signal_score = _dynamic_structure_context_signal_from_parts(
        recent_events=recent_events,
        pressure_threads=pressure_threads,
        relations=relations,
    )
    return {
        "tick": world.current_tick,
        "target_type": target_type,
        "target_id": target_id,
        "target_label": format_entity_ref(world, target_id),
        "world_frame": world.structure_template.brief_signature(),
        "proposal_signal_score": signal_score,
        "proposal_required": signal_score >= 5,
        "proposal_guidance": _proposal_guidance(signal_score),
        "recent_events": recent_events,
        "pressure_threads": pressure_threads,
        "relations": relations,
        "nearby_dynamic_structures": nearby_dynamic,
        "allowed_refs": _allowed_refs_for_context(
            world,
            target_id=target_id,
            recent_events=recent_events,
            relations=relations,
            nearby_dynamic=nearby_dynamic,
        ),
    }


def dynamic_structure_context_signal(context: dict[str, object]) -> int:
    """Estimate whether a target has enough signal for dynamic proposal generation."""
    if context.get("error"):
        return 0
    if "proposal_signal_score" in context:
        return int(context.get("proposal_signal_score", 0))
    return _dynamic_structure_context_signal_from_parts(
        recent_events=list(context.get("recent_events", [])),
        pressure_threads=list(context.get("pressure_threads", [])),
        relations=list(context.get("relations", [])),
    )


def _dynamic_structure_context_signal_from_parts(
    *,
    recent_events: list[dict[str, object]],
    pressure_threads: list[dict[str, object]],
    relations: list[dict[str, object]],
) -> int:
    score = min(len(recent_events), 4)
    score += min(len(pressure_threads), 3)
    score += min(len(relations), 2)
    return score


def _proposal_guidance(signal_score: int) -> str:
    if signal_score >= 5:
        return "strong_signal: prefer exactly one compact proposal if a plausible bounded structure can be named."
    if signal_score >= 3:
        return "medium_signal: propose one structure only if recent events imply a concrete local group, incident site, rumor network, proxy cell, or anomaly trace."
    return "weak_signal: return an empty proposals list unless the supplied context clearly names a concrete structure."


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


def _allowed_refs_for_context(
    world: WorldState,
    *,
    target_id: str,
    recent_events: list[dict[str, object]],
    relations: list[dict[str, object]],
    nearby_dynamic: list[dict[str, object]],
) -> list[str]:
    refs = [target_id]
    for event in recent_events:
        for ref in event.get("refs", []):
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    for relation in relations:
        for key in ("source_ref", "target_ref"):
            ref = relation.get(key)
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    for structure in nearby_dynamic:
        for ref in structure.get("scope_refs", []) + structure.get("linked_refs", []):
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
        structure_id = structure.get("structure_id")
        if isinstance(structure_id, str) and structure_id not in refs:
            refs.append(structure_id)

    # Keep a small fallback pool so AI can still attach proposals when the target has few events.
    fallback_refs = (
        list(world.regions)[:4]
        + list(world.factions)[:6]
        + list(world.relics)[:4]
        + list(world.projects)[:3]
        + list(world.supply_lines)[:3]
        + list(world.region_nodes)[:4]
    )
    for ref in fallback_refs:
        if ref not in refs:
            refs.append(ref)
        if len(refs) >= 32:
            break
    return refs[:32]


def _target_exists(world: WorldState, target_id: str) -> bool:
    return target_id in set(_allowed_refs(world))
