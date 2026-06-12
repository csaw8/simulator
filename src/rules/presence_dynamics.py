"""Autonomous exceptional-presence evolution rules."""

from __future__ import annotations

from random import Random

from src.events.models import Event
from src.world.network_updates import append_project_note
from src.world.presence import megastructure_origin_mode, presence_event_family
from src.world.relations import upsert_relation
from src.world.region import Region
from src.world.relic import Relic
from src.world.state import WorldState

_UPSHIFT = {"low": "medium", "medium": "high", "high": "high"}
_DOWNSHIFT = {"high": "medium", "medium": "low", "low": "low"}


def advance_presence_state(state: WorldState, rng: Random) -> list[Event]:
    """Advance exceptional presences independently of direct human action."""
    events: list[Event] = []
    for relic in state.relics.values():
        family = presence_event_family(relic)
        if family == "megastructure":
            event = _advance_megastructure(state, relic, rng)
        elif family == "autonomous_system":
            event = _advance_protocol(state, relic, rng)
        elif family == "sealed_archive":
            event = _advance_archive(state, relic, rng)
        elif family == "anomalous_lifeform":
            event = _advance_lifeform(state, relic, rng)
        else:
            event = None
        if event is not None:
            events.append(event)
    return events


def _advance_megastructure(
    state: WorldState,
    relic: Relic,
    rng: Random,
) -> Event | None:
    region = state.regions[relic.current_region_id]
    origin_mode = megastructure_origin_mode(relic)

    if origin_mode == "legacy":
        return _advance_legacy_megastructure(state, relic, region, rng)
    if origin_mode == "contemporary":
        return _advance_contemporary_megastructure(state, relic, region, rng)
    return _advance_hybrid_megastructure(state, relic, region, rng)

    return None


def _advance_legacy_megastructure(
    state: WorldState,
    relic: Relic,
    region: Region,
    rng: Random,
) -> Event | None:
    if region.security == "high" and region.scarcity != "high" and rng.random() < 0.30:
        previous_state = relic.activation_state
        previous_phase = relic.construction_state
        previous_prosperity = region.prosperity
        relic.activation_state = "sealed"
        relic.construction_state = _advance_construction_state(
            relic.construction_state,
            ["degraded", "reactivating", "operational"],
        )
        region.prosperity = _UPSHIFT[region.prosperity]
        region.infrastructure = _UPSHIFT[region.infrastructure]
        event_type = (
            "megastructure_reactivation"
            if previous_phase != "operational" and relic.construction_state == "reactivating"
            else "megastructure_phase_advance"
        )
        summary = (
            f"{relic.name} recovered part of its buried operating spine in {region.name}, "
            f"pulling the legacy structure toward {relic.construction_state} and lifting nearby infrastructure."
        )
        event = _build_presence_event(
            state,
            relic,
            event_type=event_type,
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"construction_{previous_phase}_to_{relic.construction_state}",
                f"prosperity_{previous_prosperity}_to_{region.prosperity}",
                f"infrastructure_{region.infrastructure}",
            ],
            severity="medium",
            consequence_score="high",
        )
        _record_project_network_progress(state, relic, region, event_type, "support")
        _record_megastructure_support_relations(state, relic, region, event, summary)
        _link_presence_event(relic, event)
        return event

    if _megastructure_under_stress(region) and rng.random() < 0.36:
        previous_state = relic.activation_state
        previous_phase = relic.construction_state
        previous_security = region.security
        previous_scarcity = region.scarcity
        relic.activation_state = "contested"
        relic.construction_state = _degrade_construction_state(
            relic.construction_state,
            ["operational", "reactivating", "degraded"],
        )
        region.security = _DOWNSHIFT[region.security]
        region.scarcity = _UPSHIFT[region.scarcity]
        summary = (
            f"{relic.name} shed another layer of stability in {region.name}, "
            f"dragging the legacy structure toward {relic.construction_state} and raising local strain."
        )
        event = _build_presence_event(
            state,
            relic,
            event_type="megastructure_stall",
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"construction_{previous_phase}_to_{relic.construction_state}",
                f"security_{previous_security}_to_{region.security}",
                f"scarcity_{previous_scarcity}_to_{region.scarcity}",
            ],
            severity="high",
            consequence_score="high",
        )
        _record_project_network_progress(state, relic, region, "megastructure_stall", "strain")
        _record_megastructure_strain_relations(state, relic, region, event, summary)
        _link_presence_event(relic, event)
        return event
    return None


