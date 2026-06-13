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
ALLOWED_TEMPLATE_APPROVAL_STATUSES = {"pending", "approved", "rejected", "frozen", "withdrawn"}
ALLOWED_TEMPLATE_APPROVAL_ACTIONS = {"approve", "reject", "freeze", "withdraw"}
ALLOWED_TEMPLATE_VALIDATION_ISSUE_CATEGORIES = {
    "metadata",
    "schema",
    "fields",
    "lifecycle",
    "effects",
    "descriptor",
    "style",
    "safety",
}
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
class TemplateValidationIssue:
    """Structured validation issue for audit and later approval tooling."""

    category: str
    message: str
    path: str = ""


@dataclass(slots=True)
class TemplateProposalValidationReport:
    """Detailed validation report for one structure template proposal."""

    proposal_id: str
    accepted: bool
    issues: list[TemplateValidationIssue] = field(default_factory=list)
    status_after_validation: str = "pending"


@dataclass(slots=True)
class TemplateProposalAuditRecord:
    """Non-persistent audit draft for a template proposal validation pass."""

    audit_id: str
    proposal_id: str
    tick: int
    source: str
    accepted: bool
    issue_counts: dict[str, int]
    report: TemplateProposalValidationReport


@dataclass(slots=True)
class TemplateApprovalDecision:
    """One auditable reviewer decision for a template proposal queue entry."""

    decision_id: str
    proposal_id: str
    action: str
    reviewer: str
    tick: int
    accepted: bool
    reason: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TemplateApprovalQueueEntry:
    """One proposal entry in the bounded template approval queue."""

    proposal: StructureTemplateProposal
    status: str = "pending"
    submitted_at_tick: int = 0
    validation_report: TemplateProposalValidationReport | None = None
    validation_audit: TemplateProposalAuditRecord | None = None
    decisions: list[TemplateApprovalDecision] = field(default_factory=list)


@dataclass(slots=True)
class TemplateApprovalQueue:
    """In-memory approval queue for validated template proposals."""

    entries: dict[str, TemplateApprovalQueueEntry] = field(default_factory=dict)


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


def validate_template_proposal_detailed(proposal: StructureTemplateProposal) -> TemplateProposalValidationReport:
    """Validate a proposal and return categorized issues for audit consumers."""
    issues: list[TemplateValidationIssue] = []
    _validate_proposal_metadata_issues(proposal, issues)
    _validate_template_schema_issues(proposal.template, issues)
    accepted = not issues
    return TemplateProposalValidationReport(
        proposal_id=proposal.proposal_id,
        accepted=accepted,
        issues=issues,
        status_after_validation="validated" if accepted else "rejected",
    )


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


def template_validation_issue_to_dict(issue: TemplateValidationIssue) -> dict[str, str]:
    """Serialize one structured validation issue."""
    return {
        "category": issue.category,
        "message": issue.message,
        "path": issue.path,
    }


def template_proposal_report_to_dict(report: TemplateProposalValidationReport) -> dict[str, object]:
    """Serialize a detailed proposal validation report."""
    return {
        "proposal_id": report.proposal_id,
        "accepted": report.accepted,
        "issues": [template_validation_issue_to_dict(issue) for issue in report.issues],
        "status_after_validation": report.status_after_validation,
    }


def build_template_proposal_audit_record(
    proposal: StructureTemplateProposal,
    report: TemplateProposalValidationReport | None = None,
    *,
    current_tick: int = 0,
) -> TemplateProposalAuditRecord:
    """Build an audit record draft without mutating world state."""
    validation_report = report or validate_template_proposal_detailed(proposal)
    issue_counts = _count_issues_by_category(validation_report.issues)
    audit_id = f"template_validation_{proposal.proposal_id or 'unknown'}_{max(0, current_tick)}"
    return TemplateProposalAuditRecord(
        audit_id=audit_id,
        proposal_id=proposal.proposal_id,
        tick=max(0, current_tick),
        source=proposal.source,
        accepted=validation_report.accepted,
        issue_counts=issue_counts,
        report=validation_report,
    )


