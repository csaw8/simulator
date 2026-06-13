import tempfile
import unittest
from pathlib import Path

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.config.models import AIConfig, WorldConfig
from src.core.engine import WorldEngine
from src.core.structure_template_ai import propose_structure_template
from src.core.template_instance_ai import propose_template_instance
from src.interfaces.commands import CommandContext, handle_command
from src.world.builder import build_world
from src.world.open_structure_template import (
    ApprovedStructureTemplateRegistry,
    TemplateApprovalQueue,
    create_template_instance,
    decide_template_approval_entry,
    proposal_from_payload,
    register_approved_template_from_queue,
    submit_template_proposal_to_queue,
    template_instance_from_payload,
)


class FakeTemplateClient:
    provider = "deepseek"

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def create_json_completion_with_limits(self, messages, *, max_tokens, thinking_budget):
        self.calls.append({"messages": messages, "max_tokens": max_tokens, "thinking_budget": thinking_budget})
        return self.payload


def _cfg():
    cfg = DEFAULT_AI_CONFIG.copy()
    cfg["provider"] = "none"
    cfg["template_instance_cost_tier"] = "low"
    cfg["structure_template_cost_tier"] = "low"
    return cfg


def _cli_cfg():
    cfg = DEFAULT_AI_CONFIG.copy()
    cfg["provider"] = "none"
    return cfg


def _template_payload(template_id="salvage_pressure_marker"):
    return {
        "template_id": template_id,
        "title": "Salvage Pressure Marker",
        "template_kind": "resource_flow",
        "descriptor_profile_type": "dynamic_structure",
        "fields": [
            {"field_id": "public_name", "label": "Public name", "field_type": "text", "required": True, "max_length": 80},
            {"field_id": "pressure_level", "label": "Pressure level", "field_type": "enum", "required": True, "allowed_values": ["low", "medium", "high"]},
            {"field_id": "linked_route", "label": "Linked route", "field_type": "ref", "ref_types": ["supply_line", "region_node"]},
        ],
        "lifecycle": {
            "initial_status": "active",
            "allowed_statuses": ["active", "cooling", "archived"],
            "terminal_statuses": ["archived"],
        },
        "allowed_effects": ["event", "pressure_thread"],
        "descriptor_constraints": {"behavior": ["reactive"]},
        "style_constraints": ["realistic_future_anomaly"],
        "safety_notes": ["No direct fixed object mutation."],
        "status": "pending",
        "version": 1,
    }


def _proposal_payload(template_id="salvage_pressure_marker", proposal_id="proposal_salvage_pressure_marker"):
    return {
        "proposal_id": proposal_id,
        "template": _template_payload(template_id),
        "rationale": "Tracks a bounded pressure marker.",
        "source": "unit_test",
        "created_at_tick": 1,
        "status": "pending",
    }


def _world_with_registered_template():
    world = build_world(DEFAULT_WORLD_CONFIG)
    proposal = proposal_from_payload(_proposal_payload())
    submit_template_proposal_to_queue(world.template_approval_queue, proposal, current_tick=1)
    decide_template_approval_entry(
        world.template_approval_queue,
        "proposal_salvage_pressure_marker",
        action="approve",
        reviewer="lead_designer",
        current_tick=2,
    )
    result = register_approved_template_from_queue(
        world.approved_template_registry,
        world.template_approval_queue,
        "proposal_salvage_pressure_marker",
        registered_by="registry_keeper",
        current_tick=3,
    )
    assert result.accepted, result.errors
    return world


def _instance_payload():
    return {
        "instance": {
            "instance_id": "instance_salvage_pressure_marker",
            "field_values": {
                "public_name": "North route pressure",
                "pressure_level": "medium",
                "linked_route": "supply_line:supply_001",
            },
            "linked_refs": ["supply_line:supply_001"],
            "descriptor_values": {"behavior": ["reactive"]},
            "pressure_score": 0.55,
            "status": "active",
        }
    }