def _advance_contemporary_megastructure(
    state: WorldState,
    relic: Relic,
    region: Region,
    rng: Random,
) -> Event | None:
    if region.security == "high" and region.scarcity != "high" and rng.random() < 0.34:
        previous_state = relic.activation_state
        previous_phase = relic.construction_state
        previous_prosperity = region.prosperity
        previous_infrastructure = region.infrastructure
        relic.construction_state = _advance_construction_state(
            relic.construction_state,
            ["planned", "foundation", "rising", "integration", "operational"],
        )
        relic.activation_state = "sealed" if relic.construction_state in {"integration", "operational"} else "dormant"
        region.infrastructure = _UPSHIFT[region.infrastructure]
        if relic.construction_state in {"integration", "operational"}:
            region.prosperity = _UPSHIFT[region.prosperity]
        event_type = _contemporary_megastructure_event_type(previous_phase, relic.construction_state)
        summary = _contemporary_megastructure_summary(
            relic.name,
            region.name,
            previous_phase,
            relic.construction_state,
        )
        event = _build_presence_event(
            state,
            relic,
            event_type=event_type,
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"construction_{previous_phase}_to_{relic.construction_state}",
                f"infrastructure_{previous_infrastructure}_to_{region.infrastructure}",
                f"prosperity_{previous_prosperity}_to_{region.prosperity}",
            ],
            severity="medium",
            consequence_score="high",
        )
        _record_project_network_progress(state, relic, region, event_type, "support")
        _record_megastructure_support_relations(state, relic, region, event, summary)
        _link_presence_event(relic, event)
        return event

    if _megastructure_under_stress(region) and rng.random() < 0.40:
        previous_state = relic.activation_state
        previous_phase = relic.construction_state
        previous_security = region.security
        previous_scarcity = region.scarcity
        relic.activation_state = "contested"
        relic.construction_state = _degrade_construction_state(
            relic.construction_state,
            ["operational", "integration", "rising", "foundation", "planned"],
        )
        region.security = _DOWNSHIFT[region.security]
        region.scarcity = _UPSHIFT[region.scarcity]
        event_type = (
            "megastructure_budget_crisis"
            if previous_phase in {"planned", "foundation", "rising", "integration"}
            else "megastructure_stall"
        )
        summary = (
            f"{relic.name} hit a construction crisis in {region.name}, "
            f"knocking the project back toward {relic.construction_state} while security and supply conditions worsened."
        )
        event = _build_presence_event(
            state,
            relic,
            event_type=event_type,
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"construction_{previous_phase}_to_{relic.construction_state}",
                f"security_{previous_security}_to_{region.security}",
                f"scarcity_{previous_scarcity}_to_{region.scarcity}",
            ],
            severity="high",
            consequence_score="high",
        )
        _record_project_network_progress(state, relic, region, event_type, "strain")
        _record_megastructure_strain_relations(state, relic, region, event, summary)
        _link_presence_event(relic, event)
        return event
    return None


