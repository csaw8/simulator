"""Minimal knowledge snapshots for non-omniscient actor reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.events.models import Event
from src.events.visibility_rules import (
    PUBLIC_VISIBILITY,
    RUMORED_VISIBILITY,
    VISIBLE_VISIBILITY,
    normalize_event_visibility,
)
from src.world.character import Character
from src.world.state import WorldState


@dataclass(slots=True)
class CharacterKnowledgeSnapshot:
    """The subset of world state a character can reasonably act on."""

    character_id: str
    current_region_id: str
    current_civ_id: str | None
    visible_region_ids: list[str] = field(default_factory=list)
    recent_events: list[Event] = field(default_factory=list)
    visible_relic_events: list[Event] = field(default_factory=list)
    direct_events: list[Event] = field(default_factory=list)
    rumored_events: list[Event] = field(default_factory=list)
    public_events: list[Event] = field(default_factory=list)
    flashpoint_region_id: str | None = None

    def prioritized_events(self, limit: int = 12) -> list[Event]:
        """Return deduplicated events ordered by reasoning priority."""
        ordered = self.direct_events + self.rumored_events + self.public_events
        deduped: list[Event] = []
        seen_ids: set[str] = set()
        for event in reversed(ordered):
            if event.event_id in seen_ids:
                continue
            seen_ids.add(event.event_id)
            deduped.append(event)
        deduped.reverse()
        return deduped[-limit:]

    def knowledge_overview(self) -> dict[str, int | str | None]:
        """Return a compact summary of this snapshot for UI and debugging."""
        return {
            "direct_count": len(self.direct_events),
            "rumored_count": len(self.rumored_events),
            "public_count": len(self.public_events),
            "visible_region_count": len(self.visible_region_ids),
            "flashpoint_region_id": self.flashpoint_region_id,
        }


def build_character_knowledge_snapshot(
    world: WorldState,
    character: Character,
) -> CharacterKnowledgeSnapshot:
    """Build a compact, non-omniscient event snapshot for one character."""
    visible_region_ids = _visible_region_ids(world, character)
    current_region = world.regions[character.current_region_id]
    current_civ_id = current_region.civ_id

    visible_events = [
        event
        for event in world.event_stream.recent(50)
        if _event_visible_to_character(event, character, visible_region_ids, current_civ_id)
    ]
    direct_events = [
        event for event in visible_events if _event_knowledge_tier(event, character) == "direct"
    ]
    rumored_events = [
        event for event in visible_events if _event_knowledge_tier(event, character) == "rumored"
    ]
    public_events = [
        event for event in visible_events if _event_knowledge_tier(event, character) == "public"
    ]
    visible_relic_events = [event for event in visible_events if event.relic_refs]
    flashpoint_region_id = _infer_flashpoint_region(character, visible_relic_events)
    return CharacterKnowledgeSnapshot(
        character_id=character.char_id,
        current_region_id=character.current_region_id,
        current_civ_id=current_civ_id,
        visible_region_ids=visible_region_ids,
        recent_events=visible_events[-12:],
        visible_relic_events=visible_relic_events[-6:],
        direct_events=direct_events[-6:],
        rumored_events=rumored_events[-6:],
        public_events=public_events[-6:],
        flashpoint_region_id=flashpoint_region_id,
    )


def _visible_region_ids(world: WorldState, character: Character) -> list[str]:
    refs: list[str] = [character.current_region_id]
    for faction_id in character.affiliation:
        faction = world.factions.get(faction_id)
        if faction is None:
            continue
        for region_id in faction.controlled_regions[:4]:
            if region_id not in refs:
                refs.append(region_id)
    current_region = world.regions[character.current_region_id]
    if current_region.civ_id and current_region.civ_id in world.civilizations:
        civilization = world.civilizations[current_region.civ_id]
        for region_id in civilization.key_regions[:3]:
            if region_id not in refs:
                refs.append(region_id)
    return refs


def _event_visible_to_character(
    event: Event,
    character: Character,
    visible_region_ids: list[str],
    current_civ_id: str | None,
) -> bool:
    if character.char_id in event.actor_refs:
        return True
    if any(region_id in visible_region_ids for region_id in event.region_refs):
        return True
    if any(faction_id in event.faction_refs for faction_id in character.affiliation):
        return True
    if current_civ_id and current_civ_id in event.civ_refs and event.relic_refs:
        return True
    return False


def _infer_flashpoint_region(
    character: Character,
    visible_relic_events: list[Event],
) -> str | None:
    for event in reversed(visible_relic_events):
        if any(faction_id in event.faction_refs for faction_id in character.affiliation):
            return event.region_refs[0] if event.region_refs else None
        if character.current_region_id in event.region_refs:
            return character.current_region_id
        if event.region_refs:
            return event.region_refs[0]
    return None


def _event_knowledge_tier(event: Event, character: Character) -> str:
    if character.char_id in event.actor_refs or character.current_region_id in event.region_refs:
        return "direct"
    if any(faction_id in event.faction_refs for faction_id in character.affiliation):
        return "direct"
    visibility = normalize_event_visibility(event.visibility)
    if visibility in {RUMORED_VISIBILITY, "covert"}:
        return "rumored"
    if visibility in {PUBLIC_VISIBILITY, VISIBLE_VISIBILITY}:
        return "public"
    return "public"
