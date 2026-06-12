"""Delayed fallout events for high-value historical chains."""

from __future__ import annotations

from random import Random

from src.events.models import Event
from src.world.network_updates import append_project_note, append_supply_note
from src.world.state import WorldState

_UPSHIFT = {"low": "medium", "medium": "high", "high": "high"}
_DOWNSHIFT = {"high": "medium", "medium": "low", "low": "low"}

_PROJECT_TRIGGER_TYPES = {
    "megastructure_budget_crisis",
    "megastructure_stall",
    "faction_site_accident",
}
_ARCHIVE_TRIGGER_TYPES = {
    "archive_legitimacy_shock",
    "faction_archive_breach",
}
_PROTOCOL_TRIGGER_TYPES = {
    "protocol_infiltration",
    "faction_protocol_breach",
}
_LIFEFORM_TRIGGER_TYPES = {
    "lifeform_migration_front",
    "lifeform_habitat_expansion",
    "faction_lifeform_provocation",
}


def advance_event_fallout(state: WorldState, rng: Random) -> list[Event]:
    """Generate delayed follow-up events from recent high-value source events."""
    events: list[Event] = []
    budget = 3
    recent_events = [
        event
        for event in state.event_stream.recent(120)
        if state.current_tick - 2 <= event.tick < state.current_tick
    ]
    for event in reversed(recent_events):
        if budget <= 0:
            break
        fallout_event = _build_fallout_for_source(state, event, rng)
        if fallout_event is None:
            continue
        events.append(fallout_event)
        budget -= 1
    return list(reversed(events))


def _build_fallout_for_source(
    state: WorldState,
    source_event: Event,
    rng: Random,
) -> Event | None:
    if source_event.event_type in _PROJECT_TRIGGER_TYPES:
        if _has_fallout_marker(source_event, "project"):
            return None
        event = _build_project_fallout(state, source_event, rng)
        if event is not None:
            _mark_fallout(source_event, "project")
        return event
    if source_event.event_type in _ARCHIVE_TRIGGER_TYPES:
        if _has_fallout_marker(source_event, "archive"):
            return None
        event = _build_archive_fallout(state, source_event, rng)
        if event is not None:
            _mark_fallout(source_event, "archive")
        return event
    if source_event.event_type in _PROTOCOL_TRIGGER_TYPES:
        if _has_fallout_marker(source_event, "protocol"):
            return None
        event = _build_protocol_fallout(state, source_event, rng)
        if event is not None:
            _mark_fallout(source_event, "protocol")
        return event
    if source_event.event_type in _LIFEFORM_TRIGGER_TYPES:
        if _has_fallout_marker(source_event, "lifeform"):
            return None
        event = _build_lifeform_fallout(state, source_event, rng)
        if event is not None:
            _mark_fallout(source_event, "lifeform")
        return event
    return None


def _build_project_fallout(state: WorldState, source_event: Event, rng: Random) -> Event | None:
    if not source_event.region_refs:
        return None
    region = state.regions.get(source_event.region_refs[0])
    if region is None:
        return None
    civilization = state.civilizations.get(region.civ_id) if region.civ_id else None

    if region.security == "low" or "site_accident" in source_event.event_type:
        before_security = region.security
        before_tension = region.political_tension
        region.security = _UPSHIFT[region.security]
        region.political_tension = _UPSHIFT[region.political_tension]
        append_project_note(
            state,
            relic_id=source_event.relic_refs[0] if source_event.relic_refs else None,
            faction_id=source_event.faction_refs[0] if source_event.faction_refs else None,
            region_id=region.region_id,
            civ_id=region.civ_id,
            note="security_cordon_raised",
            status="contested_buildout",
            pressure_shift="up",
        )
        return _new_fallout_event(
            state,
            source_event,
            event_type="project_security_cordon",
            summary=(
                f"Authorities and contractors threw a hard security cordon around {region.name}, "
                f"raising overt control while making the local project front more politically brittle."
            ),
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            faction_refs=source_event.faction_refs[:2],
            relic_refs=source_event.relic_refs[:1],
            result_tags=[
                f"source_event={source_event.event_id}",
                f"security_{before_security}_to_{region.security}",
                f"tension_{before_tension}_to_{region.political_tension}",
            ],
            severity="medium",
            consequence_score="medium",
        )

    before_tension = region.political_tension
    region.political_tension = _UPSHIFT[region.political_tension]
    if civilization is not None:
        before_legitimacy = civilization.legitimacy
        civilization.legitimacy = _DOWNSHIFT[civilization.legitimacy]
        result_tags = [
            f"source_event={source_event.event_id}",
            f"tension_{before_tension}_to_{region.political_tension}",
            f"legitimacy_{before_legitimacy}_to_{civilization.legitimacy}",
        ]
    else:
        result_tags = [
            f"source_event={source_event.event_id}",
            f"tension_{before_tension}_to_{region.political_tension}",
        ]
    append_project_note(
        state,
        relic_id=source_event.relic_refs[0] if source_event.relic_refs else None,
        faction_id=source_event.faction_refs[0] if source_event.faction_refs else None,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note="contract_scramble",
        status="contested_buildout",
        pressure_shift="up",
    )
    return _new_fallout_event(
        state,
        source_event,
        event_type="project_contract_scramble",
        summary=(
            f"The stalled project line in {region.name} triggered a scramble over budgets, blame, and execution authority, "
            f"pulling more actors into the engineering front."
        ),
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        faction_refs=source_event.faction_refs[:3] or region.active_factions[:3],
        relic_refs=source_event.relic_refs[:1],
        result_tags=result_tags,
        severity="high",
        consequence_score="high",
    )


