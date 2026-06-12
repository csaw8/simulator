"""Faction-scale action generation and consequence rules."""

from __future__ import annotations

from random import Random

from src.events.models import Event
from src.world.faction import Faction
from src.world.presence import is_contemporary_megastructure, presence_event_family
from src.world.region import Region
from src.world.relations import upsert_relation
from src.world.relic import Relic
from src.world.network_updates import append_project_note, append_supply_note
from src.world.state import WorldState
from src.world.supply import SupplyLine

_UPSHIFT = {"low": "medium", "medium": "high", "high": "high"}
_DOWNSHIFT = {"high": "medium", "medium": "low", "low": "low"}

_ACTION_TYPES = [
    "faction_infiltration",
    "faction_alliance",
    "faction_power_struggle",
    "faction_resource_reallocation",
    "faction_relic_contest",
    "faction_relic_control",
    "faction_project_bid",
    "faction_budget_freeze",
    "faction_financing_withdrawal",
    "faction_site_accident",
]


def advance_faction_actions(state: WorldState, rng: Random) -> list[Event]:
    """Let a small number of factions act each tick and emit consequences."""
    if not state.factions:
        return []

    events: list[Event] = []
    faction_ids = list(state.factions.keys())
    rng.shuffle(faction_ids)
    action_budget = _action_budget(len(faction_ids), rng)

    for faction_id in faction_ids[:action_budget]:
        faction = state.factions[faction_id]
        event = _resolve_faction_action(state, faction, rng)
        if event is not None:
            events.append(event)

    return events


