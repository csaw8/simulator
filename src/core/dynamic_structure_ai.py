"""AI proposal adapter for dynamic structures."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.agents.llm_client import LLMClientError, build_siliconflow_client
from src.core.ai_context import (
    build_dynamic_structure_context,
    dynamic_structure_context_signal,
)
from src.core.ai_policy import evaluate_observer_llm_policy
from src.core.ai_tiers import resolve_named_tier
from src.core.dynamic_structure_proposals import (
    DynamicProposalResult,
    apply_dynamic_structure_proposals,
    validate_dynamic_structure_proposals,
)
from src.world.ai_audit import AIProposalAudit
from src.world.state import WorldState

PROMPT_ROOT = Path("prompts")


@dataclass(slots=True)
class DynamicStructureAIResult:
    """Result of asking AI to propose dynamic structures."""

    source: str
    applied: bool
    payload: dict[str, Any] | None = None
    validation: DynamicProposalResult = field(default_factory=DynamicProposalResult)
    error: str | None = None
    tier: str | None = None
    signal_score: int = 0
    audit_id: str | None = None


def propose_dynamic_structures_for_watch(
    world: WorldState,
    *,
    target_type: str,
    target_id: str,
    ai_config: dict[str, object],
    mode: str,
    view: str,
    apply: bool = False,
    client: object | None = None,
) -> DynamicStructureAIResult:
    """Ask AI for dynamic-structure proposals around one watch target."""
    context = build_dynamic_structure_context(
        world,
        target_type=target_type,
        target_id=target_id,
    )
    if context.get("error"):
        result = DynamicStructureAIResult(source="none", applied=False, error=str(context["error"]))
        _record_dynamic_structure_audit(world, result, target_type=target_type, target_id=target_id)
        return result

    signal_score = dynamic_structure_context_signal(context)
    decision = evaluate_observer_llm_policy(
        ai_config,
        mode=mode,
        view=view,
        signal_score=signal_score,
    )
    if not decision.allowed:
        result = DynamicStructureAIResult(
            source="none",
            applied=False,
            error=decision.reason,
            signal_score=signal_score,
            tier=_dynamic_structure_tier(ai_config).tier,
        )
        _record_dynamic_structure_audit(world, result, target_type=target_type, target_id=target_id)
        return result

    llm_client = client or build_siliconflow_client(ai_config)
    tier = _dynamic_structure_tier(ai_config)
    if llm_client is None:
        result = DynamicStructureAIResult(
            source="none",
            applied=False,
            error="SiliconFlow client unavailable",
            tier=tier.tier,
            signal_score=signal_score,
        )
        _record_dynamic_structure_audit(world, result, target_type=target_type, target_id=target_id)
        return result

    try:
        payload = llm_client.create_json_completion_with_limits(
            _build_dynamic_structure_messages(context),
            max_tokens=tier.max_tokens,
            thinking_budget=tier.thinking_budget,
        )
        if not isinstance(payload, dict):
            raise LLMClientError("Dynamic structure proposal payload is not an object")
        validation = (
            apply_dynamic_structure_proposals(world, payload, origin="ai_dynamic_structure")
            if apply
            else validate_dynamic_structure_proposals(world, payload)
        )
        result = DynamicStructureAIResult(
            source="siliconflow",
            applied=apply,
            payload=payload,
            validation=validation,
            tier=tier.tier,
            signal_score=signal_score,
        )
        _record_dynamic_structure_audit(world, result, target_type=target_type, target_id=target_id)
        return result
    except LLMClientError as exc:
        result = DynamicStructureAIResult(
            source="none",
            applied=False,
            error=str(exc),
            tier=tier.tier,
            signal_score=signal_score,
        )
        _record_dynamic_structure_audit(world, result, target_type=target_type, target_id=target_id)
        return result


def format_dynamic_structure_ai_result(result: DynamicStructureAIResult) -> str:
    """Render a compact CLI block for dynamic-structure AI proposals."""
    lines = ["Dynamic structure proposal:"]
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


def format_ai_proposal_audits(world: WorldState, *, limit: int = 10) -> str:
    """Render recent AI proposal audit records."""
    audits = sorted(
        world.ai_proposal_audits.values(),
        key=lambda audit: (audit.tick, audit.audit_id),
        reverse=True,
    )[: max(1, limit)]
    if not audits:
        return "No AI proposal audits recorded."
    lines = [f"AI proposal audits ({len(audits)} shown):"]
    for audit in audits:
        lines.append(
            f"  - {audit.audit_id}: type={audit.proposal_type}, "
            f"target={audit.target_type}:{audit.target_id}, "
            f"mode={audit.mode}, source={audit.source}, applied={audit.applied}, "
            f"accepted={len(audit.accepted_refs)}, rejected={len(audit.rejected_reasons)}, "
            f"error={audit.error or 'None'}"
        )
    return "\n".join(lines)


def format_ai_proposal_audit_summary(world: WorldState, *, limit: int = 40) -> str:
    """Render aggregate quality metrics for recent AI proposal audits."""
    audits = sorted(
        world.ai_proposal_audits.values(),
        key=lambda audit: (audit.tick, audit.audit_id),
        reverse=True,
    )[: max(1, limit)]
    if not audits:
        return "No AI proposal audits recorded."

    accepted_count = sum(1 for audit in audits if audit.accepted_refs)
    applied_count = sum(1 for audit in audits if audit.applied and audit.accepted_refs)
    rejected_count = sum(1 for audit in audits if audit.rejected_reasons)
    error_counts: dict[str, int] = {}
    rejection_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for audit in audits:
        source_counts[audit.source] = source_counts.get(audit.source, 0) + 1
        if audit.error:
            key = _compact_audit_reason(audit.error)
            error_counts[key] = error_counts.get(key, 0) + 1
        for reason in audit.rejected_reasons:
            key = _compact_audit_reason(reason)
            rejection_counts[key] = rejection_counts.get(key, 0) + 1

    total = len(audits)
    acceptance_rate = int(round((accepted_count / total) * 100))
    rejection_rate = int(round((rejected_count / total) * 100))
    lines = [f"AI proposal audit summary ({total} sampled):"]
    lines.append(f"  accepted_records: {accepted_count} ({acceptance_rate}%)")
    lines.append(f"  applied_records: {applied_count}")
    lines.append(f"  rejected_records: {rejected_count} ({rejection_rate}%)")
    lines.append("  sources: " + _format_counts(source_counts))
    lines.append("  errors: " + _format_counts(error_counts))
    lines.append("  rejections: " + _format_counts(rejection_counts))
    return "\n".join(lines)


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "None"
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{key}={count}" for key, count in ordered[:5])


def _compact_audit_reason(reason: str) -> str:
    text = " ".join(reason.strip().split())
    if ":" in text:
        text = text.split(":", 1)[0]
    if len(text) > 64:
        text = text[:64].rstrip() + "..."
    return text or "unknown"


def _record_dynamic_structure_audit(
    world: WorldState,
    result: DynamicStructureAIResult,
    *,
    target_type: str,
    target_id: str,
) -> None:
    audit_id = _new_ai_proposal_audit_id(world)
    audit = AIProposalAudit(
        audit_id=audit_id,
        tick=world.current_tick,
        source=result.source,
        proposal_type="dynamic_structure",
        target_type=target_type,
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


def _dynamic_structure_tier(ai_config: dict[str, object]):
    return resolve_named_tier(
        ai_config,
        str(ai_config.get("dynamic_structure_cost_tier", "low")),
    )


def _build_dynamic_structure_messages(context: dict[str, object]) -> list[dict[str, str]]:
    system_rules = (PROMPT_ROOT / "system_rules.txt").read_text(encoding="utf-8").strip()
    task_prompt = (PROMPT_ROOT / "dynamic_structure_proposal.txt").read_text(encoding="utf-8").strip()
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    final_instruction = (
        "Final instruction for this call: proposal_required is true. This is only a candidate proposal, not an authoritative fact. Return exactly one valid proposal object in proposals."
        if context.get("proposal_required")
        else "Final instruction for this call: proposal_required is false, so return proposals only if the context clearly supports one."
    )
    return [
        {"role": "system", "content": system_rules},
        {
            "role": "user",
            "content": "\n".join(
                [
                    task_prompt,
                    "",
                    "Use this bounded world context:",
                    context_json,
                    "",
                    final_instruction,
                ]
            ),
        },
    ]
