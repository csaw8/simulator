import unittest

from src.world.descriptor_lexicon import (
    approved_descriptor_tag_ids,
    descriptor_tag,
    descriptor_zh_label,
    get_descriptor_lexicon,
    is_approved_descriptor_tag,
    normalize_descriptor_category,
    validate_descriptor_tags,
)
from src.world.style_profile import DEFAULT_STYLE_PROFILE_ID


class DescriptorLexiconTests(unittest.TestCase):
    def test_default_descriptor_lexicon_is_readable(self) -> None:
        lexicon = get_descriptor_lexicon(DEFAULT_STYLE_PROFILE_ID)
        categories = {tag.category for tag in lexicon.tags}

        self.assertEqual(lexicon.lexicon_id, DEFAULT_STYLE_PROFILE_ID)
        self.assertEqual(
            categories,
            {"appearance", "function", "behavior", "sensory", "social_read", "ecological"},
        )

    def test_unknown_descriptor_lexicon_falls_back_to_default(self) -> None:
        lexicon = get_descriptor_lexicon("missing_profile")

        self.assertEqual(lexicon.lexicon_id, DEFAULT_STYLE_PROFILE_ID)

    def test_descriptor_tag_lookup_returns_display_labels(self) -> None:
        tag = descriptor_tag("reactive", category="behavior")

        self.assertIsNotNone(tag)
        self.assertEqual(tag.zh_label, "受刺激反应")
        self.assertEqual(tag.en_label, "reactive")

    def test_descriptor_zh_label_falls_back_for_unknown_tag(self) -> None:
        self.assertEqual(descriptor_zh_label("reactive", category="behavior"), "受刺激反应")
        self.assertEqual(
            descriptor_zh_label("unknown_tag", category="behavior", fallback="未知描述"),
            "未知描述",
        )

    def test_non_approved_descriptor_tag_is_rejected(self) -> None:
        self.assertFalse(
            is_approved_descriptor_tag(
                "unbounded_ai_label",
                category="behavior",
                profile_type="emergent_presence",
            )
        )

    def test_descriptor_tag_must_match_category(self) -> None:
        self.assertTrue(
            is_approved_descriptor_tag(
                "reactive",
                category="behavior",
                profile_type="emergent_presence",
            )
        )
        self.assertFalse(
            is_approved_descriptor_tag(
                "reactive",
                category="sensory",
                profile_type="emergent_presence",
            )
        )

    def test_descriptor_tag_must_match_profile_type(self) -> None:
        self.assertTrue(
            is_approved_descriptor_tag(
                "biosecurity_filter",
                category="function",
                profile_type="region_node",
            )
        )
        self.assertFalse(
            is_approved_descriptor_tag(
                "biosecurity_filter",
                category="function",
                profile_type="character",
            )
        )

    def test_emergent_presence_existing_tags_are_approved(self) -> None:
        self.assertTrue(
            is_approved_descriptor_tag(
                "reactive",
                category="behavior",
                profile_type="emergent_presence",
            )
        )
        self.assertTrue(
            is_approved_descriptor_tag(
                "territorial",
                category="behavior",
                profile_type="emergent_presence",
            )
        )
        self.assertTrue(
            is_approved_descriptor_tag(
                "spore_haze",
                category="sensory",
                profile_type="emergent_presence",
            )
        )
        self.assertTrue(
            is_approved_descriptor_tag(
                "biosecurity_risk",
                category="ecological",
                profile_type="emergent_presence",
            )
        )

    def test_validate_descriptor_tags_splits_accepted_and_rejected(self) -> None:
        accepted, rejected = validate_descriptor_tags(
            ["reactive", "territorial", "dragon_blood", "reactive"],
            category="behavior",
            profile_type="emergent_presence",
        )

        self.assertEqual(accepted, ["reactive", "territorial"])
        self.assertEqual(rejected, ["dragon_blood"])

    def test_approved_descriptor_tag_ids_can_filter_by_profile_type(self) -> None:
        tag_ids = approved_descriptor_tag_ids(
            category="sensory",
            profile_type="emergent_presence",
        )

        self.assertIn("spore_haze", tag_ids)
        self.assertNotIn("cold_light", tag_ids)

    def test_category_normalization_rejects_unknown_category(self) -> None:
        with self.assertRaises(ValueError):
            normalize_descriptor_category("freeform")


if __name__ == "__main__":
    unittest.main()