def _advance_hybrid_megastructure(
    state: WorldState,
    relic: Relic,
    region: Region,
    rng: Random,
) -> Event | None:
    if region.security == "high" and region.scarcity != "high" and rng.random() < 0.32:
        previous_state = relic.activation_state
        previous_phase = relic.construction_state
        previous_prosperity = region.prosperity
        previous_infrastructure = region.infrastructure
        relic.construction_state = _advance_construction_state(
            relic.construction_state,
            ["degraded", "retrofit", "integration", "operational"],
        )
        relic.activation_state = "sealed" if relic.construction_state != "degraded" else "dormant"
        region.infrastructure = _UPSHIFT[region.infrastructure]
        if relic.construction_state in {"integration", "operational"}:
            region.prosperity = _UPSHIFT[region.prosperity]
        event_type = (
            "megastructure_reactivation"
            if previous_phase == "degraded"
            else "megastructure_phase_advance"
        )
        summary = (
            f"{relic.name} advanced as a rebuild project in {region.name}, "
            f"binding old structure to new industry and pushing the site toward {relic.construction_state}."
        )
        event = _build_presence_event(
            state,
            relic,
            event_type=event_type,
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"construction_{previous_phase}_to_{relic.construction_state}",
                f"infrastructure_{previous_infrastructure}_to_{region.infrastructure}",
                f"prosperity_{previous_prosperity}_to_{region.prosperity}",
            ],
            severity="medium",
            consequence_score="high",
        )
        _record_project_network_progress(state, relic, region, event_type, "support")
        _record_megastructure_support_relations(state, relic, region, event, summary)
        _link_presence_event(relic, event)
        return event

    if _megastructure_under_stress(region) and rng.random() < 0.39:
        previous_state = relic.activation_state
        previous_phase = relic.construction_state
        previous_security = region.security
        previous_scarcity = region.scarcity
        relic.activation_state = "contested"
        relic.construction_state = _degrade_construction_state(
            relic.construction_state,
            ["operational", "integration", "retrofit", "degraded"],
        )
        region.security = _DOWNSHIFT[region.security]
        region.scarcity = _UPSHIFT[region.scarcity]
        summary = (
            f"{relic.name} slipped into a reconstruction deadlock in {region.name}, "
            f"stalling the hybrid site at {relic.construction_state} and amplifying local pressure."
        )
        event = _build_presence_event(
            state,
            relic,
            event_type="megastructure_stall",
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"construction_{previous_phase}_to_{relic.construction_state}",
                f"security_{previous_security}_to_{region.security}",
                f"scarcity_{previous_scarcity}_to_{region.scarcity}",
            ],
            severity="high",
            consequence_score="high",
        )
        _record_project_network_progress(state, relic, region, "megastructure_stall", "strain")
        _record_megastructure_strain_relations(state, relic, region, event, summary)
        _link_presence_event(relic, event)
        return event
    return None


