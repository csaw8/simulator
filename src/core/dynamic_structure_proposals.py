"""Validated proposal flow for dynamic structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.events.models import Event
from src.events.visibility_rules import normalize_event_visibility
from src.world.dynamic_structure import (
    ALLOWED_DYNAMIC_STRUCTURE_TYPES,
    DynamicStructure,
)
from src.world.pressure_thread import PressureThread
from src.world.relations import upsert_relation
from src.world.state import WorldState

ALLOWED_DYNAMIC_ACTIONS = {"create", "update"}
ALLOWED_DYNAMIC_PRESSURES = {"low", "medium", "high"}
ALLOWED_DYNAMIC_RELATIONS = {
    "observes",
    "pressures",
    "disrupts",
    "screens",
    "proxy_for",
    "rumor_source_for",
    "trace_of",
    "attached_to",
}
MAX_PROPOSALS_PER_BATCH = 3
MAX_REFS_PER_PROPOSAL = 8
MAX_TAGS_PER_PROPOSAL = 8


@dataclass(slots=True)
class DynamicProposalResult:
    """Result of validating and applying a batch of dynamic-structure proposals."""

    accepted: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)


def apply_dynamic_structure_proposals(
    world: WorldState,
    payload: dict[str, Any],
    *,
    origin: str = "ai_proposal",
) -> DynamicProposalResult:
    """Validate and apply a bounded batch of dynamic-structure proposals."""
    result = DynamicProposalResult()
    proposals = payload.get("proposals", [])
    if not isinstance(proposals, list):
        result.rejected.append("payload.proposals must be a list")
        return result

    for index, raw_proposal in enumerate(proposals[:MAX_PROPOSALS_PER_BATCH]):
        if not isinstance(raw_proposal, dict):
            result.rejected.append(f"proposal[{index}] must be an object")
            continue
        error = _validate_dynamic_structure_proposal(world, raw_proposal)
        if error:
            result.rejected.append(f"proposal[{index}]: {error}")
            continue
        structure, event = _apply_one_dynamic_structure_proposal(
            world,
            raw_proposal,
            origin=origin,
        )
        result.accepted.append(structure.structure_id)
        result.events.append(event)
    return result


def validate_dynamic_structure_proposals(
    world: WorldState,
    payload: dict[str, Any],
) -> DynamicProposalResult:
    """Validate a proposal batch without mutating world state."""
    result = DynamicProposalResult()
    proposals = payload.get("proposals", [])
    if not isinstance(proposals, list):
        result.rejected.append("payload.proposals must be a list")
        return result
    for index, raw_proposal in enumerate(proposals[:MAX_PROPOSALS_PER_BATCH]):
        if not isinstance(raw_proposal, dict):
            result.rejected.append(f"proposal[{index}] must be an object")
            continue
        error = _validate_dynamic_structure_proposal(world, raw_proposal)
        if error:
            result.rejected.append(f"proposal[{index}]: {error}")
            continue
        result.accepted.append(f"proposal[{index}]")
    return result


def _validate_dynamic_structure_proposal(world: WorldState, proposal: dict[str, Any]) -> str | None:
    action = str(proposal.get("action", "create")).strip().lower()
    if action not in ALLOWED_DYNAMIC_ACTIONS:
        return f"unsupported action {action!r}"

    structure_type = str(proposal.get("structure_type", "")).strip().lower()
    if structure_type not in ALLOWED_DYNAMIC_STRUCTURE_TYPES:
        return f"unsupported structure_type {structure_type!r}"

    name = _clean_text(proposal.get("name", ""), limit=80)
    summary = _clean_text(proposal.get("summary", ""), limit=240)
    if not name:
        return "name is required"
    if not summary:
        return "summary is required"

    if action == "update":
        structure_id = str(proposal.get("structure_id", "")).strip()
        if structure_id not in world.dynamic_structures:
            return "update requires an existing structure_id"

    pressure = str(proposal.get("pressure", "medium")).strip().lower()
    if pressure not in ALLOWED_DYNAMIC_PRESSURES:
        return f"unsupported pressure {pressure!r}"

    visibility = normalize_event_visibility(str(proposal.get("visibility", "visible")))
    if not visibility:
        return "invalid visibility"

    scope_refs = _clean_ref_list(proposal.get("scope_refs", []), limit=MAX_REFS_PER_PROPOSAL)
    linked_refs = _clean_ref_list(proposal.get("linked_refs", []), limit=MAX_REFS_PER_PROPOSAL)
    if not scope_refs and not linked_refs:
        return "at least one scope_refs or linked_refs item is required"
    for ref in scope_refs + linked_refs:
        if not _ref_exists(world, ref):
            return f"unknown ref {ref!r}"

    relation_type = str(proposal.get("relation_type", "attached_to")).strip().lower()
    if relation_type not in ALLOWED_DYNAMIC_RELATIONS:
        return f"unsupported relation_type {relation_type!r}"
    return None


def _apply_one_dynamic_structure_proposal(
    world: WorldState,
    proposal: dict[str, Any],
    *,
    origin: str,
) -> tuple[DynamicStructure, Event]:
    action = str(proposal.get("action", "create")).strip().lower()
    structure_id = (
        str(proposal.get("structure_id", "")).strip()
        if action == "update"
        else _new_dynamic_structure_id(world)
    )
    structure = world.dynamic_structures.get(structure_id)
    created = structure is None
    if structure is None:
        structure = DynamicStructure(
            structure_id=structure_id,
            structure_type=str(proposal["structure_type"]).strip().lower(),
            name=_clean_text(proposal["name"], limit=80),
            summary=_clean_text(proposal["summary"], limit=240),
            origin=origin,
            created_tick=world.current_tick,
        )
        world.dynamic_structures[structure_id] = structure

    structure.structure_type = str(proposal["structure_type"]).strip().lower()
    structure.name = _clean_text(proposal["name"], limit=80)
    structure.summary = _clean_text(proposal["summary"], limit=240)
    structure.status = str(proposal.get("status", "active")).strip().lower() or "active"
    structure.visibility = normalize_event_visibility(str(proposal.get("visibility", "visible")))
    structure.scope_refs = _clean_ref_list(proposal.get("scope_refs", []), limit=MAX_REFS_PER_PROPOSAL)
    structure.linked_refs = _clean_ref_list(proposal.get("linked_refs", []), limit=MAX_REFS_PER_PROPOSAL)
    structure.tags = _clean_tag_list(proposal.get("tags", []), limit=MAX_TAGS_PER_PROPOSAL)
    structure.pressure = str(proposal.get("pressure", "medium")).strip().lower()
    structure.updated_tick = world.current_tick

    event = _build_dynamic_structure_event(world, structure, created=created)
    world.event_stream.append(event)
    world.active_event_ids = [event.event_id]
    _append_unique(structure.source_event_refs, event.event_id, limit=8)

    relation_type = str(proposal.get("relation_type", "attached_to")).strip().lower()
    for target_ref in structure.scope_refs + structure.linked_refs:
        upsert_relation(
            world,
            source_ref=structure.structure_id,
            target_ref=target_ref,
            relation_type=relation_type,
            event=event,
            strength=structure.pressure,
            notes=f"dynamic_structure:{structure.structure_type}",
            tags=["dynamic_structure", structure.structure_type] + structure.tags[:4],
        )
        _append_unique(structure.influence_refs, target_ref, limit=12)
    _refresh_dynamic_structure_pressure_threads(world, structure, event)
    return structure, event


def _build_dynamic_structure_event(
    world: WorldState,
    structure: DynamicStructure,
    *,
    created: bool,
) -> Event:
    event_type = "dynamic_structure_created" if created else "dynamic_structure_updated"
    event_id = world.event_stream.new_event_id()
    return Event(
        event_id=event_id,
        tick=world.current_tick,
        time_granularity=world.current_granularity,
        event_type=event_type,
        event_scope="dynamic_structure",
        title=structure.name,
        summary=f"{structure.name}: {structure.summary}",
        region_refs=[ref for ref in structure.scope_refs + structure.linked_refs if ref in world.regions],
        civ_refs=[ref for ref in structure.scope_refs + structure.linked_refs if ref in world.civilizations],
        faction_refs=[ref for ref in structure.scope_refs + structure.linked_refs if ref in world.factions],
        relic_refs=[ref for ref in structure.scope_refs + structure.linked_refs if ref in world.relics],
        project_refs=[ref for ref in structure.scope_refs + structure.linked_refs if ref in world.projects],
        supply_refs=[ref for ref in structure.scope_refs + structure.linked_refs if ref in world.supply_lines],
        node_refs=[ref for ref in structure.scope_refs + structure.linked_refs if ref in world.region_nodes],
        dynamic_structure_refs=[structure.structure_id],
        cause_tags=["dynamic_structure", structure.structure_type],
        result_tags=structure.tags[:6],
        severity=structure.pressure,
        novelty="medium" if created else "low",
        consequence_score=structure.pressure,
        narrative_priority="medium",
        visibility=structure.visibility,
    )


def _new_dynamic_structure_id(world: WorldState) -> str:
    next_index = len(world.dynamic_structures) + 1
    while True:
        structure_id = f"dyn_{next_index:04d}"
        if structure_id not in world.dynamic_structures:
            return structure_id
        next_index += 1


def _ref_exists(world: WorldState, ref: str) -> bool:
    return (
        ref in world.regions
        or ref in world.civilizations
        or ref in world.factions
        or ref in world.characters
        or ref in world.relics
        or ref in world.projects
        or ref in world.supply_lines
        or ref in world.region_nodes
        or ref in world.dynamic_structures
    )


def _clean_ref_list(raw_refs: Any, *, limit: int) -> list[str]:
    if not isinstance(raw_refs, list):
        return []
    refs: list[str] = []
    for raw_ref in raw_refs:
        ref = str(raw_ref).strip()
        if ref and ref not in refs:
            refs.append(ref)
        if len(refs) >= limit:
            break
    return refs


def _clean_tag_list(raw_tags: Any, *, limit: int) -> list[str]:
    if not isinstance(raw_tags, list):
        return []
    tags: list[str] = []
    for raw_tag in raw_tags:
        tag = str(raw_tag).strip().lower().replace(" ", "_")
        if tag and tag not in tags:
            tags.append(tag[:48])
        if len(tags) >= limit:
            break
    return tags


def _clean_text(raw_text: Any, *, limit: int) -> str:
    text = " ".join(str(raw_text).strip().split())
    return text[:limit].rstrip()


def _append_unique(values: list[str], value: str, *, limit: int) -> None:
    if value in values:
        values.remove(value)
    values.append(value)
    del values[:-limit]


def _refresh_dynamic_structure_pressure_threads(
    world: WorldState,
    structure: DynamicStructure,
    event: Event,
) -> None:
    theme = _dynamic_structure_pressure_theme(structure)
    for scope_ref in [structure.structure_id] + structure.scope_refs[:3] + structure.linked_refs[:3]:
        thread_id = f"thread_{scope_ref}_{theme}"
        thread = world.pressure_threads.get(thread_id)
        if thread is None:
            thread = PressureThread(
                thread_id=thread_id,
                scope_ref=scope_ref,
                theme=theme,
                first_tick=world.current_tick,
            )
            world.pressure_threads[thread_id] = thread
        thread.updated_tick = world.current_tick
        thread.visibility = structure.visibility
        _append_unique(thread.event_refs, event.event_id, limit=8)
        _append_unique(thread.public_clues, f"{structure.name}正在改变周边局势的可见压力。", limit=4)
        thread.intensity = structure.pressure
        thread.status = "active" if len(thread.event_refs) >= 2 else "forming"
        thread.summary = f"{structure.name} 的动态结构线索正在影响周边对象"


def _dynamic_structure_pressure_theme(structure: DynamicStructure) -> str:
    if structure.structure_type in {"incident_site", "anomaly_trace"}:
        return "anomaly"
    if structure.structure_type in {"proxy_cell", "local_group"}:
        return "organization"
    if structure.structure_type == "rumor_network":
        return "politics"
    return "macro"
