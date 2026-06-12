import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.config.models import AIConfig, WorldConfig
from src.core.ai_context import (
    build_emergent_presence_context,
    emergent_presence_context_signal,
)
from src.core.emergent_presence_ai import propose_emergent_presences_for_watch
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
    cfg["emergent_presence_cost_tier"] = "low"
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


class EmergentPresenceAITests(unittest.TestCase):
    def test_emergent_presence_context_includes_signal_guidance_and_typed_refs(self) -> None:
        world = _world_with_signal()
        region_id = next(iter(world.regions))
        context = build_emergent_presence_context(
            world,
            target_type="region",
            target_id=region_id,
        )

        self.assertIn("proposal_signal_score", context)
        self.assertIn("proposal_required", context)
        self.assertIn("proposal_guidance", context)
        self.assertEqual(emergent_presence_context_signal(context), context["proposal_signal_score"])
        self.assertIn(region_id, context["allowed_refs"]["regions"])

    def test_emergent_presence_ai_dry_run_validates_without_mutating_world(self) -> None:
        world = _world_with_signal()
        before_count = len(world.emergent_presences)
        client = FakeProposalClient(_payload(world))

        result = propose_emergent_presences_for_watch(
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
        self.assertEqual(len(world.emergent_presences), before_count)
        self.assertEqual(len(client.calls), 1)
        self.assertIsNotNone(result.audit_id)
        audit = world.ai_proposal_audits[result.audit_id]
        self.assertFalse(audit.applied)
        self.assertEqual(audit.proposal_type, "emergent_presence")
        self.assertEqual(audit.accepted_refs, ["proposal[0]"])

    def test_emergent_presence_ai_apply_writes_only_through_validated_layer(self) -> None:
        world = _world_with_signal()
        client = FakeProposalClient(_payload(world))

        result = propose_emergent_presences_for_watch(
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
        presence_id = result.validation.accepted[0]
        self.assertIn(presence_id, world.emergent_presences)
        self.assertTrue(any(event.emergent_presence_refs for event in world.event_stream.events))
        self.assertTrue(any(relation.source_ref == presence_id for relation in world.relations.values()))
        audit = world.ai_proposal_audits[result.audit_id]
        self.assertTrue(audit.applied)
        self.assertEqual(audit.accepted_refs, [presence_id])
        self.assertIsNotNone(audit.payload)

    def test_emergent_presence_ai_rejects_invalid_payload_without_mutating_world(self) -> None:
        world = _world_with_signal()
        client = FakeProposalClient(
            {
                "proposals": [
                    {
                        "action": "create",
                        "presence_type": "invalid_presence",
                        "name": "Bad",
                        "summary": "Bad",
                        "home_region_ref": next(iter(world.regions)),
                    }
                ]
            }
        )

        result = propose_emergent_presences_for_watch(
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
        self.assertFalse(world.emergent_presences)
        audit = next(iter(world.ai_proposal_audits.values()))
        self.assertTrue(audit.rejected_reasons)

    def test_cli_emergent_proposal_without_client_does_not_mutate_world(self) -> None:
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
                f"watch region {next(iter(world.regions))} full truth propose=emergent",
            )

        self.assertIn("Emergent presence AI proposal:", output)
        self.assertIn("client unavailable", output)
        self.assertIn("audit_id:", output)
        self.assertFalse(world.emergent_presences)
        self.assertEqual(len(world.ai_proposal_audits), 1)

    def test_ai_proposal_audits_are_preserved_in_snapshots(self) -> None:
        world = _world_with_signal()
        client = FakeProposalClient(_payload(world))
        result = propose_emergent_presences_for_watch(
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
        self.assertEqual(audit.proposal_type, "emergent_presence")
        self.assertEqual(audit.accepted_refs, ["proposal[0]"])


if __name__ == "__main__":
    unittest.main()