def _advance_protocol(
    state: WorldState,
    relic: Relic,
    rng: Random,
) -> Event | None:
    region = state.regions[relic.current_region_id]
    civilization = state.civilizations.get(region.civ_id) if region.civ_id else None

    if (
        civilization is not None
        and (civilization.legitimacy != "high" or region.political_tension == "high")
        and rng.random() < 0.34
    ):
        previous_state = relic.activation_state
        previous_legitimacy = civilization.legitimacy
        previous_security = region.security
        relic.activation_state = "contested"
        civilization.legitimacy = _DOWNSHIFT[civilization.legitimacy]
        region.security = _DOWNSHIFT[region.security]
        summary = (
            f"{relic.name} infiltrated civic control pathways in {region.name}, "
            f"eroding legitimacy and weakening the local enforcement shell."
        )
        event = _build_presence_event(
            state,
            relic,
            event_type="protocol_infiltration",
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"legitimacy_{previous_legitimacy}_to_{civilization.legitimacy}",
                f"security_{previous_security}_to_{region.security}",
            ],
            severity="high",
            consequence_score="high",
        )
        upsert_relation(
            state,
            source_ref=relic.relic_id,
            target_ref=region.region_id,
            relation_type="distorts",
            event=event,
            strength="high",
            notes=summary,
            tags=["autonomous_system", "region"],
        )
        if civilization is not None:
            upsert_relation(
                state,
                source_ref=relic.relic_id,
                target_ref=civilization.civ_id,
                relation_type="infiltrating",
                event=event,
                strength="high",
                notes=summary,
                tags=["autonomous_system", "civilization"],
            )
        _link_presence_event(relic, event)
        return event

    if civilization is not None and region.security == "high" and rng.random() < 0.25:
        previous_state = relic.activation_state
        previous_legitimacy = civilization.legitimacy
        relic.activation_state = "sealed"
        civilization.legitimacy = _UPSHIFT[civilization.legitimacy]
        summary = (
            f"{relic.name} was pushed back behind hardened control layers in {region.name}, "
            f"allowing civic legitimacy to recover."
        )
        event = _build_presence_event(
            state,
            relic,
            event_type="protocol_lockdown",
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"legitimacy_{previous_legitimacy}_to_{civilization.legitimacy}",
            ],
            severity="medium",
            consequence_score="medium",
        )
        upsert_relation(
            state,
            source_ref=relic.relic_id,
            target_ref=region.region_id,
            relation_type="contained_by_region",
            event=event,
            strength="medium",
            notes=summary,
            tags=["autonomous_system", "containment"],
        )
        if civilization is not None:
            upsert_relation(
                state,
                source_ref=relic.relic_id,
                target_ref=civilization.civ_id,
                relation_type="contained_by_civilization",
                event=event,
                strength="medium",
                notes=summary,
                tags=["autonomous_system", "containment"],
            )
        _link_presence_event(relic, event)
        return event

    return None


def _advance_archive(
    state: WorldState,
    relic: Relic,
    rng: Random,
) -> Event | None:
    region = state.regions[relic.current_region_id]
    civilization = state.civilizations.get(region.civ_id) if region.civ_id else None

    if civilization is not None and (civilization.legitimacy != "high" or region.political_tension == "high") and rng.random() < 0.28:
        previous_state = relic.activation_state
        previous_legitimacy = civilization.legitimacy
        previous_tension = region.political_tension
        relic.activation_state = "contested"
        civilization.legitimacy = _DOWNSHIFT[civilization.legitimacy]
        region.political_tension = _UPSHIFT[region.political_tension]
        summary = (
            f"{relic.name} leaked sealed historical material into {region.name}, "
            f"shaking civic legitimacy and sharpening the local political split."
        )
        event = _build_presence_event(
            state,
            relic,
            event_type="archive_legitimacy_shock",
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"legitimacy_{previous_legitimacy}_to_{civilization.legitimacy}",
                f"tension_{previous_tension}_to_{region.political_tension}",
            ],
            severity="high",
            consequence_score="high",
        )
        upsert_relation(
            state,
            source_ref=relic.relic_id,
            target_ref=civilization.civ_id,
            relation_type="delegitimizing",
            event=event,
            strength="high",
            notes=summary,
            tags=["sealed_archive", "civilization"],
        )
        upsert_relation(
            state,
            source_ref=relic.relic_id,
            target_ref=region.region_id,
            relation_type="destabilizes",
            event=event,
            strength="medium",
            notes=summary,
            tags=["sealed_archive", "region"],
        )
        if civilization is not None:
            upsert_relation(
                state,
                source_ref=relic.relic_id,
                target_ref=civilization.civ_id,
                relation_type="delegitimizing",
                event=event,
                strength="high",
                notes=summary,
                tags=["sealed_archive", "civilization"],
            )
        _link_presence_event(relic, event)
        return event

    if civilization is not None and region.security == "high" and rng.random() < 0.22:
        previous_state = relic.activation_state
        previous_legitimacy = civilization.legitimacy
        relic.activation_state = "sealed"
        civilization.legitimacy = _UPSHIFT[civilization.legitimacy]
        summary = (
            f"{relic.name} was resealed and reclassified in {region.name}, "
            f"allowing the surrounding authority structure to steady itself."
        )
        event = _build_presence_event(
            state,
            relic,
            event_type="archive_suppression",
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"legitimacy_{previous_legitimacy}_to_{civilization.legitimacy}",
            ],
            severity="medium",
            consequence_score="medium",
        )
        upsert_relation(
            state,
            source_ref=relic.relic_id,
            target_ref=region.region_id,
            relation_type="contained_by_region",
            event=event,
            strength="medium",
            notes=summary,
            tags=["sealed_archive", "containment"],
        )
        if civilization is not None:
            upsert_relation(
                state,
                source_ref=relic.relic_id,
                target_ref=civilization.civ_id,
                relation_type="suppressed_by_civilization",
                event=event,
                strength="medium",
                notes=summary,
                tags=["sealed_archive", "containment"],
            )
        _link_presence_event(relic, event)
        return event

    return None


