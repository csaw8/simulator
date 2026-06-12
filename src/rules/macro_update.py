"""Macro state update rules."""

from __future__ import annotations

from random import Random

from src.events.models import Event
from src.world.state import WorldState

_LEVELS = ["low", "medium", "high"]
_TRENDS = ["declining", "steady", "rising"]


def advance_macro_state(state: WorldState, rng: Random) -> list[Event]:
    """Advance macro-level world pressures by one step and emit events."""
    events: list[Event] = []

    for region in state.regions.values():
        scarcity_before = region.scarcity
        tension_before = region.political_tension
        security_before = region.security

        _shift_region_pressure(region, rng)

        if scarcity_before != region.scarcity:
            events.append(
                Event(
                    event_id=state.event_stream.new_event_id(),
                    tick=state.current_tick,
                    time_granularity=state.current_granularity,
                    event_type="resource_shift",
                    event_scope="region",
                    title=f"{region.name} scarcity changed",
                    summary=(
                        f"{region.name} scarcity moved from {scarcity_before} "
                        f"to {region.scarcity}."
                    ),
                    region_refs=[region.region_id],
                    civ_refs=[region.civ_id] if region.civ_id else [],
                    cause_tags=["macro_shift", "resource_pressure"],
                    result_tags=[f"scarcity_{region.scarcity}"],
                    severity=_severity_from_levels(scarcity_before, region.scarcity),
                )
            )

        if tension_before != region.political_tension:
            events.append(
                Event(
                    event_id=state.event_stream.new_event_id(),
                    tick=state.current_tick,
                    time_granularity=state.current_granularity,
                    event_type="political_shift",
                    event_scope="region",
                    title=f"{region.name} political tension changed",
                    summary=(
                        f"{region.name} political tension moved from {tension_before} "
                        f"to {region.political_tension}."
                    ),
                    region_refs=[region.region_id],
                    civ_refs=[region.civ_id] if region.civ_id else [],
                    cause_tags=["macro_shift", "political_pressure"],
                    result_tags=[f"tension_{region.political_tension}"],
                    severity=_severity_from_levels(
                        tension_before, region.political_tension
                    ),
                )
            )

        if security_before != region.security:
            events.append(
                Event(
                    event_id=state.event_stream.new_event_id(),
                    tick=state.current_tick,
                    time_granularity=state.current_granularity,
                    event_type="security_shift",
                    event_scope="region",
                    title=f"{region.name} security changed",
                    summary=(
                        f"{region.name} security moved from {security_before} "
                        f"to {region.security}."
                    ),
                    region_refs=[region.region_id],
                    civ_refs=[region.civ_id] if region.civ_id else [],
                    cause_tags=["macro_shift", "security_pressure"],
                    result_tags=[f"security_{region.security}"],
                    severity=_severity_from_levels(security_before, region.security),
                )
            )

    for civilization in state.civilizations.values():
        legitimacy_before = civilization.legitimacy
        scarcity_before = civilization.scarcity_pressure
        expansion_before = civilization.expansion_pressure

        _shift_civilization_pressure(civilization, rng)

        if legitimacy_before != civilization.legitimacy:
            events.append(
                Event(
                    event_id=state.event_stream.new_event_id(),
                    tick=state.current_tick,
                    time_granularity=state.current_granularity,
                    event_type="legitimacy_shift",
                    event_scope="civilization",
                    title=f"{civilization.name} legitimacy changed",
                    summary=(
                        f"{civilization.name} legitimacy moved from {legitimacy_before} "
                        f"to {civilization.legitimacy}."
                    ),
                    civ_refs=[civilization.civ_id],
                    cause_tags=["macro_shift", "governance_pressure"],
                    result_tags=[f"legitimacy_{civilization.legitimacy}"],
                    severity=_severity_from_levels(
                        legitimacy_before, civilization.legitimacy
                    ),
                )
            )

        if scarcity_before != civilization.scarcity_pressure:
            events.append(
                Event(
                    event_id=state.event_stream.new_event_id(),
                    tick=state.current_tick,
                    time_granularity=state.current_granularity,
                    event_type="civil_scarcity_shift",
                    event_scope="civilization",
                    title=f"{civilization.name} scarcity pressure changed",
                    summary=(
                        f"{civilization.name} scarcity pressure moved from "
                        f"{scarcity_before} to {civilization.scarcity_pressure}."
                    ),
                    civ_refs=[civilization.civ_id],
                    cause_tags=["macro_shift", "supply_pressure"],
                    result_tags=[f"scarcity_{civilization.scarcity_pressure}"],
                    severity=_severity_from_levels(
                        scarcity_before, civilization.scarcity_pressure
                    ),
                )
            )

        if expansion_before != civilization.expansion_pressure:
            events.append(
                Event(
                    event_id=state.event_stream.new_event_id(),
                    tick=state.current_tick,
                    time_granularity=state.current_granularity,
                    event_type="expansion_shift",
                    event_scope="civilization",
                    title=f"{civilization.name} expansion pressure changed",
                    summary=(
                        f"{civilization.name} expansion pressure moved from "
                        f"{expansion_before} to {civilization.expansion_pressure}."
                    ),
                    civ_refs=[civilization.civ_id],
                    cause_tags=["macro_shift", "frontier_pressure"],
                    result_tags=[f"expansion_{civilization.expansion_pressure}"],
                    severity=_severity_from_levels(
                        expansion_before, civilization.expansion_pressure
                    ),
                )
            )

    return events


def _shift_region_pressure(region: object, rng: Random) -> None:
    region.scarcity = _shift_level(region.scarcity, rng)
    region.political_tension = _shift_level(region.political_tension, rng)
    region.security = _shift_level(region.security, rng, invert=True)
    region.scarcity_trend = rng.choice(_TRENDS)
    region.political_tension_trend = rng.choice(_TRENDS)
    region.security_trend = rng.choice(_TRENDS)


def _shift_civilization_pressure(civilization: object, rng: Random) -> None:
    civilization.legitimacy = _shift_level(civilization.legitimacy, rng, invert=True)
    civilization.scarcity_pressure = _shift_level(civilization.scarcity_pressure, rng)
    civilization.expansion_pressure = _shift_level(civilization.expansion_pressure, rng)
    civilization.legitimacy_trend = rng.choice(_TRENDS)
    civilization.scarcity_trend = rng.choice(_TRENDS)
    civilization.expansion_trend = rng.choice(_TRENDS)


def _shift_level(level: str, rng: Random, invert: bool = False) -> str:
    index = _LEVELS.index(level)
    roll = rng.random()
    if roll < 0.2:
        index = max(0, index - 1)
    elif roll > 0.8:
        index = min(len(_LEVELS) - 1, index + 1)
    result = _LEVELS[index]
    if invert:
        return result
    return result


def _severity_from_levels(before: str, after: str) -> str:
    if before == after:
        return "low"
    distance = abs(_LEVELS.index(after) - _LEVELS.index(before))
    return "high" if distance >= 2 else "medium"
