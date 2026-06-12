"""Configuration models."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class WorldConfig:
    """World initialization configuration."""

    seed: int
    region_count: int
    civilization_count: int
    relic_count: int
    protagonist_count: int
    active_character_count: int

    def to_dict(self) -> dict[str, int]:
        """Return a plain dictionary for existing builder interfaces."""
        return asdict(self)


@dataclass(slots=True)
class AIConfig:
    """LLM and runtime budget configuration."""

    provider: str
    base_url: str
    api_key_env: str
    model: str
    temperature: float
    max_tokens: int
    request_timeout_seconds: int
    thinking_budget: int
    thinking_mode: str
    reasoning_effort: str
    low_cost_max_tokens: int
    low_cost_thinking_budget: int
    medium_cost_max_tokens: int
    medium_cost_thinking_budget: int
    high_cost_max_tokens: int
    high_cost_thinking_budget: int
    observer_max_tokens: int
    observer_thinking_budget: int
    observer_full_max_tokens: int
    observer_full_thinking_budget: int
    protagonist_budget_per_week: int
    active_character_budget_per_week: int
    chronicler_budget_per_week: int
    observation_budget_mode: str
    intent_llm_mode: str
    protagonist_intent_cost_tier: str
    active_intent_cost_tier: str
    protagonist_intent_signal_threshold: int
    active_intent_signal_threshold: int
    observer_llm_mode: str
    observer_brief_cost_tier: str
    observer_full_cost_tier: str
    observer_brief_signal_threshold: int
    observer_full_signal_threshold: int
    chronicler_llm_mode: str
    chronicler_cost_tier: str
    chronicle_signal_threshold: int
    observer_focus_ai_enabled: bool
    dynamic_structure_cost_tier: str
    emergent_presence_cost_tier: str
    descriptor_profile_cost_tier: str

    def to_dict(self) -> dict[str, object]:
        """Return a plain dictionary for existing integrations."""
        return asdict(self)


@dataclass(slots=True)
class AppConfig:
    """Top-level application configuration bundle."""

    world: WorldConfig
    ai: AIConfig
