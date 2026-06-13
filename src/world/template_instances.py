"""Template instance models, validators, and store helpers."""

from src.world.open_structure_template_core import (
    ALLOWED_TEMPLATE_INSTANCE_STATUSES,
    MAX_INSTANCE_DESCRIPTOR_VALUES_PER_CATEGORY,
    MAX_INSTANCE_LINKED_REFS,
    MAX_TEMPLATE_INSTANCES,
    TemplateInstance,
    TemplateInstanceStore,
    create_template_instance,
    format_template_instances,
    template_instance_from_payload,
    template_instance_store_from_payload,
    template_instance_store_to_dict,
    template_instance_to_dict,
    validate_template_instance,
)