def template_proposal_audit_to_dict(audit: TemplateProposalAuditRecord) -> dict[str, object]:
    """Serialize a template proposal validation audit record."""
    return {
        "audit_id": audit.audit_id,
        "proposal_id": audit.proposal_id,
        "tick": audit.tick,
        "source": audit.source,
        "accepted": audit.accepted,
        "issue_counts": dict(audit.issue_counts),
        "report": template_proposal_report_to_dict(audit.report),
    }


def submit_template_proposal_to_queue(
    queue: TemplateApprovalQueue,
    proposal: StructureTemplateProposal,
    *,
    current_tick: int = 0,
) -> TemplateApprovalQueueEntry:
    """Validate and submit a template proposal into the approval queue."""
    report = mark_template_proposal_validated_detailed(proposal)
    audit = build_template_proposal_audit_record(proposal, report, current_tick=current_tick)
    status = "pending" if report.accepted else "rejected"
    entry = TemplateApprovalQueueEntry(
        proposal=proposal,
        status=status,
        submitted_at_tick=max(0, current_tick),
        validation_report=report,
        validation_audit=audit,
    )
    queue.entries[proposal.proposal_id] = entry
    return entry


def decide_template_approval_entry(
    queue: TemplateApprovalQueue,
    proposal_id: str,
    *,
    action: str,
    reviewer: str,
    current_tick: int = 0,
    reason: str = "",
    notes: list[str] | None = None,
) -> TemplateApprovalDecision:
    """Apply one approval decision to a queued proposal without creating registry entries."""
    normalized_id = _normalize_id(proposal_id)
    normalized_action = _normalize_id(action)
    clean_reviewer = _clean_text(reviewer, limit=MAX_LABEL_LENGTH)
    clean_reason = _clean_text(reason, limit=MAX_TEXT_LENGTH)
    clean_notes = _clean_text_list(notes or [], limit=8)
    accepted = True
    rejection_reason = clean_reason

    if normalized_action not in ALLOWED_TEMPLATE_APPROVAL_ACTIONS:
        accepted = False
        rejection_reason = rejection_reason or f"unsupported approval action {normalized_action!r}"
    entry = queue.entries.get(normalized_id)
    if entry is None:
        accepted = False
        rejection_reason = rejection_reason or f"proposal {normalized_id!r} is not in approval queue"
    elif not clean_reviewer:
        accepted = False
        rejection_reason = rejection_reason or "reviewer is required"
    elif (
        normalized_action in {"approve", "freeze"}
        and entry.validation_report is not None
        and not entry.validation_report.accepted
    ):
        accepted = False
        rejection_reason = rejection_reason or "cannot approve or freeze invalid proposal"
    elif entry.status in {"approved", "rejected", "withdrawn"}:
        accepted = False
        rejection_reason = rejection_reason or f"proposal is already {entry.status}"
    elif normalized_action == "approve" and entry.status != "pending":
        accepted = False
        rejection_reason = rejection_reason or "only pending proposals can be approved"
    elif normalized_action == "freeze" and entry.status not in {"pending", "approved"}:
        accepted = False
        rejection_reason = rejection_reason or "only pending or approved proposals can be frozen"
    elif normalized_action in {"reject", "withdraw"} and entry.status not in {"pending", "frozen"}:
        accepted = False
        rejection_reason = rejection_reason or "only pending or frozen proposals can be rejected or withdrawn"

    decision = TemplateApprovalDecision(
        decision_id=f"template_decision_{normalized_id or 'unknown'}_{len(entry.decisions) + 1 if entry else 1:03d}",
        proposal_id=normalized_id,
        action=normalized_action,
        reviewer=clean_reviewer,
        tick=max(0, current_tick),
        accepted=accepted,
        reason=rejection_reason,
        notes=clean_notes,
    )
    if entry is None:
        return decision
    entry.decisions.append(decision)
    if accepted:
        entry.status = _status_after_approval_action(normalized_action)
        entry.proposal.reviewed_by = clean_reviewer
        entry.proposal.reviewed_at_tick = max(0, current_tick)
        if clean_reason:
            entry.proposal.decision_notes.append(clean_reason)
        entry.proposal.decision_notes.extend(note for note in clean_notes if note not in entry.proposal.decision_notes)
    return decision


