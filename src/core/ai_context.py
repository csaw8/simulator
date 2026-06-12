"""Small, bounded AI context builders."""

from __future__ import annotations

from src.events.visibility_rules import format_event_summary_for_view
from src.narrative.names import format_entity_ref
from src.world.relations import relations_for_ref
from src.world.state import WorldState
from src.world.style_profile import get_world_style_profile, style_profile_to_dict


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
        "style_profile": style_profile_to_dict(get_world_style_profile(world.style_profile_id)),
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


def build_emergent_presence_context(
    world: WorldState,
    *,
    target_type: str,
    target_id: str,
    event_limit: int = 6,
) -> dict[str, object]:
    """Build a bounded context for emergent-presence proposals."""
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
            "pressure": structure.pressure,
        }
        for structure in world.dynamic_structures.values()
        if structure.status != "archived"
        and (target_id in structure.scope_refs or target_id in structure.linked_refs)
    ][:6]
    nearby_emergent = [
        {
            "presence_id": presence.presence_id,
            "presence_type": presence.presence_type,
            "name": presence.name,
            "summary": presence.summary,
            "status": presence.status,
            "home_region_ref": presence.home_region_ref,
            "current_region_refs": presence.current_region_refs,
            "linked_relic_refs": presence.linked_relic_refs,
            "linked_dynamic_refs": presence.linked_dynamic_refs,
            "linked_faction_refs": presence.linked_faction_refs,
            "pressure": presence.pressure,
        }
        for presence in world.emergent_presences.values()
        if presence.status != "archived"
        and target_id
        in (
            ([presence.home_region_ref] if presence.home_region_ref else [])
            + presence.current_region_refs
            + presence.linked_relic_refs
            + presence.linked_dynamic_refs
            + presence.linked_faction_refs
        )
    ][:6]
    signal_score = _emergent_presence_context_signal_from_parts(
        recent_events=recent_events,
        pressure_threads=pressure_threads,
        relations=relations,
        nearby_dynamic=nearby_dynamic,
    )
    return {
        "tick": world.current_tick,
        "target_type": target_type,
        "target_id": target_id,
        "target_label": format_entity_ref(world, target_id),
        "world_frame": world.structure_template.brief_signature(),
        "style_profile": style_profile_to_dict(get_world_style_profile(world.style_profile_id)),
        "proposal_signal_score": signal_score,
        "proposal_required": signal_score >= 5,
        "proposal_guidance": _emergent_proposal_guidance(signal_score),
        "recent_events": recent_events,
        "pressure_threads": pressure_threads,
        "relations": relations,
        "nearby_dynamic_structures": nearby_dynamic,
        "nearby_emergent_presences": nearby_emergent,
        "allowed_refs": _allowed_emergent_refs_for_context(
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


def emergent_presence_context_signal(context: dict[str, object]) -> int:
    """Estimate whether a target has enough signal for emergent-presence proposals."""
    if context.get("error"):
        return 0
    if "proposal_signal_score" in context:
        return int(context.get("proposal_signal_score", 0))
    return _emergent_presence_context_signal_from_parts(
        recent_events=list(context.get("recent_events", [])),
        pressure_threads=list(context.get("pressure_threads", [])),
        relations=list(context.get("relations", [])),
        nearby_dynamic=list(context.get("nearby_dynamic_structures", [])),
    )


def related_dynamic_structure_context_lines(
    world: WorldState,
    refs: list[str],
    *,
    view: str = "truth",
    limit: int = 4,
) -> list[str]:
    """Return compact, read-only dynamic-structure lines for AI context prompts."""
    ref_set = {ref for ref in refs if ref}
    if not ref_set:
        return ["- None"]
    player_view = view == "player"
    structures = [
        structure
        for structure in world.dynamic_structures.values()
        if structure.status != "archived"
        and ref_set.intersection(structure.scope_refs + structure.linked_refs + structure.influence_refs)
    ]
    if player_view:
        structures = [
            structure
            for structure in structures
            if structure.visibility in {"public", "visible", "rumored"}
        ]
    structures.sort(
        key=lambda structure: (
            _pressure_rank(structure.pressure),
            structure.updated_tick,
            structure.structure_id,
        ),
        reverse=True,
    )
    if not structures:
        return ["- None"]
    return [
        _dynamic_structure_context_line(world, structure, player_view=player_view)
        for structure in structures[: max(1, limit)]
    ]


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


def _emergent_presence_context_signal_from_parts(
    *,
    recent_events: list[dict[str, object]],
    pressure_threads: list[dict[str, object]],
    relations: list[dict[str, object]],
    nearby_dynamic: list[dict[str, object]],
) -> int:
    score = min(len(recent_events), 3)
    score += min(len(pressure_threads), 2)
    score += min(len(relations), 2)
    score += min(len(nearby_dynamic), 2)
    return score


def _dynamic_structure_context_line(world: WorldState, structure, *, player_view: bool) -> str:
    type_label = _dynamic_structure_type_label(structure.structure_type)
    pressure_label = _pressure_label(structure.pressure)
    ref_labels = [
        format_entity_ref(world, ref)
        for ref in (structure.scope_refs + structure.linked_refs)[:4]
    ]
    if player_view:
        return (
            f"- {type_label}; pressure={pressure_label}; "
            f"visible_refs={len(structure.scope_refs + structure.linked_refs)}; "
            f"clue={_compact_text(structure.summary, 80)}"
        )
    return (
        f"- {structure.name} ({structure.structure_id}); type={structure.structure_type}; "
        f"status={structure.status}; pressure={structure.pressure}; "
        f"refs={', '.join(ref_labels) or 'None'}; summary={_compact_text(structure.summary, 120)}"
    )


def _dynamic_structure_type_label(structure_type: str) -> str:
    mapping = {
        "local_group": "local group",
        "incident_site": "incident site",
        "rumor_network": "rumor network",
        "proxy_cell": "proxy cell",
        "anomaly_trace": "anomaly trace",
    }
    return mapping.get(structure_type, structure_type.replace("_", " "))


def _pressure_label(pressure: str) -> str:
    return {"high": "high", "medium": "medium", "low": "low"}.get(pressure, "unknown")


def _pressure_rank(pressure: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(pressure, 0)


def _compact_text(text: str, limit: int) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "..."


def _proposal_guidance(signal_score: int) -> str:
    if signal_score >= 5:
        return "strong_signal: prefer exactly one compact proposal if a plausible bounded structure can be named."
    if signal_score >= 3:
        return "medium_signal: propose one structure only if recent events imply a concrete local group, incident site, rumor network, proxy cell, or anomaly trace."
    return "weak_signal: return an empty proposals list unless the supplied context clearly names a concrete structure."


def _emergent_proposal_guidance(signal_score: int) -> str:
    if signal_score >= 5:
        return "strong_signal: prefer exactly one compact emergent-presence proposal if ecological or anomalous pressure is grounded by supplied context."
    if signal_score >= 3:
        return "medium_signal: propose one emergent presence only if recent events imply a concrete bounded ecological pressure."
    return "weak_signal: return an empty proposals list unless the supplied context clearly supports a bounded emergent presence."


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
        event.emergent_presence_refs,
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
        world.emergent_presences,
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


def _allowed_emergent_refs_for_context(
    world: WorldState,
    *,
    target_id: str,
    recent_events: list[dict[str, object]],
    relations: list[dict[str, object]],
    nearby_dynamic: list[dict[str, object]],
) -> dict[str, list[str]]:
    refs: dict[str, list[str]] = {
        "regions": [],
        "relics": [],
        "dynamic_structures": [],
        "factions": [],
        "emergent_presences": [],
    }

    def add_ref(ref: str) -> None:
        if ref in world.regions:
            _append_allowed_ref(refs["regions"], ref, limit=16)
        elif ref in world.relics:
            _append_allowed_ref(refs["relics"], ref, limit=12)
        elif ref in world.dynamic_structures:
            _append_allowed_ref(refs["dynamic_structures"], ref, limit=12)
        elif ref in world.factions:
            _append_allowed_ref(refs["factions"], ref, limit=12)
        elif ref in world.emergent_presences:
            _append_allowed_ref(refs["emergent_presences"], ref, limit=8)

    add_ref(target_id)
    for event in recent_events:
        for ref in event.get("refs", []):
            if isinstance(ref, str):
                add_ref(ref)
    for relation in relations:
        for key in ("source_ref", "target_ref"):
            ref = relation.get(key)
            if isinstance(ref, str):
                add_ref(ref)
    for structure in nearby_dynamic:
        structure_id = structure.get("structure_id")
        if isinstance(structure_id, str):
            add_ref(structure_id)
        for ref in structure.get("scope_refs", []) + structure.get("linked_refs", []):
            if isinstance(ref, str):
                add_ref(ref)

    for ref in list(world.regions)[:4]:
        add_ref(ref)
    for ref in list(world.relics)[:4]:
        add_ref(ref)
    for ref in list(world.dynamic_structures)[:4]:
        add_ref(ref)
    for ref in list(world.factions)[:4]:
        add_ref(ref)
    return refs


def _append_allowed_ref(refs: list[str], ref: str, *, limit: int) -> None:
    if ref and ref not in refs and len(refs) < limit:
        refs.append(ref)


def _target_exists(world: WorldState, target_id: str) -> bool:
    return target_id in set(_allowed_refs(world))
