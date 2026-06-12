"""Shared AI cost-tier helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AITierSettings:
    """Resolved token and thinking limits for one AI call."""

    tier: str
    max_tokens: int
    thinking_budget: int


def resolve_named_tier(ai_config: dict[str, object], tier: str) -> AITierSettings:
    """Resolve one named cost tier from config."""
    normalized = tier.strip().lower()
    if normalized not in {"low", "medium", "high"}:
        normalized = "medium"
    return AITierSettings(
        tier=normalized,
        max_tokens=int(ai_config.get(f"{normalized}_cost_max_tokens", 0)),
        thinking_budget=int(ai_config.get(f"{normalized}_cost_thinking_budget", 0)),
    )


def resolve_intent_tier(ai_config: dict[str, object], *, protagonist: bool) -> AITierSettings:
    """Resolve tier settings for an intent-generation call."""
    tier = str(
        ai_config.get(
            "protagonist_intent_cost_tier" if protagonist else "active_intent_cost_tier",
            "medium" if protagonist else "low",
        )
    )
    return resolve_named_tier(ai_config, tier)


def resolve_observer_tier(ai_config: dict[str, object], *, mode: str) -> AITierSettings:
    """Resolve tier settings for one observer call."""
    if mode == "full":
        tier = str(ai_config.get("observer_full_cost_tier", "high"))
    else:
        tier = str(ai_config.get("observer_brief_cost_tier", "medium"))
    return resolve_named_tier(ai_config, tier)


def resolve_chronicler_tier(ai_config: dict[str, object]) -> AITierSettings:
    """Resolve tier settings for one chronicler call."""
    return resolve_named_tier(ai_config, str(ai_config.get("chronicler_cost_tier", "medium")))
