"""Event taxonomy helpers for stable filtering and display."""

from __future__ import annotations

from src.events.models import Event


_THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "project": (
        "project",
        "budget",
        "financing",
        "contract",
        "site_accident",
        "groundbreaking",
        "grid_link",
        "megastructure",
    ),
    "supply": (
        "supply",
        "resource",
        "corridor",
        "routing",
        "quarantine",
        "scarcity",
    ),
    "anomaly": (
        "archive",
        "protocol",
        "lifeform",
        "containment",
        "migration",
        "relic",
        "presence",
    ),
    "politics": (
        "political",
        "power_struggle",
        "alliance",
        "infiltration",
        "legitimacy",
    ),
    "security": (
        "security",
        "lockdown",
        "containment",
        "suppression",
        "control",
    ),
    "organization": (
        "faction",
        "alliance",
        "infiltration",
        "power_struggle",
        "contract",
        "financing",
    ),
    "macro": (
        "resource_shift",
        "security_shift",
        "political_shift",
        "legitimacy_shift",
        "civil_scarcity_shift",
        "expansion_shift",
    ),
    "dynamic": (
        "dynamic_structure",
        "local_group",
        "incident_site",
        "rumor_network",
        "proxy_cell",
        "anomaly_trace",
    ),
}

_ALIASES: dict[str, str] = {
    "engineering": "project",
    "logistics": "supply",
    "resource": "supply",
    "presence": "anomaly",
    "relic": "anomaly",
    "power": "politics",
    "control": "security",
    "actor": "character",
    "faction": "organization",
    "structure": "dynamic",
    "dynamic_structure": "dynamic",
}

_MIDLAYER_PAYLOAD_BUCKETS: dict[str, str] = {
    "project_bid": "project_shifts",
    "budget_freeze": "project_shifts",
    "financing_realignment": "project_shifts",
    "contract_scramble": "project_shifts",
    "groundbreaking_started": "project_shifts",
    "phase_advance": "project_shifts",
    "grid_linked": "project_shifts",
    "reactivation_window": "project_shifts",
    "budget_crisis": "project_shifts",
    "construction_stall": "project_shifts",
    "site_accident_exploited": "project_shifts",
    "alliance_backing": "project_shifts",
    "control_contest": "project_shifts",
    "control_secured": "project_shifts",
    "resource_reallocation": "supply_shocks",
    "quarantine_panic_disrupted_corridor": "supply_shocks",
    "emergency_lockdown_slowed_routing": "supply_shocks",
    "alliance_support": "supply_shocks",
    "power_struggle_pressure": "supply_shocks",
    "infiltration_pressure": "supply_shocks",
    "character_supply_stabilized": "supply_shocks",
    "character_supply_leverage": "supply_shocks",
    "security_cordon_raised": "security_clamps",
}


def normalize_focus_theme(raw: str | None) -> str | None:
    if raw is None:
        return None
    focus = raw.strip().lower()
    if not focus:
        return None
    return _ALIASES.get(focus, focus)


def event_theme_tags(event: Event) -> list[str]:
    """Return stable theme tags for an event."""
    event_type = event.event_type.lower()
    tags = {normalize_focus_theme(event.event_scope) or event.event_scope.lower()}

    if event.actor_refs:
        tags.add("character")
    if event.faction_refs:
        tags.add("organization")
    if event.civ_refs:
        tags.add("civilization")
    if event.region_refs:
        tags.add("region")
    if event.relic_refs:
        tags.add("anomaly")

    source_tokens = [event_type, *[tag.lower() for tag in event.cause_tags]]
    joined = " ".join(source_tokens)
    for theme, keywords in _THEME_KEYWORDS.items():
        if any(token in joined for token in keywords):
            tags.add(theme)

    # Macro shifts and direct state-change events may only expose their theme in result tags.
    if "macro" in tags or event_type.endswith("_shift"):
        result_tokens = " ".join(tag.lower() for tag in event.result_tags)
        for theme, keywords in _THEME_KEYWORDS.items():
            if any(token in result_tokens for token in keywords):
                tags.add(theme)
    return sorted(tags)


def event_family(event: Event) -> str:
    """Return one dominant family label for display and heuristics."""
    tags = event_theme_tags(event)
    for preferred in ("macro", "project", "supply", "anomaly", "politics", "security", "organization", "dynamic"):
        if preferred in tags:
            return preferred
    if "civilization" in tags:
        return "civilization"
    if "region" in tags:
        return "region"
    if "character" in tags:
        return "character"
    return event.event_scope.lower()


def event_matches_focus(event: Event, focus: str | None) -> bool:
    normalized = normalize_focus_theme(focus)
    if not normalized:
        return True
    if normalized == "character":
        return bool(event.actor_refs)
    if normalized == "organization":
        return bool(event.faction_refs) or "organization" in event_theme_tags(event)
    return normalized in event_theme_tags(event) or normalized in event.event_type.lower()


def payload_midlayer_bucket(payload: str) -> str:
    action = payload.split("->", 1)[0].strip().lower()
    return _MIDLAYER_PAYLOAD_BUCKETS.get(action, "other_changes")


def event_midlayer_bucket(event: Event) -> str:
    event_type = event.event_type.lower()
    themes = set(event_theme_tags(event))
    if any(token in event_type for token in {"security", "lockdown", "cordon"}):
        return "security_clamps"
    if any(token in event_type for token in {"project", "budget", "financing", "contract", "megastructure"}):
        return "project_shifts"
    if any(token in event_type for token in {"resource_reallocation", "supply", "route", "corridor"}):
        return "supply_shocks"
    if any(
        token in event_type
        for token in {
            "archive",
            "protocol",
            "lifeform",
            "migration",
            "relic",
            "containment",
            "suppression",
            "breach",
            "takeover",
            "inquiry",
            "habitat",
        }
    ):
        return "anomaly_surges"
    if "project" in themes:
        return "project_shifts"
    if "supply" in themes:
        return "supply_shocks"
    if "anomaly" in themes:
        return "anomaly_surges"
    if "security" in themes:
        return "security_clamps"
    return "other_changes"
