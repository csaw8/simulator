"""AI adapter for approved template instances."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.agents.llm_client import LLMClientError, build_siliconflow_client, llm_source_label
from src.core.ai_tiers import resolve_named_tier
from src.world.ai_audit import AIProposalAudit
from src.world.open_structure_template import (
    TemplateValidationResult,
    create_template_instance,
    get_active_approved_template,
    template_instance_from_payload,
    template_schema_to_dict,
    validate_template_instance,
)
from src.world.state import WorldState

PROMPT_ROOT = Path("prompts")


@dataclass(slots=True)
class TemplateInstanceAIResult:
    """Result of asking AI to fill one approved template instance."""

    source: str
    applied: bool
    template_id: str
    scope_ref: str
    payload: dict[str, Any] | None = None
    validation: TemplateValidationResult = field(default_factory=lambda: TemplateValidationResult(False, []))
    error: str | None = None
    tier: str | None = None
    audit_id: str | None = None


def propose_template_instance(
    world: WorldState,
    *,
    template_id: str,
    scope_ref: str,
    ai_config: dict[str, object],
    apply: bool = False,
    client: object | None = None,
) -> TemplateInstanceAIResult:
    """Ask AI to create one instance payload for an active approved template."""
    record = get_active_approved_template(world.approved_template_registry, template_id)
    if record is None:
        result = TemplateInstanceAIResult(
            source="none",
            applied=False,
            template_id=template_id,
            scope_ref=scope_ref,
            error=f"template {template_id!r} is not active in approved registry",
        )
        _record_template_instance_audit(world, result)
        return result

    tier = _template_instance_tier(ai_config)
    llm_client = client or build_siliconflow_client(ai_config)
    if llm_client is None:
        source_label = llm_source_label(ai_config)
        result = TemplateInstanceAIResult(
            source="none",
            applied=False,
            template_id=record.template.template_id,
            scope_ref=scope_ref,
            error=f"{source_label} client unavailable",
            tier=tier.tier,
        )
        _record_template_instance_audit(world, result)
        return result

    context = build_template_instance_context(world, template_id=record.template.template_id, scope_ref=scope_ref)
    try:
        payload = llm_client.create_json_completion_with_limits(
            _build_template_instance_messages(context),
            max_tokens=tier.max_tokens,
            thinking_budget=tier.thinking_budget,
        )
        if not isinstance(payload, dict):
            raise LLMClientError("Template instance payload is not an object")
        raw_instance = payload.get("instance", payload)
        if not isinstance(raw_instance, dict):
            raise LLMClientError("Template instance payload must contain an instance object")
        normalized_payload = dict(raw_instance)
        normalized_payload["template_id"] = record.template.template_id
        normalized_payload["template_version"] = record.template.version
        normalized_payload["scope_ref"] = scope_ref
        normalized_payload.setdefault("created_at_tick", world.current_tick)
        normalized_payload.setdefault("updated_at_tick", world.current_tick)
        normalized_payload.setdefault("source", "ai_template_instance")
        instance = template_instance_from_payload(normalized_payload, current_tick=world.current_tick)
        validation = (
            create_template_instance(world.template_instances, world.approved_template_registry, instance)
            if apply
            else validate_template_instance(world.approved_template_registry, instance)
        )
        result = TemplateInstanceAIResult(
            source=llm_source_label(ai_config, llm_client),
            applied=apply,
            template_id=record.template.template_id,
            scope_ref=scope_ref,
            payload={"instance": normalized_payload},
            validation=validation,
            tier=tier.tier,
        )
        _record_template_instance_audit(world, result)
        return result
    except LLMClientError as exc:
        result = TemplateInstanceAIResult(
            source="none",
            applied=False,
            template_id=record.template.template_id,
            scope_ref=scope_ref,
            error=str(exc),
            tier=tier.tier,
        )
        _record_template_instance_audit(world, result)
        return result


def build_template_instance_context(world: WorldState, *, template_id: str, scope_ref: str) -> dict[str, object]:
    """Build a bounded context for AI template instance filling."""
    record = get_active_approved_template(world.approved_template_registry, template_id)
    if record is None:
        return {"error": f"template {template_id!r} is not active in approved registry"}
    return {
        "current_tick": world.current_tick,
        "style_profile_id": world.style_profile_id,
        "template": template_schema_to_dict(record.template),
        "scope_ref": scope_ref,
        "existing_instance_ids": sorted(world.template_instances.instances)[:80],
        "requirements": {
            "output_shape": {"instance": "TemplateInstance payload object"},
            "must_use_template_id": record.template.template_id,
            "must_use_template_version": record.template.version,
            "must_use_scope_ref": scope_ref,
            "no_new_fields": True,
            "no_schema_changes": True,
            "default_mode": "dry-run unless CLI passes apply",
        },
    }


def format_template_instance_ai_result(result: TemplateInstanceAIResult) -> str:
    """Render a compact CLI block for AI template instance generation."""
    lines = ["Template instance AI proposal:"]
    lines.append(f"  source: {result.source}")
    lines.append(f"  mode: {'apply' if result.applied else 'dry-run'}")
    lines.append(f"  template_id: {result.template_id}")
    lines.append(f"  scope_ref: {result.scope_ref}")
    if result.tier:
        lines.append(f"  tier: {result.tier}")
    if result.audit_id:
        lines.append(f"  audit_id: {result.audit_id}")
    if result.error:
        lines.append(f"  error: {result.error}")
    lines.append(f"  accepted: {1 if result.validation.accepted else 0}")
    lines.append(f"  rejected: {0 if result.validation.accepted else len(result.validation.errors)}")
    for error in result.validation.errors[:3]:
        lines.append(f"    rejected_reason: {error}")
    accepted_ref = _accepted_instance_ref(result)
    if accepted_ref:
        lines.append(f"    accepted_ref: {accepted_ref}")
    return "\n".join(lines)


def _record_template_instance_audit(world: WorldState, result: TemplateInstanceAIResult) -> None:
    audit_id = _new_ai_proposal_audit_id(world)
    accepted_ref = _accepted_instance_ref(result)
    audit = AIProposalAudit(
        audit_id=audit_id,
        tick=world.current_tick,
        source=result.source,
        proposal_type="template_instance",
        target_type="template",
        target_id=result.template_id,
        mode="apply" if result.applied else "dry-run",
        applied=result.applied,
        accepted_refs=[accepted_ref] if accepted_ref else [],
        rejected_reasons=list(result.validation.errors),
        payload=result.payload,
        error=result.error,
        tier=result.tier,
        signal_score=0,
    )
    world.ai_proposal_audits[audit_id] = audit
    result.audit_id = audit_id
    _prune_ai_proposal_audits(world, limit=100)


def _accepted_instance_ref(result: TemplateInstanceAIResult) -> str | None:
    if not result.validation.accepted or not isinstance(result.payload, dict):
        return None
    raw_instance = result.payload.get("instance")
    if not isinstance(raw_instance, dict):
        return None
    instance_id = str(raw_instance.get("instance_id", "")).strip()
    return instance_id or None


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


def _template_instance_tier(ai_config: dict[str, object]):
    return resolve_named_tier(
        ai_config,
        str(ai_config.get("template_instance_cost_tier", "low")),
    )


def _build_template_instance_messages(context: dict[str, object]) -> list[dict[str, str]]:
    system_rules = (PROMPT_ROOT / "system_rules.txt").read_text(encoding="utf-8").strip()
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    task_prompt = (
        "Create one bounded TemplateInstance payload for the approved template. "
        "Return JSON only. Do not add schema fields. Do not modify fixed world objects. "
        "Use exactly this shape: {\"instance\": {\"instance_id\": string, \"template_id\": string, "
        "\"template_version\": integer, \"scope_ref\": string, \"field_values\": object, "
        "\"linked_refs\": string[], \"descriptor_values\": object, \"pressure_score\": number, "
        "\"status\": \"active\"}}."
    )
    return [
        {"role": "system", "content": system_rules},
        {
            "role": "user",
            "content": "\n".join(
                [
                    task_prompt,
                    "",
                    "Use this bounded approved-template context:",
                    context_json,
                    "",
                    "Final instruction: return exactly one valid instance object. If unsure, keep values conservative.",
                ]
            ),
        },
    ]