def _advance_lifeform(
    state: WorldState,
    relic: Relic,
    rng: Random,
) -> Event | None:
    region = state.regions[relic.current_region_id]
    civilization = state.civilizations.get(region.civ_id) if region.civ_id else None

    if relic.construction_state in {"breeding", "distributed"} and rng.random() < 0.28:
        migration_event = _advance_lifeform_migration(state, relic, region, civilization, rng)
        if migration_event is not None:
            return migration_event

    if (region.security == "low" or region.ecological_stress == "high") and rng.random() < 0.36:
        previous_state = relic.activation_state
        previous_phase = relic.construction_state
        previous_security = region.security
        previous_scarcity = region.scarcity
        relic.activation_state = "contested"
        relic.construction_state = _advance_construction_state(
            relic.construction_state,
            ["contained", "nesting", "roaming", "breeding", "distributed"],
        )
        region.security = _DOWNSHIFT[region.security]
        region.scarcity = _UPSHIFT[region.scarcity]
        summary = (
            f"{relic.name} expanded its active habitat across {region.name}, "
            f"pushing the anomalous lifeform toward {relic.construction_state} while biosecurity faltered."
        )
        event = _build_presence_event(
            state,
            relic,
            event_type="lifeform_habitat_expansion",
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"state_{previous_phase}_to_{relic.construction_state}",
                f"security_{previous_security}_to_{region.security}",
                f"scarcity_{previous_scarcity}_to_{region.scarcity}",
            ],
            severity="high",
            consequence_score="high",
        )
        _record_lifeform_pressure_relations(state, relic, region, civilization, event, summary)
        _link_presence_event(relic, event)
        return event

    if region.security == "high" and rng.random() < 0.24:
        previous_state = relic.activation_state
        previous_phase = relic.construction_state
        previous_tension = region.political_tension
        relic.activation_state = "sealed"
        relic.construction_state = "contained" if relic.origin_mode == "lab_origin" else "nesting"
        region.political_tension = _DOWNSHIFT[region.political_tension]
        summary = (
            f"{relic.name} was pushed back into a narrower behavioral envelope in {region.name}, "
            f"giving the local authorities a temporary biosecurity reprieve."
        )
        event = _build_presence_event(
            state,
            relic,
            event_type="lifeform_containment_sweep",
            summary=summary,
            region_refs=[region.region_id],
            civ_refs=[region.civ_id] if region.civ_id else [],
            result_tags=[
                f"activation_{previous_state}_to_{relic.activation_state}",
                f"state_{previous_phase}_to_{relic.construction_state}",
                f"tension_{previous_tension}_to_{region.political_tension}",
            ],
            severity="medium",
            consequence_score="medium",
        )
        _record_lifeform_containment_relations(state, relic, region, civilization, event, summary)
        _link_presence_event(relic, event)
        return event
    return None


