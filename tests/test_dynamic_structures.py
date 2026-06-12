import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.config.models import AIConfig, WorldConfig
from src.core.dynamic_structure_proposals import apply_dynamic_structure_proposals
from src.core.engine import WorldEngine
from src.events.query import select_events
from src.interfaces.commands import CommandContext, handle_command
from src.interfaces.stream_view import format_status
from src.narrative.summaries import summarize_dynamic_structure
from src.storage.snapshots import load_world_state, save_world_state
from src.world.builder import build_world


def _build_world():
    world = build_world(DEFAULT_WORLD_CONFIG)
    return world


def _sample_payload(world):
    return {
        "proposals": [
            {
                "action": "create",
                "structure_type": "incident_site",
                "name": "North Lockdown Belt",
                "summary": "A disputed project perimeter has become a visible incident site.",
                "scope_refs": [next(iter(world.regions))],
                "linked_refs": [next(iter(world.projects)), next(iter(world.region_nodes))],
                "tags": ["site_accident", "containment", "labor_unrest"],
                "visibility": "visible",
                "pressure": "high",
                "relation_type": "pressures",
            }
        ]
    }


class DynamicStructureTests(unittest.TestCase):
    def test_dynamic_structure_proposal_creates_independent_structure_and_bridges(self) -> None:
        world = _build_world()
        result = apply_dynamic_structure_proposals(world, _sample_payload(world), origin="unit_test")

        self.assertEqual(len(result.accepted), 1)
        self.assertFalse(result.rejected)
        structure_id = result.accepted[0]
        self.assertIn(structure_id, world.dynamic_structures)
        structure = world.dynamic_structures[structure_id]
        self.assertEqual(structure.structure_type, "incident_site")
        self.assertEqual(structure.origin, "unit_test")
        self.assertTrue(structure.influence_refs)

        self.assertEqual(len(result.events), 1)
        event = result.events[0]
        self.assertIn(structure_id, event.dynamic_structure_refs)
        self.assertIn(event.event_id, structure.source_event_refs)
        self.assertTrue(any(relation.source_ref == structure_id for relation in world.relations.values()))
        self.assertTrue(any(thread.scope_ref == structure_id for thread in world.pressure_threads.values()))

    def test_dynamic_structure_rejects_unknown_refs_and_types(self) -> None:
        world = _build_world()
        result = apply_dynamic_structure_proposals(
            world,
            {
                "proposals": [
                    {
                        "action": "create",
                        "structure_type": "freeform_empire",
                        "name": "Bad",
                        "summary": "Bad",
                        "scope_refs": ["missing_ref"],
                    }
                ]
            },
        )

        self.assertFalse(result.accepted)
        self.assertTrue(result.rejected)
        self.assertFalse(world.dynamic_structures)

    def test_dynamic_structure_summary_and_events_are_player_safe(self) -> None:
        world = _build_world()
        structure_id = apply_dynamic_structure_proposals(world, _sample_payload(world)).accepted[0]

        text = summarize_dynamic_structure(
            world,
            structure_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        self.assertIn("动态线索观察", text)
        self.assertIn("局势线索:", text)
        self.assertIn("可见线索:", text)
        self.assertNotIn("tags:", text)
        self.assertNotIn("dyn_", text)
        self.assertNotIn("pressure_threads:", text)

        selected = select_events(
            world.event_stream.events,
            target_type="dynamic",
            target_id=structure_id,
            limit=5,
            view="truth",
        )
        self.assertEqual(len(selected), 1)

    def test_dynamic_structures_are_preserved_in_snapshots(self) -> None:
        world = _build_world()
        structure_id = apply_dynamic_structure_proposals(world, _sample_payload(world)).accepted[0]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save_world_state(world, path)
            loaded = load_world_state(path)

        self.assertIn(structure_id, loaded.dynamic_structures)
        self.assertEqual(
            loaded.dynamic_structures[structure_id].name,
            world.dynamic_structures[structure_id].name,
        )
        self.assertTrue(any(event.dynamic_structure_refs for event in loaded.event_stream.events))

    def test_status_and_cli_watch_dynamic_structure(self) -> None:
        world = _build_world()
        structure_id = apply_dynamic_structure_proposals(world, _sample_payload(world)).accepted[0]
        status = format_status(world)
        self.assertIn("dynamic_structures: 1", status)

        cfg = DEFAULT_AI_CONFIG.copy()
        cfg["provider"] = "none"
        with tempfile.TemporaryDirectory() as tmp:
            context = CommandContext(
                engine=WorldEngine(world, ai_config=cfg),
                world_config=WorldConfig(**DEFAULT_WORLD_CONFIG),
                ai_config=AIConfig(**cfg),
                snapshot_path=Path(tmp) / "world.json",
            )
            output = handle_command(context, f"watch dynamic {structure_id} full player")

        self.assertIn("动态线索观察", output)
        self.assertNotIn("dyn_", output)
        self.assertNotIn("tags:", output)


if __name__ == "__main__":
    unittest.main()
