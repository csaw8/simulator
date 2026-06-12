import unittest
from unittest.mock import patch

from src.agents.prompt_builder import build_intent_messages
from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.core.ai_context import related_dynamic_structure_context_lines
from src.core.dynamic_structure_proposals import apply_dynamic_structure_proposals
from src.core.engine import WorldEngine
from src.narrative.observer import observe_region_with_ai
from src.world.builder import build_world


class FakeObserverClient:
    def __init__(self):
        self.messages = None

    def create_json_completion_with_limits(self, messages, *, max_tokens, thinking_budget):
        self.messages = messages
        return {"text": "局势正在被一条新的动态线索牵动。"}


def _world_with_dynamic_structure():
    world = build_world(DEFAULT_WORLD_CONFIG)
    region_id = next(iter(world.regions))
    payload = {
        "proposals": [
            {
                "action": "create",
                "structure_type": "anomaly_trace",
                "name": "Context Trace",
                "summary": "A context trace is affecting the region without changing fixed fields.",
                "scope_refs": [region_id],
                "linked_refs": [next(iter(world.relics))],
                "tags": ["context"],
                "visibility": "visible",
                "pressure": "high",
                "relation_type": "trace_of",
            }
        ]
    }
    structure_id = apply_dynamic_structure_proposals(world, payload).accepted[0]
    return world, region_id, structure_id


class DynamicStructureContextTests(unittest.TestCase):
    def test_related_dynamic_structure_lines_exclude_archived(self) -> None:
        world, region_id, structure_id = _world_with_dynamic_structure()

        active_lines = related_dynamic_structure_context_lines(
            world,
            [region_id],
            view="truth",
        )
        world.dynamic_structures[structure_id].status = "archived"
        archived_lines = related_dynamic_structure_context_lines(
            world,
            [region_id],
            view="truth",
        )

        self.assertIn("Context Trace", "\n".join(active_lines))
        self.assertEqual(archived_lines, ["- None"])

    def test_player_dynamic_structure_context_does_not_leak_internal_id(self) -> None:
        world, region_id, _ = _world_with_dynamic_structure()

        text = "\n".join(
            related_dynamic_structure_context_lines(
                world,
                [region_id],
                view="player",
            )
        )

        self.assertIn("anomaly trace", text)
        self.assertNotIn("dyn_", text)
        self.assertNotIn("Context Trace", text)

    def test_intent_prompt_includes_related_dynamic_structures_as_read_only_context(self) -> None:
        world, region_id, _ = _world_with_dynamic_structure()
        character = next(
            character
            for character in world.characters.values()
            if character.current_region_id == region_id
        )

        messages = build_intent_messages(world, character)
        user_prompt = messages[-1]["content"]

        self.assertIn("Setting summary:", user_prompt)
        self.assertIn("Anomaly mode: exceptional_presence", user_prompt)
        self.assertIn("Related dynamic structures (read-only context; do not target these ids):", user_prompt)
        self.assertIn("anomaly trace", user_prompt)
        self.assertNotIn("dyn_", user_prompt)

    def test_observer_prompt_includes_related_dynamic_structures(self) -> None:
        world, region_id, _ = _world_with_dynamic_structure()
        cfg = DEFAULT_AI_CONFIG.copy()
        cfg["observer_llm_mode"] = "all"
        cfg["observer_full_signal_threshold"] = 0
        fake_client = FakeObserverClient()

        with patch("src.narrative.observer.build_siliconflow_client", return_value=fake_client):
            result = observe_region_with_ai(
                world,
                region_id,
                cfg,
                mode="full",
                view="truth",
            )

        self.assertEqual(result.source, "deepseek")
        prompt = fake_client.messages[-1]["content"]
        self.assertIn("World style profile:", prompt)
        self.assertIn("realistic future technology civilization", prompt)
        self.assertIn("Narrative voice: Use a grounded public-observer tone", prompt)
        self.assertIn("Related dynamic structures:", prompt)
        self.assertIn("Context Trace", prompt)
        self.assertIn("dyn_", prompt)


if __name__ == "__main__":
    unittest.main()
