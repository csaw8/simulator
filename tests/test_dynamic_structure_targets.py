import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.config.models import AIConfig, WorldConfig
from src.core.dynamic_structure_proposals import apply_dynamic_structure_proposals
from src.core.dynamic_structure_targets import (
    format_dynamic_structure_targets,
    select_dynamic_structure_targets,
)
from src.core.engine import WorldEngine
from src.interfaces.commands import CommandContext, handle_command
from src.world.builder import build_world


def _world_with_signal(steps: int = 8):
    cfg = DEFAULT_AI_CONFIG.copy()
    cfg["provider"] = "none"
    world = build_world(DEFAULT_WORLD_CONFIG)
    engine = WorldEngine(world, ai_config=cfg)
    for _ in range(steps):
        engine.step()
    return world


def _payload_for_region(world, region_id: str):
    return {
        "proposals": [
            {
                "action": "create",
                "structure_type": "incident_site",
                "name": "Target Selection Incident Site",
                "summary": "A target selection test site is forming around the region.",
                "scope_refs": [region_id],
                "linked_refs": [next(iter(world.relics))],
                "tags": ["target_selection"],
                "visibility": "visible",
                "pressure": "medium",
                "relation_type": "pressures",
            }
        ]
    }


class DynamicStructureTargetTests(unittest.TestCase):
    def test_select_dynamic_structure_targets_returns_ranked_candidates(self) -> None:
        world = _world_with_signal()

        candidates = select_dynamic_structure_targets(world, limit=5)

        self.assertTrue(candidates)
        self.assertLessEqual(len(candidates), 5)
        self.assertTrue(any(candidate.recommended for candidate in candidates))
        scores = [candidate.signal_score for candidate in candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_existing_nearby_dynamic_reduces_candidate_priority(self) -> None:
        world = _world_with_signal()
        region_id = next(iter(world.regions))
        before = next(
            candidate
            for candidate in select_dynamic_structure_targets(world, limit=100)
            if candidate.target_id == region_id
        )
        apply_dynamic_structure_proposals(world, _payload_for_region(world, region_id))
        after = next(
            candidate
            for candidate in select_dynamic_structure_targets(world, limit=100)
            if candidate.target_id == region_id
        )

        self.assertGreaterEqual(before.signal_score, after.signal_score)
        self.assertGreater(after.nearby_dynamic_count, 0)

    def test_format_dynamic_structure_targets_is_cli_readable(self) -> None:
        world = _world_with_signal()

        text = format_dynamic_structure_targets(world, limit=3)

        self.assertIn("Dynamic structure target candidates", text)
        self.assertIn("score=", text)
        self.assertIn("recommended", text)

    def test_cli_targets_dynamic_command(self) -> None:
        world = _world_with_signal()
        cfg = DEFAULT_AI_CONFIG.copy()
        cfg["provider"] = "none"
        with tempfile.TemporaryDirectory() as tmp:
            context = CommandContext(
                engine=WorldEngine(world, ai_config=cfg),
                world_config=WorldConfig(**DEFAULT_WORLD_CONFIG),
                ai_config=AIConfig(**cfg),
                snapshot_path=Path(tmp) / "world.json",
            )
            output = handle_command(context, "targets dynamic 3")

        self.assertIn("Dynamic structure target candidates", output)
        self.assertLessEqual(output.count("\n  - "), 3)


if __name__ == "__main__":
    unittest.main()
