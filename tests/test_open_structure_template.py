import unittest

from src.world.open_structure_template import (
    MAX_TEMPLATE_FIELDS,
    template_from_payload,
    template_schema_to_dict,
    validate_template_payload,
    validate_template_schema,
)
from src.world.style_profile import (
    DEFAULT_STYLE_PROFILE_ID,
    POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
)


def _valid_template_payload():
    return {
        "template_id": "salvage_pressure_marker",
        "title": "Salvage Pressure Marker",
        "template_kind": "resource_flow",
        "descriptor_profile_type": "dynamic_structure",
        "fields": [
            {
                "field_id": "public_name",
                "label": "Public name",
                "field_type": "text",
                "required": True,
                "max_length": 80,
            },
            {
                "field_id": "pressure_level",
                "label": "Pressure level",
                "field_type": "enum",
                "required": True,
                "allowed_values": ["low", "medium", "high"],
            },
            {
                "field_id": "linked_route",
                "label": "Linked route",
                "field_type": "ref",
                "ref_types": ["supply_line", "region_node"],
            },
        ],
        "lifecycle": {
            "initial_status": "active",
            "allowed_statuses": ["active", "cooling", "archived"],
            "terminal_statuses": ["archived"],
            "max_active_ticks": 40,
        },
        "allowed_effects": ["event", "relation", "pressure_thread", "descriptor_profile"],
        "descriptor_constraints": {
            "behavior": ["reactive"],
            "social_read": ["rumored"],
            "ecological": ["habitat_disruption"],
        },
        "style_constraints": [DEFAULT_STYLE_PROFILE_ID],
        "safety_notes": ["No direct fixed object mutation."],
        "status": "pending",
        "version": 1,
    }


class OpenStructureTemplateTests(unittest.TestCase):
    def test_valid_template_payload_is_accepted(self) -> None:
        result = validate_template_payload(_valid_template_payload())

        self.assertTrue(result.accepted)
        self.assertEqual(result.errors, [])

    def test_template_from_payload_normalizes_and_serializes(self) -> None:
        template = template_from_payload(_valid_template_payload())
        payload = template_schema_to_dict(template)

        self.assertEqual(template.template_id, "salvage_pressure_marker")
        self.assertEqual(payload["template_id"], "salvage_pressure_marker")
        self.assertEqual(payload["lifecycle"]["initial_status"], "active")
        self.assertEqual(payload["descriptor_constraints"]["behavior"], ["reactive"])

    def test_rejects_unknown_template_kind(self) -> None:
        payload = _valid_template_payload()
        payload["template_kind"] = "freeform_python_class"

        result = validate_template_payload(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any("unsupported template_kind" in error for error in result.errors))

    def test_rejects_too_many_fields(self) -> None:
        payload = _valid_template_payload()
        payload["fields"] = [
            {
                "field_id": f"field_{index}",
                "label": f"Field {index}",
                "field_type": "boolean",
            }
            for index in range(MAX_TEMPLATE_FIELDS + 1)
        ]

        result = validate_template_payload(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any("too many fields" in error for error in result.errors))

    def test_rejects_text_field_without_max_length(self) -> None:
        payload = _valid_template_payload()
        payload["fields"][0].pop("max_length")

        result = validate_template_payload(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any("requires max_length" in error for error in result.errors))

    def test_rejects_enum_without_allowed_values(self) -> None:
        payload = _valid_template_payload()
        payload["fields"][1]["allowed_values"] = []

        result = validate_template_payload(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any("requires allowed_values" in error for error in result.errors))

    def test_rejects_unapproved_effect_channel(self) -> None:
        payload = _valid_template_payload()
        payload["allowed_effects"] = ["event", "direct_worldstate_write"]

        result = validate_template_payload(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any("unsupported allowed_effect" in error for error in result.errors))

    def test_rejects_unapproved_descriptor_tag(self) -> None:
        payload = _valid_template_payload()
        payload["descriptor_constraints"]["behavior"] = ["dragon_blood"]

        result = validate_template_payload(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any("not approved" in error for error in result.errors))

    def test_descriptor_constraints_are_style_scoped(self) -> None:
        payload = _valid_template_payload()
        payload["style_constraints"] = [POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID]
        payload["descriptor_constraints"] = {
            "behavior": ["guarded"],
            "social_read": ["owed_debts"],
            "ecological": ["water_stress"],
        }

        result = validate_template_payload(payload)

        self.assertTrue(result.accepted, result.errors)

    def test_rejects_descriptor_tag_from_wrong_style(self) -> None:
        payload = _valid_template_payload()
        payload["style_constraints"] = [POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID]
        payload["descriptor_constraints"]["behavior"] = ["reactive"]

        result = validate_template_payload(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any("not approved" in error for error in result.errors))

    def test_rejects_unknown_style_constraint(self) -> None:
        payload = _valid_template_payload()
        payload["style_constraints"] = ["unregistered_style"]

        result = validate_template_payload(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any("unknown style_constraint" in error for error in result.errors))

    def test_rejects_bad_lifecycle(self) -> None:
        payload = _valid_template_payload()
        payload["lifecycle"]["initial_status"] = "active"
        payload["lifecycle"]["allowed_statuses"] = ["cooling", "archived"]

        result = validate_template_payload(payload)

        self.assertFalse(result.accepted)
        self.assertTrue(any("initial_status" in error for error in result.errors))

    def test_validate_template_schema_accepts_template_object(self) -> None:
        template = template_from_payload(_valid_template_payload())
        result = validate_template_schema(template)

        self.assertTrue(result.accepted)


if __name__ == "__main__":
    unittest.main()
