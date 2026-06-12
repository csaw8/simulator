import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.config.models import AIConfig, WorldConfig
from src.core.descriptor_ai import (
    apply_descriptor_profile_proposals,
    build_descriptor_context,
    propose_descriptor_profile_for_ref,
    validate_descriptor_profile_proposals,
)
from src.core.engine import WorldEngine
from src.interfaces.commands import CommandContext, handle_command
from src.storage.snapshots import load_world_state, save_world_state
from src.world.builder import build_world
from src.world.descriptor_profile import validate_descriptor_profile
from src.world.style_profile import POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID


class FakeDescriptorClient:
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
    cfg["descriptor_profile_cost_tier"] = "low"
    return cfg


def _payload(ref_id: str, profile_type: str):
    return {
        "proposals": [
            {
                "ref_id": ref_id,
                "profile_type": profile_type,
                "appearance_tags": [],
                "function_tags": [],
                "behavior_tags": ["reactive"],
                "sensory_tags": [],
                "social_read_tags": ["trusted"],
                "ecological_tags": [],
                "notes": ["Seen as a responsive actor inside local pressure."],
            }
        ]
    }


class DescriptorAITests(unittest.TestCase):
    def test_descriptor_context_includes_approved_pool_and_current_profile(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        ref_id = next(iter(world.characters))
        context = build_descriptor_context(world, ref_id=ref_id, profile_type="character")

        self.assertEqual(context["ref_id"], ref_id)
        self.assertEqual(context["profile_type"], "character")
        self.assertIn("approved_descriptor_pool", context)
        self.assertIn("reactive", context["approved_descriptor_pool"]["behavior"])
        self.assertIn("trusted", context["approved_descriptor_pool"]["social_read"])
        self.assertIn("current_descriptor_tags", context)
        self.assertIn("target_snapshot", context)

    def test_descriptor_context_uses_world_style_profile_pool(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        world.style_profile_id = POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID
        ref_id = next(iter(world.characters))
        context = build_descriptor_context(world, ref_id=ref_id, profile_type="character")

        self.assertEqual(context["style_profile_id"], POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID)
        self.assertIn("guarded", context["approved_descriptor_pool"]["behavior"])
        self.assertIn("needed", context["approved_descriptor_pool"]["social_read"])
        self.assertNotIn("reactive", context["approved_descriptor_pool"]["behavior"])

    def test_descriptor_validation_accepts_only_approved_pool_tags(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        ref_id = next(iter(world.characters))

        accepted = validate_descriptor_profile_proposals(
            world,
            _payload(ref_id, "character"),
            expected_ref_id=ref_id,
        )
        rejected = validate_descriptor_profile_proposals(
            world,
            {
                "proposals": [
                    {
                        "ref_id": ref_id,
                        "profile_type": "character",
                        "behavior_tags": ["dragon_blood"],
                    }
                ]
            },
            expected_ref_id=ref_id,
        )

        self.assertEqual(accepted.accepted, ["proposal[0]"])
        self.assertFalse(accepted.rejected)
        self.assertFalse(rejected.accepted)
        self.assertIn("unsupported descriptor tag", rejected.rejected[0])

    def test_descriptor_ai_dry_run_validates_without_mutating_profile(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        ref_id = next(iter(world.characters))
        before = list(world.descriptor_profiles[ref_id].behavior_tags)
        client = FakeDescriptorClient(_payload(ref_id, "character"))

        result = propose_descriptor_profile_for_ref(
            world,
            ref_id=ref_id,
            ai_config=_cfg(),
            apply=False,
            client=client,
        )

        self.assertEqual(result.source, "siliconflow")
        self.assertFalse(result.applied)
        self.assertEqual(result.validation.accepted, ["proposal[0]"])
        self.assertEqual(world.descriptor_profiles[ref_id].behavior_tags, before)
        self.assertEqual(len(client.calls), 1)
        self.assertIsNotNone(result.audit_id)
        audit = world.ai_proposal_audits[result.audit_id]
        self.assertEqual(audit.proposal_type, "descriptor_profile")
        self.assertFalse(audit.applied)
        self.assertEqual(audit.accepted_refs, ["proposal[0]"])

    def test_descriptor_ai_apply_updates_only_descriptor_profile(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        ref_id = next(iter(world.characters))
        before_events = len(world.event_stream.events)
        before_relations = len(world.relations)
        client = FakeDescriptorClient(_payload(ref_id, "character"))

        result = propose_descriptor_profile_for_ref(
            world,
            ref_id=ref_id,
            ai_config=_cfg(),
            apply=True,
            client=client,
        )

        self.assertTrue(result.applied)
        self.assertEqual(result.validation.accepted, [ref_id])
        profile = world.descriptor_profiles[ref_id]
        self.assertEqual(profile.behavior_tags, ["reactive"])
        self.assertEqual(profile.social_read_tags, ["trusted"])
        self.assertEqual(validate_descriptor_profile(profile, style_id=world.style_profile_id), [])
        self.assertEqual(len(world.event_stream.events), before_events)
        self.assertEqual(len(world.relations), before_relations)
        audit = world.ai_proposal_audits[result.audit_id]
        self.assertTrue(audit.applied)
        self.assertEqual(audit.accepted_refs, [ref_id])

    def test_descriptor_apply_rejects_wrong_ref_without_mutating_requested_profile(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        ref_id = next(iter(world.characters))
        other_ref = next(ref for ref in world.characters if ref != ref_id)
        before = list(world.descriptor_profiles[ref_id].behavior_tags)

        result = apply_descriptor_profile_proposals(
            world,
            _payload(other_ref, "character"),
            expected_ref_id=ref_id,
        )

        self.assertFalse(result.accepted)
        self.assertIn("ref_id must match", result.rejected[0])
        self.assertEqual(world.descriptor_profiles[ref_id].behavior_tags, before)

    def test_cli_descriptor_proposal_without_client_does_not_mutate_world(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        ref_id = next(iter(world.characters))
        cfg = _cfg()
        before = list(world.descriptor_profiles[ref_id].behavior_tags)
        with tempfile.TemporaryDirectory() as tmp:
            context = CommandContext(
                engine=WorldEngine(world, ai_config=cfg),
                world_config=WorldConfig(**DEFAULT_WORLD_CONFIG),
                ai_config=AIConfig(**cfg),
                snapshot_path=Path(tmp) / "world.json",
            )
            output = handle_command(context, f"propose descriptor {ref_id}")

        self.assertIn("Descriptor AI proposal:", output)
        self.assertIn("client unavailable", output)
        self.assertIn("audit_id:", output)
        self.assertEqual(world.descriptor_profiles[ref_id].behavior_tags, before)
        self.assertEqual(len(world.ai_proposal_audits), 1)

    def test_descriptor_ai_audit_is_preserved_in_snapshots(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        ref_id = next(iter(world.characters))
        client = FakeDescriptorClient(_payload(ref_id, "character"))
        result = propose_descriptor_profile_for_ref(
            world,
            ref_id=ref_id,
            ai_config=_cfg(),
            apply=False,
            client=client,
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save_world_state(world, path)
            loaded = load_world_state(path)

        self.assertIn(result.audit_id, loaded.ai_proposal_audits)
        audit = loaded.ai_proposal_audits[result.audit_id]
        self.assertEqual(audit.proposal_type, "descriptor_profile")
        self.assertEqual(audit.accepted_refs, ["proposal[0]"])


if __name__ == "__main__":
    unittest.main()
