"""Character wake-up scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.agents.ranker import WakeCandidate, rank_character
from src.core.budget import BudgetManager
from src.world.state import WorldState


@dataclass(slots=True)
class WakeSchedule:
    """Selected characters for AI wake-up in the current step."""

    protagonists: list[WakeCandidate] = field(default_factory=list)
    active_characters: list[WakeCandidate] = field(default_factory=list)

    @property
    def all_candidates(self) -> list[WakeCandidate]:
        """Return all selected wake candidates in display order."""
        return self.protagonists + self.active_characters


def build_wake_schedule(state: WorldState, budget: BudgetManager) -> WakeSchedule:
    """Select characters to wake based on budgets and world conditions."""
    protagonist_candidates: list[WakeCandidate] = []
    active_candidates: list[WakeCandidate] = []

    for character in state.characters.values():
        candidate = rank_character(character, state)
        if character.character_level == "L3":
            protagonist_candidates.append(candidate)
        elif character.character_level == "L2":
            active_candidates.append(candidate)

    protagonist_candidates.sort(key=lambda item: item.score, reverse=True)
    active_candidates.sort(key=lambda item: item.score, reverse=True)

    return WakeSchedule(
        protagonists=protagonist_candidates[: budget.protagonist_budget],
        active_characters=active_candidates[: budget.active_character_budget],
    )