def pending_template_approval_entries(queue: TemplateApprovalQueue) -> list[TemplateApprovalQueueEntry]:
    """Return queued proposals that still await approval."""
    return [
        entry
        for entry in sorted(queue.entries.values(), key=lambda item: (item.submitted_at_tick, item.proposal.proposal_id))
        if entry.status == "pending"
    ]


def template_approval_decision_to_dict(decision: TemplateApprovalDecision) -> dict[str, object]:
    """Serialize one template approval decision."""
    return {
        "decision_id": decision.decision_id,
        "proposal_id": decision.proposal_id,
        "action": decision.action,
        "reviewer": decision.reviewer,
        "tick": decision.tick,
        "accepted": decision.accepted,
        "reason": decision.reason,
        "notes": list(decision.notes),
    }


def template_approval_entry_to_dict(entry: TemplateApprovalQueueEntry) -> dict[str, object]:
    """Serialize one approval queue entry."""
    return {
        "proposal": proposal_to_dict(entry.proposal),
        "status": entry.status,
        "submitted_at_tick": entry.submitted_at_tick,
        "validation_report": (
            template_proposal_report_to_dict(entry.validation_report)
            if entry.validation_report is not None
            else None
        ),
        "validation_audit": (
            template_proposal_audit_to_dict(entry.validation_audit)
            if entry.validation_audit is not None
            else None
        ),
        "decisions": [template_approval_decision_to_dict(decision) for decision in entry.decisions],
    }


def template_approval_queue_to_dict(queue: TemplateApprovalQueue) -> dict[str, object]:
    """Serialize an approval queue to plain data."""
    return {
        "entries": {
            proposal_id: template_approval_entry_to_dict(entry)
            for proposal_id, entry in sorted(queue.entries.items())
        }
    }


def template_approval_queue_from_payload(payload: dict[str, Any]) -> TemplateApprovalQueue:
    """Build an approval queue from plain data."""
    queue = TemplateApprovalQueue()
    raw_entries = payload.get("entries", {}) if isinstance(payload, dict) else {}
    if not isinstance(raw_entries, dict):
        return queue
    for raw_proposal_id, raw_entry in raw_entries.items():
        if not isinstance(raw_entry, dict):
            continue
        proposal_payload = raw_entry.get("proposal", {})
        if not isinstance(proposal_payload, dict):
            continue
        proposal = proposal_from_payload(proposal_payload)
        entry = TemplateApprovalQueueEntry(
            proposal=proposal,
            status=_normalize_queue_status(raw_entry.get("status", "pending")),
            submitted_at_tick=_optional_non_negative_int(raw_entry.get("submitted_at_tick")) or 0,
            validation_report=_report_from_payload(raw_entry.get("validation_report")),
            validation_audit=_audit_from_payload(raw_entry.get("validation_audit")),
            decisions=_decisions_from_payload(raw_entry.get("decisions", [])),
        )
        proposal_id = _normalize_id(raw_proposal_id) or proposal.proposal_id
        if proposal_id:
            queue.entries[proposal_id] = entry
    return queue


def format_template_approval_queue(queue: TemplateApprovalQueue, *, limit: int = 10) -> str:
    """Render a compact approval queue block for CLI inspection."""
    entries = sorted(
        queue.entries.values(),
        key=lambda entry: (entry.submitted_at_tick, entry.proposal.proposal_id),
        reverse=True,
    )[: max(1, limit)]
    if not entries:
        return "Template approval queue: empty"
    lines = ["Template approval queue:"]
    for entry in entries:
        issue_count = len(entry.validation_report.issues) if entry.validation_report is not None else 0
        lines.append(
            f"  {entry.proposal.proposal_id} status={entry.status} "
            f"template={entry.proposal.template.template_id} issues={issue_count}"
        )
    return "\n".join(lines)