def _action_budget(faction_count: int, rng: Random) -> int:
    base = max(1, faction_count // 3)
    return min(faction_count, max(1, base + rng.randint(0, 1)))


def _resolve_faction_action(
    state: WorldState,
    faction: Faction,
    rng: Random,
) -> Event | None:
    controlled_regions = [
        state.regions[region_id]
        for region_id in faction.controlled_regions
        if region_id in state.regions
    ]
    candidate_regions = controlled_regions or _regions_for_civilization(state, faction.parent_civ_id)
    if not candidate_regions:
        return None

    action_type = _choose_action_type(state, faction, rng)
    if action_type == "faction_infiltration":
        return _run_infiltration(state, faction, candidate_regions, rng)
    if action_type == "faction_alliance":
        return _run_alliance(state, faction, rng)
    if action_type == "faction_power_struggle":
        return _run_power_struggle(state, faction, candidate_regions, rng)
    if action_type == "faction_relic_contest":
        return _run_relic_contest(state, faction, candidate_regions, rng)
    if action_type == "faction_relic_control":
        return _run_relic_control(state, faction, candidate_regions, rng)
    if action_type == "faction_project_bid":
        return _run_project_bid(state, faction, candidate_regions, rng)
    if action_type == "faction_budget_freeze":
        return _run_budget_freeze(state, faction, candidate_regions, rng)
    if action_type == "faction_financing_withdrawal":
        return _run_financing_withdrawal(state, faction, candidate_regions, rng)
    if action_type == "faction_site_accident":
        return _run_site_accident(state, faction, candidate_regions, rng)
    return _run_resource_reallocation(state, faction, candidate_regions, rng)


def _choose_action_type(state: WorldState, faction: Faction, rng: Random) -> str:
    has_relic_pressure = "legacy_control" in faction.doctrine_tags or "secrecy" in faction.doctrine_tags
    has_project_pressure = "growth" in faction.doctrine_tags or "efficiency" in faction.doctrine_tags
    if faction.influence == "low":
        weights = [5, 2, 2, 4, 2 if has_relic_pressure else 1, 1, 2 if has_project_pressure else 1, 1, 1, 1]
    elif faction.influence == "high":
        weights = [2, 3, 5, 3, 2, 3 if has_relic_pressure else 2, 3 if has_project_pressure else 1, 2, 2, 2]
    else:
        weights = [3, 3, 4, 4, 2, 2 if has_relic_pressure else 1, 3 if has_project_pressure else 1, 2, 2, 2]
    posture = _civilization_posture_for_faction(state, faction)
    weights = _apply_posture_bias(weights, posture)
    weights = _apply_structure_template_bias(state, weights)
    weights = _apply_faction_type_bias(faction, weights)
    weights = _apply_operational_style_bias(faction, weights)
    weights = _apply_relationship_bias(state, faction, weights)
    return rng.choices(_ACTION_TYPES, weights=weights, k=1)[0]


def _civilization_posture_for_faction(state: WorldState, faction: Faction) -> str:
    if not faction.parent_civ_id:
        return "balanced_competition"
    civilization = state.civilizations.get(faction.parent_civ_id)
    if civilization is None:
        return "balanced_competition"
    return civilization.strategic_posture


def _apply_posture_bias(weights: list[int], posture: str) -> list[int]:
    adjusted = list(weights)
    bias_map = {
        "containment_first": {
            "faction_relic_control": 3,
            "faction_relic_contest": 2,
            "faction_budget_freeze": 1,
            "faction_site_accident": 1,
            "faction_project_bid": -2,
            "faction_alliance": -1,
        },
        "megastructure_expansion": {
            "faction_project_bid": 4,
            "faction_financing_withdrawal": 3,
            "faction_resource_reallocation": 2,
            "faction_relic_control": 1,
            "faction_site_accident": -1,
            "faction_infiltration": -1,
        },
        "stability_over_growth": {
            "faction_infiltration": 2,
            "faction_alliance": 3,
            "faction_power_struggle": 4,
            "faction_budget_freeze": 1,
            "faction_project_bid": -1,
            "faction_resource_reallocation": -1,
        },
        "opportunistic_extraction": {
            "faction_resource_reallocation": 4,
            "faction_relic_contest": 2,
            "faction_financing_withdrawal": 2,
            "faction_project_bid": 1,
            "faction_alliance": -1,
        },
    }
    for index, action_type in enumerate(_ACTION_TYPES):
        adjusted[index] = max(1, adjusted[index] + bias_map.get(posture, {}).get(action_type, 0))
    return adjusted


def _apply_structure_template_bias(state: WorldState, weights: list[int]) -> list[int]:
    adjusted = list(weights)
    frame = state.structure_template
    bias_map: dict[str, int] = {}
    if "supply_fronts" in frame.dominant_fronts:
        bias_map["faction_resource_reallocation"] = bias_map.get("faction_resource_reallocation", 0) + 3
    if "governance_fronts" in frame.dominant_fronts:
        bias_map["faction_power_struggle"] = bias_map.get("faction_power_struggle", 0) + 2
        bias_map["faction_infiltration"] = bias_map.get("faction_infiltration", 0) + 1
    if "project_fronts" in frame.dominant_fronts or frame.anomaly_bias == "megastructure_pressure":
        bias_map["faction_project_bid"] = bias_map.get("faction_project_bid", 0) + 3
        bias_map["faction_budget_freeze"] = bias_map.get("faction_budget_freeze", 0) + 2
        bias_map["faction_financing_withdrawal"] = bias_map.get("faction_financing_withdrawal", 0) + 2
    if "migration_fronts" in frame.dominant_fronts or frame.anomaly_bias == "biosecurity_pressure":
        bias_map["faction_relic_contest"] = bias_map.get("faction_relic_contest", 0) + 2
        bias_map["faction_relic_control"] = bias_map.get("faction_relic_control", 0) + 2
    if frame.anomaly_bias in {"sealed_information_pressure", "autonomous_system_pressure"}:
        bias_map["faction_infiltration"] = bias_map.get("faction_infiltration", 0) + 2
        bias_map["faction_alliance"] = bias_map.get("faction_alliance", 0) - 1

    for index, action_type in enumerate(_ACTION_TYPES):
        adjusted[index] = max(1, adjusted[index] + bias_map.get(action_type, 0))
    return adjusted


def _apply_operational_style_bias(faction: Faction, weights: list[int]) -> list[int]:
    adjusted = list(weights)
    bias_map = {
        "discipline_network": {
            "faction_infiltration": 2,
            "faction_power_struggle": 1,
            "faction_alliance": 1,
            "faction_project_bid": -1,
        },
        "contract_predator": {
            "faction_project_bid": 3,
            "faction_financing_withdrawal": 2,
            "faction_budget_freeze": 1,
            "faction_alliance": -1,
        },
        "containment_cadre": {
            "faction_relic_control": 3,
            "faction_relic_contest": 1,
            "faction_site_accident": 1,
            "faction_resource_reallocation": -1,
        },
        "extraction_broker": {
            "faction_resource_reallocation": 3,
            "faction_financing_withdrawal": 1,
            "faction_relic_contest": 1,
            "faction_alliance": -1,
        },
        "adaptive_network": {
            "faction_alliance": 1,
            "faction_power_struggle": 1,
        },
    }
    style_bias = bias_map.get(faction.operational_style, {})
    for index, action_type in enumerate(_ACTION_TYPES):
        adjusted[index] = max(1, adjusted[index] + style_bias.get(action_type, 0))
    return adjusted


def _apply_faction_type_bias(faction: Faction, weights: list[int]) -> list[int]:
    adjusted = list(weights)
    bias_map = {
        "infrastructure_consortium": {
            "faction_project_bid": 2,
            "faction_budget_freeze": 1,
            "faction_financing_withdrawal": 1,
            "faction_alliance": -1,
        },
        "data_cult": {
            "faction_infiltration": 2,
            "faction_relic_control": 2,
            "faction_relic_contest": 1,
            "faction_resource_reallocation": -1,
        },
        "civic_guild": {
            "faction_alliance": 2,
            "faction_power_struggle": 1,
            "faction_site_accident": -1,
        },
        "logistics_syndicate": {
            "faction_resource_reallocation": 2,
            "faction_financing_withdrawal": 2,
            "faction_relic_control": -1,
        },
    }
    type_bias = bias_map.get(faction.faction_type, {})
    for index, action_type in enumerate(_ACTION_TYPES):
        adjusted[index] = max(1, adjusted[index] + type_bias.get(action_type, 0))
    return adjusted


def _apply_relationship_bias(state: WorldState, faction: Faction, weights: list[int]) -> list[int]:
    adjusted = list(weights)
    rivalry_count = len(faction.rival_factions)
    alliance_count = len(faction.allied_factions)
    contested_regions = 0
    for region_id in faction.controlled_regions[:4]:
        region = state.regions.get(region_id)
        if region is None:
            continue
        active_rivals = [ref for ref in region.active_factions if ref in faction.rival_factions]
        if active_rivals:
            contested_regions += 1

    bias_map: dict[str, int] = {}
    if rivalry_count >= 2:
        bias_map["faction_power_struggle"] = bias_map.get("faction_power_struggle", 0) + 3
        bias_map["faction_infiltration"] = bias_map.get("faction_infiltration", 0) + 2
        bias_map["faction_alliance"] = bias_map.get("faction_alliance", 0) - 1
    if alliance_count >= 1:
        bias_map["faction_alliance"] = bias_map.get("faction_alliance", 0) + 2
        bias_map["faction_resource_reallocation"] = bias_map.get("faction_resource_reallocation", 0) + 1
    if alliance_count >= 2:
        bias_map["faction_project_bid"] = bias_map.get("faction_project_bid", 0) + 2
        bias_map["faction_financing_withdrawal"] = bias_map.get("faction_financing_withdrawal", 0) + 1
    if contested_regions >= 1:
        bias_map["faction_power_struggle"] = bias_map.get("faction_power_struggle", 0) + 2
        bias_map["faction_resource_reallocation"] = bias_map.get("faction_resource_reallocation", 0) + 1
    if contested_regions >= 2:
        bias_map["faction_site_accident"] = bias_map.get("faction_site_accident", 0) + 1
        bias_map["faction_budget_freeze"] = bias_map.get("faction_budget_freeze", 0) + 1

    for index, action_type in enumerate(_ACTION_TYPES):
        adjusted[index] = max(1, adjusted[index] + bias_map.get(action_type, 0))
    return adjusted


def _run_infiltration(
    state: WorldState,
    faction: Faction,
    candidate_regions: list[Region],
    rng: Random,
) -> Event:
    region = rng.choice(candidate_regions)
    before_security = region.security
    before_tension = region.political_tension
    region.security = _DOWNSHIFT[region.security]
    region.political_tension = _UPSHIFT[region.political_tension]
    faction.influence = _UPSHIFT[faction.influence]
    faction.influence_trend = "rising"
    _ensure_region_control(faction, region)
    append_supply_note(
        state,
        faction_id=faction.faction_id,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note=f"infiltration_pressure->{faction.faction_id}",
        pressure_shift="up",
    )
    append_project_note(
        state,
        faction_id=faction.faction_id,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note=f"infiltration_pressure->{faction.faction_id}",
        pressure_shift="up",
    )

    summary = (
        f"{faction.name} quietly expanded its reach inside {region.name}, "
        f"eroding security toward {region.security} while nudging political tension upward."
    )
    event = _build_faction_event(
        state,
        faction,
        "faction_infiltration",
        summary,
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        cause_tags=["faction_move", "infiltration"],
        result_tags=[
            f"security_{before_security}_to_{region.security}",
            f"tension_{before_tension}_to_{region.political_tension}",
            f"influence_{faction.influence}",
        ],
        severity="high" if before_security == "low" else "medium",
        consequence_score="medium",
    )
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=region.region_id,
        relation_type="infiltrating",
        event=event,
        strength="high" if before_security == "low" else "medium",
        notes=summary,
        tags=["organization", "region_pressure", "infiltration"],
    )
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=region.region_id,
        relation_type="operates_in",
        event=event,
        strength="medium",
        notes=summary,
        tags=["organization", "region_presence"],
    )
    return event


