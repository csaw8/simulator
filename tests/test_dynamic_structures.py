import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.config.models import AIConfig, WorldConfig
from src.core.ai_context import build_dynamic_structure_context
from src.core.dynamic_structure_proposals import (
    apply_dynamic_structure_proposals,
    validate_dynamic_structure_proposals,
)
from src.core.engine import WorldEngine, _refresh_dynamic_structure_lifecycle
from src.events.models import Event
from src.events.query import select_events
from src.interfaces.commands import CommandContext, handle_command
from src.interfaces.stream_view import format_status
from src.narrative.summaries import summarize_dynamic_structure
from src.narrative.summaries import summarize_faction
from src.narrative.summaries import summarize_project
from src.narrative.summaries import summarize_region
from src.narrative.summaries import summarize_region_node
from src.narrative.summaries import summarize_relic
from src.narrative.summaries import summarize_supply_line
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
                "linked_refs": [
                    next(iter(world.projects)),
                    next(iter(world.region_nodes)),
                    next(iter(world.relics)),
                    next(iter(world.factions)),
                    next(iter(world.supply_lines)),
                ],
                "tags": ["site_accident", "containment", "labor_unrest"],
                "visibility": "visible",
                "pressure": "high",
                "relation_type": "pressures",
            }
        ]
    }