def format_template_approval_decision(decision: TemplateApprovalDecision) -> str:
    """Render one approval decision for CLI output."""
    status = "accepted" if decision.accepted else "rejected"
    lines = [
        "Template approval decision:",
        f"  decision_id: {decision.decision_id}",
        f"  proposal_id: {decision.proposal_id}",
        f"  action: {decision.action}",
        f"  result: {status}",
    ]
    if decision.reason:
        lines.append(f"  reason: {decision.reason}")
    return "\n".join(lines)


def mark_template_proposal_validated(proposal: StructureTemplateProposal) -> TemplateValidationResult:
    """Validate and update proposal status without approving it."""
    result = validate_template_proposal(proposal)
    proposal.validation_errors = list(result.errors)
    proposal.status = "validated" if result.accepted else "rejected"
    return result


def mark_template_proposal_validated_detailed(
    proposal: StructureTemplateProposal,
) -> TemplateProposalValidationReport:
    """Validate and update proposal status while preserving categorized issues."""
    report = validate_template_proposal_detailed(proposal)
    proposal.validation_errors = [issue.message for issue in report.issues]
    proposal.status = report.status_after_validation
    return report


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
                errors.append(
                    f"descriptor tag {tag_id!r} is not approved for {category}/{template.descriptor_profile_type}"
                )


def _validate_style_constraints(template: SemiOpenStructureTemplate, errors: list[str]) -> None:
    if not template.style_constraints:
        errors.append("style_constraints is required")
    if len(template.style_constraints) > MAX_STYLE_CONSTRAINTS:
        errors.append(f"too many style_constraints; max is {MAX_STYLE_CONSTRAINTS}")
    for style_id in template.style_constraints:
        if style_id not in DEFAULT_WORLD_STYLE_PROFILES:
            errors.append(f"unknown style_constraint {style_id!r}")


def _add_issue(
    issues: list[TemplateValidationIssue],
    category: str,
    message: str,
    *,
    path: str = "",
) -> None:
    safe_category = category if category in ALLOWED_TEMPLATE_VALIDATION_ISSUE_CATEGORIES else "schema"
    issues.append(TemplateValidationIssue(category=safe_category, message=message, path=path))


def _validate_proposal_metadata_issues(
    proposal: StructureTemplateProposal,
    issues: list[TemplateValidationIssue],
) -> None:
    if not proposal.proposal_id:
        _add_issue(issues, "metadata", "proposal_id is required", path="proposal_id")
    if not proposal.rationale:
        _add_issue(issues, "metadata", "rationale is required", path="rationale")
    if not proposal.source:
        _add_issue(issues, "metadata", "source is required", path="source")
    if proposal.created_at_tick < 0:
        _add_issue(issues, "metadata", "created_at_tick must be non-negative", path="created_at_tick")
    if proposal.status not in ALLOWED_TEMPLATE_PROPOSAL_STATUSES:
        _add_issue(
            issues,
            "metadata",
            f"unsupported proposal status {proposal.status!r}",
            path="status",
        )


def _validate_template_schema_issues(
    template: SemiOpenStructureTemplate,
    issues: list[TemplateValidationIssue],
) -> None:
    _validate_identity_issues(template, issues)
    _validate_field_issues(template, issues)
    _validate_lifecycle_issues(template, issues)
    _validate_effect_issues(template, issues)
    _validate_descriptor_constraint_issues(template, issues)
    _validate_style_constraint_issues(template, issues)
    _validate_safety_issues(template, issues)


