"""Exceptional presence helpers for current relic-backed objects."""

from __future__ import annotations

from src.world.relic import Relic


_TYPE_LABELS = {
    "relic_device": "anomalous_object",
    "megastructure": "megastructure",
    "sealed_archive": "sealed_archive",
    "founding_protocol": "autonomous_system",
    "anomalous_lifeform": "anomalous_lifeform",
}

_DISPLAY_NAMES = {
    "relic_device": "Anomalous Object",
    "megastructure": "Megastructure",
    "sealed_archive": "Sealed Archive",
    "founding_protocol": "Founding Protocol",
    "anomalous_lifeform": "Anomalous Lifeform",
}

_MEGASTRUCTURE_ORIGIN_LABELS = {
    "legacy": "legacy remnant",
    "contemporary": "contemporary project",
    "hybrid": "hybrid rebuild",
}


def presence_class(relic: Relic) -> str:
    """Return the broader exceptional-presence class for a relic-backed object."""
    return _TYPE_LABELS.get(relic.relic_type, "relic")


def presence_display_name(relic: Relic) -> str:
    """Return a user-facing type label for a relic-backed object."""
    return _DISPLAY_NAMES.get(relic.relic_type, "Relic")


def exceptional_presence_id(relic: Relic) -> str:
    """Return the stable id of a non-human exceptional presence."""
    return relic.relic_id


def exceptional_presence_name(relic: Relic) -> str:
    """Return the stable display name of a non-human exceptional presence."""
    return relic.name


def exceptional_presence_kind(relic: Relic) -> str:
    """Return a neutral top-level kind for non-human exceptional presences."""
    return presence_event_family(relic)


def exceptional_presence_label(relic: Relic) -> str:
    """Return a neutral observer-facing label for non-human exceptional presences."""
    family = exceptional_presence_kind(relic)
    labels = {
        "megastructure": "exceptional_megastructure",
        "autonomous_system": "exceptional_system",
        "sealed_archive": "sealed_information_source",
        "anomalous_lifeform": "anomalous_lifeform",
        "relic": "anomalous_object",
    }
    return labels.get(family, "anomalous_presence")


def presence_event_family(relic: Relic) -> str:
    """Return the behavior family used for event branching."""
    kind = presence_class(relic)
    if kind == "megastructure":
        return "megastructure"
    if kind == "autonomous_system":
        return "autonomous_system"
    if kind == "sealed_archive":
        return "sealed_archive"
    if kind == "anomalous_lifeform":
        return "anomalous_lifeform"
    return "relic"


def suggested_story_tags(relic_type: str) -> list[str]:
    """Return default story tags by current relic type."""
    if relic_type == "megastructure":
        return ["construction_phase", "network_dependency", "scale_shock"]
    if relic_type == "founding_protocol":
        return ["governance_root", "access_doctrine", "silent_takeover"]
    if relic_type == "sealed_archive":
        return ["sealed_history", "legitimacy_shock", "forbidden_access"]
    if relic_type == "anomalous_lifeform":
        return ["adaptive_predator", "habitat_shift", "biosecurity_breach"]
    return ["legacy_control", "forbidden_access", "energy_dependency"]


def megastructure_origin_mode(relic: Relic) -> str:
    """Return the giant-structure origin track for branching logic."""
    if relic.relic_type != "megastructure":
        return "none"
    return relic.origin_mode or "legacy"


def megastructure_origin_label(relic: Relic) -> str:
    """Return a readable label for current megastructure origin."""
    return _MEGASTRUCTURE_ORIGIN_LABELS.get(
        megastructure_origin_mode(relic),
        megastructure_origin_mode(relic),
    )


def is_contemporary_megastructure(relic: Relic) -> bool:
    """Return whether the megastructure is part of the current era's buildout."""
    return megastructure_origin_mode(relic) in {"contemporary", "hybrid"}


def normalize_relic_state(relic: Relic) -> None:
    """Backfill newer presence fields for older snapshots."""
    if relic.relic_type == "anomalous_lifeform":
        if not relic.origin_mode:
            if "distributed_intelligence" in relic.story_tags:
                relic.origin_mode = "engineered_swarm"
            elif "containment_failure" in relic.story_tags:
                relic.origin_mode = "lab_origin"
            else:
                relic.origin_mode = "wild_mutation"
        if relic.construction_state in {"", "unknown"}:
            if relic.activation_state == "sealed":
                relic.construction_state = "contained"
            elif relic.activation_state == "contested":
                relic.construction_state = "roaming"
            else:
                relic.construction_state = "nesting"
        return

    if relic.relic_type != "megastructure":
        return

    if not relic.origin_mode:
        if "live_construction" in relic.story_tags:
            relic.origin_mode = "contemporary"
        elif "retrofit_ambition" in relic.story_tags:
            relic.origin_mode = "hybrid"
        else:
            relic.origin_mode = "legacy"

    if relic.construction_state in {"", "unknown"}:
        if relic.origin_mode == "contemporary":
            relic.construction_state = "rising" if relic.activation_state == "contested" else "foundation"
        elif relic.origin_mode == "hybrid":
            relic.construction_state = "integration" if relic.activation_state == "sealed" else "retrofit"
        else:
            relic.construction_state = "operational" if relic.activation_state == "sealed" else "degraded"

    if relic.origin_mode in {"contemporary", "hybrid"} and relic.sponsor_ref is None:
        relic.sponsor_ref = relic.holder_ref

    if relic.contractor_ref is None and relic.origin_mode in {"contemporary", "hybrid"}:
        relic.contractor_ref = relic.holder_ref
    if relic.financier_ref is None and relic.origin_mode == "contemporary":
        relic.financier_ref = relic.sponsor_ref
    if relic.opposition_ref is None and relic.origin_mode != "legacy" and "fraying_order" in relic.story_tags:
        relic.opposition_ref = relic.holder_ref