def _run_alliance(state: WorldState, faction: Faction, rng: Random) -> Event:
    peers = [
        other
        for other in state.factions.values()
        if other.faction_id != faction.faction_id and other.parent_civ_id == faction.parent_civ_id
    ]
    if not peers:
        faction.cohesion = _UPSHIFT[faction.cohesion]
        faction.influence_trend = "steady"
        summary = (
            f"{faction.name} failed to find a viable partner and instead tightened its internal discipline."
        )
        return _build_faction_event(
            state,
            faction,
            "faction_alliance_consolidation",
            summary,
            civ_refs=[faction.parent_civ_id] if faction.parent_civ_id else [],
            cause_tags=["faction_move", "alliance_attempt"],
            result_tags=[f"cohesion_{faction.cohesion}"],
            severity="low",
            consequence_score="low",
        )

    partner = rng.choice(peers)
    _link_unique(faction.allied_factions, partner.faction_id)
    _link_unique(partner.allied_factions, faction.faction_id)
    _unlink_if_present(faction.rival_factions, partner.faction_id)
    _unlink_if_present(partner.rival_factions, faction.faction_id)
    faction.cohesion = _UPSHIFT[faction.cohesion]
    partner.cohesion = _UPSHIFT[partner.cohesion]
    faction.influence = _UPSHIFT[faction.influence]
    partner.influence = _UPSHIFT[partner.influence]
    alliance_region_id = faction.controlled_regions[0] if faction.controlled_regions else (
        partner.controlled_regions[0] if partner.controlled_regions else None
    )
    alliance_region = state.regions.get(alliance_region_id) if alliance_region_id else None
    append_supply_note(
        state,
        faction_id=faction.faction_id,
        region_id=alliance_region.region_id if alliance_region else None,
        civ_id=faction.parent_civ_id,
        note=f"alliance_support->{partner.faction_id}",
        pressure_shift="down",
        controlling_faction_ref=faction.faction_id,
    )
    append_project_note(
        state,
        faction_id=faction.faction_id,
        region_id=alliance_region.region_id if alliance_region else None,
        civ_id=faction.parent_civ_id,
        note=f"alliance_backing->{partner.faction_id}",
        pressure_shift="down",
    )

    summary = (
        f"{faction.name} and {partner.name} formed a pragmatic alignment, "
        f"reinforcing their influence within the same civilization."
    )
    civ_refs = [faction.parent_civ_id] if faction.parent_civ_id else []
    event = _build_faction_event(
        state,
        faction,
        "faction_alliance",
        summary,
        civ_refs=civ_refs,
        faction_refs=[faction.faction_id, partner.faction_id],
        cause_tags=["faction_move", "alliance"],
        result_tags=[
            f"allied_with_{partner.faction_id}",
            f"influence_{faction.influence}",
            f"cohesion_{faction.cohesion}",
        ],
        severity="medium",
        consequence_score="medium",
    )
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=partner.faction_id,
        relation_type="allied_with",
        event=event,
        strength="high",
        notes=summary,
        tags=["organization", "alliance"],
        bidirectional=True,
    )
    return event