def _validate_identity_issues(
    template: SemiOpenStructureTemplate,
    issues: list[TemplateValidationIssue],
) -> None:
    if not template.template_id:
        _add_issue(issues, "schema", "template_id is required", path="template.template_id")
    if len(template.template_id) > MAX_ID_LENGTH:
        _add_issue(issues, "schema", "template_id is too long", path="template.template_id")
    if not template.title:
        _add_issue(issues, "schema", "title is required", path="template.title")
    if template.template_kind not in ALLOWED_TEMPLATE_KINDS:
        _add_issue(
            issues,
            "schema",
            f"unsupported template_kind {template.template_kind!r}",
            path="template.template_kind",
        )
    if template.descriptor_profile_type not in DESCRIPTOR_PROFILE_TYPES:
        _add_issue(
            issues,
            "descriptor",
            f"unsupported descriptor_profile_type {template.descriptor_profile_type!r}",
            path="template.descriptor_profile_type",
        )
    if template.status not in ALLOWED_TEMPLATE_REGISTRY_STATUSES:
        _add_issue(
            issues,
            "schema",
            f"unsupported template status {template.status!r}",
            path="template.status",
        )
    if template.version < 1:
        _add_issue(issues, "schema", "version must be positive", path="template.version")


def _validate_field_issues(
    template: SemiOpenStructureTemplate,
    issues: list[TemplateValidationIssue],
) -> None:
    if not template.fields:
        _add_issue(issues, "fields", "at least one field is required", path="template.fields")
        return
    if len(template.fields) > MAX_TEMPLATE_FIELDS:
        _add_issue(issues, "fields", f"too many fields; max is {MAX_TEMPLATE_FIELDS}", path="template.fields")
    seen: set[str] = set()
    for index, field_spec in enumerate(template.fields):
        field_path = f"template.fields[{index}]"
        if not field_spec.field_id:
            _add_issue(issues, "fields", "field.field_id is required", path=f"{field_path}.field_id")
        if field_spec.field_id in seen:
            _add_issue(
                issues,
                "fields",
                f"duplicate field_id {field_spec.field_id!r}",
                path=f"{field_path}.field_id",
            )
        seen.add(field_spec.field_id)
        if not field_spec.label:
            _add_issue(
                issues,
                "fields",
                f"field {field_spec.field_id!r} label is required",
                path=f"{field_path}.label",
            )
        if field_spec.field_type not in ALLOWED_TEMPLATE_FIELD_TYPES:
            _add_issue(
                issues,
                "fields",
                f"field {field_spec.field_id!r} has unsupported field_type {field_spec.field_type!r}",
                path=f"{field_path}.field_type",
            )
        if field_spec.field_type == "enum" and not field_spec.allowed_values:
            _add_issue(
                issues,
                "fields",
                f"enum field {field_spec.field_id!r} requires allowed_values",
                path=f"{field_path}.allowed_values",
            )
        if field_spec.field_type in {"ref", "ref_list"} and not field_spec.ref_types:
            _add_issue(
                issues,
                "fields",
                f"ref field {field_spec.field_id!r} requires ref_types",
                path=f"{field_path}.ref_types",
            )
        if field_spec.field_type == "text":
            if field_spec.max_length is None:
                _add_issue(
                    issues,
                    "fields",
                    f"text field {field_spec.field_id!r} requires max_length",
                    path=f"{field_path}.max_length",
                )
            elif field_spec.max_length > MAX_TEXT_LENGTH:
                _add_issue(
                    issues,
                    "fields",
                    f"text field {field_spec.field_id!r} max_length exceeds {MAX_TEXT_LENGTH}",
                    path=f"{field_path}.max_length",
                )
        if len(field_spec.allowed_values) > MAX_FIELD_ALLOWED_VALUES:
            _add_issue(
                issues,
                "fields",
                f"field {field_spec.field_id!r} has too many allowed_values",
                path=f"{field_path}.allowed_values",
            )


def _validate_lifecycle_issues(
    template: SemiOpenStructureTemplate,
    issues: list[TemplateValidationIssue],
) -> None:
    lifecycle = template.lifecycle
    if not lifecycle.allowed_statuses:
        _add_issue(
            issues,
            "lifecycle",
            "lifecycle.allowed_statuses is required",
            path="template.lifecycle.allowed_statuses",
        )
    for status in lifecycle.allowed_statuses + lifecycle.terminal_statuses:
        if status not in ALLOWED_TEMPLATE_STATUSES:
            _add_issue(
                issues,
                "lifecycle",
                f"unsupported lifecycle status {status!r}",
                path="template.lifecycle",
            )
    if lifecycle.initial_status not in lifecycle.allowed_statuses:
        _add_issue(
            issues,
            "lifecycle",
            "lifecycle.initial_status must be in allowed_statuses",
            path="template.lifecycle.initial_status",
        )
    for status in lifecycle.terminal_statuses:
        if status not in lifecycle.allowed_statuses:
            _add_issue(
                issues,
                "lifecycle",
                f"terminal status {status!r} must be in allowed_statuses",
                path="template.lifecycle.terminal_statuses",
            )


