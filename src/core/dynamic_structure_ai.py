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
        return DynamicStructureAIResult(source="none", applied=False, error=str(context["error"]))

    signal_score = dynamic_structure_context_signal(context)
    decision = evaluate_observer_llm_policy(
        ai_config,
        mode=mode,
        view=view,
        signal_score=signal_score,
    )
    if not decision.allowed:
        return DynamicStructureAIResult(
            source="none",
            applied=False,
            error=decision.reason,
            signal_score=signal_score,
            tier=_dynamic_structure_tier(ai_config).tier,
        )

    llm_client = client or build_siliconflow_client(ai_config)
    tier = _dynamic_structure_tier(ai_config)
    if llm_client is None:
        return DynamicStructureAIResult(
            source="none",
            applied=False,
            error="SiliconFlow client unavailable",
            tier=tier.tier,
            signal_score=signal_score,
        )

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
        return DynamicStructureAIResult(
            source="siliconflow",
            applied=apply,
            payload=payload,
            validation=validation,
            tier=tier.tier,
            signal_score=signal_score,
        )
    except LLMClientError as exc:
        return DynamicStructureAIResult(
            source="none",
            applied=False,
            error=str(exc),
            tier=tier.tier,
            signal_score=signal_score,
        )


def format_dynamic_structure_ai_result(result: DynamicStructureAIResult) -> str:
    """Render a compact CLI block for dynamic-structure AI proposals."""
    lines = ["Dynamic structure proposal:"]
    lines.append(f"  source: {result.source}")
    lines.append(f"  mode: {'apply' if result.applied else 'dry-run'}")
    if result.tier:
        lines.append(f"  tier: {result.tier}")
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


def _dynamic_structure_tier(ai_config: dict[str, object]):
    return resolve_named_tier(
        ai_config,
        str(ai_config.get("dynamic_structure_cost_tier", "low")),
    )


def _build_dynamic_structure_messages(context: dict[str, object]) -> list[dict[str, str]]:
    system_rules = (PROMPT_ROOT / "system_rules.txt").read_text(encoding="utf-8").strip()
    task_prompt = (PROMPT_ROOT / "dynamic_structure_proposal.txt").read_text(encoding="utf-8").strip()
    context_json = json.dumps(context, ensure_ascii=False, indent=2)
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
                ]
            ),
        },
    ]