def _run_power_struggle(
    state: WorldState,
    faction: Faction,
    candidate_regions: list[Region],
    rng: Random,
) -> Event:
    region = rng.choice(candidate_regions)
    rivals = [
        other_id
        for other_id in region.active_factions
        if other_id != faction.faction_id and other_id in state.factions
    ]
    rival = state.factions[rng.choice(rivals)] if rivals else None

    before_tension = region.political_tension
    before_legitimacy = None
    region.political_tension = _UPSHIFT[region.political_tension]
    faction.influence = _UPSHIFT[faction.influence]
    faction.cohesion = _DOWNSHIFT[faction.cohesion] if rng.random() < 0.35 else faction.cohesion
    supply_line = append_supply_note(
        state,
        faction_id=faction.faction_id,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note=f"power_struggle_pressure->{faction.faction_id}",
        status="contested",
        pressure_shift="up",
    )
    append_project_note(
        state,
        faction_id=faction.faction_id,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note=f"power_struggle_pressure->{faction.faction_id}",
        status="contested_buildout",
        pressure_shift="up",
    )

    civ_refs = [region.civ_id] if region.civ_id else []
    result_tags = [f"tension_{before_tension}_to_{region.political_tension}"]
    faction_refs = [faction.faction_id]
    if rival is not None:
        _link_unique(faction.rival_factions, rival.faction_id)
        _link_unique(rival.rival_factions, faction.faction_id)
        faction_refs.append(rival.faction_id)
        summary = (
            f"{faction.name} challenged {rival.name} inside {region.name}, "
            f"pushing local political tension toward {region.political_tension}."
        )
        result_tags.append(f"rivalry_with_{rival.faction_id}")
    else:
        civilization = state.civilizations.get(region.civ_id) if region.civ_id else None
        if civilization is not None:
            before_legitimacy = civilization.legitimacy
            civilization.legitimacy = _DOWNSHIFT[civilization.legitimacy]
            result_tags.append(
                f"legitimacy_{before_legitimacy}_to_{civilization.legitimacy}"
            )
        summary = (
            f"{faction.name} pressed a unilateral claim in {region.name}, "
            f"heightening tension and straining the surrounding order."
        )

    event = _build_faction_event(
        state,
        faction,
        "faction_power_struggle",
        summary,
        region_refs=[region.region_id],
        civ_refs=civ_refs,
        faction_refs=faction_refs,
        cause_tags=["faction_move", "power_struggle"],
        result_tags=result_tags,
        severity="high",
        consequence_score="high" if before_legitimacy is not None else "medium",
    )
    if rival is not None:
        upsert_relation(
            state,
            source_ref=faction.faction_id,
            target_ref=rival.faction_id,
            relation_type="rival_to",
            event=event,
            strength="high",
            notes=summary,
            tags=["organization", "power_struggle"],
            bidirectional=True,
        )
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=region.region_id,
        relation_type="contesting",
        event=event,
        strength="high",
        notes=summary,
        tags=["region_pressure", "organization"],
    )
    if supply_line is not None:
        _mark_supply_dispute(
            state,
            faction=faction,
            supply_line=supply_line,
            event=event,
            notes=summary,
        )
    return event


def _run_resource_reallocation(
    state: WorldState,
    faction: Faction,
    candidate_regions: list[Region],
    rng: Random,
) -> Event:
    region = rng.choice(candidate_regions)
    before_scarcity = region.scarcity
    before_prosperity = region.prosperity
    before_cohesion = faction.cohesion
    region.scarcity = _DOWNSHIFT[region.scarcity]
    region.prosperity = _UPSHIFT[region.prosperity]
    faction.cohesion = _UPSHIFT[faction.cohesion]
    faction.influence_trend = "steady"
    supply_line = _find_supply_line_for_faction(state, faction, region.region_id)
    if supply_line is not None:
        previous_controller = supply_line.controlling_faction_ref
        supply_before_status = supply_line.status
        supply_before_pressure = supply_line.pressure
        supply_line.status = "stable" if region.security != "low" else "fragile"
        supply_line.pressure = _DOWNSHIFT[supply_line.pressure]
        supply_line.controlling_faction_ref = faction.faction_id
        append_supply_note(
            state,
            faction_id=faction.faction_id,
            region_id=region.region_id,
            civ_id=region.civ_id,
            note=f"resource_reallocation->{region.region_id}",
            status=supply_line.status,
            pressure=supply_line.pressure,
            controlling_faction_ref=faction.faction_id,
        )
    else:
        previous_controller = None
        supply_before_status = None
        supply_before_pressure = None

    summary = (
        f"{faction.name} redirected supply and logistics through {region.name}, "
        f"easing scarcity toward {region.scarcity} and lifting prosperity."
    )
    event = _build_faction_event(
        state,
        faction,
        "faction_resource_reallocation",
        summary,
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        cause_tags=["faction_move", "resource_reallocation"],
        result_tags=[
            f"scarcity_{before_scarcity}_to_{region.scarcity}",
            f"prosperity_{before_prosperity}_to_{region.prosperity}",
            f"cohesion_{before_cohesion}_to_{faction.cohesion}",
            *(
                [
                    f"supply_status_{supply_before_status}_to_{supply_line.status}",
                    f"supply_pressure_{supply_before_pressure}_to_{supply_line.pressure}",
                    *(
                        [f"supply_controller_{previous_controller}_to_{supply_line.controlling_faction_ref}"]
                        if previous_controller and previous_controller != supply_line.controlling_faction_ref
                        else []
                    ),
                ]
                if supply_line is not None and supply_before_status is not None and supply_before_pressure is not None
                else []
            ),
        ],
        severity="medium",
        consequence_score="medium",
    )
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=region.region_id,
        relation_type="supply_influence",
        event=event,
        strength="medium",
        notes=summary,
        tags=["resource", "organization"],
    )
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=region.region_id,
        relation_type="stabilizing",
        event=event,
        strength="medium",
        notes=summary,
        tags=["organization", "region_presence", "supply"],
    )
    if supply_line is not None:
        _apply_supply_control_shift(
            state,
            faction=faction,
            supply_line=supply_line,
            event=event,
            notes=summary,
            previous_controller=previous_controller,
        )
        upsert_relation(
            state,
            source_ref=faction.faction_id,
            target_ref=supply_line.supply_id,
            relation_type="supply_influence",
            event=event,
            strength="high" if supply_line.pressure == "high" else "medium",
            notes=summary,
            tags=["organization", "supply", "logistics"],
        )
    return event


def _apply_supply_control_shift(
    state: WorldState,
    *,
    faction: Faction,
    supply_line: SupplyLine,
    event: Event,
    notes: str,
    previous_controller: str | None,
) -> None:
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=supply_line.supply_id,
        relation_type="controls",
        event=event,
        strength="high" if supply_line.status == "stable" else "medium",
        notes=notes,
        tags=["organization", "supply", "control_shift"],
    )
    if previous_controller and previous_controller != faction.faction_id and previous_controller in state.factions:
        upsert_relation(
            state,
            source_ref=previous_controller,
            target_ref=supply_line.supply_id,
            relation_type="contesting",
            event=event,
            strength="medium",
            notes=notes,
            tags=["organization", "supply", "displaced_controller"],
        )


