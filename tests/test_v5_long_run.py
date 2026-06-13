import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.core.engine import WorldEngine
from src.storage.snapshots import load_world_state, save_world_state
from src.world.builder import build_world
from src.world.open_structure_template import (
    MAX_APPROVED_TEMPLATE_REGISTRY_ENTRIES,
    MAX_TEMPLATE_APPROVAL_QUEUE_ENTRIES,
    MAX_TEMPLATE_INSTANCES,
)


class V5LongRunTests(unittest.TestCase):
    def test_v5_template_state_stays_bounded_during_long_run(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        engine = WorldEngine(world, ai_config=DEFAULT_AI_CONFIG)

        for _ in range(12):
            engine.step()

        self.assertLessEqual(len(world.template_approval_queue.entries), MAX_TEMPLATE_APPROVAL_QUEUE_ENTRIES)
        self.assertLessEqual(len(world.approved_template_registry.templates), MAX_APPROVED_TEMPLATE_REGISTRY_ENTRIES)
        self.assertLessEqual(len(world.template_instances.instances), MAX_TEMPLATE_INSTANCES)
        self.assertLessEqual(len(world.ai_proposal_audits), 100)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save_world_state(world, path)
            loaded = load_world_state(path)

        self.assertEqual(len(loaded.template_approval_queue.entries), len(world.template_approval_queue.entries))
        self.assertEqual(len(loaded.approved_template_registry.templates), len(world.approved_template_registry.templates))
        self.assertEqual(len(loaded.template_instances.instances), len(world.template_instances.instances))


if __name__ == "__main__":
    unittest.main()
