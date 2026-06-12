import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.config.models import AIConfig, WorldConfig
from src.core.dynamic_structure_ai import propose_dynamic_structures_for_watch
from src.core.engine import WorldEngine
from src.interfaces.commands import CommandContext, handle_command
from src.storage.snapshots import load_world_state, save_world_state
from src.world.builder import build_world


class FakeProposalClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create_json_completion_with_limits(self, messages, *, max_tokens, thinking_budget):
        self.calls.append(
            {
                "messages": messages,
                "max_tokens": max_tokens,
                "thinking_budget": thinking_budget,
            }
        )
        return self.payload


def _cfg():
    cfg = DEFAULT_AI_CONFIG.copy()
    cfg["provider"] = "none"
    cfg["observer_full_signal_threshold"] = 0
    cfg["dynamic_structure_cost_tier"] = "low"
    return cfg


def _world_with_signal():
    cfg = DEFAULT_AI_CONFIG.copy()
    cfg["provider"] = "none"
    world = build_world(DEFAULT_WORLD_CONFIG)
    engine = WorldEngine(world, ai_config=cfg)
    for _ in range(3):
        engine.step()
    return world


def _payload(world):
    return {
        "proposals": [
            {
                "action": "create",
                "structure_type": "rumor_network",
                "name": "Archive Whisper Chain",
                "summary": "A rumor channel is amplifying pressure around the target.",
                "scope_refs": [next(iter(world.regions))],
                "linked_refs": [next(iter(world.relics))],
                "tags": ["archive", "rumor"],
                "visibility": "rumored",
                "pressure": "medium",
                "relation_type": "rumor_source_for",
            }
        ]
    }


class DynamicStructureAITests(unittest.TestCase):
    def test_dynamic_structure_ai_dry_run_validates_without_mutating_world(self) -> None:
        world = _world_with_signal()
        before_count = len(world.dynamic_structures)
        client = FakeProposalClient(_payload(world))

        result = propose_dynamic_structures_for_watch(
            world,
            target_type="region",
            target_id=next(iter(world.regions)),
            ai_config=_cfg(),
            mode="full",
            view="truth",
            apply=False,
            client=client,
        )

        self.assertEqual(result.source, "siliconflow")
        self.assertFalse(result.applied)
        self.assertEqual(len(result.validation.accepted), 1)
        self.assertEqual(len(world.dynamic_structures), before_count)
        self.assertEqual(len(client.calls), 1)
        self.assertIsNotNone(result.audit_id)
        self.assertEqual(len(world.ai_proposal_audits), 1)
        audit = world.ai_proposal_audits[result.audit_id]
        self.assertFalse(audit.applied)
        self.assertEqual(audit.accepted_refs, ["proposal[0]"])

    def test_dynamic_structure_ai_apply_writes_only_through_validated_layer(self) -> None:
        world = _world_with_signal()
        client = FakeProposalClient(_payload(world))

        result = propose_dynamic_structures_for_watch(
            world,
            target_type="region",
            target_id=next(iter(world.regions)),
            ai_config=_cfg(),
            mode="full",
            view="truth",
            apply=True,
            client=client,
        )

        self.assertTrue(result.applied)
        self.assertEqual(len(result.validation.accepted), 1)
        structure_id = result.validation.accepted[0]
        self.assertIn(structure_id, world.dynamic_structures)
        self.assertTrue(any(event.dynamic_structure_refs for event in world.event_stream.events))
        self.assertTrue(any(relation.source_ref == structure_id for relation in world.relations.values()))
        self.assertIsNotNone(result.audit_id)
        audit = world.ai_proposal_audits[result.audit_id]
        self.assertTrue(audit.applied)
        self.assertEqual(audit.accepted_refs, [structure_id])
        self.assertIsNotNone(audit.payload)

    def test_dynamic_structure_ai_rejects_invalid_payload_without_mutating_world(self) -> None:
        world = _world_with_signal()
        client = FakeProposalClient(
            {
                "proposals": [
                    {
                        "action": "create",
                        "structure_type": "invalid_type",
                        "name": "Bad",
                        "summary": "Bad",
                        "scope_refs": ["missing"],
                    }
                ]
            }
        )

        result = propose_dynamic_structures_for_watch(
            world,
            target_type="region",
            target_id=next(iter(world.regions)),
            ai_config=_cfg(),
            mode="full",
            view="truth",
            apply=True,
            client=client,
        )

        self.assertFalse(result.validation.accepted)
        self.assertTrue(result.validation.rejected)
        self.assertFalse(world.dynamic_structures)
        self.assertEqual(len(world.ai_proposal_audits), 1)
        audit = next(iter(world.ai_proposal_audits.values()))
        self.assertTrue(audit.rejected_reasons)

    def test_cli_dynamic_proposal_without_client_does_not_mutate_world(self) -> None:
        world = _world_with_signal()
        cfg = _cfg()
        with tempfile.TemporaryDirectory() as tmp:
            context = CommandContext(
                engine=WorldEngine(world, ai_config=cfg),
                world_config=WorldConfig(**DEFAULT_WORLD_CONFIG),
                ai_config=AIConfig(**cfg),
                snapshot_path=Path(tmp) / "world.json",
            )
            output = handle_command(
                context,
                f"watch region {next(iter(world.regions))} full truth propose=dynamic",
            )

        self.assertIn("Dynamic structure proposal:", output)
        self.assertIn("SiliconFlow client unavailable", output)
        self.assertIn("audit_id:", output)
        self.assertFalse(world.dynamic_structures)
        self.assertEqual(len(world.ai_proposal_audits), 1)

    def test_cli_audit_proposals_lists_recent_records(self) -> None:
        world = _world_with_signal()
        cfg = _cfg()
        with tempfile.TemporaryDirectory() as tmp:
            context = CommandContext(
                engine=WorldEngine(world, ai_config=cfg),
                world_config=WorldConfig(**DEFAULT_WORLD_CONFIG),
                ai_config=AIConfig(**cfg),
                snapshot_path=Path(tmp) / "world.json",
            )
            handle_command(
                context,
                f"watch region {next(iter(world.regions))} full truth propose=dynamic",
            )
            output = handle_command(context, "audit proposals 3")

        self.assertIn("AI proposal audits", output)
        self.assertIn("audit_", output)
        self.assertIn("dynamic_structure", output)

    def test_ai_proposal_audits_are_preserved_in_snapshots(self) -> None:
        world = _world_with_signal()
        client = FakeProposalClient(_payload(world))
        result = propose_dynamic_structures_for_watch(
            world,
            target_type="region",
            target_id=next(iter(world.regions)),
            ai_config=_cfg(),
            mode="full",
            view="truth",
            apply=False,
            client=client,
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save_world_state(world, path)
            loaded = load_world_state(path)

        self.assertIn(result.audit_id, loaded.ai_proposal_audits)
        audit = loaded.ai_proposal_audits[result.audit_id]
        self.assertEqual(audit.proposal_type, "dynamic_structure")
        self.assertEqual(audit.accepted_refs, ["proposal[0]"])


if __name__ == "__main__":
    unittest.main()
