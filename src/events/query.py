"""Event query helpers for focused CLI inspection."""

from __future__ import annotations

from src.events.models import Event
from src.events.visibility_rules import filter_events_for_view
from src.world.character import Character
from src.world.state import WorldState


def select_events(
    events: list[Event],
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    limit: int = 10,
    view: str = "truth",
) -> list[Event]:
    """Return recent events, optionally filtered to one focus target."""
    normalized_limit = max(1, limit)
    if not target_type or not target_id:
        visible_events = filter_events_for_view(events, view=view)
        return visible_events[-normalized_limit:]

    matcher = _build_matcher(target_type)
    if matcher is None:
        return []

    filtered = [event for event in events if matcher(event, target_id)]
    visible_events = filter_events_for_view(filtered, view=view)
    return visible_events[-normalized_limit:]


def describe_focus(target_type: str | None = None, target_id: str | None = None) -> str:
    """Return a human-readable label for an event query."""
    if not target_type or not target_id:
        return "recent"
    return f"{target_type}={target_id}"


def find_character_flashpoint_events(
    world: WorldState,
    character: Character,
    limit: int = 4,
) -> list[Event]:
    """Return recent high-salience events a character is likely to react to."""
    related: list[Event] = []
    current_region = world.regions[character.current_region_id]
    current_civ_id = current_region.civ_id

    for event in world.event_stream.recent(40):
        if character.char_id in event.actor_refs:
            related.append(event)
            continue
        if character.current_region_id in event.region_refs:
            related.append(event)
            continue
        if any(faction_id in event.faction_refs for faction_id in character.affiliation):
            related.append(event)
            continue
        if current_civ_id and current_civ_id in event.civ_refs and event.relic_refs:
            related.append(event)
            continue

    return related[-limit:]


def find_relic_flashpoint_region(world: WorldState, character: Character) -> str | None:
    """Return a nearby or affiliated region under relic pressure, if any."""
    current_region = world.regions[character.current_region_id]
    current_civ_id = current_region.civ_id

    for event in reversed(world.event_stream.recent(40)):
        if not event.relic_refs:
            continue
        if any(faction_id in event.faction_refs for faction_id in character.affiliation):
            return event.region_refs[0] if event.region_refs else None
        if character.current_region_id in event.region_refs:
            return character.current_region_id
        if current_civ_id and current_civ_id in event.civ_refs and event.region_refs:
            return event.region_refs[0]
    return None


def find_recent_relic_event_for_region(world: WorldState, region_id: str) -> Event | None:
    """Return the most recent relic-linked event touching a region."""
    for event in reversed(world.event_stream.recent(40)):
        if region_id in event.region_refs and event.relic_refs:
            return event
    return None
def _build_matcher(target_type: str):
    normalized = target_type.lower()
    if normalized == "region":
        return lambda event, target_id: target_id in event.region_refs
    if normalized == "character":
        return lambda event, target_id: target_id in event.actor_refs
    if normalized == "civ":
        return lambda event, target_id: target_id in event.civ_refs
    if normalized == "faction":
        return lambda event, target_id: target_id in event.faction_refs
    if normalized == "relic":
        return lambda event, target_id: target_id in event.relic_refs
    if normalized in {"dynamic", "structure"}:
        return lambda event, target_id: target_id in event.dynamic_structure_refs
    if normalized in {"emergent", "emergent_presence"}:
        return lambda event, target_id: target_id in event.emergent_presence_refs
    return None