def _mark_supply_dispute(
    state: WorldState,
    *,
    faction: Faction,
    supply_line: SupplyLine,
    event: Event,
    notes: str,
) -> None:
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=supply_line.supply_id,
        relation_type="contesting",
        event=event,
        strength="high" if supply_line.pressure == "high" else "medium",
        notes=notes,
        tags=["organization", "supply", "contest"],
    )
    if supply_line.controlling_faction_ref and supply_line.controlling_faction_ref != faction.faction_id:
        upsert_relation(
            state,
            source_ref=faction.faction_id,
            target_ref=supply_line.controlling_faction_ref,
            relation_type="rival_to",
            event=event,
            strength="medium",
            notes=notes,
            tags=["organization", "supply", "contest"],
            bidirectional=True,
        )


def _find_supply_line_for_faction(
    state: WorldState,
    faction: Faction,
    focal_region_id: str,
) -> SupplyLine | None:
    for supply_line in state.supply_lines.values():
        if (
            supply_line.controlling_faction_ref == faction.faction_id
            or focal_region_id in {supply_line.origin_region_id, supply_line.destination_region_id}
        ):
            if faction.parent_civ_id and faction.parent_civ_id in supply_line.linked_civ_refs:
                return supply_line
    return None


def _run_relic_contest(
    state: WorldState,
    faction: Faction,
    candidate_regions: list[Region],
    rng: Random,
) -> Event:
    relic, region = _choose_relic_target(state, faction, candidate_regions, prefer_external_holder=True)
    if relic is None or region is None:
        return _run_power_struggle(state, faction, candidate_regions, rng)

    previous_holder = relic.holder_ref
    previous_activation = relic.activation_state
    previous_danger = relic.danger
    region.political_tension = _UPSHIFT[region.political_tension]
    region.security = _DOWNSHIFT[region.security]
    relic.activation_state = rng.choice(["contested", "sealed"])
    relic.danger = _UPSHIFT[relic.danger]
    faction.influence = _UPSHIFT[faction.influence]

    other_faction_id = previous_holder if previous_holder in state.factions else None
    if other_faction_id:
        _link_unique(faction.rival_factions, other_faction_id)
        _link_unique(state.factions[other_faction_id].rival_factions, faction.faction_id)
    if relic.relic_type == "megastructure":
        append_project_note(
            state,
            relic_id=relic.relic_id,
            faction_id=faction.faction_id,
            region_id=region.region_id,
            civ_id=region.civ_id,
            note=f"control_contest->{faction.faction_id}",
            status="contested_buildout",
            pressure_shift="up",
        )

    event_type, summary, cause_tag = _build_presence_contest_text(
        faction.name,
        relic,
        region.name,
        relic.activation_state,
    )
    event = _build_faction_event(
        state,
        faction,
        event_type,
        summary,
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        faction_refs=_merge_faction_refs(faction.faction_id, other_faction_id),
        relic_refs=[relic.relic_id],
        cause_tags=["faction_move", cause_tag],
        result_tags=[
            f"holder_{previous_holder}",
            f"activation_{previous_activation}_to_{relic.activation_state}",
            f"danger_{previous_danger}_to_{relic.danger}",
            f"security_{region.security}",
            f"tension_{region.political_tension}",
        ],
        severity="high",
        consequence_score="high",
    )
    _link_relic_event(relic, event)
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=relic.relic_id,
        relation_type="contesting",
        event=event,
        strength="high",
        notes=summary,
        tags=[presence_event_family(relic), "organization"],
    )
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=region.region_id,
        relation_type="flashpoint_actor",
        event=event,
        strength="high",
        notes=summary,
        tags=[presence_event_family(relic), "region_pressure"],
    )
    if other_faction_id:
        upsert_relation(
            state,
            source_ref=faction.faction_id,
            target_ref=other_faction_id,
            relation_type="rival_to",
            event=event,
            strength="high",
            notes=summary,
            tags=[presence_event_family(relic), "organization"],
            bidirectional=True,
        )
    return event


def _run_relic_control(
    state: WorldState,
    faction: Faction,
    candidate_regions: list[Region],
    rng: Random,
) -> Event:
    relic, region = _choose_relic_target(state, faction, candidate_regions, prefer_external_holder=False)
    if relic is None or region is None:
        return _run_resource_reallocation(state, faction, candidate_regions, rng)

    previous_holder = relic.holder_ref
    previous_activation = relic.activation_state
    previous_danger = relic.danger
    previous_security = region.security
    relic.holder_ref = faction.faction_id
    relic.activation_state = "sealed" if rng.random() < 0.6 else "dormant"
    relic.danger = _DOWNSHIFT[relic.danger]
    region.security = _UPSHIFT[region.security]
    faction.influence = _UPSHIFT[faction.influence]
    faction.cohesion = _UPSHIFT[faction.cohesion]
    _ensure_region_control(faction, region)

    if region.civ_id and region.civ_id in state.civilizations:
        civilization = state.civilizations[region.civ_id]
        _link_unique(civilization.key_relics, relic.relic_id)
    if relic.relic_type == "megastructure":
        _assign_project_primary_role(state, relic.relic_id, "sponsor_refs", faction.faction_id)
        append_project_note(
            state,
            relic_id=relic.relic_id,
            faction_id=faction.faction_id,
            region_id=region.region_id,
            civ_id=region.civ_id,
            note=f"control_secured->{faction.faction_id}",
            status="active_buildout" if relic.construction_state in {"rising", "integration", "operational"} else "mobilizing",
            pressure_shift="down",
        )

    event_type, summary, cause_tag = _build_presence_control_text(
        faction.name,
        relic,
        region.name,
        relic.activation_state,
    )
    event = _build_faction_event(
        state,
        faction,
        event_type,
        summary,
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        faction_refs=_merge_faction_refs(faction.faction_id, previous_holder if previous_holder in state.factions else None),
        relic_refs=[relic.relic_id],
        cause_tags=["faction_move", cause_tag],
        result_tags=[
            f"holder_{previous_holder}_to_{relic.holder_ref}",
            f"activation_{previous_activation}_to_{relic.activation_state}",
            f"danger_{previous_danger}_to_{relic.danger}",
            f"security_{previous_security}_to_{region.security}",
        ],
        severity="high" if previous_holder != faction.faction_id else "medium",
        consequence_score="high",
    )
    _link_relic_event(relic, event)
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=relic.relic_id,
        relation_type="controls",
        event=event,
        strength="high",
        notes=summary,
        tags=[presence_event_family(relic), "organization"],
    )
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=region.region_id,
        relation_type="controls",
        event=event,
        strength="medium",
        notes=summary,
        tags=["region", presence_event_family(relic)],
    )
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=region.region_id,
        relation_type="stabilizing",
        event=event,
        strength="medium",
        notes=summary,
        tags=["organization", "region_presence", presence_event_family(relic)],
    )
    _upsert_project_network_relation(
        state,
        faction=faction,
        region=region,
        event=event,
        relation_type="controls",
        strength="high",
        notes=summary,
        tags=["project", presence_event_family(relic), "organization"],
        relic_id=relic.relic_id,
    )
    return event


