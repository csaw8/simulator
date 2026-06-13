"""Approved template registry for semi-open structures."""

from src.world.open_structure_template_core import (
    ALLOWED_APPROVED_TEMPLATE_STATUSES,
    MAX_APPROVED_TEMPLATE_REGISTRY_ENTRIES,
    ApprovedStructureTemplate,
    ApprovedStructureTemplateRegistry,
    approved_template_registry_from_payload,
    approved_template_registry_to_dict,
    approved_template_to_dict,
    format_approved_template_registry,
    get_active_approved_template,
    list_active_approved_templates,
    register_approved_template_from_queue,
    set_approved_template_registry_status,
)