def _advance_lifeform_migration(
    state: WorldState,
    relic: Relic,
    region: Region,
    civilization: object,
    rng: Random,
) -> Event | None:
    target_region = _choose_lifeform_target_region(state, relic, region, rng)
    if target_region is None:
        return None

    previous_region_id = region.region_id
    previous_security = target_region.security
    previous_tension = target_region.political_tension
    previous_scarcity = target_region.scarcity
    target_region.security = _DOWNSHIFT[target_region.security]
    target_region.political_tension = _UPSHIFT[target_region.political_tension]
    target_region.scarcity = _UPSHIFT[target_region.scarcity]
    relic.current_region_id = target_region.region_id
    if relic.relic_id not in target_region.resident_relics:
        target_region.resident_relics.append(relic.relic_id)
    if relic.relic_id in region.resident_relics and relic.construction_state != "distributed":
        region.resident_relics.remove(relic.relic_id)
    summary = (
        f"{relic.name} pushed beyond {region.name} and established a new active front in {target_region.name}, "
        f"spreading anomalous pressure across regional boundaries."
    )
    event = _build_presence_event(
        state,
        relic,
        event_type="lifeform_migration_front",
        summary=summary,
        region_refs=[previous_region_id, target_region.region_id],
        civ_refs=_merge_civ_refs(region.civ_id, target_region.civ_id),
        result_tags=[
            f"moved_{previous_region_id}_to_{target_region.region_id}",
            f"security_{previous_security}_to_{target_region.security}",
            f"tension_{previous_tension}_to_{target_region.political_tension}",
            f"scarcity_{previous_scarcity}_to_{target_region.scarcity}",
        ],
        severity="high",
        consequence_score="high",
    )
    _record_lifeform_pressure_relations(
        state,
        relic,
        target_region,
        state.civilizations.get(target_region.civ_id) if target_region.civ_id else civilization,
        event,
        summary,
    )
    upsert_relation(
        state,
        source_ref=relic.relic_id,
        target_ref=region.region_id,
        relation_type="originating_from",
        event=event,
        strength="medium",
        notes=summary,
        tags=["anomalous_lifeform", "migration"],
    )
    _link_presence_event(relic, event)
    return event


def _build_presence_event(
    state: WorldState,
    relic: Relic,
    *,
    event_type: str,
    summary: str,
    region_refs: list[str],
    civ_refs: list[str],
    result_tags: list[str],
    severity: str,
    consequence_score: str,
) -> Event:
    return Event(
        event_id=state.event_stream.new_event_id(),
        tick=state.current_tick,
        time_granularity=state.current_granularity,
        event_type=event_type,
        event_scope="presence",
        title=f"{relic.name} triggered {event_type}",
        summary=summary,
        region_refs=region_refs,
        civ_refs=civ_refs,
        relic_refs=[relic.relic_id],
        cause_tags=["presence_dynamics", presence_event_family(relic)],
        result_tags=result_tags,
        severity=severity,
        novelty="medium",
        consequence_score=consequence_score,
        narrative_priority="medium",
    )


def _link_presence_event(relic: Relic, event: Event) -> None:
    if event.event_id not in relic.linked_events:
        relic.linked_events.append(event.event_id)


def _megastructure_under_stress(region: Region) -> bool:
    return (
        region.political_tension == "high"
        or region.security == "low"
        or region.scarcity == "high"
    )


def _advance_construction_state(current: str, phases: list[str]) -> str:
    if current not in phases:
        return phases[0]
    index = phases.index(current)
    return phases[min(index + 1, len(phases) - 1)]


def _degrade_construction_state(current: str, phases: list[str]) -> str:
    if current not in phases:
        return phases[-1]
    index = phases.index(current)
    return phases[min(index + 1, len(phases) - 1)]


def _contemporary_megastructure_event_type(previous_phase: str, current_phase: str) -> str:
    if previous_phase == "planned" and current_phase == "foundation":
        return "megastructure_groundbreaking"
    if current_phase == "operational":
        return "megastructure_grid_link"
    return "megastructure_phase_advance"


