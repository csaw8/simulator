"""Validated proposal flow for emergent presences."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.events.models import Event
from src.events.visibility_rules import normalize_event_visibility
from src.world.emergent_presence import (
    ALLOWED_EMERGENT_LIFECYCLE_STAGES,
    ALLOWED_EMERGENT_MOBILITY,
    ALLOWED_EMERGENT_PRESENCE_TYPES,
    ALLOWED_EMERGENT_SCALES,
    ALLOWED_EMERGENT_STATUSES,
    EmergentPresence,
)
from src.world.pressure_thread import PressureThread
from src.world.relations import upsert_relation
from src.world.state import WorldState

ALLOWED_EMERGENT_ACTIONS = {"create", "update"}
ALLOWED_EMERGENT_PRESSURES = {"low", "medium", "high"}
ALLOWED_EMERGENT_ADAPTATION = {"low", "medium", "high"}
ALLOWED_EMERGENT_RELATIONS = {
    "infests",
    "pressures",
    "avoids",
    "nests_in",
    "attracted_to",
    "disrupts",
    "emerges_from",
}
MAX_EMERGENT_PROPOSALS_PER_BATCH = 2
MAX_REFS_PER_EMERGENT_PROPOSAL = 8
MAX_TAGS_PER_EMERGENT_PROPOSAL = 6


@dataclass(slots=True)
class EmergentPresenceProposalResult:
    """Result of validating and applying emergent-presence proposals."""

    accepted: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)


def validate_emergent_presence_proposals(
    world: WorldState,
    payload: dict[str, Any],
) -> EmergentPresenceProposalResult:
    """Validate a proposal batch without mutating world state."""
    result = EmergentPresenceProposalResult()
    proposals = payload.get("proposals", [])
    if not isinstance(proposals, list):
        result.rejected.append("payload.proposals must be a list")
        return result
    for index, raw_proposal in enumerate(proposals[:MAX_EMERGENT_PROPOSALS_PER_BATCH]):
        if not isinstance(raw_proposal, dict):
            result.rejected.append(f"proposal[{index}] must be an object")
            continue
        error = _validate_emergent_presence_proposal(world, raw_proposal)
        if error:
            result.rejected.append(f"proposal[{index}]: {error}")
            continue
        duplicate_id = _find_duplicate_emergent_presence(world, raw_proposal)
        if duplicate_id:
            result.accepted.append(f"proposal[{index}]->update:{duplicate_id}")
            continue
        result.accepted.append(f"proposal[{index}]")
    return result


def apply_emergent_presence_proposals(
    world: WorldState,
    payload: dict[str, Any],
    *,
    origin: str = "manual_proposal",
) -> EmergentPresenceProposalResult:
    """Validate and apply a bounded batch of emergent-presence proposals."""
    result = EmergentPresenceProposalResult()
    proposals = payload.get("proposals", [])
    if not isinstance(proposals, list):
        result.rejected.append("payload.proposals must be a list")
        return result

    for index, raw_proposal in enumerate(proposals[:MAX_EMERGENT_PROPOSALS_PER_BATCH]):
        if not isinstance(raw_proposal, dict):
            result.rejected.append(f"proposal[{index}] must be an object")
            continue
        error = _validate_emergent_presence_proposal(world, raw_proposal)
        if error:
            result.rejected.append(f"proposal[{index}]: {error}")
            continue
        presence, event = _apply_one_emergent_presence_proposal(
            world,
            raw_proposal,
            origin=origin,
        )
        result.accepted.append(presence.presence_id)
        result.events.append(event)
    return result


def _validate_emergent_presence_proposal(world: WorldState, proposal: dict[str, Any]) -> str | None:
    action = str(proposal.get("action", "create")).strip().lower()
    if action not in ALLOWED_EMERGENT_ACTIONS:
        return f"unsupported action {action!r}"

    presence_type = str(proposal.get("presence_type", "")).strip().lower()
    if presence_type not in ALLOWED_EMERGENT_PRESENCE_TYPES:
        return f"unsupported presence_type {presence_type!r}"

    name = _clean_text(proposal.get("name", ""), limit=80)
    summary = _clean_text(proposal.get("summary", ""), limit=240)
    if not name:
        return "name is required"
    if not summary:
        return "summary is required"

    if action == "update":
        presence_id = str(proposal.get("presence_id", "")).strip()
        if presence_id not in world.emergent_presences:
            return "update requires an existing presence_id"

    home_region_ref = str(proposal.get("home_region_ref", "")).strip()
    current_region_refs = _clean_ref_list(
        proposal.get("current_region_refs", []),
        limit=MAX_REFS_PER_EMERGENT_PROPOSAL,
    )
    if home_region_ref and home_region_ref not in world.regions:
        return f"unknown home_region_ref {home_region_ref!r}"
    if not home_region_ref and not current_region_refs:
        return "home_region_ref or current_region_refs is required"
    for region_ref in current_region_refs:
        if region_ref not in world.regions:
            return f"unknown current_region_ref {region_ref!r}"

    linked_relic_refs = _clean_ref_list(
        proposal.get("linked_relic_refs", []),
        limit=MAX_REFS_PER_EMERGENT_PROPOSAL,
    )
    linked_dynamic_refs = _clean_ref_list(
        proposal.get("linked_dynamic_refs", []),
        limit=MAX_REFS_PER_EMERGENT_PROPOSAL,
    )
    linked_faction_refs = _clean_ref_list(
        proposal.get("linked_faction_refs", []),
        limit=MAX_REFS_PER_EMERGENT_PROPOSAL,
    )
    for ref in linked_relic_refs:
        if ref not in world.relics:
            return f"unknown linked_relic_refs item {ref!r}"
    for ref in linked_dynamic_refs:
        if ref not in world.dynamic_structures:
            return f"unknown linked_dynamic_refs item {ref!r}"
    for ref in linked_faction_refs:
        if ref not in world.factions:
            return f"unknown linked_faction_refs item {ref!r}"

    status = str(proposal.get("status", "active")).strip().lower()
    if status not in ALLOWED_EMERGENT_STATUSES:
        return f"unsupported status {status!r}"
    stage = str(proposal.get("lifecycle_stage", "forming")).strip().lower()
    if stage not in ALLOWED_EMERGENT_LIFECYCLE_STAGES:
        return f"unsupported lifecycle_stage {stage!r}"
    scale = str(proposal.get("population_scale", "trace")).strip().lower()
    if scale not in ALLOWED_EMERGENT_SCALES:
        return f"unsupported population_scale {scale!r}"
    adaptation = str(proposal.get("adaptation_level", "low")).strip().lower()
    if adaptation not in ALLOWED_EMERGENT_ADAPTATION:
        return f"unsupported adaptation_level {adaptation!r}"
    mobility = str(proposal.get("mobility", "local")).strip().lower()
    if mobility not in ALLOWED_EMERGENT_MOBILITY:
        return f"unsupported mobility {mobility!r}"
    pressure = str(proposal.get("pressure", "medium")).strip().lower()
    if pressure not in ALLOWED_EMERGENT_PRESSURES:
        return f"unsupported pressure {pressure!r}"
    visibility = normalize_event_visibility(str(proposal.get("visibility", "visible")))
    if not visibility:
        return "invalid visibility"
    relation_type = str(proposal.get("relation_type", "nests_in")).strip().lower()
    if relation_type not in ALLOWED_EMERGENT_RELATIONS:
        return f"unsupported relation_type {relation_type!r}"
    return None


def _apply_one_emergent_presence_proposal(
    world: WorldState,
    proposal: dict[str, Any],
    *,
    origin: str,
) -> tuple[EmergentPresence, Event]:
    action = str(proposal.get("action", "create")).strip().lower()
    presence_id = _presence_id_for_proposal(world, proposal, action)
    presence = world.emergent_presences.get(presence_id)
    created = presence is None
    if presence is None:
        presence = EmergentPresence(
            presence_id=presence_id,
            presence_type=str(proposal["presence_type"]).strip().lower(),
            name=_clean_text(proposal["name"], limit=80),
            summary=_clean_text(proposal["summary"], limit=240),
            origin=origin,
            created_tick=world.current_tick,
        )
        world.emergent_presences[presence_id] = presence

    presence.presence_type = str(proposal["presence_type"]).strip().lower()
    presence.name = _clean_text(proposal["name"], limit=80)
    presence.summary = _clean_text(proposal["summary"], limit=240)
    presence.status = str(proposal.get("status", "active")).strip().lower()
    presence.visibility = normalize_event_visibility(str(proposal.get("visibility", "visible")))
    presence.home_region_ref = str(proposal.get("home_region_ref", "")).strip() or presence.home_region_ref
    presence.current_region_refs = _merged_ref_list(
        presence.current_region_refs,
        _clean_ref_list(proposal.get("current_region_refs", []), limit=MAX_REFS_PER_EMERGENT_PROPOSAL),
        limit=MAX_REFS_PER_EMERGENT_PROPOSAL,
    )
    if presence.home_region_ref and presence.home_region_ref not in presence.current_region_refs:
        presence.current_region_refs = [presence.home_region_ref, *presence.current_region_refs][
            :MAX_REFS_PER_EMERGENT_PROPOSAL
        ]
    presence.linked_relic_refs = _merged_ref_list(
        presence.linked_relic_refs,
        _clean_ref_list(proposal.get("linked_relic_refs", []), limit=MAX_REFS_PER_EMERGENT_PROPOSAL),
        limit=MAX_REFS_PER_EMERGENT_PROPOSAL,
    )
    presence.linked_dynamic_refs = _merged_ref_list(
        presence.linked_dynamic_refs,
        _clean_ref_list(proposal.get("linked_dynamic_refs", []), limit=MAX_REFS_PER_EMERGENT_PROPOSAL),
        limit=MAX_REFS_PER_EMERGENT_PROPOSAL,
    )
    presence.linked_faction_refs = _merged_ref_list(
        presence.linked_faction_refs,
        _clean_ref_list(proposal.get("linked_faction_refs", []), limit=MAX_REFS_PER_EMERGENT_PROPOSAL),
        limit=MAX_REFS_PER_EMERGENT_PROPOSAL,
    )
    presence.lifecycle_stage = str(proposal.get("lifecycle_stage", "forming")).strip().lower()
    presence.population_scale = str(proposal.get("population_scale", "trace")).strip().lower()
    presence.adaptation_level = str(proposal.get("adaptation_level", "low")).strip().lower()
    presence.mobility = str(proposal.get("mobility", "local")).strip().lower()
    presence.pressure = str(proposal.get("pressure", "medium")).strip().lower()
    presence.behavior_tags = _merged_ref_list(
        presence.behavior_tags,
        _clean_tag_list(proposal.get("behavior_tags", []), limit=MAX_TAGS_PER_EMERGENT_PROPOSAL),
        limit=MAX_TAGS_PER_EMERGENT_PROPOSAL,
    )
    presence.sensory_tags = _merged_ref_list(
        presence.sensory_tags,
        _clean_tag_list(proposal.get("sensory_tags", []), limit=MAX_TAGS_PER_EMERGENT_PROPOSAL),
        limit=MAX_TAGS_PER_EMERGENT_PROPOSAL,
    )
    presence.ecological_tags = _merged_ref_list(
        presence.ecological_tags,
        _clean_tag_list(proposal.get("ecological_tags", []), limit=MAX_TAGS_PER_EMERGENT_PROPOSAL),
        limit=MAX_TAGS_PER_EMERGENT_PROPOSAL,
    )
    presence.updated_tick = world.current_tick

    event = _build_emergent_presence_event(world, presence, created=created)
    world.event_stream.append(event)
    world.active_event_ids = [event.event_id]
    _append_unique(presence.source_event_refs, event.event_id, limit=8)

    relation_type = str(proposal.get("relation_type", "nests_in")).strip().lower()
    for target_ref in _presence_target_refs(presence):
        upsert_relation(
            world,
            source_ref=presence.presence_id,
            target_ref=target_ref,
            relation_type=relation_type,
            event=event,
            strength=presence.pressure,
            notes=f"emergent_presence:{presence.presence_type}",
            tags=["emergent_presence", presence.presence_type] + presence.ecological_tags[:4],
        )
        _append_unique(presence.influence_refs, target_ref, limit=12)
    _refresh_emergent_pressure_threads(world, presence, event)
    return presence, event


def _presence_id_for_proposal(world: WorldState, proposal: dict[str, Any], action: str) -> str:
    if action == "update":
        return str(proposal.get("presence_id", "")).strip()
    duplicate_id = _find_duplicate_emergent_presence(world, proposal)
    return duplicate_id or _new_emergent_presence_id(world)


def _find_duplicate_emergent_presence(world: WorldState, proposal: dict[str, Any]) -> str | None:
    action = str(proposal.get("action", "create")).strip().lower()
    if action != "create":
        return None
    presence_type = str(proposal.get("presence_type", "")).strip().lower()
    home_region_ref = str(proposal.get("home_region_ref", "")).strip()
    current_region_refs = set(_clean_ref_list(proposal.get("current_region_refs", []), limit=MAX_REFS_PER_EMERGENT_PROPOSAL))
    linked_relic_refs = set(_clean_ref_list(proposal.get("linked_relic_refs", []), limit=MAX_REFS_PER_EMERGENT_PROPOSAL))
    linked_dynamic_refs = set(_clean_ref_list(proposal.get("linked_dynamic_refs", []), limit=MAX_REFS_PER_EMERGENT_PROPOSAL))
    proposal_regions = ({home_region_ref} if home_region_ref else set()) | current_region_refs
    proposal_links = linked_relic_refs | linked_dynamic_refs
    if not presence_type or not proposal_regions:
        return None
    candidates: list[EmergentPresence] = []
    for presence in world.emergent_presences.values():
        if presence.status == "archived":
            continue
        if presence.presence_type != presence_type:
            continue
        existing_regions = set(presence.current_region_refs)
        if presence.home_region_ref:
            existing_regions.add(presence.home_region_ref)
        existing_links = set(presence.linked_relic_refs) | set(presence.linked_dynamic_refs)
        if proposal_regions & existing_regions and (proposal_links & existing_links or not proposal_links):
            candidates.append(presence)
    if not candidates:
        return None
    candidates.sort(
        key=lambda presence: (
            _pressure_rank(presence.pressure),
            presence.updated_tick,
            presence.presence_id,
        ),
        reverse=True,
    )
    return candidates[0].presence_id


def _build_emergent_presence_event(
    world: WorldState,
    presence: EmergentPresence,
    *,
    created: bool,
) -> Event:
    event_type = "emergent_presence_created" if created else "emergent_presence_updated"
    event_id = world.event_stream.new_event_id()
    return Event(
        event_id=event_id,
        tick=world.current_tick,
        time_granularity=world.current_granularity,
        event_type=event_type,
        event_scope="emergent_presence",
        title=presence.name,
        summary=f"{presence.name}: {presence.summary}",
        region_refs=list(presence.current_region_refs),
        faction_refs=list(presence.linked_faction_refs),
        relic_refs=list(presence.linked_relic_refs),
        dynamic_structure_refs=list(presence.linked_dynamic_refs),
        emergent_presence_refs=[presence.presence_id],
        cause_tags=["emergent_presence", presence.presence_type],
        result_tags=presence.ecological_tags[:6],
        severity=presence.pressure,
        novelty="medium" if created else "low",
        consequence_score=presence.pressure,
        narrative_priority="medium",
        visibility=presence.visibility,
    )


def _new_emergent_presence_id(world: WorldState) -> str:
    next_index = len(world.emergent_presences) + 1
    while True:
        presence_id = f"ep_{next_index:04d}"
        if presence_id not in world.emergent_presences:
            return presence_id
        next_index += 1


def _presence_target_refs(presence: EmergentPresence) -> list[str]:
    refs: list[str] = []
    for ref in (
        presence.current_region_refs
        + presence.linked_relic_refs
        + presence.linked_dynamic_refs
        + presence.linked_faction_refs
    ):
        if ref and ref not in refs:
            refs.append(ref)
    return refs


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


def _merged_ref_list(existing: list[str], incoming: list[str], *, limit: int) -> list[str]:
    merged = list(existing)
    for value in incoming:
        if value in merged:
            merged.remove(value)
        merged.append(value)
    return merged[-limit:]


def _clean_text(raw_text: Any, *, limit: int) -> str:
    text = " ".join(str(raw_text).strip().split())
    return text[:limit].rstrip()


def _append_unique(values: list[str], value: str, *, limit: int) -> None:
    if value in values:
        values.remove(value)
    values.append(value)
    del values[:-limit]


def _refresh_emergent_pressure_threads(
    world: WorldState,
    presence: EmergentPresence,
    event: Event,
) -> None:
    theme = _emergent_presence_pressure_theme(presence)
    for scope_ref in [presence.presence_id] + _presence_target_refs(presence)[:6]:
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
        thread.visibility = presence.visibility
        _append_unique(thread.event_refs, event.event_id, limit=8)
        _append_unique(thread.public_clues, f"{presence.name}留下了可见生态压力迹象。", limit=4)
        thread.intensity = presence.pressure
        thread.status = "active" if len(thread.event_refs) >= 2 else "forming"
        thread.summary = f"{presence.name} 的异常生态压力正在影响周边对象"


def _emergent_presence_pressure_theme(presence: EmergentPresence) -> str:
    if presence.presence_type in {"spore_bloom", "mycelial_mat", "feral_cluster"}:
        return "anomaly"
    if presence.presence_type == "migrant_swarm":
        return "supply"
    if presence.presence_type == "signal_biota":
        return "politics"
    return "macro"


def _pressure_rank(pressure: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(pressure, 0)
