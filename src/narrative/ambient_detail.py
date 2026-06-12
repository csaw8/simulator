"""On-demand local object and scene detail generation for observation views."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from src.events.models import Event
from src.events.taxonomy import event_theme_tags
from src.world.presence import presence_event_family
from src.world.region import Region
from src.world.relic import Relic
from src.world.state import WorldState


@dataclass(slots=True)
class AmbientDetail:
    """A lightweight observation-only local object or scene fragment."""

    label: str
    detail_type: str
    condition: str
    pressure_link: str
    note: str


def build_region_ambient_details(
    world: WorldState,
    region_id: str,
    *,
    limit: int = 3,
) -> list[AmbientDetail]:
    region = world.regions.get(region_id)
    if region is None:
        return []
    recent_events = [
        event for event in world.event_stream.recent(40) if region_id in event.region_refs
    ][-8:]
    local_relics = [
        world.relics[relic_id]
        for relic_id in region.resident_relics[:3]
        if relic_id in world.relics
    ]
    rng = Random(_seed_for_ref(world, region_id, limit, salt=701))
    return [
        _build_region_detail(region, recent_events, local_relics, rng, index=index)
        for index in range(limit)
    ]


def build_relic_ambient_details(
    world: WorldState,
    relic_id: str,
    *,
    limit: int = 3,
) -> list[AmbientDetail]:
    relic = world.relics.get(relic_id)
    if relic is None:
        return []
    region = world.regions[relic.current_region_id]
    recent_events = [
        event for event in world.event_stream.recent(50) if relic_id in event.relic_refs
    ][-8:]
    rng = Random(_seed_for_ref(world, relic_id, limit, salt=997))
    return [
        _build_relic_detail(region, relic, recent_events, rng, index=index)
        for index in range(limit)
    ]


def _build_region_detail(
    region: Region,
    events: list[Event],
    relics: list[Relic],
    rng: Random,
    *,
    index: int,
) -> AmbientDetail:
    detail_type = rng.choice(_region_detail_pool(region, events))
    pressure = _region_pressure(events, relics, region)
    condition = _region_condition(region, pressure)
    note = _region_note(region, detail_type, pressure)
    return AmbientDetail(
        label=_detail_label(region.name, detail_type, index + 1),
        detail_type=detail_type,
        condition=condition,
        pressure_link=pressure,
        note=note,
    )


def _build_relic_detail(
    region: Region,
    relic: Relic,
    events: list[Event],
    rng: Random,
    *,
    index: int,
) -> AmbientDetail:
    family = presence_event_family(relic)
    detail_type = rng.choice(_relic_detail_pool(family, events))
    pressure = _relic_pressure(family, events, region, relic)
    condition = _relic_condition(family, relic, region)
    note = _relic_note(detail_type, pressure, relic, region)
    return AmbientDetail(
        label=_detail_label(relic.name, detail_type, index + 1),
        detail_type=detail_type,
        condition=condition,
        pressure_link=pressure,
        note=note,
    )


def _region_detail_pool(region: Region, events: list[Event]) -> list[str]:
    pool = {
        "arcology": ["elevator bank", "crowd funnel", "sealed maintenance hatch"],
        "orbital_port": ["cargo pallet", "docking manifest", "inspection gantry"],
        "industrial_belt": ["scrap hopper", "coolant drum", "shift siren tower"],
        "frontier_zone": ["checkpoint barrier", "watch beacon", "fuel crate row"],
        "research_hub": ["sample locker", "glass partition", "containment trolley"],
        "agri_dome": ["ration chute", "water valve nest", "soil sensor rack"],
        "subsea_city": ["pressure hatch", "pipe junction", "drainage sled"],
        "waste_reclaim": ["filter stack", "sorting cage", "slag conveyor"],
    }.get(region.region_type, ["storage cage", "permit board", "service terminal"])
    if _events_have_theme(events, "project"):
        pool.append("temporary scaffold spine")
    if _events_include_token(events, "archive"):
        pool.append("sealed document case")
    if _events_include_token(events, "protocol"):
        pool.append("override console shell")
    if _events_include_token(events, "lifeform"):
        pool.append("quarantine tape corridor")
    return pool


def _relic_detail_pool(family: str, events: list[Event]) -> list[str]:
    if family == "megastructure":
        pool = ["anchor truss", "budget terminal", "safety mesh corridor", "crew beacon"]
        if _events_include_token(events, "stall") or _events_include_token(events, "accident"):
            pool.append("buckled support frame")
        return pool
    if family == "autonomous_system":
        return ["cooling stack", "control sheath", "override cradle", "access relay"]
    if family == "sealed_archive":
        return ["index cassette", "sealed drawer bank", "document crate", "redacted wall panel"]
    if family == "anomalous_lifeform":
        return ["shed tissue sample", "motion trap", "feeding scar", "containment fence segment"]
    return ["signal housing", "locked transit case", "power coupler", "inspection shell"]


def _region_pressure(events: list[Event], relics: list[Relic], region: Region) -> str:
    if _events_include_token(events, "lifeform"):
        return "biosecurity spillover"
    if _events_include_token(events, "archive"):
        return "document panic"
    if _events_include_token(events, "protocol"):
        return "systems distrust"
    if _events_have_theme(events, "project"):
        return "engineering strain"
    if relics:
        families = {presence_event_family(relic) for relic in relics}
        if "anomalous_lifeform" in families:
            return "biosecurity watch"
        if "sealed_archive" in families:
            return "suppressed disclosure"
    if region.scarcity == "high":
        return "ration pressure"
    if region.political_tension == "high":
        return "tense checkpoint order"
    return "routine district wear"


def _relic_pressure(family: str, events: list[Event], region: Region, relic: Relic) -> str:
    if family == "megastructure":
        if _events_have_theme(events, "project") or _events_include_token(events, "contract"):
            return "budget and execution conflict"
        if _events_include_token(events, "stall") or _events_include_token(events, "accident"):
            return "construction instability"
        return "live infrastructure coupling"
    if family == "autonomous_system":
        return "silent override risk"
    if family == "sealed_archive":
        return "controlled disclosure risk"
    if family == "anomalous_lifeform":
        if _events_include_token(events, "migration"):
            return "spread corridor pressure"
        return "containment drift"
    return "access control friction"


def _region_condition(region: Region, pressure: str) -> str:
    if region.security == "low":
        return "exposed"
    if region.scarcity == "high":
        return "strained"
    if "panic" in pressure or "spillover" in pressure:
        return "fragile"
    if region.infrastructure == "high":
        return "overused but functional"
    return "serviceable"


def _relic_condition(family: str, relic: Relic, region: Region) -> str:
    if family == "megastructure":
        if relic.construction_state in {"planned", "foundation"}:
            return "incomplete"
        if relic.construction_state in {"integration", "operational"}:
            return "live"
        return "unstable"
    if family == "autonomous_system":
        return "sealed" if relic.activation_state == "sealed" else "quietly contested"
    if family == "sealed_archive":
        return "locked" if relic.activation_state == "sealed" else "leaking"
    if family == "anomalous_lifeform":
        return "contained" if relic.activation_state == "sealed" else "active"
    return "guarded"


def _region_note(region: Region, detail_type: str, pressure: str) -> str:
    if pressure == "engineering strain":
        return f"{detail_type} around {region.name} is being repurposed to keep project throughput alive."
    if pressure == "biosecurity spillover":
        return f"{detail_type} has become part of an improvised quarantine edge inside {region.name}."
    if pressure == "document panic":
        return f"{detail_type} now sits inside a chain of custody disputes and selective record handling."
    if pressure == "systems distrust":
        return f"{detail_type} is treated less like infrastructure and more like a possible breach point."
    if pressure == "ration pressure":
        return f"{detail_type} is being watched for signs that shortage is about to turn into open queue conflict."
    return f"{detail_type} is absorbing the ordinary wear of {pressure} in {region.name}."


def _relic_note(detail_type: str, pressure: str, relic: Relic, region: Region) -> str:
    if pressure == "budget and execution conflict":
        return f"{detail_type} near {relic.name} is now a choke point in the fight over who gets to keep the project moving."
    if pressure == "construction instability":
        return f"{detail_type} around {relic.name} shows how close the site is to slipping from delay into cascading failure."
    if pressure == "silent override risk":
        return f"{detail_type} near {relic.name} is treated as a possible path for hidden protocol authority."
    if pressure == "controlled disclosure risk":
        return f"{detail_type} around {relic.name} is being handled as if one missing unit could change the political story in {region.name}."
    if pressure == "spread corridor pressure":
        return f"{detail_type} marks one of the places where {relic.name} may extend beyond its last known edge."
    if pressure == "containment drift":
        return f"{detail_type} shows that {relic.name} is not fully under custody, even when the perimeter still looks intact."
    return f"{detail_type} remains tied to the daily control problem surrounding {relic.name} in {region.name}."


def _detail_label(base_name: str, detail_type: str, index: int) -> str:
    base = base_name.split(" ", 1)[0]
    code = "".join(word[0] for word in detail_type.split()[:2]).upper()
    return f"{base}-{code}-{index:02d}"


def _seed_for_ref(world: WorldState, ref: str, limit: int, *, salt: int) -> int:
    return world.seed * 173 + world.current_tick * 29 + salt + sum(ord(char) for char in ref) + limit


def _events_have_theme(events: list[Event], theme: str) -> bool:
    return any(theme in event_theme_tags(event) for event in events)


def _events_include_token(events: list[Event], token: str) -> bool:
    token = token.lower()
    return any(token in event.event_type.lower() for event in events)
