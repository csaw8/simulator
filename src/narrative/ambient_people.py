"""On-demand local people generation for observation views."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from src.events.models import Event
from src.events.taxonomy import event_theme_tags
from src.world.faction import Faction
from src.world.region import Region
from src.world.state import WorldState


@dataclass(slots=True)
class AmbientPerson:
    """A lightweight observation-only local person."""

    handle: str
    role: str
    stance: str
    pressure_link: str
    activity: str


def build_region_ambient_people(
    world: WorldState,
    region_id: str,
    *,
    limit: int = 3,
) -> list[AmbientPerson]:
    region = world.regions.get(region_id)
    if region is None:
        return []
    related_events = [
        event for event in world.event_stream.recent(40) if region_id in event.region_refs
    ][-8:]
    local_factions = [
        world.factions[faction_id]
        for faction_id in region.active_factions[:4]
        if faction_id in world.factions
    ]
    rng = Random(_seed_for_ref(world, region_id, limit))
    people: list[AmbientPerson] = []
    for index in range(limit):
        people.append(
            _build_region_person(
                world,
                region,
                local_factions,
                related_events,
                rng,
                index=index,
            )
        )
    return people


def build_faction_ambient_people(
    world: WorldState,
    faction_id: str,
    *,
    limit: int = 3,
) -> list[AmbientPerson]:
    faction = world.factions.get(faction_id)
    if faction is None:
        return []
    focal_regions = [
        world.regions[region_id]
        for region_id in faction.controlled_regions[:4]
        if region_id in world.regions
    ]
    region = focal_regions[0] if focal_regions else None
    related_events = [
        event for event in world.event_stream.recent(50) if faction_id in event.faction_refs
    ][-8:]
    rng = Random(_seed_for_ref(world, faction_id, limit))
    people: list[AmbientPerson] = []
    for index in range(limit):
        people.append(
            _build_faction_person(
                world,
                faction,
                region,
                related_events,
                rng,
                index=index,
            )
        )
    return people


def _build_region_person(
    world: WorldState,
    region: Region,
    factions: list[Faction],
    events: list[Event],
    rng: Random,
    *,
    index: int,
) -> AmbientPerson:
    role_pool = _region_role_pool(region, events)
    role = rng.choice(role_pool)
    faction = factions[index % len(factions)] if factions else None
    pressure_link = _region_pressure_link(region, events, faction)
    stance = _region_stance(region, faction)
    activity = _region_activity(region, role, pressure_link, faction)
    return AmbientPerson(
        handle=_ambient_handle(region.name, role, index + 1),
        role=role,
        stance=stance,
        pressure_link=pressure_link,
        activity=activity,
    )


def _build_faction_person(
    world: WorldState,
    faction: Faction,
    region: Region | None,
    events: list[Event],
    rng: Random,
    *,
    index: int,
) -> AmbientPerson:
    role_pool = _faction_role_pool(faction, region, events)
    role = rng.choice(role_pool)
    pressure_link = _faction_pressure_link(faction, region, events)
    stance = _faction_stance(faction)
    activity = _faction_activity(faction, region, role, pressure_link)
    region_name = region.name if region is not None else faction.name
    return AmbientPerson(
        handle=_ambient_handle(region_name, role, index + 1),
        role=role,
        stance=stance,
        pressure_link=pressure_link,
        activity=activity,
    )


def _region_role_pool(region: Region, events: list[Event]) -> list[str]:
    pool = {
        "arcology": ["transit marshal", "tower medic", "maintenance broker"],
        "orbital_port": ["cargo scheduler", "dock sentinel", "customs fixer"],
        "industrial_belt": ["line foreman", "scrap broker", "safety watcher"],
        "frontier_zone": ["perimeter scout", "salvage runner", "checkpoint clerk"],
        "research_hub": ["lab steward", "containment tech", "records analyst"],
        "agri_dome": ["ration allocator", "water monitor", "field supervisor"],
        "subsea_city": ["pressure diver", "bulkhead inspector", "pump controller"],
        "waste_reclaim": ["sort-yard boss", "filter mechanic", "reclaim diver"],
    }.get(region.region_type, ["district runner", "watch officer", "local broker"])
    if _events_include_token(events, "archive"):
        pool.append("records courier")
    if _events_include_token(events, "protocol"):
        pool.append("systems auditor")
    if _events_include_token(events, "lifeform"):
        pool.append("quarantine orderly")
    if _events_have_theme(events, "project"):
        pool.append("site coordinator")
    return pool


def _faction_role_pool(faction: Faction, region: Region | None, events: list[Event]) -> list[str]:
    pool = {
        "government": ["district secretary", "permit enforcer", "policy courier"],
        "megacorp": ["contract broker", "site accountant", "asset supervisor"],
        "security_force": ["field captain", "checkpoint marshal", "counterintel runner"],
        "research_institute": ["systems researcher", "containment planner", "data custodian"],
        "labor_union": ["crew delegate", "supply organizer", "yard speaker"],
        "network_cell": ["cutout broker", "silent operator", "relay keeper"],
        "infrastructure_consortium": ["grid coordinator", "site integrator", "maintenance allocator"],
        "data_cult": ["memory cantor", "signal interpreter", "archive witness"],
        "civic_guild": ["permit negotiator", "district mediator", "public works broker"],
        "logistics_syndicate": ["route broker", "cargo diverter", "gate scheduler"],
    }.get(faction.faction_type, ["local operative", "administrative fixer", "pressure runner"])
    if region is not None and region.scarcity == "high":
        pool.append("ration gatekeeper")
    if _events_have_theme(events, "project"):
        pool.append("contract corridor watcher")
    if _events_have_theme(events, "politics") or _events_include_token(events, "infiltration"):
        pool.append("broker liaison")
    return pool


def _region_pressure_link(region: Region, events: list[Event], faction: Faction | None) -> str:
    if _events_include_token(events, "lifeform"):
        return "biosecurity drift"
    if _events_include_token(events, "archive"):
        return "disclosure panic"
    if _events_include_token(events, "protocol"):
        return "system trust fracture"
    if _events_have_theme(events, "project"):
        return "project corridor stress"
    if region.scarcity == "high":
        return "ration strain"
    if region.political_tension == "high":
        return "brokered tension"
    if faction is not None and faction.operational_style == "extraction_broker":
        return "supply leverage"
    return "routine district pressure"


def _faction_pressure_link(faction: Faction, region: Region | None, events: list[Event]) -> str:
    if faction.operational_style == "contract_predator":
        return "contract capture"
    if faction.operational_style == "discipline_network":
        return "covert leverage"
    if faction.operational_style == "containment_cadre":
        return "containment control"
    if faction.operational_style == "extraction_broker":
        return "supply routing"
    if _events_include_token(events, "alliance"):
        return "alignment maintenance"
    if region is not None and region.political_tension == "high":
        return "order management"
    return "distributed local pressure"


def _region_stance(region: Region, faction: Faction | None) -> str:
    if region.security == "low":
        return "nervous but exposed"
    if region.political_tension == "high":
        return "careful and faction-aware"
    if faction is not None and faction.operational_style == "contract_predator":
        return "watching the contract line closely"
    if region.scarcity == "high":
        return "practical under shortage"
    return "settled but alert"


def _events_have_theme(events: list[Event], theme: str) -> bool:
    return any(theme in event_theme_tags(event) for event in events)


def _events_include_token(events: list[Event], token: str) -> bool:
    token = token.lower()
    return any(token in event.event_type.lower() for event in events)


def _faction_stance(faction: Faction) -> str:
    mapping = {
        "discipline_network": "speaks little and tracks loyalties",
        "contract_predator": "counts cost, access, and signatures first",
        "containment_cadre": "treats every opening like a spill risk",
        "extraction_broker": "reads pressure as a material bargaining edge",
        "adaptive_network": "adjusts quickly to whoever controls the seam",
    }
    return mapping.get(faction.operational_style, "adjusts quickly to local pressure")


def _region_activity(region: Region, role: str, pressure_link: str, faction: Faction | None) -> str:
    if pressure_link == "project corridor stress":
        return f"{role} is quietly rerouting crews and permits around the live construction seam."
    if pressure_link == "biosecurity drift":
        return f"{role} is treating movement logs and checkpoints as early warning tools against spread."
    if pressure_link == "disclosure panic":
        return f"{role} is filtering names, records, and questions before they can harden into a public line."
    if pressure_link == "system trust fracture":
        return f"{role} is double-checking access channels and watching for silent override behavior."
    if pressure_link == "ration strain":
        return f"{role} is trading favors and queues to keep shortages from becoming open disorder."
    if faction is not None and faction.operational_style == "discipline_network":
        return f"{role} is moving through {region.name} with one eye on broker chains and one on loyalty shifts."
    return f"{role} is reacting to {pressure_link} without enough authority to fully control it."


def _faction_activity(faction: Faction, region: Region | None, role: str, pressure_link: str) -> str:
    region_name = region.name if region is not None else "the current district"
    if faction.operational_style == "contract_predator":
        return f"{role} is trying to turn budget paperwork and execution bottlenecks in {region_name} into durable control."
    if faction.operational_style == "discipline_network":
        return f"{role} is keeping a narrow contact chain alive in {region_name} while testing which brokers can be bent."
    if faction.operational_style == "containment_cadre":
        return f"{role} is treating access, custody, and containment procedure as the real terrain of power in {region_name}."
    if faction.operational_style == "extraction_broker":
        return f"{role} is mapping storage, transport, and permit chokepoints in {region_name} for later leverage."
    return f"{role} is adjusting to {pressure_link} around {region_name} and waiting for a cleaner opening."


def _ambient_handle(region_name: str, role: str, index: int) -> str:
    base = region_name.split(" ", 1)[0]
    role_code = "".join(word[0] for word in role.split()[:2]).upper()
    return f"{base}-{role_code}-{index:02d}"


def _seed_for_ref(world: WorldState, ref: str, limit: int) -> int:
    return world.seed * 131 + world.current_tick * 17 + sum(ord(char) for char in ref) + limit
