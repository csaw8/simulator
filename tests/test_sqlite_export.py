import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.config.models import AIConfig, WorldConfig
from src.core.dynamic_structure_proposals import apply_dynamic_structure_proposals
from src.core.emergent_presence_proposals import apply_emergent_presence_proposals
from src.core.engine import WorldEngine
from src.interfaces.commands import CommandContext, handle_command
from src.storage.db import export_world_to_sqlite, sqlite_stats
from src.world.builder import build_world


def _dynamic_payload(world):
    return {
        "proposals": [
            {
                "action": "create",
                "structure_type": "anomaly_trace",
                "name": "SQLite Trace",
                "summary": "A bounded trace exists for SQLite export testing.",
                "scope_refs": [next(iter(world.regions))],
                "linked_refs": [next(iter(world.relics))],
                "tags": ["sqlite_test"],
                "visibility": "visible",
                "pressure": "medium",
                "relation_type": "trace_of",
            }
        ]
    }


def _emergent_payload(world):
    region_id = next(iter(world.regions))
    return {
        "proposals": [
            {
                "action": "create",
                "presence_type": "spore_bloom",
                "name": "SQLite Bloom",
                "summary": "A bounded bloom exists for SQLite export testing.",
                "home_region_ref": region_id,
                "current_region_refs": [region_id],
                "linked_relic_refs": [next(iter(world.relics))],
                "lifecycle_stage": "forming",
                "population_scale": "trace",
                "adaptation_level": "low",
                "mobility": "local",
                "pressure": "medium",
                "visibility": "visible",
                "relation_type": "nests_in",
            }
        ]
    }


class SQLiteExportTests(unittest.TestCase):
    def test_sqlite_export_includes_events_relations_dynamic_and_emergent(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        apply_dynamic_structure_proposals(world, _dynamic_payload(world))
        apply_emergent_presence_proposals(world, _emergent_payload(world))

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.sqlite3"
            export_world_to_sqlite(world, path)
            stats = sqlite_stats(path)

        self.assertGreaterEqual(stats["events"], 2)
        self.assertGreaterEqual(stats["relations"], 2)
        self.assertEqual(stats["dynamic_structures"], 1)
        self.assertEqual(stats["emergent_presences"], 1)
        self.assertEqual(stats["ai_proposal_audits"], 0)

    def test_cli_db_export_and_stats(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        cfg = DEFAULT_AI_CONFIG.copy()
        cfg["provider"] = "none"

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "world.sqlite3"
            context = CommandContext(
                engine=WorldEngine(world, ai_config=cfg),
                world_config=WorldConfig(**DEFAULT_WORLD_CONFIG),
                ai_config=AIConfig(**cfg),
                snapshot_path=Path(tmp) / "world.json",
            )
            export_output = handle_command(context, f"db export {db_path}")
            stats_output = handle_command(context, f"db stats {db_path}")

        self.assertIn("SQLite export written", export_output)
        self.assertIn("SQLite stats:", stats_output)
        self.assertIn("events:", stats_output)
        self.assertIn("emergent_presences:", stats_output)


if __name__ == "__main__":
    unittest.main()