def _run_project_bid(
    state: WorldState,
    faction: Faction,
    candidate_regions: list[Region],
    rng: Random,
) -> Event:
    relic, region = _choose_megastructure_target(state, candidate_regions)
    if relic is None or region is None:
        return _run_resource_reallocation(state, faction, candidate_regions, rng)

    previous_contractor = relic.contractor_ref
    previous_cohesion = faction.cohesion
    relic.contractor_ref = faction.faction_id
    _assign_project_primary_role(
        state,
        relic.relic_id,
        "contractor_refs",
        faction.faction_id,
        displaced_ref=previous_contractor,
    )
    faction.cohesion = _UPSHIFT[faction.cohesion]
    faction.influence = _UPSHIFT[faction.influence]
    append_project_note(
        state,
        relic_id=relic.relic_id,
        faction_id=faction.faction_id,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note=f"project_bid->{faction.faction_id}",
        status="active_buildout" if relic.construction_state in {"rising", "integration", "operational"} else "mobilizing",
        pressure_shift="up" if previous_contractor and previous_contractor != faction.faction_id else None,
    )
    summary = (
        f"{faction.name} won a fresh construction bid around {relic.name} in {region.name}, "
        f"displacing earlier execution claims and tightening its grip on the site."
    )
    event = _build_faction_event(
        state,
        faction,
        "faction_project_bid",
        summary,
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        faction_refs=_merge_faction_refs(faction.faction_id, previous_contractor if previous_contractor in state.factions else None),
        relic_refs=[relic.relic_id],
        cause_tags=["faction_move", "project_bid"],
        result_tags=[
            f"contractor_{previous_contractor}_to_{relic.contractor_ref}",
            f"cohesion_{previous_cohesion}_to_{faction.cohesion}",
            f"influence_{faction.influence}",
        ],
        severity="medium",
        consequence_score="medium",
    )
    _link_relic_event(relic, event)
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=relic.relic_id,
        relation_type="contracting",
        event=event,
        strength="high",
        notes=summary,
        tags=["megastructure", "organization", "construction"],
    )
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=region.region_id,
        relation_type="operates_in",
        event=event,
        strength="medium",
        notes=summary,
        tags=["organization", "region_presence", "construction"],
    )
    _upsert_project_network_relation(
        state,
        faction=faction,
        region=region,
        event=event,
        relation_type="contracting",
        strength="high",
        notes=summary,
        tags=["project", "organization", "construction"],
        relic_id=relic.relic_id,
    )
    return event


def _run_budget_freeze(
    state: WorldState,
    faction: Faction,
    candidate_regions: list[Region],
    rng: Random,
) -> Event:
    relic, region = _choose_megastructure_target(state, candidate_regions)
    if relic is None or region is None:
        return _run_power_struggle(state, faction, candidate_regions, rng)

    previous_phase = relic.construction_state
    previous_prosperity = region.prosperity
    relic.construction_state = _degrade_project_phase(relic.construction_state)
    region.prosperity = _DOWNSHIFT[region.prosperity]
    append_project_note(
        state,
        relic_id=relic.relic_id,
        faction_id=faction.faction_id,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note=f"budget_freeze->{faction.faction_id}",
        status="stalled_recovery" if relic.construction_state in {"planned", "foundation"} else "contested_buildout",
        pressure_shift="up",
    )
    summary = (
        f"{faction.name} froze budget corridors around {relic.name} in {region.name}, "
        f"dragging the project back toward {relic.construction_state} and souring local expectations."
    )
    event = _build_faction_event(
        state,
        faction,
        "faction_budget_freeze",
        summary,
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        relic_refs=[relic.relic_id],
        cause_tags=["faction_move", "budget_freeze"],
        result_tags=[
            f"construction_{previous_phase}_to_{relic.construction_state}",
            f"prosperity_{previous_prosperity}_to_{region.prosperity}",
        ],
        severity="high",
        consequence_score="high",
    )
    _link_relic_event(relic, event)
    _mark_project_opposition(state, relic.relic_id, faction.faction_id)
    _record_project_obstruction(state, faction, relic, region, event, summary)
    return event


