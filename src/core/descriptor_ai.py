"""AI candidate adapter for descriptor profiles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.agents.llm_client import LLMClientError, build_siliconflow_client, llm_source_label
from src.core.ai_tiers import resolve_named_tier
from src.world.ai_audit import AIProposalAudit
from src.world.descriptor_lexicon import approved_descriptor_tag_ids
from src.world.descriptor_profile import (
    DescriptorProfile,
    descriptor_profile_player_labels,
    ensure_descriptor_profile,
    validate_descriptor_profile,
)
from src.world.state import WorldState

PROMPT_ROOT = Path("prompts")
DESCRIPTOR_CATEGORIES = (
    "appearance",
    "function",
    "behavior",
    "sensory",
    "social_read",
    "ecological",
)
MAX_DESCRIPTOR_TAGS_PER_CATEGORY = 3


@dataclass(slots=True)
class DescriptorProposalResult:
    """Result of validating/applying descriptor profile proposals."""

    accepted: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DescriptorAIResult:
    """Result of asking AI for descriptor candidates."""

    source: str
    applied: bool
    payload: dict[str, Any] | None = None
    validation: DescriptorProposalResult = field(default_factory=DescriptorProposalResult)
    error: str | None = None
    tier: str | None = None
    signal_score: int = 0
    audit_id: str | None = None


def propose_descriptor_profile_for_ref(
    world: WorldState,
    *,
    ref_id: str,
    ai_config: dict[str, object],
    apply: bool = False,
    client: object | None = None,
) -> DescriptorAIResult:
    """Ask AI to choose descriptor tags from the approved pool for one ref."""
    profile_type = resolve_descriptor_profile_type(world, ref_id)
    if profile_type is None:
        result = DescriptorAIResult(
            source="none",
            applied=False,
            error=f"unknown descriptor target {ref_id!r}",
        )
        _record_descriptor_audit(world, result, target_id=ref_id)
        return result

    context = build_descriptor_context(world, ref_id=ref_id, profile_type=profile_type)
    tier = _descriptor_tier(ai_config)
    llm_client = client or build_siliconflow_client(ai_config)
    if llm_client is None:
        source_label = llm_source_label(ai_config)
        result = DescriptorAIResult(
            source="none",
            applied=False,
            error=f"{source_label} client unavailable",
            tier=tier.tier,
            signal_score=descriptor_context_signal(context),
        )
        _record_descriptor_audit(world, result, target_id=ref_id)
        return result

    try:
        payload = llm_client.create_json_completion_with_limits(
            _build_descriptor_messages(context),
            max_tokens=tier.max_tokens,
            thinking_budget=tier.thinking_budget,
        )
        if not isinstance(payload, dict):
            raise LLMClientError("Descriptor proposal payload is not an object")
        validation = (
            apply_descriptor_profile_proposals(world, payload, expected_ref_id=ref_id)
            if apply
            else validate_descriptor_profile_proposals(world, payload, expected_ref_id=ref_id)
        )
        result = DescriptorAIResult(
            source=llm_source_label(ai_config, llm_client),
            applied=apply,
            payload=payload,
            validation=validation,
            tier=tier.tier,
            signal_score=descriptor_context_signal(context),
        )
        _record_descriptor_audit(world, result, target_id=ref_id)
        return result
    except LLMClientError as exc:
        result = DescriptorAIResult(
            source="none",
            applied=False,
            error=str(exc),
            tier=tier.tier,
            signal_score=descriptor_context_signal(context),
        )
        _record_descriptor_audit(world, result, target_id=ref_id)
        return result


def validate_descriptor_profile_proposals(
    world: WorldState,
    payload: dict[str, Any],
    *,
    expected_ref_id: str | None = None,
) -> DescriptorProposalResult:
    """Validate descriptor proposals without mutating world state."""
    result = DescriptorProposalResult()
    proposals = payload.get("proposals", [])
    if not isinstance(proposals, list):
        result.rejected.append("payload.proposals must be a list")
        return result
    for index, raw_proposal in enumerate(proposals[:1]):
        if not isinstance(raw_proposal, dict):
            result.rejected.append(f"proposal[{index}] must be an object")
            continue
        error = _validate_descriptor_proposal(world, raw_proposal, expected_ref_id=expected_ref_id)
        if error:
            result.rejected.append(f"proposal[{index}]: {error}")
            continue
        result.accepted.append(f"proposal[{index}]")
    return result


def apply_descriptor_profile_proposals(
    world: WorldState,
    payload: dict[str, Any],
    *,
    expected_ref_id: str | None = None,
) -> DescriptorProposalResult:
    """Validate and apply descriptor proposals to DescriptorProfile only."""
    result = DescriptorProposalResult()
    proposals = payload.get("proposals", [])
    if not isinstance(proposals, list):
        result.rejected.append("payload.proposals must be a list")
        return result
    for index, raw_proposal in enumerate(proposals[:1]):
        if not isinstance(raw_proposal, dict):
            result.rejected.append(f"proposal[{index}] must be an object")
            continue
        error = _validate_descriptor_proposal(world, raw_proposal, expected_ref_id=expected_ref_id)
        if error:
            result.rejected.append(f"proposal[{index}]: {error}")
            continue
        ref_id = str(raw_proposal["ref_id"]).strip()
        profile_type = str(raw_proposal["profile_type"]).strip().lower()
        profile = ensure_descriptor_profile(world, ref_id, profile_type)
        _apply_descriptor_tags(profile, raw_proposal)
        errors = validate_descriptor_profile(profile, style_id=world.style_profile_id)
        if errors:
            result.rejected.extend(f"proposal[{index}]: {error}" for error in errors)
            continue
        result.accepted.append(ref_id)
    return result


def build_descriptor_context(
    world: WorldState,
    *,
    ref_id: str,
    profile_type: str,
) -> dict[str, object]:
    """Build a bounded context for descriptor proposal selection."""
    profile = ensure_descriptor_profile(world, ref_id, profile_type)
    return {
        "style_profile_id": world.style_profile_id,
        "ref_id": ref_id,
        "profile_type": profile_type,
        "current_descriptor_tags": _profile_tags(profile),
        "current_player_labels": descriptor_profile_player_labels(
            profile,
            style_id=world.style_profile_id,
        ),
        "approved_descriptor_pool": {
            category: list(
                approved_descriptor_tag_ids(
                    category=category,
                    profile_type=profile_type,
                    style_id=world.style_profile_id,
                )
            )
            for category in DESCRIPTOR_CATEGORIES
        },
        "target_snapshot": _target_snapshot(world, ref_id, profile_type),
        "proposal_signal_score": 1,
        "proposal_guidance": (
            "Choose compact descriptor tag combinations only from approved_descriptor_pool. "
            "Do not invent new tag ids."
        ),
    }


def descriptor_context_signal(context: dict[str, object]) -> int:
    """Return descriptor proposal signal score."""
    return int(context.get("proposal_signal_score", 0))


def resolve_descriptor_profile_type(world: WorldState, ref_id: str) -> str | None:
    """Resolve the DescriptorProfile type for an existing world ref."""
    if ref_id in world.characters:
        return "character"
    if ref_id in world.region_nodes:
        return "region_node"
    if ref_id in world.relics:
        return "relic"
    if ref_id in world.projects:
        return "project"
    if ref_id in world.supply_lines:
        return "supply_line"
    if ref_id in world.dynamic_structures:
        return "dynamic_structure"
    if ref_id in world.emergent_presences:
        return "emergent_presence"
    return None


def format_descriptor_ai_result(result: DescriptorAIResult) -> str:
    """Render a compact CLI block for descriptor AI proposals."""
    lines = ["Descriptor AI proposal:"]
    lines.append(f"  source: {result.source}")
    lines.append(f"  mode: {'apply' if result.applied else 'dry-run'}")
    if result.tier:
        lines.append(f"  tier: {result.tier}")
    if result.audit_id:
        lines.append(f"  audit_id: {result.audit_id}")
    lines.append(f"  signal_score: {result.signal_score}")
    if result.error:
        lines.append(f"  error: {result.error}")
    lines.append(f"  accepted: {len(result.validation.accepted)}")
    lines.append(f"  rejected: {len(result.validation.rejected)}")
    for item in result.validation.accepted[:3]:
        lines.append(f"    accepted_ref: {item}")
    for item in result.validation.rejected[:3]:
        lines.append(f"    rejected_reason: {item}")
    return "\n".join(lines)


def _validate_descriptor_proposal(
    world: WorldState,
    proposal: dict[str, Any],
    *,
    expected_ref_id: str | None,
) -> str | None:
    ref_id = str(proposal.get("ref_id", "")).strip()
    if not ref_id:
        return "ref_id is required"
    if expected_ref_id is not None and ref_id != expected_ref_id:
        return f"ref_id must match requested target {expected_ref_id!r}"
    profile_type = str(proposal.get("profile_type", "")).strip().lower()
    expected_profile_type = resolve_descriptor_profile_type(world, ref_id)
    if expected_profile_type is None:
        return f"unknown ref_id {ref_id!r}"
    if profile_type != expected_profile_type:
        return f"profile_type must be {expected_profile_type!r}"
    scratch = DescriptorProfile(ref_id=ref_id, profile_type=profile_type)
    _apply_descriptor_tags(scratch, proposal)
    errors = validate_descriptor_profile(scratch, style_id=world.style_profile_id)
    if errors:
        return "; ".join(errors[:3])
    return None


def _apply_descriptor_tags(profile: DescriptorProfile, proposal: dict[str, Any]) -> None:
    profile.appearance_tags = _clean_tag_list(proposal.get("appearance_tags", []))
    profile.function_tags = _clean_tag_list(proposal.get("function_tags", []))
    profile.behavior_tags = _clean_tag_list(proposal.get("behavior_tags", []))
    profile.sensory_tags = _clean_tag_list(proposal.get("sensory_tags", []))
    profile.social_read_tags = _clean_tag_list(proposal.get("social_read_tags", []))
    profile.ecological_tags = _clean_tag_list(proposal.get("ecological_tags", []))
    profile.notes = _clean_notes(proposal.get("notes", []))


def _clean_tag_list(raw_tags: Any) -> list[str]:
    if not isinstance(raw_tags, list):
        return []
    tags: list[str] = []
    for raw_tag in raw_tags:
        tag = str(raw_tag).strip().lower().replace("-", "_").replace(" ", "_")[:48]
        if tag and tag not in tags:
            tags.append(tag)
        if len(tags) >= MAX_DESCRIPTOR_TAGS_PER_CATEGORY:
            break
    return tags


def _clean_notes(raw_notes: Any) -> list[str]:
    if not isinstance(raw_notes, list):
        return []
    notes: list[str] = []
    for raw_note in raw_notes:
        note = " ".join(str(raw_note).strip().split())[:160].rstrip()
        if note:
            notes.append(note)
        if len(notes) >= 3:
            break
    return notes


def _profile_tags(profile: DescriptorProfile) -> dict[str, list[str]]:
    return {
        "appearance": list(profile.appearance_tags),
        "function": list(profile.function_tags),
        "behavior": list(profile.behavior_tags),
        "sensory": list(profile.sensory_tags),
        "social_read": list(profile.social_read_tags),
        "ecological": list(profile.ecological_tags),
    }


def _target_snapshot(world: WorldState, ref_id: str, profile_type: str) -> dict[str, object]:
    if profile_type == "character":
        char = world.characters[ref_id]
        return {
            "name": char.name,
            "role_tags": list(char.role_tags),
            "capability_tags": list(char.capability_tags),
            "agency_mode": char.agency_mode,
        }
    if profile_type == "region_node":
        node = world.region_nodes[ref_id]
        return {"name": node.name, "node_type": node.node_type, "tags": list(node.tags)}
    if profile_type == "relic":
        relic = world.relics[ref_id]
        return {
            "name": relic.name,
            "relic_type": relic.relic_type,
            "story_tags": list(relic.story_tags),
            "activation_state": relic.activation_state,
        }
    if profile_type == "project":
        project = world.projects[ref_id]
        return {"name": project.name, "project_type": project.project_type, "front_tags": list(project.front_tags)}
    if profile_type == "supply_line":
        supply = world.supply_lines[ref_id]
        return {"name": supply.name, "status": supply.status, "front_tags": list(supply.front_tags)}
    if profile_type == "dynamic_structure":
        structure = world.dynamic_structures[ref_id]
        return {"name": structure.name, "structure_type": structure.structure_type, "tags": list(structure.tags)}
    if profile_type == "emergent_presence":
        presence = world.emergent_presences[ref_id]
        return {
            "name": presence.name,
            "presence_type": presence.presence_type,
            "behavior_tags": list(presence.behavior_tags),
            "sensory_tags": list(presence.sensory_tags),
            "ecological_tags": list(presence.ecological_tags),
        }
    return {}


def _record_descriptor_audit(
    world: WorldState,
    result: DescriptorAIResult,
    *,
    target_id: str,
) -> None:
    audit_id = _new_ai_proposal_audit_id(world)
    audit = AIProposalAudit(
        audit_id=audit_id,
        tick=world.current_tick,
        source=result.source,
        proposal_type="descriptor_profile",
        target_type="descriptor",
        target_id=target_id,
        mode="apply" if result.applied else "dry-run",
        applied=result.applied,
        accepted_refs=list(result.validation.accepted),
        rejected_reasons=list(result.validation.rejected),
        payload=result.payload,
        error=result.error,
        tier=result.tier,
        signal_score=result.signal_score,
    )
    world.ai_proposal_audits[audit_id] = audit
    result.audit_id = audit_id
    _prune_ai_proposal_audits(world, limit=80)


def _new_ai_proposal_audit_id(world: WorldState) -> str:
    next_index = len(world.ai_proposal_audits) + 1
    while True:
        audit_id = f"audit_{next_index:05d}"
        if audit_id not in world.ai_proposal_audits:
            return audit_id
        next_index += 1


def _prune_ai_proposal_audits(world: WorldState, *, limit: int) -> None:
    if len(world.ai_proposal_audits) <= limit:
        return
    ordered = sorted(
        world.ai_proposal_audits.values(),
        key=lambda audit: (audit.tick, audit.audit_id),
        reverse=True,
    )
    keep = {audit.audit_id for audit in ordered[:limit]}
    for audit_id in list(world.ai_proposal_audits):
        if audit_id not in keep:
            del world.ai_proposal_audits[audit_id]


def _descriptor_tier(ai_config: dict[str, object]):
    return resolve_named_tier(
        ai_config,
        str(ai_config.get("descriptor_profile_cost_tier", "low")),
    )


def _build_descriptor_messages(context: dict[str, object]) -> list[dict[str, str]]:
    system_rules = (PROMPT_ROOT / "system_rules.txt").read_text(encoding="utf-8").strip()
    task_prompt = (PROMPT_ROOT / "descriptor_profile_proposal.txt").read_text(
        encoding="utf-8"
    ).strip()
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    return [
        {"role": "system", "content": system_rules},
        {
            "role": "user",
            "content": "\n".join(
                [
                    task_prompt,
                    "",
                    "Use this bounded descriptor context:",
                    context_json,
                    "",
                    "Final instruction: return exactly one proposal for the requested ref_id. Use only approved tag ids.",
                ]
            ),
        },
    ]
