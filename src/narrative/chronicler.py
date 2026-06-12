"""Chronicle summary generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.agents.llm_client import LLMClientError, build_siliconflow_client
from src.core.ai_policy import evaluate_chronicler_llm_policy
from src.core.ai_tiers import resolve_chronicler_tier
from src.events.filters import select_chronicle_events
from src.events.models import Event
from src.events.visibility_rules import filter_events_for_view, format_event_summary_for_view
from src.narrative.visibility import is_player_view
from src.world.state import WorldState

PROMPT_ROOT = Path("prompts")


@dataclass(slots=True)
class ChronicleResult:
    """Narrative summary for a step."""

    source: str
    text: str | None
    error: str | None = None
    tier: str | None = None


def generate_chronicle(
    events: list[Event],
    ai_config: dict[str, object],
) -> ChronicleResult:
    """Generate a short chronicle note for the current step."""
    selected = select_chronicle_events(events, limit=5)
    if not selected:
        return ChronicleResult(source="none", text=None)

    decision = evaluate_chronicler_llm_policy(selected, ai_config)
    if not decision.allowed:
        return ChronicleResult(
            source="fallback",
            text=_fallback_chronicle(selected),
            error=decision.reason,
        )

    client = build_siliconflow_client(ai_config)
    if client is None:
        return ChronicleResult(source="fallback", text=_fallback_chronicle(selected))

    try:
        tier = resolve_chronicler_tier(ai_config)
        payload = client.create_json_completion_with_limits(
            _build_chronicler_messages(selected),
            max_tokens=tier.max_tokens,
            thinking_budget=tier.thinking_budget,
        )
        text = str(payload.get("text", "")).strip()
        if not text:
            raise LLMClientError("Chronicler JSON missing text")
        return ChronicleResult(source="siliconflow", text=text, tier=tier.tier)
    except LLMClientError as exc:
        return ChronicleResult(
            source="fallback",
            text=_fallback_chronicle(selected),
            error=str(exc),
            tier=resolve_chronicler_tier(ai_config).tier,
        )


def format_chronicle_for_view(
    chronicle: ChronicleResult | None,
    events: list[Event],
    *,
    view: str = "truth",
    world: WorldState | None = None,
) -> ChronicleResult | None:
    """Return a chronicle block suitable for the requested observer view."""
    if not is_player_view(view):
        return chronicle

    selected = select_chronicle_events(filter_events_for_view(events, view=view), limit=4)
    if not selected:
        return None
    return ChronicleResult(
        source="player_fallback",
        text=_player_fallback_chronicle(selected, world=world),
        error=None,
    )


def _build_chronicler_messages(events: list[Event]) -> list[dict[str, str]]:
    system_rules = (PROMPT_ROOT / "system_rules.txt").read_text(encoding="utf-8").strip()
    chronicler_prompt = (PROMPT_ROOT / "chronicler_summary.txt").read_text(
        encoding="utf-8"
    ).strip()
    event_lines = [f"- [{event.event_type}] {event.summary}" for event in events]
    user_prompt = "\n".join(
        [
            chronicler_prompt,
            "",
            "Return a JSON object with one key: text.",
            "text must be one short chronicle paragraph in Chinese.",
            "Keep text under 120 Chinese characters.",
            "Use a restrained, historical tone.",
            "Do not invent facts beyond the supplied events.",
            "",
            "Events:",
            *event_lines,
        ]
    )
    return [
        {"role": "system", "content": system_rules},
        {"role": "user", "content": user_prompt},
    ]


def _fallback_chronicle(events: list[Event]) -> str:
    fragments = [event.summary for event in events[:3]]
    if not fragments:
        return ""
    return "本周局势没有骤然倾覆，而是在几处关键压力线上继续偏移：" + "；".join(
        fragments
    )
def _player_fallback_chronicle(
    events: list[Event],
    *,
    world: WorldState | None = None,
) -> str:
    fragments = [
        format_event_summary_for_view(event, view="player", world=world).rstrip("。.")
        for event in events[:3]
    ]
    if not fragments:
        return ""
    return "本周可见局势继续推进：" + "；".join(fragments) + "。"