def _build_archive_fallout(state: WorldState, source_event: Event, rng: Random) -> Event | None:
    if not source_event.region_refs:
        return None
    region = state.regions.get(source_event.region_refs[0])
    if region is None:
        return None
    civilization = state.civilizations.get(region.civ_id) if region.civ_id else None
    before_tension = region.political_tension
    region.political_tension = _UPSHIFT[region.political_tension]
    result_tags = [
        f"source_event={source_event.event_id}",
        f"tension_{before_tension}_to_{region.political_tension}",
    ]
    if civilization is not None and rng.random() < 0.7:
        before_legitimacy = civilization.legitimacy
        civilization.legitimacy = _DOWNSHIFT[civilization.legitimacy]
        result_tags.append(f"legitimacy_{before_legitimacy}_to_{civilization.legitimacy}")
    return _new_fallout_event(
        state,
        source_event,
        event_type="archive_inquiry_wave",
        summary=(
            f"After sealed disclosures surfaced around {region.name}, inquiry waves and selective leaks kept spreading, "
            f"turning a single archival shock into a longer legitimacy struggle."
        ),
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        faction_refs=source_event.faction_refs[:2],
        relic_refs=source_event.relic_refs[:1],
        result_tags=result_tags,
        severity="medium",
        consequence_score="high",
    )


def _build_protocol_fallout(state: WorldState, source_event: Event, rng: Random) -> Event | None:
    if not source_event.region_refs:
        return None
    region = state.regions.get(source_event.region_refs[0])
    if region is None:
        return None
    civilization = state.civilizations.get(region.civ_id) if region.civ_id else None
    before_security = region.security
    before_tension = region.political_tension
    region.security = _UPSHIFT[region.security]
    region.political_tension = _UPSHIFT[region.political_tension]
    append_supply_note(
        state,
        faction_id=source_event.faction_refs[0] if source_event.faction_refs else None,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note="emergency_lockdown_slowed_routing",
        status="contested" if region.security != "high" else "fragile",
        pressure_shift="up",
    )
    result_tags = [
        f"source_event={source_event.event_id}",
        f"security_{before_security}_to_{region.security}",
        f"tension_{before_tension}_to_{region.political_tension}",
    ]
    if civilization is not None and rng.random() < 0.7:
        before_legitimacy = civilization.legitimacy
        civilization.legitimacy = _DOWNSHIFT[civilization.legitimacy]
        result_tags.append(f"legitimacy_{before_legitimacy}_to_{civilization.legitimacy}")
    return _new_fallout_event(
        state,
        source_event,
        event_type="protocol_emergency_lockdown",
        summary=(
            f"The protocol disturbance in {region.name} forced an emergency lockdown cycle, "
            f"tightening overt controls while deepening public unease about who still governs the system."
        ),
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        faction_refs=source_event.faction_refs[:2],
        relic_refs=source_event.relic_refs[:1],
        result_tags=result_tags,
        severity="medium",
        consequence_score="high",
    )


def _build_lifeform_fallout(state: WorldState, source_event: Event, rng: Random) -> Event | None:
    if not source_event.region_refs:
        return None
    target_region_id = source_event.region_refs[-1]
    region = state.regions.get(target_region_id)
    if region is None:
        return None
    before_scarcity = region.scarcity
    before_tension = region.political_tension
    before_security = region.security
    region.scarcity = _UPSHIFT[region.scarcity]
    region.political_tension = _UPSHIFT[region.political_tension]
    region.security = _DOWNSHIFT[region.security]
    append_supply_note(
        state,
        faction_id=source_event.faction_refs[0] if source_event.faction_refs else None,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note="quarantine_panic_disrupted_corridor",
        status="contested",
        pressure_shift="up",
    )
    return _new_fallout_event(
        state,
        source_event,
        event_type="lifeform_quarantine_panic",
        summary=(
            f"Containment lines around {region.name} thickened after the anomalous spread, "
            f"but quarantine fear and disrupted movement turned the biosecurity front into a wider civic strain."
        ),
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        faction_refs=source_event.faction_refs[:2],
        relic_refs=source_event.relic_refs[:1],
        result_tags=[
            f"source_event={source_event.event_id}",
            f"security_{before_security}_to_{region.security}",
            f"tension_{before_tension}_to_{region.political_tension}",
            f"scarcity_{before_scarcity}_to_{region.scarcity}",
        ],
        severity="high",
        consequence_score="high",
    )


def _new_fallout_event(
    state: WorldState,
    source_event: Event,
    *,
    event_type: str,
    summary: str,
    region_refs: list[str],
    civ_refs: list[str],
    faction_refs: list[str],
    relic_refs: list[str],
    result_tags: list[str],
    severity: str,
    consequence_score: str,
) -> Event:
    return Event(
        event_id=state.event_stream.new_event_id(),
        tick=state.current_tick,
        time_granularity=state.current_granularity,
        event_type=event_type,
        event_scope="fallout",
        title=f"Fallout from {source_event.event_type}",
        summary=summary,
        region_refs=region_refs,
        civ_refs=civ_refs,
        faction_refs=faction_refs,
        relic_refs=relic_refs,
        cause_tags=["event_fallout", f"from:{source_event.event_type}", f"source:{source_event.event_id}"],
        result_tags=result_tags,
        severity=severity,
        novelty="medium",
        consequence_score=consequence_score,
        narrative_priority="high",
    )


def _has_fallout_marker(event: Event, family: str) -> bool:
    return f"fallout_emitted:{family}" in event.result_tags


def _mark_fallout(event: Event, family: str) -> None:
    marker = f"fallout_emitted:{family}"
    if marker not in event.result_tags:
        event.result_tags.append(marker)
