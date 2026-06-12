import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.core.engine import WorldEngine
from src.core.dynamic_structure_proposals import apply_dynamic_structure_proposals
from src.storage.snapshots import load_world_state, save_world_state
from src.world.builder import build_world


def _build_evolved_world(steps: int = 8):
    cfg = DEFAULT_AI_CONFIG.copy()
    cfg["provider"] = "none"
    world = build_world(DEFAULT_WORLD_CONFIG)
    engine = WorldEngine(world, ai_config=cfg)
    for _ in range(steps):
        engine.step()
    return world


class SnapshotTests(unittest.TestCase):
    def test_snapshot_preserves_region_nodes_and_pressure_threads(self) -> None:
        world = _build_evolved_world()
        self.assertGreater(len(world.region_nodes), 0)
        self.assertGreater(len(world.pressure_threads), 0)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save_world_state(world, path)
            loaded = load_world_state(path)

        self.assertEqual(len(loaded.region_nodes), len(world.region_nodes))
        self.assertEqual(len(loaded.pressure_threads), len(world.pressure_threads))
        self.assertTrue(any(thread.summary for thread in loaded.pressure_threads.values()))

    def test_snapshot_preserves_dynamic_structures(self) -> None:
        world = _build_evolved_world()
        result = apply_dynamic_structure_proposals(
            world,
            {
                "proposals": [
                    {
                        "action": "create",
                        "structure_type": "rumor_network",
                        "name": "Archive Whisper Chain",
                        "summary": "A loose rumor channel is amplifying archive-related pressure.",
                        "scope_refs": [next(iter(world.regions))],
                        "linked_refs": [next(iter(world.relics))],
                        "tags": ["archive", "rumor"],
                        "visibility": "rumored",
                        "pressure": "medium",
                        "relation_type": "rumor_source_for",
                    }
                ]
            },
        )
        structure_id = result.accepted[0]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save_world_state(world, path)
            loaded = load_world_state(path)

        self.assertIn(structure_id, loaded.dynamic_structures)
        self.assertTrue(any(event.dynamic_structure_refs for event in loaded.event_stream.events))


if __name__ == "__main__":
    unittest.main()