def _validate_effect_issues(
    template: SemiOpenStructureTemplate,
    issues: list[TemplateValidationIssue],
) -> None:
    if not template.allowed_effects:
        _add_issue(issues, "effects", "allowed_effects is required", path="template.allowed_effects")
    for index, effect in enumerate(template.allowed_effects):
        if effect not in ALLOWED_TEMPLATE_EFFECTS:
            category = "safety" if effect == "direct_worldstate_write" else "effects"
            _add_issue(
                issues,
                category,
                f"unsupported allowed_effect {effect!r}",
                path=f"template.allowed_effects[{index}]",
            )


def _validate_descriptor_constraint_issues(
    template: SemiOpenStructureTemplate,
    issues: list[TemplateValidationIssue],
) -> None:
    for category, tag_ids in template.descriptor_constraints.items():
        category_path = f"template.descriptor_constraints.{category}"
        if category not in DESCRIPTOR_CATEGORIES:
            _add_issue(
                issues,
                "descriptor",
                f"unsupported descriptor category {category!r}",
                path=category_path,
            )
            continue
        if len(tag_ids) > MAX_DESCRIPTOR_TAGS_PER_TEMPLATE_CATEGORY:
            _add_issue(
                issues,
                "descriptor",
                f"too many descriptor tags for {category!r}",
                path=category_path,
            )
        for index, tag_id in enumerate(tag_ids):
            if not is_approved_descriptor_tag(
                tag_id,
                category=category,
                profile_type=template.descriptor_profile_type,
                style_id=_primary_style(template),
            ):
                _add_issue(
                    issues,
                    "descriptor",
                    f"descriptor tag {tag_id!r} is not approved for {category}/{template.descriptor_profile_type}",
                    path=f"{category_path}[{index}]",
                )


def _validate_style_constraint_issues(
    template: SemiOpenStructureTemplate,
    issues: list[TemplateValidationIssue],
) -> None:
    if not template.style_constraints:
        _add_issue(issues, "style", "style_constraints is required", path="template.style_constraints")
    if len(template.style_constraints) > MAX_STYLE_CONSTRAINTS:
        _add_issue(
            issues,
            "style",
            f"too many style_constraints; max is {MAX_STYLE_CONSTRAINTS}",
            path="template.style_constraints",
        )
    for index, style_id in enumerate(template.style_constraints):
        if style_id not in DEFAULT_WORLD_STYLE_PROFILES:
            _add_issue(
                issues,
                "style",
                f"unknown style_constraint {style_id!r}",
                path=f"template.style_constraints[{index}]",
            )


def _validate_safety_issues(
    template: SemiOpenStructureTemplate,
    issues: list[TemplateValidationIssue],
) -> None:
    unsafe_notes = {"direct_worldstate_write", "python_dataclass", "worldstate_field"}
    for index, note in enumerate(template.safety_notes):
        normalized = _normalize_id(note)
        if any(marker in normalized for marker in unsafe_notes):
            _add_issue(
                issues,
                "safety",
                f"safety note contains blocked capability marker {note!r}",
                path=f"template.safety_notes[{index}]",
            )


def _count_issues_by_category(issues: list[TemplateValidationIssue]) -> dict[str, int]:
    counts = {category: 0 for category in sorted(ALLOWED_TEMPLATE_VALIDATION_ISSUE_CATEGORIES)}
    for issue in issues:
        category = issue.category if issue.category in counts else "schema"
        counts[category] += 1
    return {category: count for category, count in counts.items() if count}


