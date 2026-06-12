import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_WORLD_CONFIG
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

    def test_unknown_narrative_lexicon_falls_back_to_default(self) -> None:
        lexicon = get_narrative_lexicon("missing_profile")

        self.assertEqual(lexicon.dynamic_structure_player_title, "动态线索观察")

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
