"""Candidate ranking utilities."""

from __future__ import annotations

from dataclasses import dataclass

from src.events.query import find_character_flashpoint_events
from src.world.character import Character
from src.world.state import WorldState

_LEVEL_SCORE = {"L3": 40, "L2": 20, "L1": 8, "L0": 0}
_TIER_SCORE = {"low": 0, "medium": 8, "high": 16}
_INITIATIVE_SCORE = {"low": 2, "medium": 5, "high": 9}
_AGENCY_SCORE = {"reactive": 3, "opportunistic": 6, "strategic": 10}


@dataclass(slots=True)
class WakeCandidate:
    """A ranked wake-up candidate for the current step."""

    character_id: str
    score: int
    reasons: list[str]


def rank_character(character: Character, state: WorldState) -> WakeCandidate:
    """Rank a character for this step based on world context."""
    reasons: list[str] = []
    score = _LEVEL_SCORE.get(character.character_level, 0)
    if score:
        reasons.append(f"level:{character.character_level}")

    score += min(character.wake_priority_seed, 20)
    if character.wake_priority_seed:
        reasons.append("seed_priority")

    region = state.regions[character.current_region_id]
    region_pressure = max(
        _TIER_SCORE.get(region.scarcity, 0),
        _TIER_SCORE.get(region.political_tension, 0),
    )
    if region_pressure:
        score += region_pressure
        reasons.append("regional_pressure")

    low_security_bonus = {"high": 0, "medium": 4, "low": 10}.get(region.security, 0)
    if low_security_bonus:
        score += low_security_bonus
        reasons.append("security_instability")

    score += _INITIATIVE_SCORE.get(character.initiative, 0)
    score += _AGENCY_SCORE.get(character.agency_mode, 0)

    if character.observation_trace > 0:
        score += min(character.observation_trace * 3, 12)
        reasons.append("observer_attention")

    if state.active_event_ids:
        score += min(len(state.active_event_ids), 5)
        reasons.append("active_event_context")

    flashpoint_events = find_character_flashpoint_events(state, character, limit=3)
    if flashpoint_events:
        score += min(len(flashpoint_events) * 4, 12)
        reasons.append("flashpoint_proximity")
        if any(event.relic_refs for event in flashpoint_events):
            score += 6
            reasons.append("relic_pressure")

    if character.status != "active":
        score -= 15
        reasons.append("inactive_penalty")

    return WakeCandidate(character_id=character.char_id, score=score, reasons=reasons)
