"""Approval queue for semi-open structure template proposals."""

from src.world.open_structure_template_core import (
    ALLOWED_TEMPLATE_APPROVAL_ACTIONS,
    ALLOWED_TEMPLATE_APPROVAL_STATUSES,
    MAX_TEMPLATE_APPROVAL_QUEUE_ENTRIES,
    TemplateApprovalDecision,
    TemplateApprovalQueue,
    TemplateApprovalQueueEntry,
    decide_template_approval_entry,
    format_template_approval_decision,
    format_template_approval_queue,
    pending_template_approval_entries,
    submit_template_proposal_to_queue,
    template_approval_decision_to_dict,
    template_approval_entry_to_dict,
    template_approval_queue_from_payload,
    template_approval_queue_to_dict,
)

