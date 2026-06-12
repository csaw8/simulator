import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_WORLD_CONFIG
from src.core.dynamic_structure_proposals import apply_dynamic_structure_proposals
from src.core.emergent_presence_proposals import apply_emergent_presence_proposals
from src.narrative.names import player_display_name
from src.narrative.names import player_faction_type_label
from src.storage.snapshots import load_world_state, save_world_state
from src.world.builder import build_world
from src.world.style_profile import (
    DEFAULT_STYLE_PROFILE_ID,
    get_narrative_lexicon,
    get_world_style_profile,
    observer_voice,
    style_profile_prompt_lines,
    style_profile_to_dict,
)


class WorldStyleProfileTests(unittest.TestCase):
    def test_default_style_profile_is_readable(self) -> None:
        profile = get_world_style_profile()

        self.assertEqual(profile.style_id, DEFAULT_STYLE_PROFILE_ID)
        self.assertEqual(profile.world_style, "realistic future technology civilization")
        self.assertIn("anomalous pressure", profile.preferred_terms)
        self.assertIn("magic", profile.forbidden_terms)
        self.assertIn(DEFAULT_STYLE_PROFILE_ID, profile.prompt_signature())

    def test_unknown_style_profile_falls_back_to_default(self) -> None:
        profile = get_world_style_profile("missing_profile")

        self.assertEqual(profile.style_id, DEFAULT_STYLE_PROFILE_ID)

    def test_style_profile_serializes_to_plain_dict(self) -> None:
        payload = style_profile_to_dict(get_world_style_profile())

        self.assertEqual(payload["style_id"], DEFAULT_STYLE_PROFILE_ID)
        self.assertIn("preferred_terms", payload)

    def test_style_profile_prompt_lines_include_boundaries(self) -> None:
        lines = style_profile_prompt_lines(DEFAULT_STYLE_PROFILE_ID)
        text = "\n".join(lines)

        self.assertIn("World style: realistic future technology civilization.", text)
        self.assertIn("Setting summary:", text)
        self.assertIn("Forbidden terms:", text)

    def test_observer_voice_comes_from_style_profile(self) -> None:
        voice = observer_voice(DEFAULT_STYLE_PROFILE_ID, "region_public_pressure")

        self.assertIn("grounded public-observer tone", voice)

    def test_observer_voice_falls_back_to_default_voice(self) -> None:
        profile = get_world_style_profile()
        voice = observer_voice(DEFAULT_STYLE_PROFILE_ID, "missing_voice_key")

        self.assertEqual(voice, profile.default_observer_voice)

    def test_narrative_lexicon_contains_dynamic_and_emergent_labels(self) -> None:
        lexicon = get_narrative_lexicon(DEFAULT_STYLE_PROFILE_ID)

        self.assertEqual(lexicon.dynamic_structure_player_title, "动态线索观察")
        self.assertEqual(lexicon.dynamic_structure_region_label, "动态线索")
        self.assertEqual(lexicon.dynamic_structure_truth_block, "dynamic_structures")
        self.assertEqual(lexicon.emergent_presence_player_title, "异常生态观察")
        self.assertEqual(lexicon.emergent_presence_region_label, "异常生态")
        self.assertEqual(lexicon.emergent_presence_truth_block, "emergent_presences")
        self.assertEqual(lexicon.relic_presence_labels["megastructure"], "巨构异常")
        self.assertEqual(lexicon.project_display_prefix, "项目")
        self.assertEqual(lexicon.dynamic_structure_display_prefix, "线索")
        self.assertEqual(lexicon.emergent_presence_display_prefix, "异常生态迹象")
        self.assertEqual(lexicon.faction_type_labels["government"], "行政势力")
        self.assertEqual(lexicon.faction_type_fallback_label, "组织势力")

    def test_unknown_narrative_lexicon_falls_back_to_default(self) -> None:
        lexicon = get_narrative_lexicon("missing_profile")

        self.assertEqual(lexicon.dynamic_structure_player_title, "动态线索观察")

    def test_player_display_name_uses_narrative_lexicon_prefixes(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        region_id = next(iter(world.regions))
        structure_id = apply_dynamic_structure_proposals(
            world,
            {
                "proposals": [
                    {
                        "action": "create",
                        "structure_type": "incident_site",
                        "name": "North Lockdown Belt",
                        "summary": "A disputed project perimeter has become a visible incident site.",
                        "scope_refs": [region_id],
                        "linked_refs": [],
                        "tags": ["site_accident"],
                        "visibility": "visible",
                        "pressure": "medium",
                        "relation_type": "pressures",
                    }
                ]
            },
        ).accepted[0]
        presence_id = apply_emergent_presence_proposals(
            world,
            {
                "proposals": [
                    {
                        "action": "create",
                        "presence_type": "spore_bloom",
                        "name": "Veil Bloom-01",
                        "summary": "A spore-like ecological pressure is forming around a containment edge.",
                        "home_region_ref": region_id,
                        "current_region_refs": [region_id],
                        "pressure": "medium",
                        "visibility": "rumored",
                        "relation_type": "nests_in",
                    }
                ]
            },
        ).accepted[0]

        self.assertTrue(player_display_name(world, next(iter(world.projects))).startswith("项目“"))
        self.assertTrue(player_display_name(world, next(iter(world.supply_lines))).startswith("补给线“"))
        self.assertTrue(player_display_name(world, next(iter(world.region_nodes))).startswith("节点“"))
        self.assertTrue(player_display_name(world, structure_id).startswith("线索“"))
        self.assertTrue(player_display_name(world, presence_id).startswith("异常生态迹象“"))

    def test_player_faction_type_label_uses_narrative_lexicon(self) -> None:
        self.assertEqual(player_faction_type_label("government"), "行政势力")
        self.assertEqual(player_faction_type_label("logistics_syndicate"), "物流势力")
        self.assertEqual(player_faction_type_label("unknown_type"), "组织势力")

    def test_world_state_uses_default_style_profile_id(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)

        self.assertEqual(world.style_profile_id, DEFAULT_STYLE_PROFILE_ID)

    def test_snapshot_preserves_style_profile_id(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save_world_state(world, path)
            loaded = load_world_state(path)

        self.assertEqual(loaded.style_profile_id, DEFAULT_STYLE_PROFILE_ID)


if __name__ == "__main__":
    unittest.main()
