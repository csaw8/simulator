"""AI adapter for semi-open structure template proposals."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.agents.llm_client import LLMClientError, build_siliconflow_client, llm_source_label
from src.core.ai_tiers import resolve_named_tier
from src.world.ai_audit import AIProposalAudit
from src.world.open_structure_template import (
    StructureTemplateProposal,
    TemplateValidationResult,
    proposal_from_payload,
    proposal_to_dict,
    submit_template_proposal_to_queue,
    template_schema_to_dict,
    validate_template_proposal,
)
from src.world.state import WorldState

PROMPT_ROOT = Path("prompts")


@dataclass(slots=True)
class StructureTemplateAIResult:
    """Result of asking AI to propose a new semi-open template."""

    source: str
    applied: bool
    payload: dict[str, Any] | None = None
    proposal: StructureTemplateProposal | None = None
    validation: TemplateValidationResult = field(default_factory=lambda: TemplateValidationResult(False, []))
    error: str | None = None
    tier: str | None = None
    audit_id: str | None = None


def propose_structure_template(
    world: WorldState,
    *,
    ai_config: dict[str, object],
    apply: bool = False,
    guidance: str = "",
    client: object | None = None,
) -> StructureTemplateAIResult:
    """Ask AI to propose one bounded template schema."""
    tier = _structure_template_tier(ai_config)
    llm_client = client or build_siliconflow_client(ai_config)
    if llm_client is None:
        source_label = llm_source_label(ai_config)
        result = StructureTemplateAIResult(
            source="none",
            applied=False,
            error=f"{source_label} client unavailable",
            tier=tier.tier,
        )
        _record_structure_template_audit(world, result)
        return result

    context = build_structure_template_context(world, guidance=guidance)
    try:
        payload = llm_client.create_json_completion_with_limits(
            _build_structure_template_messages(context),
            max_tokens=tier.max_tokens,
            thinking_budget=tier.thinking_budget,
        )
        if not isinstance(payload, dict):
            raise LLMClientError("Structure template proposal payload is not an object")
        raw_proposal = payload.get("proposal", payload)
        if not isinstance(raw_proposal, dict):
            raise LLMClientError("Structure template payload must contain a proposal object")
        proposal = proposal_from_payload(raw_proposal, current_tick=world.current_tick)
        validation = validate_template_proposal(proposal)
        if apply and validation.accepted:
            entry = submit_template_proposal_to_queue(world.template_approval_queue, proposal, current_tick=world.current_tick)
            validation = TemplateValidationResult(entry.status == "pending", list(proposal.validation_errors))
        result = StructureTemplateAIResult(
            source=llm_source_label(ai_config, llm_client),
            applied=apply,
            payload={"proposal": proposal_to_dict(proposal)},
            proposal=proposal,
            validation=validation,
            tier=tier.tier,
        )
        _record_structure_template_audit(world, result)
        return result
    except LLMClientError as exc:
        result = StructureTemplateAIResult(
            source="none",
            applied=False,
            error=str(exc),
            tier=tier.tier,
        )
        _record_structure_template_audit(world, result)
        return result


def build_structure_template_context(world: WorldState, *, guidance: str = "") -> dict[str, object]:
    """Build bounded context for proposing one new template."""
    return {
        "current_tick": world.current_tick,
        "style_profile_id": world.style_profile_id,
        "guidance": guidance,
        "existing_template_ids": sorted(world.approved_template_registry.templates)[:80],
        "pending_proposal_ids": sorted(world.template_approval_queue.entries)[:80],
        "approved_templates": [
            template_schema_to_dict(record.template)
            for record in sorted(
                world.approved_template_registry.templates.values(),
                key=lambda item: item.template.template_id,
            )[:8]
        ],
        "allowed_template_kinds": [
            "social_formation",
            "place_condition",
            "hazard_pattern",
            "resource_flow",
            "signal_pattern",
        ],
        "allowed_field_types": ["text", "integer", "number", "boolean", "enum", "ref", "ref_list", "tag_list"],
        "allowed_effects": ["event", "relation", "pressure_thread", "narrative_observation", "descriptor_profile"],
        "requirements": {
            "output_shape": {"proposal": "StructureTemplateProposal payload object"},
            "max_fields": 8,
            "text_fields_need_max_length": True,
            "enum_fields_need_allowed_values": True,
            "ref_fields_need_ref_types": True,
            "no_python_dataclass": True,
            "no_worldstate_fields": True,
            "no_direct_apply_to_registry": True,
        },
    }


def format_structure_template_ai_result(result: StructureTemplateAIResult) -> str:
    """Render a compact CLI block for AI template proposals."""
    lines = ["Structure template AI proposal:"]
    lines.append(f"  source: {result.source}")
    lines.append(f"  mode: {'queue' if result.applied else 'dry-run'}")
    if result.tier:
        lines.append(f"  tier: {result.tier}")
    if result.audit_id:
        lines.append(f"  audit_id: {result.audit_id}")
    if result.error:
        lines.append(f"  error: {result.error}")
    lines.append(f"  accepted: {1 if result.validation.accepted else 0}")
    lines.append(f"  rejected: {0 if result.validation.accepted else len(result.validation.errors)}")
    if result.proposal is not None:
        lines.append(f"    proposal_id: {result.proposal.proposal_id}")
        lines.append(f"    template_id: {result.proposal.template.template_id}")
    for error in result.validation.errors[:3]:
        lines.append(f"    rejected_reason: {error}")
    return "\n".join(lines)


def _record_structure_template_audit(world: WorldState, result: StructureTemplateAIResult) -> None:
    audit_id = _new_ai_proposal_audit_id(world)
    accepted_refs = []
    if result.validation.accepted and result.proposal is not None:
        accepted_refs.append(result.proposal.proposal_id)
    audit = AIProposalAudit(
        audit_id=audit_id,
        tick=world.current_tick,
        source=result.source,
        proposal_type="structure_template",
        target_type="template_registry",
        target_id="semi_open_structure",
        mode="queue" if result.applied else "dry-run",
        applied=result.applied,
        accepted_refs=accepted_refs,
        rejected_reasons=list(result.validation.errors),
        payload=result.payload,
        error=result.error,
        tier=result.tier,
        signal_score=0,
    )
    world.ai_proposal_audits[audit_id] = audit
    result.audit_id = audit_id
    _prune_ai_proposal_audits(world, limit=100)


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


def _structure_template_tier(ai_config: dict[str, object]):
    return resolve_named_tier(
        ai_config,
        str(ai_config.get("structure_template_cost_tier", "medium")),
    )


def _build_structure_template_messages(context: dict[str, object]) -> list[dict[str, str]]:
    system_rules = (PROMPT_ROOT / "system_rules.txt").read_text(encoding="utf-8").strip()
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    task_prompt = (
        "Propose one bounded semi-open structure template as data, not code. "
        "Return JSON only. Do not invent Python classes. Do not add WorldState fields. "
        "Use exactly this shape: {\"proposal\": {\"proposal_id\": string, \"template\": object, "
        "\"rationale\": string, \"source\": string}}."
    )
    return [
        {"role": "system", "content": system_rules},
        {
            "role": "user",
            "content": "\n".join(
                [
                    task_prompt,
                    "",
                    "Use this bounded world/template context:",
                    context_json,
                    "",
                    "Final instruction: return exactly one valid template proposal object.",
                ]
            ),
        },
    ]