def _contemporary_megastructure_summary(
    relic_name: str,
    region_name: str,
    previous_phase: str,
    current_phase: str,
) -> str:
    if previous_phase == "planned" and current_phase == "foundation":
        return (
            f"{relic_name} broke ground in {region_name}, "
            f"turning a paper megaproject into a physical construction corridor."
        )
    if current_phase == "operational":
        return (
            f"{relic_name} linked into the wider grid in {region_name}, "
            f"letting the contemporary wonder begin to function as real infrastructure."
        )
    return (
        f"{relic_name} advanced from {previous_phase} to {current_phase} in {region_name}, "
        f"pushing the live megaproject deeper into the region's daily systems."
    )


def _record_megastructure_support_relations(
    state: WorldState,
    relic: Relic,
    region: Region,
    event: Event,
    summary: str,
) -> None:
    upsert_relation(
        state,
        source_ref=relic.relic_id,
        target_ref=region.region_id,
        relation_type="stabilizes",
        event=event,
        strength="high",
        notes=summary,
        tags=["megastructure", "region"],
    )
    if region.civ_id:
        upsert_relation(
            state,
            source_ref=relic.relic_id,
            target_ref=region.civ_id,
            relation_type="supports",
            event=event,
            strength="medium",
            notes=summary,
            tags=["megastructure", "civilization"],
        )
    if relic.sponsor_ref:
        upsert_relation(
            state,
            source_ref=relic.sponsor_ref,
            target_ref=relic.relic_id,
            relation_type="sponsoring",
            event=event,
            strength="medium",
            notes=summary,
            tags=["megastructure", "organization"],
        )
    if relic.contractor_ref:
        upsert_relation(
            state,
            source_ref=relic.contractor_ref,
            target_ref=relic.relic_id,
            relation_type="contracting",
            event=event,
            strength="high" if relic.construction_state in {"rising", "integration", "operational"} else "medium",
            notes=summary,
            tags=["megastructure", "organization", "construction"],
        )
    if relic.financier_ref:
        upsert_relation(
            state,
            source_ref=relic.financier_ref,
            target_ref=relic.relic_id,
            relation_type="financing",
            event=event,
            strength="medium",
            notes=summary,
            tags=["megastructure", "organization", "finance"],
        )
    if relic.opposition_ref:
        upsert_relation(
            state,
            source_ref=relic.opposition_ref,
            target_ref=relic.relic_id,
            relation_type="opposing",
            event=event,
            strength="low",
            status="active",
            notes="Opposition remains present but is not currently dominant.",
            tags=["megastructure", "organization", "opposition"],
        )


def _record_megastructure_strain_relations(
    state: WorldState,
    relic: Relic,
    region: Region,
    event: Event,
    summary: str,
) -> None:
    upsert_relation(
        state,
        source_ref=relic.relic_id,
        target_ref=region.region_id,
        relation_type="destabilizes",
        event=event,
        strength="high",
        notes=summary,
        tags=["megastructure", "region"],
    )
    if region.civ_id:
        upsert_relation(
            state,
            source_ref=relic.relic_id,
            target_ref=region.civ_id,
            relation_type="strains",
            event=event,
            strength="high",
            notes=summary,
            tags=["megastructure", "civilization"],
        )
    if relic.contractor_ref:
        upsert_relation(
            state,
            source_ref=relic.contractor_ref,
            target_ref=relic.relic_id,
            relation_type="contracting",
            event=event,
            strength="medium",
            notes=summary,
            tags=["megastructure", "organization", "construction"],
        )
    if relic.financier_ref:
        upsert_relation(
            state,
            source_ref=relic.financier_ref,
            target_ref=relic.relic_id,
            relation_type="financing",
            event=event,
            strength="low",
            notes=summary,
            tags=["megastructure", "organization", "finance"],
        )
    if relic.opposition_ref:
        upsert_relation(
            state,
            source_ref=relic.opposition_ref,
            target_ref=relic.relic_id,
            relation_type="obstructing",
            event=event,
            strength="high",
            notes=summary,
            tags=["megastructure", "organization", "opposition"],
        )