def _status_after_approval_action(action: str) -> str:
    if action == "approve":
        return "approved"
    if action == "reject":
        return "rejected"
    if action == "freeze":
        return "frozen"
    if action == "withdraw":
        return "withdrawn"
    return "pending"


def _normalize_queue_status(raw_value: Any) -> str:
    status = _normalize_id(raw_value)
    return status if status in ALLOWED_TEMPLATE_APPROVAL_STATUSES else "pending"


def _issues_from_payload(raw_issues: Any) -> list[TemplateValidationIssue]:
    if not isinstance(raw_issues, list):
        return []
    issues: list[TemplateValidationIssue] = []
    for raw_issue in raw_issues:
        if not isinstance(raw_issue, dict):
            continue
        _add_issue(
            issues,
            _normalize_id(raw_issue.get("category", "schema")),
            _clean_text(raw_issue.get("message", ""), limit=MAX_TEXT_LENGTH),
            path=_clean_text(raw_issue.get("path", ""), limit=MAX_TEXT_LENGTH),
        )
    return issues


def _report_from_payload(raw_report: Any) -> TemplateProposalValidationReport | None:
    if not isinstance(raw_report, dict):
        return None
    issues = _issues_from_payload(raw_report.get("issues", []))
    status_after_validation = _normalize_id(raw_report.get("status_after_validation", "pending"))
    if status_after_validation not in ALLOWED_TEMPLATE_PROPOSAL_STATUSES:
        status_after_validation = "pending"
    return TemplateProposalValidationReport(
        proposal_id=_normalize_id(raw_report.get("proposal_id", "")),
        accepted=bool(raw_report.get("accepted", False)),
        issues=issues,
        status_after_validation=status_after_validation,
    )


def _audit_from_payload(raw_audit: Any) -> TemplateProposalAuditRecord | None:
    if not isinstance(raw_audit, dict):
        return None
    report = _report_from_payload(raw_audit.get("report"))
    if report is None:
        return None
    issue_counts = {}
    raw_counts = raw_audit.get("issue_counts", {})
    if isinstance(raw_counts, dict):
        for raw_category, raw_count in raw_counts.items():
            category = _normalize_id(raw_category)
            if category in ALLOWED_TEMPLATE_VALIDATION_ISSUE_CATEGORIES:
                issue_counts[category] = _optional_non_negative_int(raw_count) or 0
    return TemplateProposalAuditRecord(
        audit_id=_normalize_id(raw_audit.get("audit_id", "")),
        proposal_id=_normalize_id(raw_audit.get("proposal_id", "")),
        tick=_optional_non_negative_int(raw_audit.get("tick")) or 0,
        source=_clean_text(raw_audit.get("source", ""), limit=MAX_LABEL_LENGTH),
        accepted=bool(raw_audit.get("accepted", False)),
        issue_counts=issue_counts,
        report=report,
    )


def _decisions_from_payload(raw_decisions: Any) -> list[TemplateApprovalDecision]:
    if not isinstance(raw_decisions, list):
        return []
    decisions: list[TemplateApprovalDecision] = []
    for raw_decision in raw_decisions:
        if not isinstance(raw_decision, dict):
            continue
        action = _normalize_id(raw_decision.get("action", ""))
        if action not in ALLOWED_TEMPLATE_APPROVAL_ACTIONS:
            action = "reject"
        decisions.append(
            TemplateApprovalDecision(
                decision_id=_normalize_id(raw_decision.get("decision_id", "")),
                proposal_id=_normalize_id(raw_decision.get("proposal_id", "")),
                action=action,
                reviewer=_clean_text(raw_decision.get("reviewer", ""), limit=MAX_LABEL_LENGTH),
                tick=_optional_non_negative_int(raw_decision.get("tick")) or 0,
                accepted=bool(raw_decision.get("accepted", False)),
                reason=_clean_text(raw_decision.get("reason", ""), limit=MAX_TEXT_LENGTH),
                notes=_clean_text_list(raw_decision.get("notes", []), limit=8),
            )
        )
    return decisions


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
