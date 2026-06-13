"""Schema and validation for semi-open AI-proposed structure templates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.world.descriptor_lexicon import (
    DESCRIPTOR_CATEGORIES,
    DESCRIPTOR_PROFILE_TYPES,
    is_approved_descriptor_tag,
)
from src.world.style_profile import DEFAULT_STYLE_PROFILE_ID, DEFAULT_WORLD_STYLE_PROFILES


ALLOWED_TEMPLATE_KINDS = {
    "social_formation",
    "place_condition",
    "hazard_pattern",
    "resource_flow",
    "signal_pattern",
}
ALLOWED_TEMPLATE_FIELD_TYPES = {"text", "integer", "number", "boolean", "enum", "ref", "ref_list", "tag_list"}
ALLOWED_TEMPLATE_EFFECTS = {"event", "relation", "pressure_thread", "narrative_observation", "descriptor_profile"}
ALLOWED_TEMPLATE_STATUSES = {"active", "cooling", "archived"}
ALLOWED_TEMPLATE_REGISTRY_STATUSES = {"pending", "approved", "rejected", "frozen", "retired"}
ALLOWED_TEMPLATE_PROPOSAL_STATUSES = {"pending", "validated", "rejected", "withdrawn"}
MAX_TEMPLATE_FIELDS = 8
MAX_FIELD_ALLOWED_VALUES = 12
MAX_DESCRIPTOR_TAGS_PER_TEMPLATE_CATEGORY = 8
MAX_STYLE_CONSTRAINTS = 4
MAX_ALLOWED_EFFECTS = 5
MAX_ID_LENGTH = 48
MAX_LABEL_LENGTH = 80
MAX_TEXT_LENGTH = 240


@dataclass(slots=True)
class TemplateFieldSpec:
    """One bounded field definition inside a semi-open structure template."""

    field_id: str
    label: str
    field_type: str
    required: bool = False
    max_length: int | None = None
    allowed_values: list[str] = field(default_factory=list)
    ref_types: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TemplateLifecycleSpec:
    """Allowed lifecycle states for instances created from a template."""

    initial_status: str = "active"
    allowed_statuses: list[str] = field(default_factory=lambda: ["active", "cooling", "archived"])
    terminal_statuses: list[str] = field(default_factory=lambda: ["archived"])
    max_active_ticks: int | None = None


@dataclass(slots=True)
class SemiOpenStructureTemplate:
    """A constrained JSON-defined template; it is data, not executable code."""

    template_id: str
    title: str
    template_kind: str
    descriptor_profile_type: str
    fields: list[TemplateFieldSpec] = field(default_factory=list)
    lifecycle: TemplateLifecycleSpec = field(default_factory=TemplateLifecycleSpec)
    allowed_effects: list[str] = field(default_factory=list)
    descriptor_constraints: dict[str, list[str]] = field(default_factory=dict)
    style_constraints: list[str] = field(default_factory=lambda: [DEFAULT_STYLE_PROFILE_ID])
    safety_notes: list[str] = field(default_factory=list)
    status: str = "pending"
    version: int = 1


@dataclass(slots=True)
class TemplateValidationResult:
    """Validation result for one semi-open template schema."""

    accepted: bool
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StructureTemplateProposal:
    """Auditable candidate wrapper around a semi-open template schema."""

    proposal_id: str
    template: SemiOpenStructureTemplate
    rationale: str
    source: str
    created_at_tick: int
    status: str = "pending"
    validation_errors: list[str] = field(default_factory=list)
    reviewed_by: str | None = None
    reviewed_at_tick: int | None = None
    decision_notes: list[str] = field(default_factory=list)


def template_from_payload(payload: dict[str, Any]) -> SemiOpenStructureTemplate:
    """Build a template object from plain JSON-like data."""
    fields = [
        TemplateFieldSpec(
            field_id=_normalize_id(raw_field.get("field_id", "")),
            label=_clean_text(raw_field.get("label", ""), limit=MAX_LABEL_LENGTH),
            field_type=_normalize_id(raw_field.get("field_type", "")),
            required=bool(raw_field.get("required", False)),
            max_length=_optional_positive_int(raw_field.get("max_length")),
            allowed_values=_clean_text_list(raw_field.get("allowed_values", []), limit=MAX_FIELD_ALLOWED_VALUES),
            ref_types=_clean_id_list(raw_field.get("ref_types", []), limit=MAX_FIELD_ALLOWED_VALUES),
        )
        for raw_field in payload.get("fields", [])
        if isinstance(raw_field, dict)
    ]
    lifecycle_payload = payload.get("lifecycle", {})
    lifecycle = TemplateLifecycleSpec()
    if isinstance(lifecycle_payload, dict):
        lifecycle = TemplateLifecycleSpec(
            initial_status=_normalize_id(lifecycle_payload.get("initial_status", "active")),
            allowed_statuses=_clean_id_list(
                lifecycle_payload.get("allowed_statuses", ["active", "cooling", "archived"]),
                limit=len(ALLOWED_TEMPLATE_STATUSES),
            ),
            terminal_statuses=_clean_id_list(
                lifecycle_payload.get("terminal_statuses", ["archived"]),
                limit=len(ALLOWED_TEMPLATE_STATUSES),
            ),
            max_active_ticks=_optional_positive_int(lifecycle_payload.get("max_active_ticks")),
        )
    return SemiOpenStructureTemplate(
        template_id=_normalize_id(payload.get("template_id", "")),
        title=_clean_text(payload.get("title", ""), limit=MAX_LABEL_LENGTH),
        template_kind=_normalize_id(payload.get("template_kind", "")),
        descriptor_profile_type=_normalize_id(payload.get("descriptor_profile_type", "")),
        fields=fields,
        lifecycle=lifecycle,
        allowed_effects=_clean_id_list(payload.get("allowed_effects", []), limit=MAX_ALLOWED_EFFECTS),
        descriptor_constraints=_clean_descriptor_constraints(payload.get("descriptor_constraints", {})),
        style_constraints=_clean_id_list(
            payload.get("style_constraints", [DEFAULT_STYLE_PROFILE_ID]),
            limit=MAX_STYLE_CONSTRAINTS,
        ),
        safety_notes=_clean_text_list(payload.get("safety_notes", []), limit=5),
        status=_normalize_id(payload.get("status", "pending")),
        version=_optional_positive_int(payload.get("version")) or 1,
    )


def validate_template_schema(template: SemiOpenStructureTemplate) -> TemplateValidationResult:
    """Validate one semi-open structure template without mutating world state."""
    errors: list[str] = []
    _validate_identity(template, errors)
    _validate_fields(template, errors)
    _validate_lifecycle(template, errors)
    _validate_effects(template, errors)
    _validate_descriptor_constraints(template, errors)
    _validate_style_constraints(template, errors)
    return TemplateValidationResult(accepted=not errors, errors=errors)


def validate_template_payload(payload: dict[str, Any]) -> TemplateValidationResult:
    """Validate a JSON-like template payload."""
    if not isinstance(payload, dict):
        return TemplateValidationResult(accepted=False, errors=["template payload must be an object"])
    return validate_template_schema(template_from_payload(payload))


def proposal_from_payload(payload: dict[str, Any], *, current_tick: int = 0) -> StructureTemplateProposal:
    """Build a structure template proposal from plain JSON-like data."""
    template_payload = payload.get("template", {})
    if not isinstance(template_payload, dict):
        template_payload = {}
    template = template_from_payload(template_payload)
    validation = validate_template_schema(template)
    explicit_errors = _clean_text_list(payload.get("validation_errors", []), limit=12)
    validation_errors = explicit_errors or list(validation.errors)
    status = _normalize_id(payload.get("status", "pending"))
    if status not in ALLOWED_TEMPLATE_PROPOSAL_STATUSES:
        status = "pending"
    if validation_errors and status == "validated":
        status = "rejected"
    created_at_tick = _optional_non_negative_int(payload.get("created_at_tick"))
    return StructureTemplateProposal(
        proposal_id=_normalize_id(payload.get("proposal_id", "")),
        template=template,
        rationale=_clean_text(payload.get("rationale", ""), limit=MAX_TEXT_LENGTH),
        source=_clean_text(payload.get("source", "manual"), limit=MAX_LABEL_LENGTH) or "manual",
        created_at_tick=current_tick if created_at_tick is None else created_at_tick,
        status=status,
        validation_errors=validation_errors,
        reviewed_by=_optional_text(payload.get("reviewed_by"), limit=MAX_LABEL_LENGTH),
        reviewed_at_tick=_optional_non_negative_int(payload.get("reviewed_at_tick")),
        decision_notes=_clean_text_list(payload.get("decision_notes", []), limit=8),
    )


def validate_template_proposal(proposal: StructureTemplateProposal) -> TemplateValidationResult:
    """Validate a structure template proposal and its embedded schema."""
    errors: list[str] = []
    if not proposal.proposal_id:
        errors.append("proposal_id is required")
    if not proposal.rationale:
        errors.append("rationale is required")
    if not proposal.source:
        errors.append("source is required")
    if proposal.created_at_tick < 0:
        errors.append("created_at_tick must be non-negative")
    if proposal.status not in ALLOWED_TEMPLATE_PROPOSAL_STATUSES:
        errors.append(f"unsupported proposal status {proposal.status!r}")
    schema_result = validate_template_schema(proposal.template)
    errors.extend(schema_result.errors)
    return TemplateValidationResult(accepted=not errors, errors=errors)


def proposal_to_dict(proposal: StructureTemplateProposal) -> dict[str, object]:
    """Serialize a structure template proposal to plain data."""
    return {
        "proposal_id": proposal.proposal_id,
        "template": template_schema_to_dict(proposal.template),
        "rationale": proposal.rationale,
        "source": proposal.source,
        "created_at_tick": proposal.created_at_tick,
        "status": proposal.status,
        "validation_errors": list(proposal.validation_errors),
        "reviewed_by": proposal.reviewed_by,
        "reviewed_at_tick": proposal.reviewed_at_tick,
        "decision_notes": list(proposal.decision_notes),
    }


def mark_template_proposal_validated(proposal: StructureTemplateProposal) -> TemplateValidationResult:
    """Validate and update proposal status without approving it."""
    result = validate_template_proposal(proposal)
    proposal.validation_errors = list(result.errors)
    proposal.status = "validated" if result.accepted else "rejected"
    return result


def template_schema_to_dict(template: SemiOpenStructureTemplate) -> dict[str, object]:
    """Serialize a template schema to plain data."""
    return {
        "template_id": template.template_id,
        "title": template.title,
        "template_kind": template.template_kind,
        "descriptor_profile_type": template.descriptor_profile_type,
        "fields": [
            {
                "field_id": field_spec.field_id,
                "label": field_spec.label,
                "field_type": field_spec.field_type,
                "required": field_spec.required,
                "max_length": field_spec.max_length,
                "allowed_values": list(field_spec.allowed_values),
                "ref_types": list(field_spec.ref_types),
            }
            for field_spec in template.fields
        ],
        "lifecycle": {
            "initial_status": template.lifecycle.initial_status,
            "allowed_statuses": list(template.lifecycle.allowed_statuses),
            "terminal_statuses": list(template.lifecycle.terminal_statuses),
            "max_active_ticks": template.lifecycle.max_active_ticks,
        },
        "allowed_effects": list(template.allowed_effects),
        "descriptor_constraints": {
            category: list(tags) for category, tags in template.descriptor_constraints.items()
        },
        "style_constraints": list(template.style_constraints),
        "safety_notes": list(template.safety_notes),
        "status": template.status,
        "version": template.version,
    }


def _validate_identity(template: SemiOpenStructureTemplate, errors: list[str]) -> None:
    if not template.template_id:
        errors.append("template_id is required")
    if len(template.template_id) > MAX_ID_LENGTH:
        errors.append("template_id is too long")
    if not template.title:
        errors.append("title is required")
    if template.template_kind not in ALLOWED_TEMPLATE_KINDS:
        errors.append(f"unsupported template_kind {template.template_kind!r}")
    if template.descriptor_profile_type not in DESCRIPTOR_PROFILE_TYPES:
        errors.append(f"unsupported descriptor_profile_type {template.descriptor_profile_type!r}")
    if template.status not in ALLOWED_TEMPLATE_REGISTRY_STATUSES:
        errors.append(f"unsupported template status {template.status!r}")
    if template.version < 1:
        errors.append("version must be positive")


def _validate_fields(template: SemiOpenStructureTemplate, errors: list[str]) -> None:
    if not template.fields:
        errors.append("at least one field is required")
        return
    if len(template.fields) > MAX_TEMPLATE_FIELDS:
        errors.append(f"too many fields; max is {MAX_TEMPLATE_FIELDS}")
    seen: set[str] = set()
    for field_spec in template.fields:
        if not field_spec.field_id:
            errors.append("field.field_id is required")
        if field_spec.field_id in seen:
            errors.append(f"duplicate field_id {field_spec.field_id!r}")
        seen.add(field_spec.field_id)
        if not field_spec.label:
            errors.append(f"field {field_spec.field_id!r} label is required")
        if field_spec.field_type not in ALLOWED_TEMPLATE_FIELD_TYPES:
            errors.append(f"field {field_spec.field_id!r} has unsupported field_type {field_spec.field_type!r}")
        if field_spec.field_type == "enum" and not field_spec.allowed_values:
            errors.append(f"enum field {field_spec.field_id!r} requires allowed_values")
        if field_spec.field_type in {"ref", "ref_list"} and not field_spec.ref_types:
            errors.append(f"ref field {field_spec.field_id!r} requires ref_types")
        if field_spec.field_type == "text":
            if field_spec.max_length is None:
                errors.append(f"text field {field_spec.field_id!r} requires max_length")
            elif field_spec.max_length > MAX_TEXT_LENGTH:
                errors.append(f"text field {field_spec.field_id!r} max_length exceeds {MAX_TEXT_LENGTH}")
        if len(field_spec.allowed_values) > MAX_FIELD_ALLOWED_VALUES:
            errors.append(f"field {field_spec.field_id!r} has too many allowed_values")


def _validate_lifecycle(template: SemiOpenStructureTemplate, errors: list[str]) -> None:
    lifecycle = template.lifecycle
    if not lifecycle.allowed_statuses:
        errors.append("lifecycle.allowed_statuses is required")
    for status in lifecycle.allowed_statuses + lifecycle.terminal_statuses:
        if status not in ALLOWED_TEMPLATE_STATUSES:
            errors.append(f"unsupported lifecycle status {status!r}")
    if lifecycle.initial_status not in lifecycle.allowed_statuses:
        errors.append("lifecycle.initial_status must be in allowed_statuses")
    for status in lifecycle.terminal_statuses:
        if status not in lifecycle.allowed_statuses:
            errors.append(f"terminal status {status!r} must be in allowed_statuses")


def _validate_effects(template: SemiOpenStructureTemplate, errors: list[str]) -> None:
    if not template.allowed_effects:
        errors.append("allowed_effects is required")
    for effect in template.allowed_effects:
        if effect not in ALLOWED_TEMPLATE_EFFECTS:
            errors.append(f"unsupported allowed_effect {effect!r}")


def _validate_descriptor_constraints(template: SemiOpenStructureTemplate, errors: list[str]) -> None:
    for category, tag_ids in template.descriptor_constraints.items():
        if category not in DESCRIPTOR_CATEGORIES:
            errors.append(f"unsupported descriptor category {category!r}")
            continue
        if len(tag_ids) > MAX_DESCRIPTOR_TAGS_PER_TEMPLATE_CATEGORY:
            errors.append(f"too many descriptor tags for {category!r}")
        for tag_id in tag_ids:
            if not is_approved_descriptor_tag(
                tag_id,
                category=category,
                profile_type=template.descriptor_profile_type,
                style_id=_primary_style(template),
            ):
                errors.append(f"descriptor tag {tag_id!r} is not approved for {category}/{template.descriptor_profile_type}")


def _validate_style_constraints(template: SemiOpenStructureTemplate, errors: list[str]) -> None:
    if not template.style_constraints:
        errors.append("style_constraints is required")
    if len(template.style_constraints) > MAX_STYLE_CONSTRAINTS:
        errors.append(f"too many style_constraints; max is {MAX_STYLE_CONSTRAINTS}")
    for style_id in template.style_constraints:
        if style_id not in DEFAULT_WORLD_STYLE_PROFILES:
            errors.append(f"unknown style_constraint {style_id!r}")


def _primary_style(template: SemiOpenStructureTemplate) -> str:
    return template.style_constraints[0] if template.style_constraints else DEFAULT_STYLE_PROFILE_ID


def _clean_descriptor_constraints(raw_constraints: Any) -> dict[str, list[str]]:
    if not isinstance(raw_constraints, dict):
        return {}
    cleaned: dict[str, list[str]] = {}
    for raw_category, raw_tags in raw_constraints.items():
        category = _normalize_id(raw_category)
        if not isinstance(raw_tags, list):
            cleaned[category] = []
            continue
        cleaned[category] = _clean_id_list(raw_tags, limit=MAX_DESCRIPTOR_TAGS_PER_TEMPLATE_CATEGORY)
    return cleaned


def _clean_id_list(raw_values: Any, *, limit: int) -> list[str]:
    if not isinstance(raw_values, list):
        return []
    values: list[str] = []
    for raw_value in raw_values:
        value = _normalize_id(raw_value)
        if value and value not in values:
            values.append(value)
        if len(values) >= limit:
            break
    return values


def _clean_text_list(raw_values: Any, *, limit: int) -> list[str]:
    if not isinstance(raw_values, list):
        return []
    values: list[str] = []
    for raw_value in raw_values:
        value = _clean_text(raw_value, limit=MAX_TEXT_LENGTH)
        if value and value not in values:
            values.append(value)
        if len(values) >= limit:
            break
    return values


def _optional_positive_int(raw_value: Any) -> int | None:
    if raw_value in {None, ""}:
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _optional_non_negative_int(raw_value: Any) -> int | None:
    if raw_value in {None, ""}:
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _optional_text(raw_value: Any, *, limit: int) -> str | None:
    if raw_value in {None, ""}:
        return None
    text = _clean_text(raw_value, limit=limit)
    return text or None


def _normalize_id(raw_value: Any) -> str:
    return str(raw_value).strip().lower().replace("-", "_").replace(" ", "_")[:MAX_ID_LENGTH]


def _clean_text(raw_value: Any, *, limit: int) -> str:
    return " ".join(str(raw_value).strip().split())[:limit].rstrip()