def _record_project_network_progress(
    state: WorldState,
    relic: Relic,
    region: Region,
    event_type: str,
    mode: str,
) -> None:
    status_map = {
        "megastructure_groundbreaking": "mobilizing",
        "megastructure_phase_advance": "active_buildout",
        "megastructure_grid_link": "grid_attached",
        "megastructure_reactivation": "active_buildout",
        "megastructure_budget_crisis": "contested_buildout",
        "megastructure_stall": "stalled_recovery",
    }
    note_map = {
        "megastructure_groundbreaking": "groundbreaking_started",
        "megastructure_phase_advance": "phase_advance",
        "megastructure_grid_link": "grid_linked",
        "megastructure_reactivation": "reactivation_window",
        "megastructure_budget_crisis": "budget_crisis",
        "megastructure_stall": "construction_stall",
    }
    append_project_note(
        state,
        relic_id=relic.relic_id,
        faction_id=relic.contractor_ref or relic.sponsor_ref,
        region_id=region.region_id,
        civ_id=region.civ_id,
        note=note_map.get(event_type, event_type),
        status=status_map.get(event_type),
        pressure_shift="down" if mode == "support" else "up",
    )


def _record_lifeform_pressure_relations(
    state: WorldState,
    relic: Relic,
    region: Region,
    civilization: object,
    event: Event,
    summary: str,
) -> None:
    upsert_relation(
        state,
        source_ref=relic.relic_id,
        target_ref=region.region_id,
        relation_type="encroaching_on",
        event=event,
        strength="high",
        notes=summary,
        tags=["anomalous_lifeform", "region"],
    )
    if civilization is not None:
        upsert_relation(
            state,
            source_ref=relic.relic_id,
            target_ref=civilization.civ_id,
            relation_type="biosecurity_threat",
            event=event,
            strength="medium",
            notes=summary,
            tags=["anomalous_lifeform", "civilization"],
        )


def _record_lifeform_containment_relations(
    state: WorldState,
    relic: Relic,
    region: Region,
    civilization: object,
    event: Event,
    summary: str,
) -> None:
    upsert_relation(
        state,
        source_ref=relic.relic_id,
        target_ref=region.region_id,
        relation_type="contained_by_region",
        event=event,
        strength="medium",
        notes=summary,
        tags=["anomalous_lifeform", "containment"],
    )
    if civilization is not None:
        upsert_relation(
            state,
            source_ref=relic.relic_id,
            target_ref=civilization.civ_id,
            relation_type="contained_by_civilization",
            event=event,
            strength="medium",
            notes=summary,
            tags=["anomalous_lifeform", "containment"],
        )


def _choose_lifeform_target_region(
    state: WorldState,
    relic: Relic,
    current_region: Region,
    rng: Random,
) -> Region | None:
    candidate_regions = [
        region
        for region in state.regions.values()
        if region.region_id != current_region.region_id
    ]
    if not candidate_regions:
        return None
    same_civ = [region for region in candidate_regions if region.civ_id == current_region.civ_id]
    high_connectivity = [region for region in candidate_regions if region.connectivity == "high"]
    ecological = [region for region in candidate_regions if region.ecological_stress != "low"]
    if relic.origin_mode == "engineered_swarm" and high_connectivity:
        return rng.choice(high_connectivity)
    if relic.origin_mode == "wild_mutation" and ecological:
        return rng.choice(ecological)
    if same_civ:
        return rng.choice(same_civ)
    return rng.choice(candidate_regions)


def _merge_civ_refs(primary: str | None, secondary: str | None) -> list[str]:
    refs: list[str] = []
    if primary:
        refs.append(primary)
    if secondary and secondary not in refs:
        refs.append(secondary)
    return refs