class TemplateAITests(unittest.TestCase):
    def test_template_instance_ai_dry_run_validates_without_mutating_world(self) -> None:
        world = _world_with_registered_template()
        client = FakeTemplateClient(_instance_payload())

        result = propose_template_instance(
            world,
            template_id="salvage_pressure_marker",
            scope_ref="region:region_001",
            ai_config=_cfg(),
            apply=False,
            client=client,
        )

        self.assertEqual(result.source, "deepseek")
        self.assertFalse(result.applied)
        self.assertTrue(result.validation.accepted, result.validation.errors)
        self.assertEqual(world.template_instances.instances, {})
        self.assertIsNotNone(result.audit_id)
        audit = world.ai_proposal_audits[result.audit_id]
        self.assertEqual(audit.proposal_type, "template_instance")
        self.assertFalse(audit.applied)
        self.assertEqual(audit.accepted_refs, ["instance_salvage_pressure_marker"])

    def test_template_instance_ai_apply_writes_through_validator(self) -> None:
        world = _world_with_registered_template()
        client = FakeTemplateClient(_instance_payload())

        result = propose_template_instance(
            world,
            template_id="salvage_pressure_marker",
            scope_ref="region:region_001",
            ai_config=_cfg(),
            apply=True,
            client=client,
        )

        self.assertTrue(result.validation.accepted, result.validation.errors)
        self.assertIn("instance_salvage_pressure_marker", world.template_instances.instances)
        audit = world.ai_proposal_audits[result.audit_id]
        self.assertTrue(audit.applied)

    def test_template_instance_ai_rejects_invalid_payload(self) -> None:
        world = _world_with_registered_template()
        payload = _instance_payload()
        payload["instance"]["field_values"]["pressure_level"] = "extreme"
        client = FakeTemplateClient(payload)

        result = propose_template_instance(
            world,
            template_id="salvage_pressure_marker",
            scope_ref="region:region_001",
            ai_config=_cfg(),
            apply=True,
            client=client,
        )

        self.assertFalse(result.validation.accepted)
        self.assertEqual(world.template_instances.instances, {})
        audit = world.ai_proposal_audits[result.audit_id]
        self.assertTrue(audit.rejected_reasons)

    def test_template_instance_cli_without_client_records_audit(self) -> None:
        world = _world_with_registered_template()
        with tempfile.TemporaryDirectory() as tmp:
            context = CommandContext(
                engine=WorldEngine(world, ai_config=_cfg()),
                world_config=WorldConfig(**DEFAULT_WORLD_CONFIG),
                ai_config=AIConfig(**_cli_cfg()),
                snapshot_path=Path(tmp) / "world.json",
            )
            output = handle_command(context, "templates propose-instance salvage_pressure_marker region:region_001")

        self.assertIn("Template instance AI proposal:", output)
        self.assertIn("client unavailable", output)
        self.assertEqual(len(world.ai_proposal_audits), 1)

    def test_structure_template_ai_dry_run_validates_without_queueing(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        client = FakeTemplateClient({"proposal": _proposal_payload("signal_brokerage", "proposal_signal_brokerage")})

        result = propose_structure_template(world, ai_config=_cfg(), apply=False, client=client)

        self.assertTrue(result.validation.accepted, result.validation.errors)
        self.assertEqual(world.template_approval_queue.entries, {})
        self.assertIsNotNone(result.audit_id)
        audit = world.ai_proposal_audits[result.audit_id]
        self.assertEqual(audit.proposal_type, "structure_template")
        self.assertFalse(audit.applied)

    def test_structure_template_ai_apply_queues_proposal_for_review(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        client = FakeTemplateClient({"proposal": _proposal_payload("signal_brokerage", "proposal_signal_brokerage")})

        result = propose_structure_template(world, ai_config=_cfg(), apply=True, client=client)

        self.assertTrue(result.validation.accepted, result.validation.errors)
        self.assertIn("proposal_signal_brokerage", world.template_approval_queue.entries)
        self.assertEqual(world.template_approval_queue.entries["proposal_signal_brokerage"].status, "pending")
        audit = world.ai_proposal_audits[result.audit_id]
        self.assertTrue(audit.applied)

    def test_structure_template_cli_without_client_records_audit(self) -> None:
        world = build_world(DEFAULT_WORLD_CONFIG)
        with tempfile.TemporaryDirectory() as tmp:
            context = CommandContext(
                engine=WorldEngine(world, ai_config=_cfg()),
                world_config=WorldConfig(**DEFAULT_WORLD_CONFIG),
                ai_config=AIConfig(**_cli_cfg()),
                snapshot_path=Path(tmp) / "world.json",
            )
            output = handle_command(context, "templates propose-template")

        self.assertIn("Structure template AI proposal:", output)
        self.assertIn("client unavailable", output)
        self.assertEqual(len(world.ai_proposal_audits), 1)

    def test_duplicate_template_proposal_is_rejected_for_pollution_control(self) -> None:
        queue = TemplateApprovalQueue()
        first = proposal_from_payload(_proposal_payload("signal_brokerage", "proposal_one"))
        second = proposal_from_payload(_proposal_payload("signal_brokerage", "proposal_two"))

        first_entry = submit_template_proposal_to_queue(queue, first, current_tick=1)
        second_entry = submit_template_proposal_to_queue(queue, second, current_tick=2)

        self.assertEqual(first_entry.status, "pending")
        self.assertEqual(second_entry.status, "rejected")
        self.assertIn("duplicate template_id", second.validation_errors[0])

    def test_template_instance_store_capacity_limit_rejects_overflow(self) -> None:
        world = _world_with_registered_template()
        for index in range(120):
            payload = _instance_payload()["instance"]
            payload["instance_id"] = f"instance_{index}"
            result = create_template_instance(
                world.template_instances,
                world.approved_template_registry,
                template_instance_from_payload(
                    {
                        **payload,
                        "template_id": "salvage_pressure_marker",
                        "template_version": 1,
                        "scope_ref": "region:region_001",
                    }
                ),
            )
            self.assertTrue(result.accepted, result.errors)
        overflow = template_instance_from_payload(
            {
                **_instance_payload()["instance"],
                "instance_id": "instance_overflow",
                "template_id": "salvage_pressure_marker",
                "template_version": 1,
                "scope_ref": "region:region_001",
            }
        )

        result = create_template_instance(world.template_instances, world.approved_template_registry, overflow)

        self.assertFalse(result.accepted)
        self.assertIn("store is full", result.errors[0])


if __name__ == "__main__":
    unittest.main()
