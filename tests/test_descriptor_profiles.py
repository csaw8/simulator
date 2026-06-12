import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_WORLD_CONFIG
from src.core.dynamic_structure_proposals import apply_dynamic_structure_proposals
from src.core.emergent_presence_proposals import apply_emergent_presence_proposals
from src.storage.snapshots import load_world_state, save_world_state
from src.world.builder import build_world
from src.world.descriptor_profile import (
    descriptor_profile_player_labels,
    validate_descriptor_profile,
)


class DescriptorProfileTests(unittest.TestCase):
    def test_build_world_initializes_descriptor_profiles_for_fixed_objects(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)

        expected_refs = set(world.characters)
        expected_refs.update(world.region_nodes)
        expected_refs.update(world.relics)
        expected_refs.update(world.projects)
        expected_refs.update(world.supply_lines)

        self.assertTrue(expected_refs)
        self.assertTrue(expected_refs.issubset(world.descriptor_profiles))
        self.assertEqual(world.summary()["descriptor_profiles"], len(world.descriptor_profiles))

    def test_descriptor_profile_initialization_is_seed_reproducible(self) -> None:
        world_a = build_world(DEFAULT_WORLD_CONFIG)
        world_b = build_world(DEFAULT_WORLD_CONFIG)

        payload_a = {
            ref: (
                profile.profile_type,
                tuple(profile.appearance_tags),
                tuple(profile.function_tags),
                tuple(profile.behavior_tags),
                tuple(profile.sensory_tags),
                tuple(profile.social_read_tags),
                tuple(profile.ecological_tags),
            )
            for ref, profile in world_a.descriptor_profiles.items()
        }
        payload_b = {
            ref: (
                profile.profile_type,
                tuple(profile.appearance_tags),
                tuple(profile.function_tags),
                tuple(profile.behavior_tags),
                tuple(profile.sensory_tags),
                tuple(profile.social_read_tags),
                tuple(profile.ecological_tags),
            )
            for ref, profile in world_b.descriptor_profiles.items()
        }

        self.assertEqual(payload_a, payload_b)

    def test_initialized_descriptor_profiles_use_approved_tags(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)

        for profile in world.descriptor_profiles.values():
            with self.subTest(ref_id=profile.ref_id):
                self.assertEqual(
                    validate_descriptor_profile(profile, style_id=world.style_profile_id),
                    [],
                )

    def test_descriptor_profile_player_labels_hide_tag_ids(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        profile = next(iter(world.descriptor_profiles.values()))
        labels = descriptor_profile_player_labels(profile, style_id=world.style_profile_id)

        self.assertEqual(
            set(labels),
            {"appearance", "function", "behavior", "sensory", "social_read", "ecological"},
        )
        flattened = [label for values in labels.values() for label in values]
        self.assertTrue(flattened)
        self.assertFalse(any("_" in label for label in flattened))

    def test_snapshot_preserves_descriptor_profiles(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save_world_state(world, path)
            loaded = load_world_state(path)

        self.assertEqual(len(loaded.descriptor_profiles), len(world.descriptor_profiles))
        sample_ref = next(iter(world.descriptor_profiles))
        self.assertEqual(
            loaded.descriptor_profiles[sample_ref].appearance_tags,
            world.descriptor_profiles[sample_ref].appearance_tags,
        )

    def test_dynamic_structure_proposal_creates_descriptor_profile(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        region_id = next(iter(world.regions))
        result = apply_dynamic_structure_proposals(
            world,
            {
                "proposals": [
                    {
                        "action": "create",
                        "structure_type": "incident_site",
                        "name": "Descriptor Lockdown Belt",
                        "summary": "A visible incident site is drawing descriptor coverage.",
                        "scope_refs": [region_id],
                        "linked_refs": [],
                        "tags": ["site_accident"],
                        "visibility": "visible",
                        "pressure": "medium",
                        "relation_type": "pressures",
                    }
                ]
            },
        )
        structure_id = result.accepted[0]

        self.assertIn(structure_id, world.descriptor_profiles)
        profile = world.descriptor_profiles[structure_id]
        self.assertEqual(profile.profile_type, "dynamic_structure")
        self.assertEqual(validate_descriptor_profile(profile, style_id=world.style_profile_id), [])

    def test_emergent_presence_proposal_creates_descriptor_profile(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        region_id = next(iter(world.regions))
        result = apply_emergent_presence_proposals(
            world,
            {
                "proposals": [
                    {
                        "action": "create",
                        "presence_type": "spore_bloom",
                        "name": "Descriptor Bloom-01",
                        "summary": "A spore-like ecological pressure is forming around a containment edge.",
                        "home_region_ref": region_id,
                        "current_region_refs": [region_id],
                        "behavior_tags": ["reactive", "territorial"],
                        "sensory_tags": ["spore_haze"],
                        "ecological_tags": ["biosecurity_risk"],
                        "pressure": "medium",
                        "visibility": "rumored",
                        "relation_type": "nests_in",
                    }
                ]
            },
        )
        presence_id = result.accepted[0]

        self.assertIn(presence_id, world.descriptor_profiles)
        profile = world.descriptor_profiles[presence_id]
        self.assertEqual(profile.profile_type, "emergent_presence")
        self.assertEqual(validate_descriptor_profile(profile, style_id=world.style_profile_id), [])


if __name__ == "__main__":
    unittest.main()