def _duplicate_payload(world):
    return {
        "proposals": [
            {
                "action": "create",
                "structure_type": "incident_site",
                "name": "North Lockdown Belt Extended",
                "summary": "The same disputed perimeter has widened into adjacent logistics choke points.",
                "scope_refs": [next(iter(world.regions))],
                "linked_refs": [
                    next(iter(world.projects)),
                    next(iter(world.supply_lines)),
                ],
                "tags": ["site_accident", "logistics_choke"],
                "visibility": "visible",
                "pressure": "medium",
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

    def test_duplicate_dynamic_structure_create_updates_existing_structure(self) -> None:
        world = _build_world()
        first_id = apply_dynamic_structure_proposals(world, _sample_payload(world)).accepted[0]

        result = apply_dynamic_structure_proposals(world, _duplicate_payload(world))

        self.assertEqual(result.accepted, [first_id])
        self.assertEqual(len(world.dynamic_structures), 1)
        self.assertEqual(world.dynamic_structures[first_id].name, "North Lockdown Belt Extended")
        self.assertIn(next(iter(world.supply_lines)), world.dynamic_structures[first_id].linked_refs)
        self.assertTrue(
            any(
                event.event_type == "dynamic_structure_updated"
                and first_id in event.dynamic_structure_refs
                for event in result.events
            )
        )

    def test_duplicate_dynamic_structure_dry_run_marks_update_target(self) -> None:
        world = _build_world()
        first_id = apply_dynamic_structure_proposals(world, _sample_payload(world)).accepted[0]

        result = validate_dynamic_structure_proposals(world, _duplicate_payload(world))

        self.assertEqual(result.accepted, [f"proposal[0]->update:{first_id}"])
        self.assertEqual(len(world.dynamic_structures), 1)

    def test_archived_dynamic_structure_does_not_block_new_create(self) -> None:
        world = _build_world()
        first_id = apply_dynamic_structure_proposals(world, _sample_payload(world)).accepted[0]
        world.dynamic_structures[first_id].status = "archived"

        result = apply_dynamic_structure_proposals(world, _duplicate_payload(world))

        self.assertEqual(len(world.dynamic_structures), 2)
        self.assertNotEqual(result.accepted, [first_id])

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

    def test_dynamic_structure_links_appear_in_fixed_object_summaries(self) -> None:
        world = _build_world()
        apply_dynamic_structure_proposals(world, _sample_payload(world))
        refs_and_summaries = [
            (next(iter(world.regions)), summarize_region),
            (next(iter(world.projects)), summarize_project),
            (next(iter(world.region_nodes)), summarize_region_node),
            (next(iter(world.relics)), summarize_relic),
            (next(iter(world.factions)), summarize_faction),
            (next(iter(world.supply_lines)), summarize_supply_line),
        ]

        for ref, summary_func in refs_and_summaries:
            with self.subTest(ref=ref):
                player_text = summary_func(world, ref, event_limit=5, mode="full", view="player")
                truth_text = summary_func(world, ref, event_limit=5, mode="full", view="truth")
                self.assertIn("动态线索:", player_text)
                self.assertIn("dynamic_structures:", truth_text)
                self.assertIn("North Lockdown Belt", truth_text)
                self.assertNotIn("dyn_", player_text)
                self.assertNotIn("dynamic_structures:", player_text)

    def test_dynamic_structure_lifecycle_cools_and_archives_stale_structures(self) -> None:
        world = _build_world()
        structure_id = apply_dynamic_structure_proposals(world, _sample_payload(world)).accepted[0]
        structure = world.dynamic_structures[structure_id]

        world.current_tick = structure.updated_tick + 9
        _refresh_dynamic_structure_lifecycle(world, [])
        self.assertEqual(structure.status, "cooling")

        world.current_tick = structure.updated_tick + 21
        _refresh_dynamic_structure_lifecycle(world, [])
        self.assertEqual(structure.status, "archived")

        region_id = next(iter(world.regions))
        player_text = summarize_region(world, region_id, event_limit=5, mode="full", view="player")
        truth_text = summarize_region(world, region_id, event_limit=5, mode="full", view="truth")
        self.assertIn("动态线索: 外界暂未看出稳定动态牵连", player_text)
        self.assertIn("dynamic_structures: None", truth_text)

    def test_dynamic_structure_direct_event_reactivates_archived_structure(self) -> None:
        world = _build_world()
        structure_id = apply_dynamic_structure_proposals(world, _sample_payload(world)).accepted[0]
        structure = world.dynamic_structures[structure_id]
        structure.status = "archived"
        world.current_tick = 30
        event = Event(
            event_id="event_dynamic_refresh",
            tick=30,
            time_granularity="week",
            event_type="dynamic_structure_updated",
            event_scope="dynamic_structure",
            title="Dynamic refresh",
            summary="The dynamic structure was refreshed by a direct event.",
            dynamic_structure_refs=[structure_id],
        )

        _refresh_dynamic_structure_lifecycle(world, [event])

        self.assertEqual(structure.status, "active")
        self.assertEqual(structure.updated_tick, 30)

    def test_archived_dynamic_structures_are_excluded_from_ai_context(self) -> None:
        world = _build_world()
        structure_id = apply_dynamic_structure_proposals(world, _sample_payload(world)).accepted[0]
        world.dynamic_structures[structure_id].status = "archived"
        region_id = next(iter(world.regions))

        context = build_dynamic_structure_context(
            world,
            target_type="region",
            target_id=region_id,
        )

        self.assertEqual(context["nearby_dynamic_structures"], [])

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

    def test_dynamic_structure_apply_survives_long_run_without_leaks_or_growth(self) -> None:
        world = _build_world()
        structure_id = apply_dynamic_structure_proposals(world, _sample_payload(world)).accepted[0]
        cfg = DEFAULT_AI_CONFIG.copy()
        cfg["provider"] = "none"
        engine = WorldEngine(world, ai_config=cfg)

        for _ in range(60):
            engine.step()

        self.assertEqual(len(world.dynamic_structures), 1)
        self.assertEqual(world.dynamic_structures[structure_id].status, "archived")
        self.assertTrue(
            any(structure_id in event.dynamic_structure_refs for event in world.event_stream.events),
            "expected original dynamic structure event to remain traceable after long run",
        )
        refs = {thread.scope_ref for thread in world.pressure_threads.values()}
        self.assertLessEqual(
            max(
                sum(1 for thread in world.pressure_threads.values() if thread.scope_ref == ref)
                for ref in refs
            ),
            5,
        )

        region_id = next(iter(world.regions))
        region_text = summarize_region(world, region_id, event_limit=5, mode="full", view="player")
        dynamic_text = summarize_dynamic_structure(
            world,
            structure_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        self.assertIn("动态线索: 外界暂未看出稳定动态牵连", region_text)
        self.assertNotIn("dyn_", region_text)
        self.assertNotIn("dynamic_structures:", region_text)
        self.assertNotIn("dyn_", dynamic_text)
        self.assertNotIn("pressure_threads:", dynamic_text)


if __name__ == "__main__":
    unittest.main()