def _run_financing_withdrawal(
    state: WorldState,
    faction: Faction,
    candidate_regions: list[Region],
    rng: Random,
) -> Event:
    relic, region = _choose_megastructure_target(state, candidate_regions)
    if relic is None or region is None:
        return _run_resource_reallocation(state, faction, candidate_regions, rng)

    previous_financier = relic.financier_ref
    previous_security = region.security
    previous_scarcity = region.scarcity
    relic.financier_ref = faction.faction_id
    _assign_project_primary_role(
        state,
        relic.relic_id,
        "financier_refs",
        faction.faction_id,
        displaced_ref=previous_financier,
    )
    region.security = _DOWNSHIFT[region.security]
    region.scarcity = _UPSHIFT[region.scarcity]
    append_project_note(
        state,
        relic_id=relic.relic_id,
        faction_id=faction.faction_id,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note=f"financing_realignment->{faction.faction_id}",
        status="contested_buildout",
        pressure_shift="up",
    )
    summary = (
        f"{faction.name} forced a financing realignment around {relic.name} in {region.name}, "
        f"pulling capital through new hands while exposing the site to supply shocks."
    )
    event = _build_faction_event(
        state,
        faction,
        "faction_financing_withdrawal",
        summary,
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        faction_refs=_merge_faction_refs(faction.faction_id, previous_financier if previous_financier in state.factions else None),
        relic_refs=[relic.relic_id],
        cause_tags=["faction_move", "financing_withdrawal"],
        result_tags=[
            f"financier_{previous_financier}_to_{relic.financier_ref}",
            f"security_{previous_security}_to_{region.security}",
            f"scarcity_{previous_scarcity}_to_{region.scarcity}",
        ],
        severity="high",
        consequence_score="high",
    )
    _link_relic_event(relic, event)
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=relic.relic_id,
        relation_type="financing",
        event=event,
        strength="high",
        notes=summary,
        tags=["megastructure", "organization", "finance"],
    )
    _upsert_project_network_relation(
        state,
        faction=faction,
        region=region,
        event=event,
        relation_type="financing",
        strength="high",
        notes=summary,
        tags=["project", "organization", "finance"],
        relic_id=relic.relic_id,
    )
    return event


def _run_site_accident(
    state: WorldState,
    faction: Faction,
    candidate_regions: list[Region],
    rng: Random,
) -> Event:
    relic, region = _choose_megastructure_target(state, candidate_regions)
    if relic is None or region is None:
        return _run_infiltration(state, faction, candidate_regions, rng)

    previous_security = region.security
    previous_tension = region.political_tension
    previous_phase = relic.construction_state
    region.security = _DOWNSHIFT[region.security]
    region.political_tension = _UPSHIFT[region.political_tension]
    relic.construction_state = _degrade_project_phase(relic.construction_state)
    append_project_note(
        state,
        relic_id=relic.relic_id,
        faction_id=faction.faction_id,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note=f"site_accident_exploited->{faction.faction_id}",
        status="contested_buildout" if relic.construction_state != "planned" else "stalled_recovery",
        pressure_shift="up",
    )
    summary = (
        f"{faction.name} exploited a site accident around {relic.name} in {region.name}, "
        f"turning a construction failure into leverage while the project slipped toward {relic.construction_state}."
    )
    event = _build_faction_event(
        state,
        faction,
        "faction_site_accident",
        summary,
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        relic_refs=[relic.relic_id],
        cause_tags=["faction_move", "site_accident"],
        result_tags=[
            f"construction_{previous_phase}_to_{relic.construction_state}",
            f"security_{previous_security}_to_{region.security}",
            f"tension_{previous_tension}_to_{region.political_tension}",
        ],
        severity="high",
        consequence_score="high",
    )
    _link_relic_event(relic, event)
    _mark_project_opposition(state, relic.relic_id, faction.faction_id)
    _record_project_obstruction(state, faction, relic, region, event, summary)
    return event


def _upsert_project_network_relation(
    state: WorldState,
    *,
    faction: Faction,
    region: Region,
    event: Event,
    relation_type: str,
    strength: str,
    notes: str,
    tags: list[str],
    relic_id: str | None = None,
) -> None:
    project = None
    if relic_id:
        for candidate in state.projects.values():
            if relic_id in candidate.linked_presence_refs:
                project = candidate
                break
    if project is None:
        for candidate in state.projects.values():
            if region.region_id in candidate.linked_regions:
                project = candidate
                break
    if project is None:
        return
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=project.project_id,
        relation_type=relation_type,
        event=event,
        strength=strength,
        notes=notes,
        tags=tags,
    )


def _find_project_for_relic(state: WorldState, relic_id: str) -> object | None:
    for project in state.projects.values():
        if relic_id in project.linked_presence_refs:
            return project
    return None


def _assign_project_primary_role(
    state: WorldState,
    relic_id: str,
    field_name: str,
    faction_id: str,
    *,
    displaced_ref: str | None = None,
) -> None:
    project = _find_project_for_relic(state, relic_id)
    if project is None or faction_id not in state.factions:
        return
    refs = [ref for ref in getattr(project, field_name, []) if ref in state.factions and ref != faction_id]
    setattr(project, field_name, [faction_id, *refs][:6])
    _link_unique(project.linked_factions, faction_id)
    if displaced_ref and displaced_ref != faction_id and displaced_ref in state.factions:
        _mark_project_opposition(state, relic_id, displaced_ref)


def _mark_project_opposition(state: WorldState, relic_id: str, faction_id: str) -> None:
    project = _find_project_for_relic(state, relic_id)
    if project is None or faction_id not in state.factions:
        return
    refs = [ref for ref in project.opposition_refs if ref != faction_id and ref in state.factions]
    project.opposition_refs = [faction_id, *refs][:6]
    _link_unique(project.linked_factions, faction_id)


def _build_faction_event(
    state: WorldState,
    faction: Faction,
    event_type: str,
    summary: str,
    *,
    region_refs: list[str] | None = None,
    civ_refs: list[str] | None = None,
    faction_refs: list[str] | None = None,
    relic_refs: list[str] | None = None,
    cause_tags: list[str] | None = None,
    result_tags: list[str] | None = None,
    severity: str = "medium",
    consequence_score: str = "medium",
) -> Event:
    return Event(
        event_id=state.event_stream.new_event_id(),
        tick=state.current_tick,
        time_granularity=state.current_granularity,
        event_type=event_type,
        event_scope="faction",
        title=f"{faction.name} executed {event_type}",
        summary=summary,
        region_refs=region_refs or [],
        civ_refs=civ_refs or [],
        faction_refs=faction_refs or [faction.faction_id],
        relic_refs=relic_refs or [],
        cause_tags=cause_tags or ["faction_move"],
        result_tags=result_tags or [],
        severity=severity,
        novelty="medium",
        consequence_score=consequence_score,
        narrative_priority="medium",
    )


