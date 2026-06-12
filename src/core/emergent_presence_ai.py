"""AI proposal adapter for emergent presences."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.agents.llm_client import LLMClientError, build_siliconflow_client, llm_source_label
from src.core.ai_context import (
    build_emergent_presence_context,
    emergent_presence_context_signal,
)
from src.core.ai_policy import evaluate_observer_llm_policy
from src.core.ai_tiers import resolve_named_tier
from src.core.emergent_presence_proposals import (
    EmergentPresenceProposalResult,
    apply_emergent_presence_proposals,
    validate_emergent_presence_proposals,
)
from src.world.ai_audit import AIProposalAudit
from src.world.state import WorldState

PROMPT_ROOT = Path("prompts")


@dataclass(slots=True)
class EmergentPresenceAIResult:
    """Result of asking AI to propose emergent presences."""

    source: str
    applied: bool
    payload: dict[str, Any] | None = None
    validation: EmergentPresenceProposalResult = field(
        default_factory=EmergentPresenceProposalResult
    )
    error: str | None = None
    tier: str | None = None
    signal_score: int = 0
    audit_id: str | None = None


def propose_emergent_presences_for_watch(
    world: WorldState,
    *,
    target_type: str,
    target_id: str,
    ai_config: dict[str, object],
    mode: str,
    view: str,
    apply: bool = False,
    client: object | None = None,
) -> EmergentPresenceAIResult:
    """Ask AI for emergent-presence proposals around one watch target."""
    context = build_emergent_presence_context(
        world,
        target_type=target_type,
        target_id=target_id,
    )
    if context.get("error"):
        result = EmergentPresenceAIResult(
            source="none",
            applied=False,
            error=str(context["error"]),
        )
        _record_emergent_presence_audit(world, result, target_type=target_type, target_id=target_id)
        return result

    signal_score = emergent_presence_context_signal(context)
    decision = evaluate_observer_llm_policy(
        ai_config,
        mode=mode,
        view=view,
        signal_score=signal_score,
    )
    tier = _emergent_presence_tier(ai_config)
    if not decision.allowed:
        result = EmergentPresenceAIResult(
            source="none",
            applied=False,
            error=decision.reason,
            signal_score=signal_score,
            tier=tier.tier,
        )
        _record_emergent_presence_audit(world, result, target_type=target_type, target_id=target_id)
        return result

    llm_client = client or build_siliconflow_client(ai_config)
    if llm_client is None:
        source_label = llm_source_label(ai_config)
        result = EmergentPresenceAIResult(
            source="none",
            applied=False,
            error=f"{source_label} client unavailable",
            tier=tier.tier,
            signal_score=signal_score,
        )
        _record_emergent_presence_audit(world, result, target_type=target_type, target_id=target_id)
        return result

    try:
        payload = llm_client.create_json_completion_with_limits(
            _build_emergent_presence_messages(context),
            max_tokens=tier.max_tokens,
            thinking_budget=tier.thinking_budget,
        )
        if not isinstance(payload, dict):
            raise LLMClientError("Emergent presence proposal payload is not an object")
        validation = (
            apply_emergent_presence_proposals(world, payload, origin="ai_emergent_presence")
            if apply
            else validate_emergent_presence_proposals(world, payload)
        )
        result = EmergentPresenceAIResult(
            source=llm_source_label(ai_config, llm_client),
            applied=apply,
            payload=payload,
            validation=validation,
            tier=tier.tier,
            signal_score=signal_score,
        )
        _record_emergent_presence_audit(world, result, target_type=target_type, target_id=target_id)
        return result
    except LLMClientError as exc:
        result = EmergentPresenceAIResult(
            source="none",
            applied=False,
            error=str(exc),
            tier=tier.tier,
            signal_score=signal_score,
        )
        _record_emergent_presence_audit(world, result, target_type=target_type, target_id=target_id)
        return result


def format_emergent_presence_ai_result(result: EmergentPresenceAIResult) -> str:
    """Render a compact CLI block for emergent-presence AI proposals."""
    lines = ["Emergent presence AI proposal:"]
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


def _record_emergent_presence_audit(
    world: WorldState,
    result: EmergentPresenceAIResult,
    *,
    target_type: str,
    target_id: str,
) -> None:
    audit_id = _new_ai_proposal_audit_id(world)
    audit = AIProposalAudit(
        audit_id=audit_id,
        tick=world.current_tick,
        source=result.source,
        proposal_type="emergent_presence",
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


def _emergent_presence_tier(ai_config: dict[str, object]):
    return resolve_named_tier(
        ai_config,
        str(ai_config.get("emergent_presence_cost_tier", "medium")),
    )


def _build_emergent_presence_messages(context: dict[str, object]) -> list[dict[str, str]]:
    system_rules = (PROMPT_ROOT / "system_rules.txt").read_text(encoding="utf-8").strip()
    task_prompt = (PROMPT_ROOT / "emergent_presence_proposal.txt").read_text(
        encoding="utf-8"
    ).strip()
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
    final_instruction = (
        "Final instruction for this call: proposal_required is true. Return exactly one valid emergent-presence proposal in proposals."
        if context.get("proposal_required")
        else "Final instruction for this call: proposal_required is false, so return proposals only if the context clearly supports one bounded emergent presence."
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
