import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.config.models import AIConfig, WorldConfig
from src.core.engine import WorldEngine
from src.interfaces.commands import CommandContext, handle_command
from src.storage.snapshots import load_world_state, save_world_state
from src.world.builder import build_world
from src.world.open_structure_template import (
    ApprovedStructureTemplateRegistry,
    MAX_TEMPLATE_FIELDS,
    TemplateApprovalQueue,
    approved_template_registry_from_payload,
    approved_template_registry_to_dict,
    build_template_proposal_audit_record,
    decide_template_approval_entry,
    get_active_approved_template,
    list_active_approved_templates,
    mark_template_proposal_validated,
    mark_template_proposal_validated_detailed,
    pending_template_approval_entries,
    proposal_from_payload,
    proposal_to_dict,
    register_approved_template_from_queue,
    set_approved_template_registry_status,
    submit_template_proposal_to_queue,
    template_approval_queue_from_payload,
    template_approval_queue_to_dict,
    template_proposal_audit_to_dict,
    template_proposal_report_to_dict,
    template_from_payload,
    template_schema_to_dict,
    validate_template_proposal_detailed,
    validate_template_proposal,
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


def _valid_proposal_payload():
    return {
        "proposal_id": "proposal_salvage_pressure_marker",
        "template": _valid_template_payload(),
        "rationale": "Tracks a bounded salvage-route pressure without adding new fixed object fields.",
        "source": "unit_test",
        "created_at_tick": 12,
        "status": "pending",
        "validation_errors": [],
        "reviewed_by": None,
        "reviewed_at_tick": None,
        "decision_notes": [],
    }


def _approved_queue_with_proposal():
    queue = TemplateApprovalQueue()
    proposal = proposal_from_payload(_valid_proposal_payload())
    submit_template_proposal_to_queue(queue, proposal, current_tick=50)
    decide_template_approval_entry(
        queue,
        "proposal_salvage_pressure_marker",
        action="approve",
        reviewer="lead_designer",
        current_tick=51,
        reason="Approved for registry tests.",
    )
    return queue, proposal


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

    def test_template_proposal_from_payload_round_trips(self) -> None:
        proposal = proposal_from_payload(_valid_proposal_payload(), current_tick=99)
        payload = proposal_to_dict(proposal)

        self.assertEqual(proposal.proposal_id, "proposal_salvage_pressure_marker")
        self.assertEqual(proposal.created_at_tick, 12)
        self.assertEqual(proposal.status, "pending")
        self.assertEqual(proposal.validation_errors, [])
        self.assertEqual(payload["proposal_id"], "proposal_salvage_pressure_marker")
        self.assertEqual(payload["template"]["template_id"], "salvage_pressure_marker")

    def test_template_proposal_uses_current_tick_when_tick_missing(self) -> None:
        payload = _valid_proposal_payload()
        payload.pop("created_at_tick")

        proposal = proposal_from_payload(payload, current_tick=44)

        self.assertEqual(proposal.created_at_tick, 44)

    def test_validate_template_proposal_requires_metadata(self) -> None:
        payload = _valid_proposal_payload()
        payload["proposal_id"] = ""
        payload["rationale"] = ""
        proposal = proposal_from_payload(payload)

        result = validate_template_proposal(proposal)

        self.assertFalse(result.accepted)
        self.assertIn("proposal_id is required", result.errors)
        self.assertIn("rationale is required", result.errors)

    def test_mark_template_proposal_validated_sets_validated_status(self) -> None:
        proposal = proposal_from_payload(_valid_proposal_payload())

        result = mark_template_proposal_validated(proposal)

        self.assertTrue(result.accepted)
        self.assertEqual(proposal.status, "validated")
        self.assertEqual(proposal.validation_errors, [])

    def test_mark_template_proposal_validated_sets_rejected_status(self) -> None:
        payload = _valid_proposal_payload()
        payload["template"]["allowed_effects"] = ["direct_worldstate_write"]
        proposal = proposal_from_payload(payload)

        result = mark_template_proposal_validated(proposal)

        self.assertFalse(result.accepted)
        self.assertEqual(proposal.status, "rejected")
        self.assertTrue(any("unsupported allowed_effect" in error for error in proposal.validation_errors))

    def test_detailed_proposal_validation_accepts_valid_proposal(self) -> None:
        proposal = proposal_from_payload(_valid_proposal_payload())

        report = validate_template_proposal_detailed(proposal)

        self.assertTrue(report.accepted)
        self.assertEqual(report.proposal_id, "proposal_salvage_pressure_marker")
        self.assertEqual(report.issues, [])
        self.assertEqual(report.status_after_validation, "validated")

    def test_detailed_proposal_validation_categorizes_metadata_and_field_issues(self) -> None:
        payload = _valid_proposal_payload()
        payload["proposal_id"] = ""
        payload["rationale"] = ""
        payload["template"]["fields"][0].pop("max_length")
        proposal = proposal_from_payload(payload)

        report = validate_template_proposal_detailed(proposal)

        categories = {issue.category for issue in report.issues}
        self.assertFalse(report.accepted)
        self.assertIn("metadata", categories)
        self.assertIn("fields", categories)
        self.assertTrue(any(issue.path == "proposal_id" for issue in report.issues))
        self.assertTrue(any(issue.path.endswith(".max_length") for issue in report.issues))

    def test_detailed_proposal_validation_categorizes_descriptor_style_lifecycle_and_safety(self) -> None:
        payload = _valid_proposal_payload()
        payload["template"]["allowed_effects"] = ["direct_worldstate_write"]
        payload["template"]["descriptor_constraints"]["behavior"] = ["dragon_blood"]
        payload["template"]["style_constraints"] = ["unregistered_style"]
        payload["template"]["lifecycle"]["initial_status"] = "archived"
        payload["template"]["lifecycle"]["allowed_statuses"] = ["active", "cooling"]
        payload["template"]["safety_notes"] = ["Requests python_dataclass expansion."]
        proposal = proposal_from_payload(payload)

        report = validate_template_proposal_detailed(proposal)

        categories = {issue.category for issue in report.issues}
        self.assertFalse(report.accepted)
        self.assertIn("descriptor", categories)
        self.assertIn("style", categories)
        self.assertIn("lifecycle", categories)
        self.assertIn("safety", categories)

    def test_detailed_report_serializes_to_plain_data(self) -> None:
        payload = _valid_proposal_payload()
        payload["template"]["fields"][0].pop("max_length")
        proposal = proposal_from_payload(payload)

        report_payload = template_proposal_report_to_dict(validate_template_proposal_detailed(proposal))

        self.assertEqual(report_payload["proposal_id"], "proposal_salvage_pressure_marker")
        self.assertFalse(report_payload["accepted"])
        self.assertEqual(report_payload["status_after_validation"], "rejected")
        self.assertEqual(report_payload["issues"][0]["category"], "fields")
        self.assertIn("message", report_payload["issues"][0])
        self.assertIn("path", report_payload["issues"][0])

    def test_build_template_proposal_audit_record_summarizes_issue_counts(self) -> None:
        payload = _valid_proposal_payload()
        payload["proposal_id"] = ""
        payload["template"]["allowed_effects"] = ["direct_worldstate_write"]
        proposal = proposal_from_payload(payload)

        audit = build_template_proposal_audit_record(proposal, current_tick=22)
        audit_payload = template_proposal_audit_to_dict(audit)

        self.assertEqual(audit.audit_id, "template_validation_unknown_22")
        self.assertEqual(audit.tick, 22)
        self.assertFalse(audit.accepted)
        self.assertGreaterEqual(audit.issue_counts["metadata"], 1)
        self.assertGreaterEqual(audit.issue_counts["safety"], 1)
        self.assertEqual(audit_payload["report"]["status_after_validation"], "rejected")

    def test_mark_template_proposal_validated_detailed_updates_status_and_errors(self) -> None:
        payload = _valid_proposal_payload()
        payload["template"]["allowed_effects"] = ["direct_worldstate_write"]
        proposal = proposal_from_payload(payload)

        report = mark_template_proposal_validated_detailed(proposal)

        self.assertFalse(report.accepted)
        self.assertEqual(proposal.status, "rejected")
        self.assertTrue(any("unsupported allowed_effect" in error for error in proposal.validation_errors))

    def test_submit_template_proposal_to_queue_validates_and_queues_pending_entry(self) -> None:
        queue = TemplateApprovalQueue()
        proposal = proposal_from_payload(_valid_proposal_payload())

        entry = submit_template_proposal_to_queue(queue, proposal, current_tick=31)

        self.assertEqual(entry.status, "pending")
        self.assertEqual(entry.submitted_at_tick, 31)
        self.assertEqual(proposal.status, "validated")
        self.assertTrue(entry.validation_report.accepted)
        self.assertTrue(entry.validation_audit.accepted)
        self.assertIn("proposal_salvage_pressure_marker", queue.entries)

    def test_submit_invalid_template_proposal_to_queue_records_rejected_entry(self) -> None:
        queue = TemplateApprovalQueue()
        payload = _valid_proposal_payload()
        payload["template"]["allowed_effects"] = ["direct_worldstate_write"]
        proposal = proposal_from_payload(payload)

        entry = submit_template_proposal_to_queue(queue, proposal, current_tick=32)

        self.assertEqual(entry.status, "rejected")
        self.assertEqual(proposal.status, "rejected")
        self.assertFalse(entry.validation_report.accepted)
        self.assertGreaterEqual(entry.validation_audit.issue_counts["safety"], 1)

    def test_approval_queue_approve_updates_entry_and_review_metadata(self) -> None:
        queue = TemplateApprovalQueue()
        proposal = proposal_from_payload(_valid_proposal_payload())
        submit_template_proposal_to_queue(queue, proposal, current_tick=33)

        decision = decide_template_approval_entry(
            queue,
            "proposal_salvage_pressure_marker",
            action="approve",
            reviewer="lead_designer",
            current_tick=34,
            reason="Schema is bounded and useful.",
            notes=["Ready for registry in V5-E."],
        )

        entry = queue.entries["proposal_salvage_pressure_marker"]
        self.assertTrue(decision.accepted)
        self.assertEqual(entry.status, "approved")
        self.assertEqual(proposal.reviewed_by, "lead_designer")
        self.assertEqual(proposal.reviewed_at_tick, 34)
        self.assertIn("Schema is bounded and useful.", proposal.decision_notes)
        self.assertEqual(len(entry.decisions), 1)

    def test_approval_queue_rejects_pending_entry(self) -> None:
        queue = TemplateApprovalQueue()
        proposal = proposal_from_payload(_valid_proposal_payload())
        submit_template_proposal_to_queue(queue, proposal, current_tick=35)

        decision = decide_template_approval_entry(
            queue,
            "proposal_salvage_pressure_marker",
            action="reject",
            reviewer="lead_designer",
            current_tick=36,
            reason="Too close to an existing fixed model.",
        )

        entry = queue.entries["proposal_salvage_pressure_marker"]
        self.assertTrue(decision.accepted)
        self.assertEqual(entry.status, "rejected")
        self.assertEqual(entry.decisions[0].action, "reject")

    def test_approval_queue_freeze_then_withdraw_entry(self) -> None:
        queue = TemplateApprovalQueue()
        proposal = proposal_from_payload(_valid_proposal_payload())
        submit_template_proposal_to_queue(queue, proposal, current_tick=37)

        freeze = decide_template_approval_entry(
            queue,
            "proposal_salvage_pressure_marker",
            action="freeze",
            reviewer="lead_designer",
            current_tick=38,
        )
        withdraw = decide_template_approval_entry(
            queue,
            "proposal_salvage_pressure_marker",
            action="withdraw",
            reviewer="lead_designer",
            current_tick=39,
            reason="Deferred until registry rules are ready.",
        )

        entry = queue.entries["proposal_salvage_pressure_marker"]
        self.assertTrue(freeze.accepted)
        self.assertTrue(withdraw.accepted)
        self.assertEqual(entry.status, "withdrawn")
        self.assertEqual([decision.action for decision in entry.decisions], ["freeze", "withdraw"])

    def test_approval_queue_rejects_invalid_decision_without_state_change(self) -> None:
        queue = TemplateApprovalQueue()
        proposal = proposal_from_payload(_valid_proposal_payload())
        submit_template_proposal_to_queue(queue, proposal, current_tick=40)

        decision = decide_template_approval_entry(
            queue,
            "proposal_salvage_pressure_marker",
            action="approve",
            reviewer="",
            current_tick=41,
        )

        entry = queue.entries["proposal_salvage_pressure_marker"]
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "reviewer is required")
        self.assertEqual(entry.status, "pending")
        self.assertEqual(len(entry.decisions), 1)

    def test_pending_template_approval_entries_only_returns_pending(self) -> None:
        queue = TemplateApprovalQueue()
        first = proposal_from_payload(_valid_proposal_payload())
        second_payload = _valid_proposal_payload()
        second_payload["proposal_id"] = "proposal_second_marker"
        second_payload["template"]["template_id"] = "second_marker"
        second = proposal_from_payload(second_payload)
        submit_template_proposal_to_queue(queue, first, current_tick=42)
        submit_template_proposal_to_queue(queue, second, current_tick=43)
        decide_template_approval_entry(
            queue,
            "proposal_salvage_pressure_marker",
            action="approve",
            reviewer="lead_designer",
            current_tick=44,
        )

        pending = pending_template_approval_entries(queue)

        self.assertEqual([entry.proposal.proposal_id for entry in pending], ["proposal_second_marker"])

    def test_template_approval_queue_round_trips_plain_data(self) -> None:
        queue = TemplateApprovalQueue()
        proposal = proposal_from_payload(_valid_proposal_payload())
        submit_template_proposal_to_queue(queue, proposal, current_tick=45)
        decide_template_approval_entry(
            queue,
            "proposal_salvage_pressure_marker",
            action="approve",
            reviewer="lead_designer",
            current_tick=46,
            reason="Approved for later registry testing.",
        )

        payload = template_approval_queue_to_dict(queue)
        loaded = template_approval_queue_from_payload(payload)

        entry = loaded.entries["proposal_salvage_pressure_marker"]
        self.assertEqual(entry.status, "approved")
        self.assertEqual(entry.proposal.template.template_id, "salvage_pressure_marker")
        self.assertTrue(entry.validation_report.accepted)
        self.assertEqual(entry.validation_audit.proposal_id, "proposal_salvage_pressure_marker")
        self.assertEqual(entry.decisions[0].action, "approve")

    def test_template_approval_queue_is_preserved_in_snapshots(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        proposal = proposal_from_payload(_valid_proposal_payload())
        submit_template_proposal_to_queue(world.template_approval_queue, proposal, current_tick=world.current_tick)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save_world_state(world, path)
            loaded = load_world_state(path)

        self.assertIn("proposal_salvage_pressure_marker", loaded.template_approval_queue.entries)
        entry = loaded.template_approval_queue.entries["proposal_salvage_pressure_marker"]
        self.assertEqual(entry.status, "pending")
        self.assertTrue(entry.validation_report.accepted)

    def test_cli_templates_queue_and_approve_queued_proposal(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        proposal = proposal_from_payload(_valid_proposal_payload())
        submit_template_proposal_to_queue(world.template_approval_queue, proposal, current_tick=world.current_tick)

        with tempfile.TemporaryDirectory() as tmp:
            context = CommandContext(
                engine=WorldEngine(world, ai_config=DEFAULT_AI_CONFIG),
                world_config=WorldConfig(**DEFAULT_WORLD_CONFIG),
                ai_config=AIConfig(**DEFAULT_AI_CONFIG),
                snapshot_path=Path(tmp) / "world.json",
            )
            queue_output = handle_command(context, "templates queue 5")
            approve_output = handle_command(
                context,
                "templates approve proposal_salvage_pressure_marker lead_designer bounded schema",
            )

        self.assertIn("Template approval queue:", queue_output)
        self.assertIn("proposal_salvage_pressure_marker", queue_output)
        self.assertIn("Template approval decision:", approve_output)
        self.assertIn("result: accepted", approve_output)
        self.assertEqual(world.template_approval_queue.entries["proposal_salvage_pressure_marker"].status, "approved")

    def test_register_approved_template_from_queue_adds_active_registry_record(self) -> None:
        queue, _proposal = _approved_queue_with_proposal()
        registry = ApprovedStructureTemplateRegistry()

        result = register_approved_template_from_queue(
            registry,
            queue,
            "proposal_salvage_pressure_marker",
            registered_by="registry_keeper",
            current_tick=52,
            notes=["Ready for V5-F instance generation."],
        )

        self.assertTrue(result.accepted, result.errors)
        self.assertIn("salvage_pressure_marker", registry.templates)
        record = registry.templates["salvage_pressure_marker"]
        self.assertEqual(record.status, "active")
        self.assertEqual(record.source_proposal_id, "proposal_salvage_pressure_marker")
        self.assertEqual(record.approved_by, "lead_designer")
        self.assertEqual(record.registered_by, "registry_keeper")
        self.assertEqual(record.registered_at_tick, 52)
        self.assertEqual(record.registry_notes, ["Ready for V5-F instance generation."])

    def test_register_approved_template_rejects_unapproved_queue_entry(self) -> None:
        queue = TemplateApprovalQueue()
        proposal = proposal_from_payload(_valid_proposal_payload())
        submit_template_proposal_to_queue(queue, proposal, current_tick=53)
        registry = ApprovedStructureTemplateRegistry()

        result = register_approved_template_from_queue(
            registry,
            queue,
            "proposal_salvage_pressure_marker",
            registered_by="registry_keeper",
        )

        self.assertFalse(result.accepted)
        self.assertIn("is not approved", result.errors[0])
        self.assertEqual(registry.templates, {})

    def test_register_approved_template_rejects_same_or_older_version(self) -> None:
        queue, _proposal = _approved_queue_with_proposal()
        registry = ApprovedStructureTemplateRegistry()
        first = register_approved_template_from_queue(
            registry,
            queue,
            "proposal_salvage_pressure_marker",
            registered_by="registry_keeper",
        )
        second = register_approved_template_from_queue(
            registry,
            queue,
            "proposal_salvage_pressure_marker",
            registered_by="registry_keeper",
        )

        self.assertTrue(first.accepted)
        self.assertFalse(second.accepted)
        self.assertIn("is not newer", second.errors[0])

    def test_approved_template_registry_active_query_and_status_updates(self) -> None:
        queue, _proposal = _approved_queue_with_proposal()
        registry = ApprovedStructureTemplateRegistry()
        register_approved_template_from_queue(
            registry,
            queue,
            "proposal_salvage_pressure_marker",
            registered_by="registry_keeper",
        )

        active = get_active_approved_template(registry, "salvage_pressure_marker")
        listed = list_active_approved_templates(registry)
        frozen = set_approved_template_registry_status(
            registry,
            "salvage_pressure_marker",
            "frozen",
            note="Paused until instance validator lands.",
        )

        self.assertIsNotNone(active)
        self.assertEqual([record.template.template_id for record in listed], ["salvage_pressure_marker"])
        self.assertTrue(frozen.accepted)
        self.assertIsNone(get_active_approved_template(registry, "salvage_pressure_marker"))
        self.assertEqual(list_active_approved_templates(registry), [])
        self.assertIn("Paused until instance validator lands.", registry.templates["salvage_pressure_marker"].registry_notes)

    def test_approved_template_registry_round_trips_plain_data(self) -> None:
        queue, _proposal = _approved_queue_with_proposal()
        registry = ApprovedStructureTemplateRegistry()
        register_approved_template_from_queue(
            registry,
            queue,
            "proposal_salvage_pressure_marker",
            registered_by="registry_keeper",
            current_tick=54,
        )

        payload = approved_template_registry_to_dict(registry)
        loaded = approved_template_registry_from_payload(payload)

        self.assertIn("salvage_pressure_marker", loaded.templates)
        record = loaded.templates["salvage_pressure_marker"]
        self.assertEqual(record.template.template_id, "salvage_pressure_marker")
        self.assertEqual(record.source_proposal_id, "proposal_salvage_pressure_marker")
        self.assertEqual(record.registered_by, "registry_keeper")
        self.assertEqual(record.registered_at_tick, 54)

    def test_approved_template_registry_is_preserved_in_snapshots(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        queue, _proposal = _approved_queue_with_proposal()
        world.template_approval_queue = queue
        register_approved_template_from_queue(
            world.approved_template_registry,
            world.template_approval_queue,
            "proposal_salvage_pressure_marker",
            registered_by="registry_keeper",
            current_tick=55,
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save_world_state(world, path)
            loaded = load_world_state(path)

        self.assertIn("salvage_pressure_marker", loaded.approved_template_registry.templates)
        record = loaded.approved_template_registry.templates["salvage_pressure_marker"]
        self.assertEqual(record.status, "active")
        self.assertEqual(record.source_proposal_id, "proposal_salvage_pressure_marker")

    def test_cli_templates_register_and_registry(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        queue, _proposal = _approved_queue_with_proposal()
        world.template_approval_queue = queue

        with tempfile.TemporaryDirectory() as tmp:
            context = CommandContext(
                engine=WorldEngine(world, ai_config=DEFAULT_AI_CONFIG),
                world_config=WorldConfig(**DEFAULT_WORLD_CONFIG),
                ai_config=AIConfig(**DEFAULT_AI_CONFIG),
                snapshot_path=Path(tmp) / "world.json",
            )
            register_output = handle_command(
                context,
                "templates register proposal_salvage_pressure_marker registry_keeper ready for V5-F",
            )
            registry_output = handle_command(context, "templates registry 5")

        self.assertIn("Template registered: proposal_salvage_pressure_marker", register_output)
        self.assertIn("Approved template registry:", registry_output)
        self.assertIn("salvage_pressure_marker", registry_output)
        self.assertIn("status=active", registry_output)


if __name__ == "__main__":
    unittest.main()
