"""Shared AI policy gates for cost-aware call decisions."""

from __future__ import annotations

from dataclasses import dataclass

from src.events.models import Event
from src.narrative.visibility import is_player_view


@dataclass(slots=True)
class AIPolicyDecision:
    """One resolved AI call decision."""

    allowed: bool
    reason: str
    signal_score: int = 0
    threshold: int = 0


def evaluate_intent_llm_policy(
    ai_config: dict[str, object],
    *,
    protagonist: bool,
    signal_score: int,
) -> AIPolicyDecision:
    """Resolve whether an intent request should spend an LLM call."""
    mode = str(ai_config.get("intent_llm_mode", "protagonist_only")).strip().lower()
    role = "protagonist" if protagonist else "active"
    if mode == "disabled":
        return AIPolicyDecision(False, "intent_policy_disabled", signal_score=signal_score)
    if mode == "protagonist_only" and not protagonist:
        return AIPolicyDecision(False, "intent_role_blocked", signal_score=signal_score)
    if mode == "active_only" and protagonist:
        return AIPolicyDecision(False, "intent_role_blocked", signal_score=signal_score)

    threshold_key = (
        "protagonist_intent_signal_threshold"
        if protagonist
        else "active_intent_signal_threshold"
    )
    default_threshold = 3 if protagonist else 4
    threshold = max(0, int(ai_config.get(threshold_key, default_threshold)))
    if signal_score < threshold:
        return AIPolicyDecision(
            False,
            f"intent_signal_below_threshold:{role}:{signal_score}<{threshold}",
            signal_score=signal_score,
            threshold=threshold,
        )
    return AIPolicyDecision(
        True,
        f"intent_allowed:{role}:{signal_score}>={threshold}",
        signal_score=signal_score,
        threshold=threshold,
    )


def evaluate_observer_llm_policy(
    ai_config: dict[str, object],
    *,
    mode: str,
    view: str,
    signal_score: int,
) -> AIPolicyDecision:
    """Resolve whether one watch observation should spend an LLM call."""
    policy = str(ai_config.get("observer_llm_mode", "brief_only")).strip().lower()
    if policy == "disabled":
        return AIPolicyDecision(False, "observer_policy_disabled", signal_score=signal_score)
    if policy == "truth_only" and is_player_view(view):
        return AIPolicyDecision(False, "observer_view_blocked", signal_score=signal_score)
    if policy == "full_only" and mode != "full":
        return AIPolicyDecision(False, "observer_mode_blocked", signal_score=signal_score)
    if policy == "brief_only" and mode != "brief":
        return AIPolicyDecision(False, "observer_mode_blocked", signal_score=signal_score)
    if policy not in {"all", "truth_only", "full_only", "brief_only", "manual_focus_only"}:
        if mode != "brief":
            return AIPolicyDecision(False, "observer_mode_blocked", signal_score=signal_score)

    threshold_key = (
        "observer_full_signal_threshold" if mode == "full" else "observer_brief_signal_threshold"
    )
    threshold = max(0, int(ai_config.get(threshold_key, 0)))
    if signal_score < threshold:
        return AIPolicyDecision(
            False,
            f"observer_signal_below_threshold:{mode}:{signal_score}<{threshold}",
            signal_score=signal_score,
            threshold=threshold,
        )
    return AIPolicyDecision(
        True,
        f"observer_allowed:{mode}:{signal_score}>={threshold}",
        signal_score=signal_score,
        threshold=threshold,
    )


def evaluate_chronicler_llm_policy(
    events: list[Event],
    ai_config: dict[str, object],
) -> AIPolicyDecision:
    """Resolve whether the current event batch deserves an LLM chronicle."""
    policy = str(ai_config.get("chronicler_llm_mode", "high_signal_only")).strip().lower()
    signal_score = chronicler_signal_score(events)
    if policy == "disabled":
        return AIPolicyDecision(False, "chronicle_policy_disabled", signal_score=signal_score)
    if policy == "fallback_only":
        return AIPolicyDecision(False, "chronicle_fallback_only", signal_score=signal_score)
    if policy == "all":
        return AIPolicyDecision(True, "chronicle_allowed:all", signal_score=signal_score)

    threshold = max(1, int(ai_config.get("chronicle_signal_threshold", 2)))
    if signal_score < threshold:
        return AIPolicyDecision(
            False,
            f"chronicle_signal_below_threshold:{signal_score}<{threshold}",
            signal_score=signal_score,
            threshold=threshold,
        )
    return AIPolicyDecision(
        True,
        f"chronicle_allowed:{signal_score}>={threshold}",
        signal_score=signal_score,
        threshold=threshold,
    )


def chronicler_signal_score(events: list[Event]) -> int:
    """Estimate whether a step has enough narrative signal for AI chronicle spend."""
    score = 0
    for event in events:
        score += _event_signal_points(event)
    return score


def _event_signal_points(event: Event) -> int:
    score = 0
    if event.severity == "high":
        score += 1
    if event.narrative_priority == "high":
        score += 1
    if event.event_scope in {"fallout", "character", "presence"}:
        score += 1
    if event.novelty == "high":
        score += 1
    if event.consequence_score == "high":
        score += 1
    return score