def _regions_for_civilization(state: WorldState, civ_id: str | None) -> list[Region]:
    if not civ_id:
        return []
    return [region for region in state.regions.values() if region.civ_id == civ_id]


def _ensure_region_control(faction: Faction, region: Region) -> None:
    _link_unique(faction.controlled_regions, region.region_id)
    _link_unique(region.active_factions, faction.faction_id)


def _choose_relic_target(
    state: WorldState,
    faction: Faction,
    candidate_regions: list[Region],
    *,
    prefer_external_holder: bool,
) -> tuple[Relic | None, Region | None]:
    relic_candidates: list[tuple[Relic, Region]] = []
    for region in candidate_regions:
        for relic_id in region.resident_relics:
            relic = state.relics.get(relic_id)
            if relic is None:
                continue
            if prefer_external_holder and relic.holder_ref == faction.faction_id:
                continue
            relic_candidates.append((relic, region))

    if not relic_candidates:
        return None, None
    return relic_candidates[0]


def _choose_megastructure_target(
    state: WorldState,
    candidate_regions: list[Region],
) -> tuple[Relic | None, Region | None]:
    megastructure_candidates: list[tuple[Relic, Region]] = []
    for region in candidate_regions:
        for relic_id in region.resident_relics:
            relic = state.relics.get(relic_id)
            if relic is None or relic.relic_type != "megastructure":
                continue
            megastructure_candidates.append((relic, region))
    if not megastructure_candidates:
        return None, None
    return megastructure_candidates[0]


def _merge_faction_refs(primary: str, secondary: str | None) -> list[str]:
    refs = [primary]
    if secondary and secondary not in refs:
        refs.append(secondary)
    return refs


def _link_relic_event(relic: Relic, event: Event) -> None:
    _link_unique(relic.linked_events, event.event_id)


def _degrade_project_phase(current: str) -> str:
    if current in {"operational", "integration"}:
        return "rising"
    if current == "rising":
        return "foundation"
    return "planned"


def _record_project_obstruction(
    state: WorldState,
    faction: Faction,
    relic: Relic,
    region: Region,
    event: Event,
    summary: str,
) -> None:
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=relic.relic_id,
        relation_type="obstructing",
        event=event,
        strength="high",
        notes=summary,
        tags=["megastructure", "organization", "opposition"],
    )
    upsert_relation(
        state,
        source_ref=faction.faction_id,
        target_ref=region.region_id,
        relation_type="flashpoint_actor",
        event=event,
        strength="medium",
        notes=summary,
        tags=["megastructure", "region_pressure"],
    )


def _build_presence_contest_text(
    faction_name: str,
    relic: Relic,
    region_name: str,
    activation_state: str,
) -> tuple[str, str, str]:
    family = presence_event_family(relic)
    if family == "megastructure":
        site_phrase = (
            "the active construction corridor of"
            if is_contemporary_megastructure(relic)
            else "the operating spine of"
        )
        return (
            "faction_megastructure_stall",
            f"{faction_name} disrupted {site_phrase} {relic.name} in {region_name}, "
            f"forcing the megastructure into a {activation_state} posture and destabilizing the surrounding district.",
            "megastructure_stall",
        )
    if family == "autonomous_system":
        return (
            "faction_protocol_breach",
            f"{faction_name} breached the control surface of {relic.name} in {region_name}, "
            f"driving the protocol into a {activation_state} state and unsettling local governance.",
            "protocol_breach",
        )
    if family == "sealed_archive":
        return (
            "faction_archive_breach",
            f"{faction_name} breached the sealed layers around {relic.name} in {region_name}, "
            f"turning buried records into a live source of political instability.",
            "archive_breach",
        )
    if family == "anomalous_lifeform":
        return (
            "faction_lifeform_provocation",
            f"{faction_name} provoked the movement pattern of {relic.name} in {region_name}, "
            f"driving the lifeform into a {activation_state} state and worsening local biosecurity pressure.",
            "lifeform_provocation",
        )
    return (
        "faction_relic_contest",
        f"{faction_name} moved against control of {relic.name} in {region_name}, "
        f"driving the relic into a {activation_state} state and destabilizing the area.",
        "relic_contest",
    )


def _build_presence_control_text(
    faction_name: str,
    relic: Relic,
    region_name: str,
    activation_state: str,
) -> tuple[str, str, str]:
    family = presence_event_family(relic)
    if family == "megastructure":
        site_phrase = (
            "secured the live build authority of"
            if is_contemporary_megastructure(relic)
            else "reasserted operating authority over"
        )
        return (
            "faction_megastructure_phase_advance",
            f"{faction_name} {site_phrase} {relic.name} in {region_name}, "
            f"tightening site control and pushing the megastructure toward a {activation_state} alignment.",
            "megastructure_phase_advance",
        )
    if family == "autonomous_system":
        return (
            "faction_protocol_takeover",
            f"{faction_name} seized execution authority over {relic.name} in {region_name}, "
            f"tightening security while forcing the protocol into a {activation_state} posture.",
            "protocol_takeover",
        )
    if family == "sealed_archive":
        return (
            "faction_archive_suppression",
            f"{faction_name} secured sealed custody over {relic.name} in {region_name}, "
            f"containing disclosure pathways and forcing the archive into a {activation_state} posture.",
            "archive_suppression",
        )
    if family == "anomalous_lifeform":
        return (
            "faction_lifeform_containment",
            f"{faction_name} established a hard containment perimeter around {relic.name} in {region_name}, "
            f"tightening site security while forcing the lifeform into a {activation_state} posture.",
            "lifeform_containment",
        )
    return (
        "faction_relic_control",
        f"{faction_name} secured operational control over {relic.name} in {region_name}, "
        f"tightening security and forcing the relic into a {activation_state} posture.",
        "relic_control",
    )


def _link_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _unlink_if_present(items: list[str], value: str) -> None:
    if value in items:
        items.remove(value)
