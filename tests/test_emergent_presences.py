import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.config.models import AIConfig, WorldConfig
from src.core.emergent_presence_proposals import (
    apply_emergent_presence_proposals,
    validate_emergent_presence_proposals,
)
from src.core.engine import WorldEngine, _refresh_emergent_presence_lifecycle
from src.events.models import Event
from src.events.query import select_events
from src.interfaces.commands import CommandContext, handle_command
from src.interfaces.stream_view import format_status
from src.narrative.summaries import summarize_emergent_presence, summarize_region
from src.storage.snapshots import load_world_state, save_world_state
from src.world.builder import build_world


def _build_world():
    return build_world(DEFAULT_WORLD_CONFIG)


def _sample_payload(world):
    region_id = next(iter(world.regions))
    return {
        "proposals": [
            {
                "action": "create",
                "presence_type": "spore_bloom",
                "name": "Veil Bloom-01",
                "summary": "A spore-like ecological pressure is forming around a containment edge.",
                "home_region_ref": region_id,
                "current_region_refs": [region_id],
                "linked_relic_refs": [next(iter(world.relics))],
                "linked_dynamic_refs": [],
                "linked_faction_refs": [next(iter(world.factions))],
                "lifecycle_stage": "forming",
                "population_scale": "trace",
                "adaptation_level": "low",
                "mobility": "local",
                "pressure": "medium",
                "behavior_tags": ["reactive", "territorial"],
                "sensory_tags": ["spore_haze"],
                "ecological_tags": ["biosecurity_risk"],
                "visibility": "rumored",
                "relation_type": "nests_in",
            }
        ]
    }


class EmergentPresenceTests(unittest.TestCase):
    def test_emergent_presence_proposal_creates_presence_and_bridges(self) -> None:
        world = _build_world()

        result = apply_emergent_presence_proposals(world, _sample_payload(world), origin="unit_test")

        self.assertEqual(len(result.accepted), 1)
        self.assertFalse(result.rejected)
        presence_id = result.accepted[0]
        self.assertIn(presence_id, world.emergent_presences)
        presence = world.emergent_presences[presence_id]
        self.assertEqual(presence.presence_type, "spore_bloom")
        self.assertEqual(presence.origin, "unit_test")
        self.assertTrue(presence.influence_refs)
        self.assertEqual(len(result.events), 1)
        event = result.events[0]
        self.assertIn(presence_id, event.emergent_presence_refs)
        self.assertIn(event.event_id, presence.source_event_refs)
        self.assertTrue(any(relation.source_ref == presence_id for relation in world.relations.values()))
        self.assertTrue(any(thread.scope_ref == presence_id for thread in world.pressure_threads.values()))

    def test_emergent_presence_rejects_unknown_type_and_refs(self) -> None:
        world = _build_world()
        result = apply_emergent_presence_proposals(
            world,
            {
                "proposals": [
                    {
                        "action": "create",
                        "presence_type": "freeform_god",
                        "name": "Bad",
                        "summary": "Bad",
                        "home_region_ref": "missing_region",
                    }
                ]
            },
        )

        self.assertFalse(result.accepted)
        self.assertTrue(result.rejected)
        self.assertFalse(world.emergent_presences)

    def test_duplicate_emergent_presence_dry_run_marks_update_target(self) -> None:
        world = _build_world()
        first_id = apply_emergent_presence_proposals(world, _sample_payload(world)).accepted[0]

        result = validate_emergent_presence_proposals(world, _sample_payload(world))

        self.assertEqual(result.accepted, [f"proposal[0]->update:{first_id}"])
        self.assertEqual(len(world.emergent_presences), 1)

    def test_emergent_presence_summary_and_region_links_are_player_safe(self) -> None:
        world = _build_world()
        presence_id = apply_emergent_presence_proposals(world, _sample_payload(world)).accepted[0]
        region_id = world.emergent_presences[presence_id].home_region_ref

        presence_text = summarize_emergent_presence(
            world,
            presence_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        region_text = summarize_region(world, region_id, event_limit=5, mode="full", view="player")
        truth_region_text = summarize_region(world, region_id, event_limit=5, mode="full", view="truth")

        self.assertIn("异常生态观察", presence_text)
        self.assertIn("生态线索:", presence_text)
        self.assertIn("异常生态:", region_text)
        self.assertIn("emergent_presences:", truth_region_text)
        self.assertNotIn("ep_", presence_text)
        self.assertNotIn("ep_", region_text)
        self.assertNotIn("emergent_presences:", region_text)

    def test_emergent_presences_are_preserved_in_snapshots(self) -> None:
        world = _build_world()
        presence_id = apply_emergent_presence_proposals(world, _sample_payload(world)).accepted[0]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save_world_state(world, path)
            loaded = load_world_state(path)

        self.assertIn(presence_id, loaded.emergent_presences)
        self.assertEqual(
            loaded.emergent_presences[presence_id].name,
            world.emergent_presences[presence_id].name,
        )
        self.assertTrue(any(event.emergent_presence_refs for event in loaded.event_stream.events))

    def test_status_events_and_cli_watch_emergent_presence(self) -> None:
        world = _build_world()
        presence_id = apply_emergent_presence_proposals(world, _sample_payload(world)).accepted[0]
        status = format_status(world)
        self.assertIn("emergent_presences: 1", status)

        selected = select_events(
            world.event_stream.events,
            target_type="emergent",
            target_id=presence_id,
            limit=5,
            view="truth",
        )
        self.assertEqual(len(selected), 1)

        cfg = DEFAULT_AI_CONFIG.copy()
        cfg["provider"] = "none"
        with tempfile.TemporaryDirectory() as tmp:
            context = CommandContext(
                engine=WorldEngine(world, ai_config=cfg),
                world_config=WorldConfig(**DEFAULT_WORLD_CONFIG),
                ai_config=AIConfig(**cfg),
                snapshot_path=Path(tmp) / "world.json",
            )
            output = handle_command(context, f"watch emergent {presence_id} full player")

        self.assertIn("异常生态观察", output)
        self.assertNotIn("ep_", output)

    def test_emergent_presence_lifecycle_archives_stale_presence(self) -> None:
        world = _build_world()
        presence_id = apply_emergent_presence_proposals(world, _sample_payload(world)).accepted[0]
        presence = world.emergent_presences[presence_id]

        world.current_tick = presence.updated_tick + 10
        _refresh_emergent_presence_lifecycle(world, [])
        self.assertEqual(presence.status, "cooling")

        world.current_tick = presence.updated_tick + 16
        _refresh_emergent_presence_lifecycle(world, [])
        self.assertEqual(presence.status, "dormant")

        world.current_tick = presence.updated_tick + 30
        _refresh_emergent_presence_lifecycle(world, [])
        self.assertEqual(presence.status, "archived")

        world.current_tick = 40
        event = Event(
            event_id="event_emergent_refresh",
            tick=40,
            time_granularity="week",
            event_type="emergent_presence_updated",
            event_scope="emergent_presence",
            title="Emergent refresh",
            summary="The emergent presence was refreshed by a direct event.",
            emergent_presence_refs=[presence_id],
        )
        _refresh_emergent_presence_lifecycle(world, [event])
        self.assertEqual(presence.status, "active")
        self.assertEqual(presence.updated_tick, 40)


if __name__ == "__main__":
    unittest.main()
