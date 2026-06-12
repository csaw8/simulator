"""Action resolution and conflict adjudication."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.agents.fallback import Intent
from src.events.models import Event
from src.world.presence import is_contemporary_megastructure, presence_event_family
from src.world.network_updates import append_project_note, append_supply_note
from src.world.relations import upsert_relation
from src.world.relic import Relic
from src.world.state import WorldState

_UPSHIFT = {"low": "medium", "medium": "high", "high": "high"}
_DOWNSHIFT = {"high": "medium", "medium": "low", "low": "low"}


@dataclass(slots=True)
class ResolutionResult:
    """Resolved consequences for a batch of intents."""

    events: list[Event] = field(default_factory=list)
    resolved_character_ids: list[str] = field(default_factory=list)


def resolve_intents(world: WorldState, intents: list[Intent]) -> ResolutionResult:
    """Apply intent consequences to the world and emit character-driven events."""
    result = ResolutionResult()
    for intent in intents:
        character = world.characters[intent.character_id]
        region = world.regions[intent.target_ref]
        event = _resolve_single_intent(world, character.char_id, region.region_id, intent)
        result.events.append(event)
        result.resolved_character_ids.append(character.char_id)
    return result


def _resolve_single_intent(
    world: WorldState,
    character_id: str,
    region_id: str,
    intent: Intent,
) -> Event:
    character = world.characters[character_id]
    _relocate_character_if_needed(world, character, region_id)
    region = world.regions[region_id]

    if intent.intent_type == "stabilize_supply":
        region.scarcity = _DOWNSHIFT[region.scarcity]
        region.security = _UPSHIFT[region.security]
        event_type = "character_supply_action"
        summary = (
            f"{character.name} moved to stabilize supply conditions in {region.name}, "
            f"easing scarcity toward {region.scarcity}."
        )
        result_tags = [f"scarcity_{region.scarcity}", f"security_{region.security}"]
    elif intent.intent_type == "manage_unrest":
        region.political_tension = _DOWNSHIFT[region.political_tension]
        region.security = _UPSHIFT[region.security]
        event_type = "character_unrest_action"
        summary = (
            f"{character.name} tried to contain unrest in {region.name}, "
            f"pulling political tension toward {region.political_tension}."
        )
        result_tags = [
            f"tension_{region.political_tension}",
            f"security_{region.security}",
        ]
    elif intent.intent_type in {"broker_power_shift", "expand_influence", "improve_position"}:
        region.political_tension = _UPSHIFT[region.political_tension]
        character.notoriety = _UPSHIFT.get(character.notoriety, "high")
        event_type = "character_power_play"
        summary = (
            f"{character.name} maneuvered for influence in {region.name}, "
            f"raising the local tension toward {region.political_tension}."
        )
        result_tags = [
            f"tension_{region.political_tension}",
            f"notoriety_{character.notoriety}",
        ]
    elif intent.intent_type == "seize_supply_leverage":
        region.scarcity = _DOWNSHIFT[region.scarcity]
        region.political_tension = _UPSHIFT[region.political_tension]
        character.notoriety = _UPSHIFT.get(character.notoriety, "high")
        event_type = "character_supply_power_play"
        summary = (
            f"{character.name} consolidated supply leverage in {region.name}, "
            f"reducing scarcity but heightening political tension."
        )
        result_tags = [
            f"scarcity_{region.scarcity}",
            f"tension_{region.political_tension}",
        ]
    elif intent.intent_type == "secure_relic_access":
        relic = _select_region_relic(world, region.region_id)
        region.security = _UPSHIFT[region.security]
        region.political_tension = _UPSHIFT[region.political_tension]
        character.notoriety = _UPSHIFT.get(character.notoriety, "high")
        event_type = "character_relic_access_action"
        if relic is not None:
            previous_holder = relic.holder_ref
            previous_state = relic.activation_state
            relic.holder_ref = character.affiliation[0] if character.affiliation else relic.holder_ref
            relic.activation_state = "sealed" if region.security != "low" else "contested"
            event_type, summary = _build_presence_access_text(
                character.name,
                relic,
                region.name,
            )
            result_tags = [
                f"security_{region.security}",
                f"tension_{region.political_tension}",
                f"holder_{previous_holder}_to_{relic.holder_ref}",
                f"activation_{previous_state}_to_{relic.activation_state}",
            ]
        else:
            summary = (
                f"{character.name} imposed new access controls across {region.name}, "
                f"treating the district like a relic flashpoint."
            )
            result_tags = [f"security_{region.security}", f"tension_{region.political_tension}"]
    elif intent.intent_type == "contain_relic_fallout":
        relic = _select_region_relic(world, region.region_id)
        region.security = _UPSHIFT[region.security]
        region.political_tension = _DOWNSHIFT[region.political_tension]
        event_type = "character_relic_containment_action"
        if relic is not None:
            previous_danger = relic.danger
            previous_state = relic.activation_state
            relic.danger = _DOWNSHIFT[relic.danger]
            relic.activation_state = "sealed"
            event_type, summary = _build_presence_containment_text(
                character.name,
                relic,
                region.name,
            )
            result_tags = [
                f"security_{region.security}",
                f"tension_{region.political_tension}",
                f"danger_{previous_danger}_to_{relic.danger}",
                f"activation_{previous_state}_to_{relic.activation_state}",
            ]
        else:
            summary = (
                f"{character.name} tried to contain unrest and spillover risks in {region.name} "
                f"after a suspected relic disturbance."
            )
            result_tags = [f"security_{region.security}", f"tension_{region.political_tension}"]
    elif intent.intent_type == "track_lifeform_spread":
        relic = _select_region_relic_by_type(world, region.region_id, "anomalous_lifeform")
        region.security = _UPSHIFT[region.security]
        event_type = "character_lifeform_tracking_action"
        if relic is not None:
            summary = (
                f"{character.name} tracked the spread routes around {relic.name} in {region.name}, "
                f"trying to predict the next movement front before it widened."
            )
            result_tags = [f"security_{region.security}", f"tracked_{relic.relic_id}"]
        else:
            summary = f"{character.name} mapped likely anomalous spillover routes in {region.name}."
            result_tags = [f"security_{region.security}"]
    elif intent.intent_type == "seal_migration_corridor":
        relic = _select_region_relic_by_type(world, region.region_id, "anomalous_lifeform")
        region.security = _UPSHIFT[region.security]
        region.scarcity = _UPSHIFT[region.scarcity]
        event_type = "character_migration_corridor_seal"
        if relic is not None:
            previous_state = relic.activation_state
            relic.activation_state = "sealed"
            summary = (
                f"{character.name} sealed movement corridors around {relic.name} in {region.name}, "
                f"trying to lock the anomalous front into a narrower envelope."
            )
            result_tags = [
                f"security_{region.security}",
                f"scarcity_{region.scarcity}",
                f"activation_{previous_state}_to_{relic.activation_state}",
            ]
        else:
            summary = f"{character.name} sealed exposed transit seams in {region.name} to slow anomalous spillover."
            result_tags = [f"security_{region.security}", f"scarcity_{region.scarcity}"]
    elif intent.intent_type == "secure_project_budget":
        relic = _select_region_relic_by_type(world, region.region_id, "megastructure")
        region.prosperity = _UPSHIFT[region.prosperity]
        region.security = _UPSHIFT[region.security]
        event_type = "character_project_budget_action"
        if relic is not None:
            summary = (
                f"{character.name} stabilized the budget chain around {relic.name} in {region.name}, "
                f"keeping the project front from slipping deeper into paralysis."
            )
            result_tags = [f"prosperity_{region.prosperity}", f"security_{region.security}"]
        else:
            summary = f"{character.name} stabilized the funding chain behind a stressed project front in {region.name}."
            result_tags = [f"prosperity_{region.prosperity}", f"security_{region.security}"]
    elif intent.intent_type == "contest_project_contract":
        relic = _select_region_relic_by_type(world, region.region_id, "megastructure")
        region.political_tension = _UPSHIFT[region.political_tension]
        event_type = "character_project_contract_contest"
        if relic is not None:
            previous_contractor = relic.contractor_ref
            relic.contractor_ref = character.affiliation[0] if character.affiliation else relic.contractor_ref
            if character.affiliation:
                _assign_project_primary_role_from_character(
                    world,
                    relic.relic_id,
                    "contractor_refs",
                    character.affiliation[0],
                    displaced_ref=previous_contractor,
                )
            summary = (
                f"{character.name} contested execution control around {relic.name} in {region.name}, "
                f"pressing to shift the project contract toward aligned hands."
            )
            result_tags = [
                f"tension_{region.political_tension}",
                f"contractor_{previous_contractor}_to_{relic.contractor_ref}",
            ]
        else:
            summary = f"{character.name} contested local execution authority over a project front in {region.name}."
            result_tags = [f"tension_{region.political_tension}"]
    elif intent.intent_type == "redirect_project_financing":
        relic = _select_region_relic_by_type(world, region.region_id, "megastructure")
        region.security = _UPSHIFT[region.security]
        region.scarcity = _DOWNSHIFT[region.scarcity]
        event_type = "character_project_financing_redirect"
        if relic is not None:
            previous_financier = relic.financier_ref
            relic.financier_ref = character.affiliation[0] if character.affiliation else relic.financier_ref
            if character.affiliation:
                _assign_project_primary_role_from_character(
                    world,
                    relic.relic_id,
                    "financier_refs",
                    character.affiliation[0],
                    displaced_ref=previous_financier,
                )
            summary = (
                f"{character.name} redirected the financing channels around {relic.name} in {region.name}, "
                f"trying to pull the project back under friendlier capital discipline."
            )
            result_tags = [
                f"security_{region.security}",
                f"scarcity_{region.scarcity}",
                f"financier_{previous_financier}_to_{relic.financier_ref}",
            ]
        else:
            summary = f"{character.name} rerouted stressed project capital flows in {region.name}."
            result_tags = [f"security_{region.security}", f"scarcity_{region.scarcity}"]
    elif intent.intent_type == "suppress_site_accident_fallout":
        relic = _select_region_relic_by_type(world, region.region_id, "megastructure")
        region.security = _UPSHIFT[region.security]
        region.political_tension = _DOWNSHIFT[region.political_tension]
        event_type = "character_site_accident_suppression"
        if relic is not None:
            if character.affiliation:
                _assign_project_primary_role_from_character(
                    world,
                    relic.relic_id,
                    "sponsor_refs",
                    character.affiliation[0],
                )
            summary = (
                f"{character.name} suppressed the fallout from a site failure around {relic.name} in {region.name}, "
                f"limiting panic and denying rivals an easy opening."
            )
            result_tags = [f"security_{region.security}", f"tension_{region.political_tension}"]
        else:
            summary = f"{character.name} suppressed the fallout from a project accident in {region.name}."
            result_tags = [f"security_{region.security}", f"tension_{region.political_tension}"]
    else:
        event_type = "character_action"
        summary = f"{character.name} acted in {region.name}."
        result_tags = ["generic_action"]

    event = Event(
        event_id=world.event_stream.new_event_id(),
        tick=world.current_tick,
        time_granularity=world.current_granularity,
        event_type=event_type,
        event_scope="character",
        title=f"{character.name} acted in {region.name}",
        summary=summary,
        region_refs=[region.region_id],
        civ_refs=[region.civ_id] if region.civ_id else [],
        actor_refs=[character.char_id],
        faction_refs=character.affiliation,
        relic_refs=[relic.relic_id] if "relic" in locals() and relic is not None else [],
        cause_tags=[intent.intent_type, "resolved_intent"],
        result_tags=result_tags,
        severity="medium" if intent.urgency < 0.8 else "high",
        novelty="medium" if character.character_level == "L3" else "low",
        consequence_score="medium",
        narrative_priority="medium" if character.character_level == "L3" else "low",
    )
    if "relic" in locals() and relic is not None:
        _link_relic_event(relic, event)
        _update_relic_relations(world, character.char_id, region.region_id, relic, intent.intent_type, event)
    _write_midlayer_character_impact(
        world,
        character_id=character.char_id,
        region_id=region.region_id,
        civ_id=region.civ_id,
        faction_id=character.affiliation[0] if character.affiliation else None,
        intent_type=intent.intent_type,
    )
    _update_character_region_relation(world, character.char_id, region.region_id, intent.intent_type, event)
    _update_character_supply_relations(
        world,
        character=character,
        region_id=region.region_id,
        intent_type=intent.intent_type,
        event=event,
    )
    return event


def _relocate_character_if_needed(
    world: WorldState,
    character: object,
    target_region_id: str,
) -> None:
    if character.current_region_id == target_region_id:
        return
    if character.current_region_id in world.regions:
        previous_region = world.regions[character.current_region_id]
        if character.char_id in previous_region.active_characters:
            previous_region.active_characters.remove(character.char_id)
    character.current_region_id = target_region_id
    target_region = world.regions[target_region_id]
    if character.char_id not in target_region.active_characters:
        target_region.active_characters.append(character.char_id)


def _select_region_relic(world: WorldState, region_id: str) -> Relic | None:
    region = world.regions[region_id]
    for relic_id in region.resident_relics:
        relic = world.relics.get(relic_id)
        if relic is not None:
            return relic
    return None


def _select_region_relic_by_type(world: WorldState, region_id: str, relic_type: str) -> Relic | None:
    region = world.regions[region_id]
    for relic_id in region.resident_relics:
        relic = world.relics.get(relic_id)
        if relic is not None and relic.relic_type == relic_type:
            return relic
    return None


def _link_relic_event(relic: Relic, event: Event) -> None:
    if event.event_id not in relic.linked_events:
        relic.linked_events.append(event.event_id)


def _build_presence_access_text(
    character_name: str,
    relic: Relic,
    region_name: str,
) -> tuple[str, str]:
    family = presence_event_family(relic)
    if family == "megastructure":
        context = (
            "a live megaproject site"
            if is_contemporary_megastructure(relic)
            else "a contested legacy infrastructure spine"
        )
        return (
            "character_megastructure_access_action",
            f"{character_name} moved to secure operating access around {relic.name} in {region_name}, "
            f"treating the megastructure as {context}.",
        )
    if family == "autonomous_system":
        return (
            "character_protocol_access_action",
            f"{character_name} moved to secure execution access around {relic.name} in {region_name}, "
            f"tightening control over a contested protocol surface.",
        )
    if family == "sealed_archive":
        return (
            "character_archive_access_action",
            f"{character_name} moved to secure disclosure access around {relic.name} in {region_name}, "
            f"trying to control which buried records could still reshape the local order.",
        )
    if family == "anomalous_lifeform":
        return (
            "character_lifeform_tracking_action",
            f"{character_name} moved to track and channel the behavior of {relic.name} in {region_name}, "
            f"treating the lifeform as an unstable mobile threat.",
        )
    return (
        "character_relic_access_action",
        f"{character_name} moved to secure access around {relic.name} in {region_name}, "
        f"tightening control while pressure around the relic remained high.",
    )


def _build_presence_containment_text(
    character_name: str,
    relic: Relic,
    region_name: str,
) -> tuple[str, str]:
    family = presence_event_family(relic)
    if family == "megastructure":
        context = (
            "the construction envelope"
            if is_contemporary_megastructure(relic)
            else "the reactivated operating shell"
        )
        return (
            "character_megastructure_stabilization_action",
            f"{character_name} worked to stabilize {context} of {relic.name} in {region_name}, "
            f"reducing structural danger and suppressing local panic.",
        )
    if family == "autonomous_system":
        return (
            "character_protocol_containment_action",
            f"{character_name} worked to contain runaway behavior around {relic.name} in {region_name}, "
            f"reducing immediate protocol danger and lowering local panic.",
        )
    if family == "sealed_archive":
        return (
            "character_archive_containment_action",
            f"{character_name} worked to contain disclosure fallout around {relic.name} in {region_name}, "
            f"reducing immediate political shock and damping local panic.",
        )
    if family == "anomalous_lifeform":
        return (
            "character_lifeform_containment_action",
            f"{character_name} worked to compress the roaming envelope of {relic.name} in {region_name}, "
            f"reducing immediate predation risk and calming local panic.",
        )
    return (
        "character_relic_containment_action",
        f"{character_name} worked to contain fallout around {relic.name} in {region_name}, "
        f"reducing immediate danger and lowering local panic.",
    )


def _update_character_region_relation(
    world: WorldState,
    character_id: str,
    region_id: str,
    intent_type: str,
    event: Event,
) -> None:
    relation_type = "operates_in"
    if intent_type in {"broker_power_shift", "expand_influence", "improve_position", "contest_project_contract"}:
        relation_type = "influencing"
    elif intent_type in {
        "manage_unrest",
        "contain_relic_fallout",
        "seal_migration_corridor",
        "suppress_site_accident_fallout",
        "secure_project_budget",
    }:
        relation_type = "stabilizing"
    upsert_relation(
        world,
        source_ref=character_id,
        target_ref=region_id,
        relation_type=relation_type,
        event=event,
        strength="medium" if event.severity == "medium" else "high",
        notes=event.summary,
        tags=["character", intent_type],
    )


def _update_relic_relations(
    world: WorldState,
    character_id: str,
    region_id: str,
    relic: Relic,
    intent_type: str,
    event: Event,
) -> None:
    if intent_type in {"secure_relic_access", "contest_project_contract"}:
        relation_type = "seeking_control"
    elif intent_type in {"contain_relic_fallout", "seal_migration_corridor", "suppress_site_accident_fallout"}:
        relation_type = "containing"
    elif intent_type in {"secure_project_budget", "redirect_project_financing"}:
        relation_type = "supporting"
    elif intent_type == "track_lifeform_spread":
        relation_type = "tracking"
    else:
        relation_type = "engaged_with"

    upsert_relation(
        world,
        source_ref=character_id,
        target_ref=relic.relic_id,
        relation_type=relation_type,
        event=event,
        strength="high" if event.severity == "high" else "medium",
        notes=event.summary,
        tags=["character", "relic", intent_type],
    )
    upsert_relation(
        world,
        source_ref=relic.relic_id,
        target_ref=region_id,
        relation_type="anchored_in",
        event=event,
        strength="high",
        notes=event.summary,
        tags=["relic", "region"],
    )


def _assign_project_primary_role_from_character(
    world: WorldState,
    relic_id: str,
    field_name: str,
    faction_id: str,
    *,
    displaced_ref: str | None = None,
) -> None:
    if faction_id not in world.factions:
        return
    project = None
    for candidate in world.projects.values():
        if relic_id in candidate.linked_presence_refs:
            project = candidate
            break
    if project is None:
        return
    refs = [ref for ref in getattr(project, field_name, []) if ref in world.factions and ref != faction_id]
    setattr(project, field_name, [faction_id, *refs][:6])
    if faction_id not in project.linked_factions:
        project.linked_factions.append(faction_id)
    if displaced_ref and displaced_ref != faction_id and displaced_ref in world.factions:
        opposition = [ref for ref in project.opposition_refs if ref in world.factions and ref != displaced_ref]
        project.opposition_refs = [displaced_ref, *opposition][:6]
        if displaced_ref not in project.linked_factions:
            project.linked_factions.append(displaced_ref)


def _update_character_supply_relations(
    world: WorldState,
    *,
    character: object,
    region_id: str,
    intent_type: str,
    event: Event,
) -> None:
    if intent_type not in {"stabilize_supply", "seize_supply_leverage"}:
        return
    faction_id = character.affiliation[0] if character.affiliation else None
    if not faction_id or faction_id not in world.factions:
        return
    supply_line = None
    for candidate in world.supply_lines.values():
        if region_id in {candidate.origin_region_id, candidate.destination_region_id}:
            if world.factions[faction_id].parent_civ_id in candidate.linked_civ_refs:
                supply_line = candidate
                break
    if supply_line is None:
        return
    previous_controller = supply_line.controlling_faction_ref
    if intent_type == "stabilize_supply":
        supply_line.status = "stable" if supply_line.pressure != "high" else "fragile"
        supply_line.controlling_faction_ref = faction_id
        upsert_relation(
            world,
            source_ref=faction_id,
            target_ref=supply_line.supply_id,
            relation_type="controls",
            event=event,
            strength="medium",
            notes=event.summary,
            tags=["character", "supply", "stabilization"],
        )
        upsert_relation(
            world,
            source_ref=faction_id,
            target_ref=supply_line.supply_id,
            relation_type="supply_influence",
            event=event,
            strength="medium",
            notes=event.summary,
            tags=["character", "supply", "stabilization"],
        )
    else:
        supply_line.status = "contested"
        supply_line.controlling_faction_ref = faction_id
        upsert_relation(
            world,
            source_ref=faction_id,
            target_ref=supply_line.supply_id,
            relation_type="contesting",
            event=event,
            strength="high",
            notes=event.summary,
            tags=["character", "supply", "leverage"],
        )
        upsert_relation(
            world,
            source_ref=faction_id,
            target_ref=supply_line.supply_id,
            relation_type="controls",
            event=event,
            strength="medium",
            notes=event.summary,
            tags=["character", "supply", "leverage"],
        )
    if previous_controller and previous_controller != faction_id and previous_controller in world.factions:
        upsert_relation(
            world,
            source_ref=previous_controller,
            target_ref=supply_line.supply_id,
            relation_type="contesting",
            event=event,
            strength="medium",
            notes=event.summary,
            tags=["supply", "displaced_controller"],
        )


def _write_midlayer_character_impact(
    world: WorldState,
    *,
    character_id: str,
    region_id: str,
    civ_id: str | None,
    faction_id: str | None,
    intent_type: str,
) -> None:
    if intent_type == "secure_project_budget":
        project = append_project_note(
            world,
            note=f"character_budget_secured->{character_id}",
            faction_id=faction_id,
            region_id=region_id,
            civ_id=civ_id,
            pressure_shift="down",
        )
        if project is not None and character_id not in project.linked_characters:
            project.linked_characters.append(character_id)
        return
    if intent_type == "contest_project_contract":
        project = append_project_note(
            world,
            note=f"character_contract_contested->{character_id}",
            faction_id=faction_id,
            region_id=region_id,
            civ_id=civ_id,
            pressure_shift="up",
        )
        if project is not None and character_id not in project.linked_characters:
            project.linked_characters.append(character_id)
        return
    if intent_type == "redirect_project_financing":
        project = append_project_note(
            world,
            note=f"character_financing_redirected->{character_id}",
            faction_id=faction_id,
            region_id=region_id,
            civ_id=civ_id,
            pressure_shift="down",
        )
        if project is not None and character_id not in project.linked_characters:
            project.linked_characters.append(character_id)
        return
    if intent_type == "suppress_site_accident_fallout":
        project = append_project_note(
            world,
            note=f"character_accident_suppressed->{character_id}",
            faction_id=faction_id,
            region_id=region_id,
            civ_id=civ_id,
            pressure_shift="down",
        )
        if project is not None and character_id not in project.linked_characters:
            project.linked_characters.append(character_id)
        return
    if intent_type == "stabilize_supply":
        append_supply_note(
            world,
            note=f"character_supply_stabilized->{character_id}",
            faction_id=faction_id,
            region_id=region_id,
            civ_id=civ_id,
            pressure_shift="down",
            controlling_faction_ref=faction_id,
        )
        return
    if intent_type == "seize_supply_leverage":
        append_supply_note(
            world,
            note=f"character_supply_leverage->{character_id}",
            faction_id=faction_id,
            region_id=region_id,
            civ_id=civ_id,
            pressure_shift="up",
            controlling_faction_ref=faction_id,
        )
