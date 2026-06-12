import unittest

from src.config.defaults import DEFAULT_AI_CONFIG
from src.core.ai_policy import (
    chronicler_signal_score,
    evaluate_chronicler_llm_policy,
    evaluate_intent_llm_policy,
    evaluate_observer_llm_policy,
)
from src.core.budget import BudgetManager
from src.core.ai_tiers import (
    resolve_chronicler_tier,
    resolve_intent_tier,
    resolve_named_tier,
    resolve_observer_tier,
)
from src.core.engine import WorldEngine
from src.events.models import Event
from src.interfaces.stream_view import format_step_result
from src.world.builder import build_world
from src.config.defaults import DEFAULT_WORLD_CONFIG


class AITierTests(unittest.TestCase):
    def test_named_tier_uses_configured_limits(self) -> None:
        settings = resolve_named_tier(DEFAULT_AI_CONFIG, "high")
        self.assertEqual(settings.tier, "high")
        self.assertEqual(settings.max_tokens, DEFAULT_AI_CONFIG["high_cost_max_tokens"])
        self.assertEqual(
            settings.thinking_budget,
            DEFAULT_AI_CONFIG["high_cost_thinking_budget"],
        )

    def test_intent_tiers_split_protagonist_and_active(self) -> None:
        protagonist = resolve_intent_tier(DEFAULT_AI_CONFIG, protagonist=True)
        active = resolve_intent_tier(DEFAULT_AI_CONFIG, protagonist=False)
        self.assertEqual(protagonist.tier, DEFAULT_AI_CONFIG["protagonist_intent_cost_tier"])
        self.assertEqual(active.tier, DEFAULT_AI_CONFIG["active_intent_cost_tier"])

    def test_observer_tiers_split_brief_and_full(self) -> None:
        brief = resolve_observer_tier(DEFAULT_AI_CONFIG, mode="brief")
        full = resolve_observer_tier(DEFAULT_AI_CONFIG, mode="full")
        self.assertEqual(brief.tier, DEFAULT_AI_CONFIG["observer_brief_cost_tier"])
        self.assertEqual(full.tier, DEFAULT_AI_CONFIG["observer_full_cost_tier"])
        self.assertGreaterEqual(full.max_tokens, brief.max_tokens)

    def test_chronicler_uses_configured_tier(self) -> None:
        settings = resolve_chronicler_tier(DEFAULT_AI_CONFIG)
        self.assertEqual(settings.tier, DEFAULT_AI_CONFIG["chronicler_cost_tier"])

    def test_budget_manager_describe_includes_tiers(self) -> None:
        summary = BudgetManager.from_config(DEFAULT_AI_CONFIG).describe()
        self.assertIn("wake[p=", summary)
        self.assertIn("@medium", summary)
        self.assertIn("observer[", summary)
        self.assertIn("chronicle[", summary)

    def test_step_result_surfaces_ai_budget_summary(self) -> None:
        cfg = DEFAULT_AI_CONFIG.copy()
        cfg["provider"] = "none"
        world = build_world(DEFAULT_WORLD_CONFIG)
        engine = WorldEngine(world, ai_config=cfg)
        result = engine.step()
        text = format_step_result(result, 1, view="truth", world=world)
        self.assertIn("ai_budget_summary:", text)

    def test_intent_policy_applies_signal_threshold(self) -> None:
        cfg = DEFAULT_AI_CONFIG.copy()
        decision = evaluate_intent_llm_policy(cfg, protagonist=True, signal_score=1)
        self.assertFalse(decision.allowed)
        self.assertIn("below_threshold", decision.reason)

    def test_observer_policy_blocks_full_when_brief_only(self) -> None:
        cfg = DEFAULT_AI_CONFIG.copy()
        cfg["observer_llm_mode"] = "brief_only"
        decision = evaluate_observer_llm_policy(
            cfg,
            mode="full",
            view="truth",
            signal_score=5,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "observer_mode_blocked")

    def test_observer_policy_default_truth_only_allows_full_truth(self) -> None:
        decision = evaluate_observer_llm_policy(
            DEFAULT_AI_CONFIG,
            mode="full",
            view="truth",
            signal_score=8,
        )
        self.assertTrue(decision.allowed)

    def test_chronicler_policy_uses_unified_signal_score(self) -> None:
        cfg = DEFAULT_AI_CONFIG.copy()
        events = [
            Event(
                event_id="evt_1",
                tick=1,
                time_granularity="week",
                event_type="project_accident",
                event_scope="fallout",
                title="Accident",
                summary="A major construction accident destabilized the site.",
                severity="high",
                narrative_priority="high",
                novelty="high",
                consequence_score="high",
            ),
            Event(
                event_id="evt_2",
                tick=1,
                time_granularity="week",
                event_type="archive_breach",
                event_scope="presence",
                title="Breach",
                summary="An archive breach pushed the region into cascading inquiry and panic.",
                severity="high",
                narrative_priority="high",
                novelty="high",
                consequence_score="high",
            ),
            Event(
                event_id="evt_3",
                tick=1,
                time_granularity="week",
                event_type="power_struggle",
                event_scope="character",
                title="Struggle",
                summary="A factional power struggle spilled into visible public conflict.",
                severity="high",
                narrative_priority="high",
                novelty="medium",
                consequence_score="high",
            ),
            Event(
                event_id="evt_4",
                tick=1,
                time_granularity="week",
                event_type="containment_breach",
                event_scope="fallout",
                title="Breach 2",
                summary="Containment failed again and spread consequences across adjacent districts.",
                severity="high",
                narrative_priority="high",
                novelty="high",
                consequence_score="high",
            ),
        ]
        self.assertGreaterEqual(chronicler_signal_score(events), cfg["chronicle_signal_threshold"])
        decision = evaluate_chronicler_llm_policy(events, cfg)
        self.assertTrue(decision.allowed)


if __name__ == "__main__":
    unittest.main()
