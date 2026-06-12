"""AI budget management."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BudgetManager:
    """Tracks per-step AI wake-up budgets."""

    protagonist_budget: int
    active_character_budget: int
    chronicler_budget: int
    observation_budget_mode: str
    protagonist_intent_tier: str
    active_intent_tier: str
    observer_brief_tier: str
    observer_full_tier: str
    chronicler_tier: str

    @classmethod
    def from_config(cls, ai_config: dict[str, object]) -> "BudgetManager":
        """Build a budget manager from config values."""
        return cls(
            protagonist_budget=int(ai_config["protagonist_budget_per_week"]),
            active_character_budget=int(ai_config["active_character_budget_per_week"]),
            chronicler_budget=int(ai_config["chronicler_budget_per_week"]),
            observation_budget_mode=str(ai_config["observation_budget_mode"]),
            protagonist_intent_tier=str(ai_config.get("protagonist_intent_cost_tier", "medium")),
            active_intent_tier=str(ai_config.get("active_intent_cost_tier", "low")),
            observer_brief_tier=str(ai_config.get("observer_brief_cost_tier", "medium")),
            observer_full_tier=str(ai_config.get("observer_full_cost_tier", "high")),
            chronicler_tier=str(ai_config.get("chronicler_cost_tier", "medium")),
        )

    def describe(self) -> str:
        """Return one compact budget-and-tier summary line."""
        return (
            f"wake[p={self.protagonist_budget}@{self.protagonist_intent_tier},"
            f"a={self.active_character_budget}@{self.active_intent_tier}] "
            f"observer[b={self.observer_brief_tier},f={self.observer_full_tier},"
            f"mode={self.observation_budget_mode}] "
            f"chronicle[{self.chronicler_budget}@{self.chronicler_tier}]"
        )
