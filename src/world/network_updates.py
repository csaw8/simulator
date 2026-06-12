"""Helpers for writing lightweight history into mid-layer structures."""

from __future__ import annotations

from src.world.project import ProjectNetwork
from src.world.state import WorldState
from src.world.supply import SupplyLine

_NOTE_LIMIT = 6
_PRESSURE_UPSHIFT = {"low": "medium", "medium": "high", "high": "high"}
_PRESSURE_DOWNSHIFT = {"high": "medium", "medium": "low", "low": "low"}


def append_project_note(
    state: WorldState,
    *,
    note: str,
    relic_id: str | None = None,
    faction_id: str | None = None,
    region_id: str | None = None,
    civ_id: str | None = None,
    status: str | None = None,
    pressure: str | None = None,
    pressure_shift: str | None = None,
) -> ProjectNetwork | None:
    """Append a history note to the best matching project network."""
    project = (
        _find_project_by_relic(state, relic_id)
        or _find_project_by_faction_region(state, faction_id=faction_id, region_id=region_id, civ_id=civ_id)
        or _find_project_by_region(state, region_id)
    )
    if project is None:
        return None
    _append_note(project.recent_notes, state.current_tick, note)
    if faction_id:
        _link_unique(project.linked_factions, faction_id)
    if region_id:
        _link_unique(project.linked_regions, region_id)
    if civ_id:
        _link_unique(project.linked_civs, civ_id)
    if relic_id:
        _link_unique(project.linked_presence_refs, relic_id)
    if status is not None:
        project.status = status
    if pressure is not None:
        project.pressure = pressure
    elif pressure_shift == "up":
        project.pressure = _PRESSURE_UPSHIFT.get(project.pressure, project.pressure)
    elif pressure_shift == "down":
        project.pressure = _PRESSURE_DOWNSHIFT.get(project.pressure, project.pressure)
    return project


def append_supply_note(
    state: WorldState,
    *,
    note: str,
    faction_id: str | None = None,
    region_id: str | None = None,
    civ_id: str | None = None,
    status: str | None = None,
    pressure: str | None = None,
    pressure_shift: str | None = None,
    controlling_faction_ref: str | None = None,
) -> SupplyLine | None:
    """Append a history note to the best matching supply corridor."""
    supply_line = _find_supply_by_faction_region(
        state,
        faction_id=faction_id,
        region_id=region_id,
        civ_id=civ_id,
    ) or _find_supply_by_region(state, region_id, civ_id=civ_id)
    if supply_line is None:
        return None
    _append_note(supply_line.recent_notes, state.current_tick, note)
    if civ_id:
        _link_unique_multi(supply_line.linked_civ_refs, civ_id)
    if status is not None:
        supply_line.status = status
    if pressure is not None:
        supply_line.pressure = pressure
    elif pressure_shift == "up":
        supply_line.pressure = _PRESSURE_UPSHIFT.get(supply_line.pressure, supply_line.pressure)
    elif pressure_shift == "down":
        supply_line.pressure = _PRESSURE_DOWNSHIFT.get(supply_line.pressure, supply_line.pressure)
    if controlling_faction_ref is not None:
        supply_line.controlling_faction_ref = controlling_faction_ref
    return supply_line


def _find_project_by_relic(state: WorldState, relic_id: str | None) -> ProjectNetwork | None:
    if not relic_id:
        return None
    for project in state.projects.values():
        if relic_id in project.linked_presence_refs:
            return project
    return None


def _find_project_by_faction_region(
    state: WorldState,
    *,
    faction_id: str | None,
    region_id: str | None,
    civ_id: str | None,
) -> ProjectNetwork | None:
    for project in state.projects.values():
        if faction_id and faction_id in project.linked_factions:
            if region_id is None or region_id in project.linked_regions:
                return project
        if civ_id and civ_id in project.linked_civs:
            if region_id is None or region_id in project.linked_regions:
                return project
    return None


def _find_project_by_region(state: WorldState, region_id: str | None) -> ProjectNetwork | None:
    if not region_id:
        return None
    for project in state.projects.values():
        if region_id in project.linked_regions:
            return project
    return None


def _find_supply_by_faction_region(
    state: WorldState,
    *,
    faction_id: str | None,
    region_id: str | None,
    civ_id: str | None,
) -> SupplyLine | None:
    for supply_line in state.supply_lines.values():
        if faction_id and supply_line.controlling_faction_ref == faction_id:
            if region_id is None or region_id in {supply_line.origin_region_id, supply_line.destination_region_id}:
                if civ_id is None or civ_id in supply_line.linked_civ_refs:
                    return supply_line
        if region_id and region_id in {supply_line.origin_region_id, supply_line.destination_region_id}:
            if civ_id is None or civ_id in supply_line.linked_civ_refs:
                return supply_line
    return None


def _find_supply_by_region(
    state: WorldState,
    region_id: str | None,
    *,
    civ_id: str | None,
) -> SupplyLine | None:
    if not region_id:
        return None
    for supply_line in state.supply_lines.values():
        if region_id in {supply_line.origin_region_id, supply_line.destination_region_id}:
            if civ_id is None or civ_id in supply_line.linked_civ_refs:
                return supply_line
    return None


def _append_note(notes: list[str], tick: int, note: str) -> None:
    notes.append(f"tick_{tick}:{note}")
    del notes[:-_NOTE_LIMIT]


def _link_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _link_unique_multi(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)
