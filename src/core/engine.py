"""Main world engine orchestration."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from random import Random

from src.agents.fallback import Intent
from src.agents.intent_generator import IntentBatch, generate_intents
from src.agents.scheduler import WakeSchedule, build_wake_schedule
from src.config.defaults import DEFAULT_AI_CONFIG
from src.core.budget import BudgetManager
from src.events.models import Event
from src.events.taxonomy import event_theme_tags
from src.events.visibility_rules import apply_visibility_policy, player_facing_event_clue
from src.narrative.chronicler import ChronicleResult, generate_chronicle
from src.rules.faction_actions import advance_faction_actions
from src.rules.event_fallout import advance_event_fallout
from src.rules.macro_update import advance_macro_state
from src.rules.presence_dynamics import advance_presence_state
from src.rules.resolver import resolve_intents
from src.world.relations import relations_for_ref
from src.world.pressure_thread import PressureThread
from src.world.state import WorldState
from src.world.relations import upsert_relation


@dataclass(slots=True)
class StepResult:
    """Result bundle for a single world step."""

    events: list[Event]
    wake_schedule: WakeSchedule
    intents: IntentBatch
    chronicle: ChronicleResult | None = None
    last_llm_error: str | None = None
    ai_budget_summary: str | None = None


@dataclass(slots=True)
class WorldEngine:
    """Minimal world engine that advances macro state and emits events."""

    world: WorldState
    ai_config: dict[str, object] = field(default_factory=lambda: DEFAULT_AI_CONFIG.copy())
    rng: Random = field(init=False)
    budget_manager: BudgetManager = field(init=False)

    def __post_init__(self) -> None:
        self.rng = Random(self.world.seed + self.world.current_tick)
        self.budget_manager = BudgetManager.from_config(self.ai_config)

    def step(self) -> StepResult:
        """Advance the world by one tick."""
        self.world.current_tick += 1
        self.rng.seed(self.world.seed + self.world.current_tick)
        macro_events = advance_macro_state(self.world, self.rng)
        self.world.event_stream.extend(macro_events)
        presence_events = advance_presence_state(self.world, self.rng)
        self.world.event_stream.extend(presence_events)
        faction_events = advance_faction_actions(self.world, self.rng)
        self.world.event_stream.extend(faction_events)
        structural_events = macro_events + presence_events + faction_events
        apply_visibility_policy(structural_events)
        self.world.active_event_ids = [event.event_id for event in structural_events]
        wake_schedule = build_wake_schedule(self.world, self.budget_manager)
        intents = generate_intents(self.world, wake_schedule, self.ai_config)
        _store_last_intents(self.world, intents.all_intents)
        resolution = resolve_intents(self.world, intents.all_intents)
        apply_visibility_policy(resolution.events)
        self.world.event_stream.extend(resolution.events)
        fallout_events = advance_event_fallout(self.world, self.rng)
        apply_visibility_policy(fallout_events)
        self.world.event_stream.extend(fallout_events)
        all_events = structural_events + resolution.events + fallout_events
        _backfill_event_structure_refs(self.world, all_events)
        self.world.active_event_ids = [event.event_id for event in all_events]
        _refresh_civilization_memory(self.world, all_events)
        _refresh_faction_behavior(self.world, all_events)
        _refresh_structural_role_relations(self.world)
        _refresh_relation_summaries(self.world)
        _refresh_character_frontier_history(self.world, intents.all_intents, all_events)
        _refresh_character_active_goals(self.world, intents.all_intents, all_events)
        _refresh_faction_objectives(self.world, all_events)
        _refresh_project_progress(self.world, all_events)
        _refresh_supply_corridors(self.world, all_events)
        _refresh_relic_contests(self.world, all_events)
        _refresh_region_nodes(self.world, all_events)
        _refresh_pressure_threads(self.world, all_events)
        _refresh_dynamic_structure_lifecycle(self.world, all_events)
        _refresh_emergent_presence_lifecycle(self.world, all_events)
        _refresh_objective_feedback_relations(self.world)
        chronicle = generate_chronicle(all_events, self.ai_config)
        return StepResult(
            events=all_events,
            wake_schedule=wake_schedule,
            intents=intents,
            chronicle=chronicle,
            last_llm_error=intents.last_llm_error,
            ai_budget_summary=self.budget_manager.describe(),
        )


def _store_last_intents(world: WorldState, intents: list[Intent]) -> None:
    """Persist last generated intents on characters for future steps."""
    for intent in intents:
        character = world.characters[intent.character_id]
        character.last_intent = {
            "intent_type": intent.intent_type,
            "target_ref": intent.target_ref,
            "goal": intent.goal,
            "urgency": intent.urgency,
            "source": intent.source,
        }


def _refresh_civilization_memory(world: WorldState, events: list[Event]) -> None:
    for civilization in world.civilizations.values():
        civ_events = [event for event in events if civilization.civ_id in event.civ_refs]
        civ_relations = _recent_civilization_relations(world, civilization.civ_id)
        if not civ_events and not civ_relations:
            continue
        crisis_posture = _detect_crisis_override(civ_events[-4:])
        if crisis_posture is not None:
            _force_civilization_posture(civilization, crisis_posture)
        posture = civilization.strategic_posture
        recent_notes: list[str] = []
        for event in civ_events[-4:]:
            posture = _update_civilization_posture(posture, event)
            focal_region = event.region_refs[0] if event.region_refs else "unknown_region"
            recent_notes.append(f"tick_{world.current_tick}:{event.event_type}@{focal_region}")
        recent_notes.extend(_civilization_relation_memory_notes(world, civilization.civ_id, civ_relations))
        posture = _apply_civilization_relation_nudge(posture, civ_relations)
        posture = _apply_structure_template_posture_nudge(world, posture)
        if crisis_posture is None:
            _apply_civilization_posture_inertia(civilization, posture)
        _extend_unique_tail(civilization.strategic_memory, recent_notes, limit=8)
        civilization.strategic_bias_trace = _build_civilization_bias_trace(world, civilization, civ_events)


def _refresh_faction_behavior(world: WorldState, events: list[Event]) -> None:
    for faction in world.factions.values():
        faction_events = [event for event in events if faction.faction_id in event.faction_refs]
        faction_relations = relations_for_ref(world, faction.faction_id, limit=6)
        if not faction_events and not faction_relations:
            continue

        proposed_style = _derive_faction_operational_style(
            world,
            faction,
            faction_events[-4:] if faction_events else [],
            faction_relations,
        )
        _apply_faction_style_inertia(faction, proposed_style)

        recent_notes: list[str] = []
        for event in faction_events[-4:]:
            focal_region = event.region_refs[0] if event.region_refs else "unknown_region"
            recent_notes.append(f"tick_{world.current_tick}:{event.event_type}@{focal_region}")
        recent_notes.extend(_faction_relation_memory_notes(faction.faction_id, faction_relations))
        _extend_unique_tail(faction.operational_style_memory, recent_notes, limit=8)
        faction.operational_style_trace = _build_faction_style_trace(world, faction, faction_events)


def _faction_relation_memory_notes(faction_id: str, relations) -> list[str]:
    notes: list[str] = []
    seen: set[str] = set()
    for relation in relations[:3]:
        target = relation.target_ref if relation.source_ref == faction_id else relation.source_ref
        entry = f"tick_{relation.updated_tick}:relation_{relation.relation_type}@{target}"
        if entry in seen:
            continue
        seen.add(entry)
        notes.append(entry)
    return notes


def _refresh_relation_summaries(world: WorldState) -> None:
    for faction in world.factions.values():
        relations = relations_for_ref(world, faction.faction_id, limit=12)
        counterparty_relations: dict[str, list] = {}
        for relation in relations:
            counterparty = (
                relation.target_ref
                if relation.source_ref == faction.faction_id
                else relation.source_ref
            )
            if counterparty not in world.factions:
                continue
            counterparty_relations.setdefault(counterparty, []).append(relation)
        allies: list[str] = []
        rivals: list[str] = []
        for counterparty, pair_relations in counterparty_relations.items():
            bucket = _dominant_faction_relation_bucket(pair_relations)
            if bucket == "ally":
                _push_unique(allies, counterparty, limit=6)
            elif bucket == "rival":
                _push_unique(rivals, counterparty, limit=6)
        faction.allied_factions = allies
        faction.rival_factions = rivals

    for civilization in world.civilizations.values():
        external: dict[str, str] = {}
        faction_ids = set(civilization.key_factions)
        for faction_id in civilization.key_factions[:6]:
            for relation in relations_for_ref(world, faction_id, limit=8):
                counterparty = (
                    relation.target_ref
                    if relation.source_ref == faction_id
                    else relation.source_ref
                )
                if counterparty in faction_ids:
                    continue
                if counterparty in world.factions:
                    external[counterparty] = relation.relation_type
                elif counterparty in world.regions or counterparty in world.relics:
                    external[counterparty] = relation.relation_type
                if len(external) >= 8:
                    break
            if len(external) >= 8:
                break
        civilization.external_relations = external


def _refresh_structural_role_relations(world: WorldState) -> None:
    event = Event(
        event_id=f"system_structural_sync_{world.current_tick}",
        tick=world.current_tick,
        time_granularity=world.current_granularity,
        event_type="system_structural_sync",
        event_scope="system",
        title="Structural role sync",
        summary="System synchronized structural project and supply roles.",
        severity="low",
        novelty="low",
        consequence_score="low",
        narrative_priority="low",
        visibility="hidden",
    )
    _refresh_project_role_relations(world, event)
    _refresh_supply_role_relations(world, event)


def _refresh_project_role_relations(world: WorldState, event: Event) -> None:
    role_map = {
        "sponsoring": "sponsor_refs",
        "contracting": "contractor_refs",
        "financing": "financier_refs",
        "obstructing": "opposition_refs",
    }
    for project in world.projects.values():
        _sync_project_refs_from_presence(world, project.project_id)
        for relation_type, field_name in role_map.items():
            current_refs = [
                ref
                for ref in getattr(project, field_name, [])
                if ref in world.factions
            ]
            for faction_id in current_refs:
                _push_unique(project.linked_factions, faction_id, limit=12)
                _upsert_structural_relation_if_needed(
                    world,
                    source_ref=faction_id,
                    target_ref=project.project_id,
                    relation_type=relation_type,
                    event=event,
                    notes=f"structural_sync:{relation_type}->{project.project_id}",
                    tags=["project", "structural_role", relation_type],
                )
            _deactivate_structural_relations_not_in_current_refs(
                world,
                target_ref=project.project_id,
                relation_type=relation_type,
                valid_source_refs=set(current_refs),
            )


def _refresh_supply_role_relations(world: WorldState, event: Event) -> None:
    for supply_line in world.supply_lines.values():
        controller = supply_line.controlling_faction_ref
        if controller and controller in world.factions:
            _upsert_structural_relation_if_needed(
                world,
                source_ref=controller,
                target_ref=supply_line.supply_id,
                relation_type="controls",
                event=event,
                notes=f"structural_sync:controls->{supply_line.supply_id}",
                tags=["supply", "structural_role", "controls"],
            )
            _deactivate_structural_relations_not_in_current_refs(
                world,
                target_ref=supply_line.supply_id,
                relation_type="controls",
                valid_source_refs={controller},
            )
        else:
            _deactivate_structural_relations_not_in_current_refs(
                world,
                target_ref=supply_line.supply_id,
                relation_type="controls",
                valid_source_refs=set(),
            )


def _sync_project_refs_from_presence(world: WorldState, project_id: str) -> None:
    project = world.projects.get(project_id)
    if project is None:
        return
    sponsor_refs = list(project.sponsor_refs)
    contractor_refs = list(project.contractor_refs)
    financier_refs = list(project.financier_refs)
    opposition_refs = list(project.opposition_refs)
    for relic_id in project.linked_presence_refs:
        relic = world.relics.get(relic_id)
        if relic is None:
            continue
        if relic.sponsor_ref in world.factions:
            _push_unique(sponsor_refs, relic.sponsor_ref, limit=6)
        if relic.contractor_ref in world.factions:
            _push_unique(contractor_refs, relic.contractor_ref, limit=6)
        if relic.financier_ref in world.factions:
            _push_unique(financier_refs, relic.financier_ref, limit=6)
        if relic.opposition_ref in world.factions:
            _push_unique(opposition_refs, relic.opposition_ref, limit=6)
    project.sponsor_refs = sponsor_refs
    project.contractor_refs = contractor_refs
    project.financier_refs = financier_refs
    project.opposition_refs = opposition_refs


def _upsert_structural_relation_if_needed(
    world: WorldState,
    *,
    source_ref: str,
    target_ref: str,
    relation_type: str,
    event: Event,
    notes: str,
    tags: list[str],
) -> None:
    relation_id = f"{source_ref}->{target_ref}:{relation_type}"
    relation = world.relations.get(relation_id)
    if relation is not None and relation.status == "active":
        relation.tags = list(dict.fromkeys(relation.tags + tags))
        return
    upsert_relation(
        world,
        source_ref=source_ref,
        target_ref=target_ref,
        relation_type=relation_type,
        event=event,
        strength="medium",
        status="active",
        notes=notes,
        tags=tags,
    )


def _deactivate_structural_relations_not_in_current_refs(
    world: WorldState,
    *,
    target_ref: str,
    relation_type: str,
    valid_source_refs: set[str],
) -> None:
    for relation in world.relations.values():
        if relation.target_ref != target_ref or relation.relation_type != relation_type:
            continue
        if relation.source_ref in valid_source_refs:
            relation.status = "active"
            continue
        relation.status = "inactive"


def _faction_relation_bucket(relation_type: str) -> str:
    if relation_type in {
        "allied_with",
        "supports",
        "supporting",
        "stabilizes",
        "contracting",
        "financing",
        "sponsoring",
    }:
        return "ally"
    if relation_type in {
        "rival_to",
        "contesting",
        "obstructing",
        "opposing",
        "infiltrating",
        "seeking_control",
        "flashpoint_actor",
    }:
        return "rival"
    return "neutral"


def _dominant_faction_relation_bucket(relations) -> str:
    if not relations:
        return "neutral"
    priority = {"rival": 3, "ally": 2, "neutral": 1}
    strength_score = {"high": 3, "medium": 2, "low": 1}
    ranked = sorted(
        relations,
        key=lambda relation: (
            priority.get(_faction_relation_bucket(relation.relation_type), 0),
            strength_score.get(relation.strength, 0),
            relation.updated_tick,
        ),
        reverse=True,
    )
    return _faction_relation_bucket(ranked[0].relation_type)


def _push_unique(items: list[str], value: str, *, limit: int) -> None:
    if value in items:
        return
    items.append(value)
    del items[limit:]


def _recent_civilization_relations(world: WorldState, civ_id: str):
    civilization = world.civilizations.get(civ_id)
    if civilization is None:
        return []
    seen: dict[str, object] = {}
    for faction_id in civilization.key_factions[:6]:
        for relation in relations_for_ref(world, faction_id, limit=4):
            key = relation.relation_id
            if key not in seen:
                seen[key] = relation
    return sorted(
        seen.values(),
        key=lambda item: (item.updated_tick, item.last_event_id),
        reverse=True,
    )[:6]


def _civilization_relation_memory_notes(world: WorldState, civ_id: str, relations) -> list[str]:
    civilization = world.civilizations.get(civ_id)
    if civilization is None:
        return []
    faction_ids = set(civilization.key_factions)
    notes: list[str] = []
    for relation in relations[:3]:
        if relation.source_ref in faction_ids and relation.target_ref in faction_ids:
            target = relation.target_ref
            notes.append(
                f"tick_{relation.updated_tick}:internal_{relation.relation_type}@{target}"
            )
        else:
            target = relation.target_ref if relation.source_ref in faction_ids else relation.source_ref
            notes.append(
                f"tick_{relation.updated_tick}:front_{relation.relation_type}@{target}"
            )
    return notes


def _apply_civilization_relation_nudge(current: str, relations) -> str:
    internal_rivalries = 0
    alliance_mesh = 0
    control_lines = 0
    external_pressure = 0
    for relation in relations[:6]:
        if relation.relation_type in {"rival_to", "contesting"}:
            internal_rivalries += 1
        elif relation.relation_type == "allied_with":
            alliance_mesh += 1
        elif relation.relation_type in {"controls", "contracting", "financing", "sponsoring", "supply_influence"}:
            control_lines += 1
        else:
            external_pressure += 1

    if internal_rivalries >= 3:
        return "stability_over_growth"
    if control_lines >= 3:
        return "megastructure_expansion"
    if external_pressure >= 3 and alliance_mesh <= 1:
        return "containment_first"
    if alliance_mesh >= 2 and current == "balanced_competition":
        return "balanced_competition"
    return current


def _extend_unique_tail(memory: list[str], entries: list[str], *, limit: int) -> None:
    for entry in entries:
        if entry in memory:
            memory.remove(entry)
        memory.append(entry)
    del memory[:-limit]


def _derive_faction_operational_style(world: WorldState, faction, events: list[Event], relations) -> str:
    scores: Counter[str] = Counter()
    for event in events:
        for style, weight in _faction_style_weights_for_event(event).items():
            scores[style] += weight
    for style, weight in _faction_style_weights_for_relations(relations).items():
        scores[style] += weight
    for style, weight in _faction_style_weights_for_frame(world).items():
        scores[style] += weight
    if not scores:
        return faction.operational_style
    return scores.most_common(1)[0][0]


def _faction_style_weights_for_event(event: Event) -> dict[str, int]:
    event_type = event.event_type.lower()
    themes = set(event_theme_tags(event))
    if "infiltration" in event_type or "power_struggle" in event_type:
        return {"discipline_network": 3}
    if "alliance" in event_type:
        return {"adaptive_network": 2, "discipline_network": 1}
    if "project" in themes and any(
        token in event_type
        for token in {"project_bid", "budget", "financing", "accident", "stall", "phase_advance"}
    ):
        return {"contract_predator": 3}
    if "resource_reallocation" in event_type or "supply" in themes:
        return {"extraction_broker": 3}
    if "anomaly" in themes and any(
        token in event_type
        for token in {"control", "takeover", "suppression", "containment"}
    ):
        return {"containment_cadre": 3}
    if "anomaly" in themes and any(
        token in event_type
        for token in {"contest", "breach", "provocation"}
    ):
        return {"containment_cadre": 2, "discipline_network": 1}
    return {"adaptive_network": 1}


def _faction_style_weights_for_frame(world: WorldState) -> dict[str, int]:
    frame = world.structure_template
    weights: Counter[str] = Counter()
    if "quiet_infiltration" in frame.organization_climates:
        weights["discipline_network"] += 2
    if "security_consolidation" in frame.organization_climates:
        weights["containment_cadre"] += 2
    if "contract_warfare" in frame.organization_climates:
        weights["contract_predator"] += 2
    if "extractive_opportunism" in frame.organization_climates:
        weights["extraction_broker"] += 2
    if "bureaucratic_competition" in frame.organization_climates or "managed_fragility" in frame.organization_climates:
        weights["adaptive_network"] += 1

    if "project_fronts" in frame.dominant_fronts or frame.anomaly_bias == "megastructure_pressure":
        weights["contract_predator"] += 1
    if "governance_fronts" in frame.dominant_fronts:
        weights["discipline_network"] += 1
    if "supply_fronts" in frame.dominant_fronts:
        weights["extraction_broker"] += 1
    if frame.anomaly_bias in {"biosecurity_pressure", "autonomous_system_pressure"}:
        weights["containment_cadre"] += 1
    return dict(weights)


def _faction_style_weights_for_relations(relations) -> dict[str, int]:
    weights: Counter[str] = Counter()
    for relation in relations[:6]:
        if relation.relation_type in {"rival_to", "contesting"}:
            weights["discipline_network"] += 1
        if relation.relation_type in {"allied_with"}:
            weights["adaptive_network"] += 1
        if relation.relation_type in {"controls", "contracting", "financing", "sponsoring"}:
            weights["contract_predator"] += 1
        if relation.relation_type in {"infiltrating", "flashpoint_actor", "seeking_control"}:
            weights["discipline_network"] += 1
        if relation.relation_type in {"supply_influence"}:
            weights["extraction_broker"] += 1
        if relation.relation_type in {"contained_by_region", "contained_by_civilization"}:
            weights["containment_cadre"] += 1
    return dict(weights)


def _apply_faction_style_inertia(faction, proposed_style: str) -> None:
    current = faction.operational_style
    if proposed_style == current:
        faction.operational_style_pending = "none"
        faction.operational_style_pending_hits = 0
        faction.operational_style_stability = "locked" if current != "adaptive_network" else "steady"
        return

    if faction.operational_style_pending == proposed_style:
        faction.operational_style_pending_hits += 1
    else:
        faction.operational_style_pending = proposed_style
        faction.operational_style_pending_hits = 1

    threshold = 2 if current != "adaptive_network" else 1
    if faction.operational_style_pending_hits >= threshold:
        faction.operational_style = proposed_style
        faction.operational_style_pending = "none"
        faction.operational_style_pending_hits = 0
        faction.operational_style_stability = "redirected"
    else:
        faction.operational_style_stability = "contested"


def _build_faction_style_trace(world: WorldState, faction, faction_events: list[Event]) -> list[str]:
    trace: list[str] = []
    style = faction.operational_style
    style_bias = {
        "discipline_network": [
            "bias_actions=infiltration,power_struggle,alliance_locking",
            "organization_logic=covert leverage and order shaping",
        ],
        "contract_predator": [
            "bias_actions=project_bid,budget_freeze,financing_capture",
            "organization_logic=project choke points and contract capture",
        ],
        "containment_cadre": [
            "bias_actions=relic_control,protocol_takeover,containment_push",
            "organization_logic=seal, suppress, and hold abnormal pressure",
        ],
        "extraction_broker": [
            "bias_actions=resource_reallocation,supply_capture,capital redirection",
            "organization_logic=route pressure into material leverage",
        ],
        "adaptive_network": [
            "bias_actions=distributed",
            "organization_logic=shift with local openings",
        ],
    }
    trace.extend(style_bias.get(style, style_bias["adaptive_network"]))
    trace.append(
        "world_frame="
        f"climates:{'/'.join(world.structure_template.organization_climates[:2])}"
        f"|fronts:{'/'.join(world.structure_template.dominant_fronts[:2])}"
        f"|anomaly:{world.structure_template.anomaly_bias}"
    )
    trace.append(
        "style_inertia="
        f"{faction.operational_style_stability}"
        f"(pending={faction.operational_style_pending}, hits={faction.operational_style_pending_hits})"
    )
    for event in faction_events[-3:]:
        focal_region = event.region_refs[0] if event.region_refs else "unknown_region"
        trace.append(f"recent_pull={event.event_type}@{focal_region}")
    return trace[-5:]


def _update_civilization_posture(current: str, event: Event) -> str:
    event_type = event.event_type.lower()
    themes = set(event_theme_tags(event))
    if "anomaly" in themes and any(
        token in event_type for token in {"lifeform", "containment", "migration", "suppression", "lockdown"}
    ):
        return "containment_first"
    if "project" in themes and any(
        token in event_type for token in {"groundbreaking", "grid_link", "project_bid", "budget", "financing"}
    ):
        return "megastructure_expansion"
    if "politics" in themes or "organization" in themes:
        return "stability_over_growth"
    if "supply" in themes:
        return "opportunistic_extraction"
    return current


def _refresh_character_frontier_history(
    world: WorldState,
    intents: list[Intent],
    events: list[Event],
) -> None:
    event_by_actor = {
        event.actor_refs[0]: event
        for event in events
        if event.actor_refs
    }
    for intent in intents:
        character = world.characters[intent.character_id]
        event = event_by_actor.get(character.char_id)
        if event is None:
            continue
        focal_relic = _resolve_frontier_focus_ref(world, intent, event)
        history_entry = (
            f"tick_{world.current_tick}:{intent.intent_type}"
            f"->{intent.target_ref}[event={event.event_type}, focal={focal_relic}]"
        )
        character.frontier_history.append(history_entry)
        character.frontier_history = character.frontier_history[-8:]
        _refresh_character_frontier_theme(character)


def _refresh_character_frontier_theme(character) -> None:
    recent_history = character.frontier_history[-6:]
    if not recent_history:
        character.frontier_previous_theme = character.frontier_theme
        character.frontier_theme = "none"
        character.frontier_theme_trace = []
        character.frontier_theme_strength = "none"
        character.frontier_theme_shift = "steady"
        character.frontier_focus_ref = "none"
        character.frontier_focus_type = "none"
        character.frontier_focus_shift = "steady"
        character.frontier_focus_trace = []
        character.frontier_focus_reason = "none"
        return

    theme_rules = {
        "biosecurity_hunter": {"track_lifeform_spread", "seal_migration_corridor", "contain_relic_fallout"},
        "project_operator": {"secure_project_budget", "contest_project_contract", "redirect_project_financing"},
        "containment_stabilizer": {"suppress_site_accident_fallout", "contain_relic_fallout", "manage_unrest"},
        "political_leverage_runner": {"broker_power_shift", "expand_influence", "improve_position", "seize_supply_leverage"},
    }
    scores: Counter[str] = Counter()
    trace: dict[str, list[str]] = {theme: [] for theme in theme_rules}
    latest_index: dict[str, int] = {}
    for index, entry in enumerate(recent_history):
        intent_type = _extract_intent_type_from_history(entry)
        event_type = _extract_event_type_from_history(entry)
        for theme, intent_types in theme_rules.items():
            if intent_type in intent_types:
                scores[theme] += 1
                trace[theme].append(intent_type)
                latest_index[theme] = index
        derived_theme = _derive_theme_from_history_context(intent_type, event_type)
        if derived_theme is not None:
            scores[derived_theme] += 1
            trace[derived_theme].append(f"{intent_type}|{event_type}")
            latest_index[derived_theme] = index

    if not scores:
        previous_theme = character.frontier_theme
        character.frontier_previous_theme = previous_theme
        character.frontier_theme = "mixed_front_operator"
        character.frontier_theme_trace = recent_history[-3:]
        character.frontier_theme_strength = "weak"
        character.frontier_theme_shift = _derive_frontier_theme_shift(previous_theme, character.frontier_theme)
        _refresh_character_frontier_focus(character, recent_history)
        return

    previous_theme = character.frontier_theme
    theme = max(
        scores,
        key=lambda item: (scores[item], latest_index.get(item, -1)),
    )
    top_score = scores[theme]
    total_score = sum(scores.values())
    strength = _derive_frontier_theme_strength(top_score, total_score, len(recent_history))
    character.frontier_previous_theme = previous_theme
    character.frontier_theme = theme
    character.frontier_theme_trace = trace[theme][-4:]
    character.frontier_theme_strength = strength
    character.frontier_theme_shift = _derive_frontier_theme_shift(previous_theme, theme)
    _refresh_character_frontier_focus(character, recent_history)


def _extract_intent_type_from_history(entry: str) -> str:
    if ":" not in entry or "->" not in entry:
        return "unknown"
    return entry.split(":", 1)[1].split("->", 1)[0]


def _extract_event_type_from_history(entry: str) -> str:
    marker = "event="
    if marker not in entry:
        return "unknown"
    return entry.split(marker, 1)[1].split(",", 1)[0].rstrip("]")


def _derive_theme_from_history_context(intent_type: str, event_type: str) -> str | None:
    event_type = event_type.lower()
    if intent_type == "secure_relic_access":
        if "megastructure" in event_type or "project" in event_type:
            return "project_operator"
        if "lifeform" in event_type or "migration" in event_type:
            return "biosecurity_hunter"
        if "protocol" in event_type or "archive" in event_type or "relic" in event_type:
            return "containment_stabilizer"
    if intent_type == "manage_unrest" and any(
        token in event_type for token in {"power", "infiltration", "alliance", "legitimacy"}
    ):
        return "political_leverage_runner"
    return None


def _derive_frontier_theme_strength(top_score: int, total_score: int, history_size: int) -> str:
    if total_score <= 0 or history_size <= 0:
        return "none"
    dominance = top_score / max(1, total_score)
    if top_score >= 4 and dominance >= 0.7:
        return "hard_locked"
    if top_score >= 3 and dominance >= 0.55:
        return "strong"
    if top_score >= 2:
        return "medium"
    return "weak"


def _derive_frontier_theme_shift(previous_theme: str, current_theme: str) -> str:
    if previous_theme in {"none", ""}:
        return "emerging"
    if previous_theme == current_theme:
        return "steady"
    if current_theme == "mixed_front_operator":
        return "diffusing"
    return "redirected"


def _refresh_character_active_goals(
    world: WorldState,
    intents: list[Intent],
    events: list[Event],
) -> None:
    intent_by_character = {intent.character_id: intent for intent in intents}
    for character in world.characters.values():
        recent_events = [
            event
            for event in events
            if character.char_id in event.actor_refs
            or character.current_region_id in event.region_refs
            or character.frontier_focus_ref in event.relic_refs
        ][-4:]
        intent = intent_by_character.get(character.char_id)
        target_ref = _pick_character_goal_target(character, intent)
        character.active_goal_target_ref = target_ref
        character.active_goal_summary = _summarize_character_active_goal(world, character, intent, target_ref)
        character.active_goal_status = _derive_character_goal_status(character, recent_events)
        character.active_goal_blockers = _collect_event_blockers(recent_events, limit=2)
        character.active_goal_recent_result = _summarize_recent_result(world, recent_events)


def _refresh_faction_objectives(world: WorldState, events: list[Event]) -> None:
    for faction in world.factions.values():
        faction_events = [event for event in events if faction.faction_id in event.faction_refs][-5:]
        objective_target = _pick_faction_objective_target(world, faction)
        faction.strategic_objective_target_ref = objective_target
        faction.strategic_objective = _summarize_faction_objective(world, faction, objective_target)
        faction.strategic_objective_status = _derive_faction_objective_status(world, faction, faction_events)
        faction.strategic_objective_blockers = _collect_faction_objective_blockers(world, faction, faction_events)
        faction.strategic_objective_recent_result = _summarize_recent_result(world, faction_events)


def _backfill_event_structure_refs(world: WorldState, events: list[Event]) -> None:
    for event in events:
        themes = set(event_theme_tags(event))
        for project_id in _infer_event_project_refs(world, event, themes):
            _push_unique(event.project_refs, project_id, limit=4)
        for supply_id in _infer_event_supply_refs(world, event, themes):
            _push_unique(event.supply_refs, supply_id, limit=4)
        for node_id in _infer_event_node_refs(world, event, themes):
            _push_unique(event.node_refs, node_id, limit=6)


def _infer_event_project_refs(world: WorldState, event: Event, themes: set[str]) -> list[str]:
    refs: list[str] = []
    if "project" not in themes and not event.relic_refs:
        return refs
    for project in world.projects.values():
        if event.relic_refs and set(event.relic_refs).intersection(project.linked_presence_refs):
            _push_unique(refs, project.project_id, limit=4)
            continue
        if event.region_refs and set(event.region_refs).intersection(project.linked_regions) and "project" in themes:
            _push_unique(refs, project.project_id, limit=4)
            continue
        if event.faction_refs and set(event.faction_refs).intersection(project.linked_factions) and "project" in themes:
            _push_unique(refs, project.project_id, limit=4)
    return refs


def _infer_event_supply_refs(world: WorldState, event: Event, themes: set[str]) -> list[str]:
    refs: list[str] = []
    if "supply" not in themes:
        return refs
    event_regions = set(event.region_refs)
    event_factions = set(event.faction_refs)
    event_civs = set(event.civ_refs)
    for supply_line in world.supply_lines.values():
        line_regions = {supply_line.origin_region_id, supply_line.destination_region_id}
        if event_regions.intersection(line_regions):
            _push_unique(refs, supply_line.supply_id, limit=4)
            continue
        if supply_line.controlling_faction_ref and supply_line.controlling_faction_ref in event_factions:
            _push_unique(refs, supply_line.supply_id, limit=4)
            continue
        if event_civs.intersection(supply_line.linked_civ_refs):
            _push_unique(refs, supply_line.supply_id, limit=4)
    return refs


def _infer_event_node_refs(world: WorldState, event: Event, themes: set[str]) -> list[str]:
    refs: list[str] = []
    linked_refs = set(event.project_refs + event.supply_refs + event.relic_refs)
    for node in world.region_nodes.values():
        if node.region_id not in event.region_refs and not linked_refs:
            continue
        if node.linked_project_id and node.linked_project_id in linked_refs:
            _push_unique(refs, node.node_id, limit=6)
            continue
        if node.linked_supply_id and node.linked_supply_id in linked_refs:
            _push_unique(refs, node.node_id, limit=6)
            continue
        if node.linked_relic_id and node.linked_relic_id in linked_refs:
            _push_unique(refs, node.node_id, limit=6)
            continue
        if node.region_id in event.region_refs and (
            ("project" in themes and node.linked_project_id)
            or ("supply" in themes and node.linked_supply_id)
            or ("anomaly" in themes and node.linked_relic_id)
        ):
            _push_unique(refs, node.node_id, limit=6)
    return refs


def _refresh_project_progress(world: WorldState, events: list[Event]) -> None:
    for project in world.projects.values():
        project_events = _recent_project_events_for_refresh(events, project)
        project.progress_state = _derive_project_progress_state(world, project, project_events)
        project.progress_blockers = _collect_project_progress_blockers(world, project, project_events)
        project.progress_summary = _summarize_project_progress(world, project, project_events)


def _refresh_supply_corridors(world: WorldState, events: list[Event]) -> None:
    for supply_line in world.supply_lines.values():
        supply_events = _recent_supply_events_for_refresh(events, supply_line)
        supply_line.corridor_state = _derive_supply_corridor_state(world, supply_line, supply_events)
        supply_line.corridor_blockers = _collect_supply_corridor_blockers(world, supply_line, supply_events)
        supply_line.corridor_summary = _summarize_supply_corridor(world, supply_line, supply_events)


def _refresh_relic_contests(world: WorldState, events: list[Event]) -> None:
    for relic in world.relics.values():
        relic_events = [event for event in events if relic.relic_id in event.relic_refs][-6:]
        relic.contest_state = _derive_relic_contest_state(world, relic, relic_events)
        relic.contesting_refs = _collect_relic_contesting_refs(world, relic, relic_events)
        relic.contest_summary = _summarize_relic_contest(world, relic, relic_events)


def _refresh_region_nodes(world: WorldState, events: list[Event]) -> None:
    for node in world.region_nodes.values():
        node_events = _recent_region_node_events(world, node, events)
        node.pressure = _derive_region_node_pressure(world, node)
        node.contention_state = _derive_region_node_contention_state(world, node, node_events)
        node.blockers = _collect_region_node_blockers(world, node, node_events)
        node.state_summary = _summarize_region_node_state(world, node, node_events)
        _extend_unique_tail(
            node.recent_notes,
            _region_node_recent_notes(world, node, node_events),
            limit=8,
        )


def _refresh_pressure_threads(world: WorldState, events: list[Event]) -> None:
    for thread in world.pressure_threads.values():
        if world.current_tick - thread.updated_tick > 6:
            thread.status = "cooling"
        if world.current_tick - thread.updated_tick > 16:
            thread.status = "dormant"
        thread.summary = _summarize_pressure_thread(world, thread)

    for event in events:
        themes = [
            theme for theme in event_theme_tags(event)
            if theme in {"project", "supply", "anomaly", "politics", "security", "organization", "macro"}
        ]
        if not themes:
            continue
        for scope_ref in _pressure_thread_scope_refs(event):
            for theme in themes[:3]:
                thread_id = f"thread_{scope_ref}_{theme}"
                thread = world.pressure_threads.get(thread_id)
                if thread is None:
                    thread = PressureThread(
                        thread_id=thread_id,
                        scope_ref=scope_ref,
                        theme=theme,
                        first_tick=event.tick,
                    )
                    world.pressure_threads[thread_id] = thread
                thread.updated_tick = event.tick
                thread.visibility = _pressure_thread_visibility(thread.visibility, event.visibility)
                _extend_unique_tail(thread.event_refs, [event.event_id], limit=8)
                if event.visibility in {"public", "visible", "rumored"}:
                    _extend_unique_tail(
                        thread.public_clues,
                        [player_facing_event_clue(event, world=world)],
                        limit=4,
                    )
                thread.intensity = _pressure_thread_intensity(thread, world)
                thread.status = _pressure_thread_status(thread, world)
                thread.summary = _summarize_pressure_thread(world, thread)
    _prune_pressure_threads(world)


def _refresh_dynamic_structure_lifecycle(world: WorldState, events: list[Event]) -> None:
    direct_event_ticks: dict[str, int] = {}
    for event in events:
        for structure_id in event.dynamic_structure_refs:
            direct_event_ticks[structure_id] = max(
                direct_event_ticks.get(structure_id, event.tick),
                event.tick,
            )

    for structure in world.dynamic_structures.values():
        if structure.structure_id in direct_event_ticks:
            structure.updated_tick = max(
                structure.updated_tick,
                direct_event_ticks[structure.structure_id],
            )
            structure.status = "active"
            continue

        idle_ticks = world.current_tick - structure.updated_tick
        if idle_ticks > 20:
            structure.status = "archived"
        elif idle_ticks > 8:
            structure.status = "cooling"
        elif structure.status not in {"active", "cooling", "archived"}:
            structure.status = "active"


def _refresh_emergent_presence_lifecycle(world: WorldState, events: list[Event]) -> None:
    direct_event_ticks: dict[str, int] = {}
    for event in events:
        for presence_id in event.emergent_presence_refs:
            direct_event_ticks[presence_id] = max(
                direct_event_ticks.get(presence_id, event.tick),
                event.tick,
            )

    for presence in world.emergent_presences.values():
        if presence.presence_id in direct_event_ticks:
            presence.updated_tick = max(
                presence.updated_tick,
                direct_event_ticks[presence.presence_id],
            )
            if presence.status in {"cooling", "dormant", "archived"}:
                presence.status = "active"
            continue

        idle_ticks = world.current_tick - presence.updated_tick
        if idle_ticks > 28:
            presence.status = "archived"
        elif idle_ticks > 14:
            presence.status = "dormant"
        elif idle_ticks > 8:
            presence.status = "cooling"
        elif presence.status not in {"active", "contained", "cooling", "dormant", "archived"}:
            presence.status = "active"


def _pressure_thread_scope_refs(event: Event) -> list[str]:
    refs: list[str] = []
    for ref in (
        event.region_refs
        + event.civ_refs
        + event.faction_refs
        + event.relic_refs
        + event.project_refs
        + event.supply_refs
        + event.node_refs
        + event.dynamic_structure_refs
        + event.emergent_presence_refs
    ):
        if ref not in refs:
            refs.append(ref)
    return refs[:8]


def _pressure_thread_visibility(current: str, incoming: str) -> str:
    priority = {"hidden": 0, "covert": 1, "rumored": 2, "visible": 3, "public": 4}
    return current if priority.get(current, 0) >= priority.get(incoming, 0) else incoming


def _pressure_thread_intensity(thread: PressureThread, world: WorldState) -> str:
    recent_events = [
        event for event in world.event_stream.events
        if event.event_id in thread.event_refs and world.current_tick - event.tick <= 8
    ]
    score = sum(
        {"low": 1, "medium": 2, "high": 3}.get(event.severity, 1)
        + {"low": 0, "medium": 1, "high": 2}.get(event.consequence_score, 0)
        for event in recent_events
    )
    if score >= 10:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def _pressure_thread_status(thread: PressureThread, world: WorldState) -> str:
    age = world.current_tick - thread.first_tick
    recency = world.current_tick - thread.updated_tick
    if recency > 12:
        return "dormant"
    if recency > 4:
        return "cooling"
    if thread.intensity == "high" and len(thread.event_refs) >= 3:
        return "escalating"
    if age >= 3 and len(thread.event_refs) >= 2:
        return "active"
    return "forming"


def _prune_pressure_threads(world: WorldState) -> None:
    stale_ids = [
        thread_id
        for thread_id, thread in world.pressure_threads.items()
        if thread.status == "dormant" and world.current_tick - thread.updated_tick > 24
    ]
    for thread_id in stale_ids:
        del world.pressure_threads[thread_id]

    by_scope: dict[str, list[PressureThread]] = {}
    for thread in world.pressure_threads.values():
        by_scope.setdefault(thread.scope_ref, []).append(thread)
    for threads in by_scope.values():
        if len(threads) <= 5:
            continue
        threads.sort(
            key=lambda thread: (
                _pressure_thread_rank(thread),
                thread.updated_tick,
            ),
            reverse=True,
        )
        for thread in threads[5:]:
            world.pressure_threads.pop(thread.thread_id, None)


def _pressure_thread_rank(thread: PressureThread) -> int:
    intensity_score = {"high": 30, "medium": 20, "low": 10}.get(thread.intensity, 0)
    status_score = {
        "escalating": 5,
        "active": 4,
        "forming": 3,
        "cooling": 2,
        "dormant": 1,
    }.get(thread.status, 0)
    return intensity_score + status_score + min(len(thread.event_refs), 8)


def _summarize_pressure_thread(world: WorldState, thread: PressureThread) -> str:
    subject = _safe_ref_label(world, thread.scope_ref)
    theme_text = {
        "project": "项目线",
        "supply": "补给线",
        "anomaly": "异常线",
        "politics": "政治线",
        "security": "安保线",
        "organization": "组织线",
        "macro": "宏观压力",
    }.get(thread.theme, thread.theme)
    status_text = {
        "forming": "仍在成形",
        "active": "持续发酵",
        "escalating": "正在升温",
        "cooling": "开始降温",
        "dormant": "暂时沉底",
    }.get(thread.status, thread.status)
    return f"{subject} 的{theme_text}{status_text}"


def _refresh_objective_feedback_relations(world: WorldState) -> None:
    event = Event(
        event_id=f"system_objective_feedback_{world.current_tick}",
        tick=world.current_tick,
        time_granularity=world.current_granularity,
        event_type="system_objective_feedback",
        event_scope="system",
        title="Objective feedback sync",
        summary="System synchronized objective feedback relations.",
        severity="low",
        novelty="low",
        consequence_score="low",
        narrative_priority="low",
        visibility="hidden",
    )
    for faction in world.factions.values():
        if faction.parent_civ_id in world.civilizations:
            _upsert_structural_relation_if_needed(
                world,
                source_ref=faction.parent_civ_id,
                target_ref=faction.faction_id,
                relation_type="authorizes",
                event=event,
                notes=f"objective_feedback:authorizes->{faction.faction_id}",
                tags=["organization", "authorization"],
            )
        for region_id in faction.controlled_regions[:4]:
            _upsert_structural_relation_if_needed(
                world,
                source_ref=faction.faction_id,
                target_ref=region_id,
                relation_type="operates_in",
                event=event,
                notes=f"objective_feedback:operates_in->{region_id}",
                tags=["organization", "anchor", "region"],
            )
        target_ref = faction.strategic_objective_target_ref
        if target_ref.startswith("project_"):
            relation_type = "seeking_control" if faction.strategic_objective_status in {"contested", "blocked"} else "sponsoring"
            _upsert_structural_relation_if_needed(
                world,
                source_ref=faction.faction_id,
                target_ref=target_ref,
                relation_type=relation_type,
                event=event,
                notes=f"objective_feedback:{relation_type}->{target_ref}",
                tags=["objective", "project", relation_type],
            )
        elif target_ref.startswith("supply_"):
            relation_type = "contesting" if faction.strategic_objective_status in {"contested", "blocked"} else "supply_influence"
            _upsert_structural_relation_if_needed(
                world,
                source_ref=faction.faction_id,
                target_ref=target_ref,
                relation_type=relation_type,
                event=event,
                notes=f"objective_feedback:{relation_type}->{target_ref}",
                tags=["objective", "supply", relation_type],
            )
        elif target_ref.startswith("region_"):
            _upsert_structural_relation_if_needed(
                world,
                source_ref=faction.faction_id,
                target_ref=target_ref,
                relation_type="stabilizing",
                event=event,
                notes=f"objective_feedback:stabilizing->{target_ref}",
                tags=["objective", "region", "stabilizing"],
            )

    for project in world.projects.values():
        for supply_id in _find_supply_lines_for_project(world, project):
            relation_type = "depends_on" if project.progress_state in {"forming", "stalled", "contested"} else "supported_by_supply"
            _upsert_structural_relation_if_needed(
                world,
                source_ref=project.project_id,
                target_ref=supply_id,
                relation_type=relation_type,
                event=event,
                notes=f"objective_feedback:{relation_type}->{supply_id}",
                tags=["project", "dependency", "supply"],
            )

    for relic in world.relics.values():
        if relic.holder_ref:
            _upsert_structural_relation_if_needed(
                world,
                source_ref=relic.holder_ref,
                target_ref=relic.relic_id,
                relation_type="controls",
                event=event,
                notes=f"objective_feedback:controls->{relic.relic_id}",
                tags=["relic", "control"],
            )

    for node in world.region_nodes.values():
        if node.controller_ref and node.controller_ref in world.factions:
            _upsert_structural_relation_if_needed(
                world,
                source_ref=node.controller_ref,
                target_ref=node.node_id,
                relation_type="controls_node",
                event=event,
                notes=f"objective_feedback:controls_node->{node.node_id}",
                tags=["region_node", "control", node.node_type],
            )
        linked_ref = _region_node_primary_link(node)
        if linked_ref:
            relation_type = "depends_on" if node.contention_state in {"strained", "contested", "blocked"} else "stabilizes_node"
            _upsert_structural_relation_if_needed(
                world,
                source_ref=linked_ref,
                target_ref=node.node_id,
                relation_type=relation_type,
                event=event,
                notes=f"objective_feedback:{relation_type}->{node.node_id}",
                tags=["region_node", "midlayer", node.node_type],
            )
        if node.contention_state in {"contested", "blocked"}:
            for faction_id in _region_node_contesting_factions(world, node)[:3]:
                if faction_id == node.controller_ref:
                    continue
                _upsert_structural_relation_if_needed(
                    world,
                    source_ref=faction_id,
                    target_ref=node.node_id,
                    relation_type="contests_node",
                    event=event,
                    notes=f"objective_feedback:contests_node->{node.node_id}",
                    tags=["region_node", "contest", node.node_type],
                )


def _pick_character_goal_target(character, intent: Intent | None) -> str:
    if intent is not None and intent.target_ref:
        return intent.target_ref
    if character.last_intent:
        last_target = str(character.last_intent.get("target_ref", "") or "")
        if last_target:
            return last_target
    if character.frontier_focus_ref not in {"", "none"}:
        return character.frontier_focus_ref
    return "regional_pressure"


def _summarize_character_active_goal(world: WorldState, character, intent: Intent | None, target_ref: str) -> str:
    focus_type = character.frontier_focus_type
    goal_text = ""
    if intent is not None and intent.goal:
        goal_text = intent.goal
    elif character.recent_goal:
        goal_text = character.recent_goal
    elif character.memory_summary:
        goal_text = character.memory_summary

    if focus_type == "project":
        return "沿项目线稳住预算、合同与执行秩序"
    if focus_type == "supply":
        return "稳住补给走廊的放行节奏并压低运输波动"
    if focus_type == "presence":
        return "围绕异常接入、封控与控制权持续施力"
    if focus_type == "region":
        region_name = world.regions[character.current_region_id].name
        return f"在 {region_name} 持续推动局部局势朝有利方向收束"
    if goal_text:
        return goal_text[:80]
    if target_ref.startswith("project_"):
        return "沿项目节点持续推进执行秩序"
    if target_ref.startswith("supply_"):
        return "围绕补给节点持续争取放行与调配优势"
    if target_ref.startswith("relic_"):
        return "围绕异常焦点持续争取接入与处置主动权"
    return "围绕当前压力线持续寻找可放大的突破口"


def _derive_character_goal_status(character, recent_events: list[Event]) -> str:
    if not recent_events:
        return "forming"
    if any(_event_type_contains(event, "block", "stall", "freeze", "breach", "crisis") for event in recent_events):
        return "blocked"
    if any(_event_type_contains(event, "contest", "struggle", "infiltration", "rival", "attack") for event in recent_events):
        return "contested"
    if character.frontier_focus_shift == "steady" and character.frontier_theme_strength in {"strong", "hard_locked"}:
        return "stabilizing"
    return "advancing"


def _pick_faction_objective_target(world: WorldState, faction) -> str:
    project_refs = _find_projects_for_faction_from_world(world, faction.faction_id)
    if project_refs:
        return project_refs[0]
    supply_refs = _find_supply_for_faction_from_world(world, faction.faction_id)
    if supply_refs:
        return supply_refs[0]
    if faction.controlled_regions:
        return faction.controlled_regions[0]
    return "none"


def _summarize_faction_objective(world: WorldState, faction, target_ref: str) -> str:
    style = faction.operational_style
    if target_ref.startswith("project_"):
        return "把资源与组织动作继续压向核心项目线，确保推进权不被旁路夺走"
    if target_ref.startswith("supply_"):
        return "稳住关键补给走廊，把放行权和调配权继续握在自己手里"
    if style in {"security_bureaucracy", "militia_command", "discipline_hierarchy"}:
        return "继续收紧组织控制链，优先维持秩序与执行服从"
    if style in {"broker_network", "adaptive_network", "market_coalition"}:
        return "在多方竞争中维持接口优势，把更多节点接到自己的协调网络上"
    if target_ref.startswith("region_"):
        return f"围绕 {_safe_ref_label(world, target_ref)} 维持主导权并扩大制度抓手"
    return "在当前结构波动中稳住核心利益，并把下一步施力方向继续钉牢"


def _derive_faction_objective_status(world: WorldState, faction, recent_events: list[Event]) -> str:
    profile = _relation_pressure_profile(world, faction.faction_id)
    if not recent_events:
        if profile["support"] >= 3:
            return "stabilizing"
        if profile["contest"] >= 2:
            return "contested"
        return "forming"
    if any(_event_type_contains(event, "freeze", "stall", "collapse", "breach", "crisis") for event in recent_events):
        return "blocked"
    if profile["contest"] > profile["support"]:
        return "contested"
    if any(_event_type_contains(event, "alliance", "infiltration", "contest", "struggle", "takeover") for event in recent_events):
        return "contested"
    if faction.operational_style_stability in {"locked", "steady"}:
        return "stabilizing"
    return "advancing"


def _recent_project_events_for_refresh(events: list[Event], project) -> list[Event]:
    project_regions = set(project.linked_regions)
    project_relics = set(project.linked_presence_refs)
    return [
        event
        for event in events
        if project.project_id in event.project_refs
        or bool(project_regions.intersection(event.region_refs))
        or bool(project_relics.intersection(event.relic_refs))
    ][-5:]


def _derive_project_progress_state(world: WorldState, project, project_events: list[Event]) -> str:
    profile = _relation_pressure_profile(world, project.project_id)
    if project.status in {"contested", "fragile"}:
        return "contested"
    if project.status in {"strained", "stalled_recovery"}:
        return "stalled"
    if profile["contest"] >= 2 and profile["support"] <= 1:
        return "contested"
    if profile["dependency"] >= 2 and project.pressure == "high":
        return "stalled"
    if any(_event_type_contains(event, "stall", "freeze", "accident", "crisis") for event in project_events):
        return "stalled"
    if any(_event_type_contains(event, "contest", "security", "infiltration") for event in project_events):
        return "contested"
    if any(_event_type_contains(event, "phase_advance", "groundbreaking", "grid_link", "financing") for event in project_events):
        return "advancing"
    if project.pressure == "low":
        return "stabilizing"
    return "forming"


def _summarize_project_progress(world: WorldState, project, project_events: list[Event]) -> str:
    if project.progress_state == "advancing":
        return "项目仍在向前推进，但预算、安保与施工节奏需要同时被维持。"
    if project.progress_state == "stalled":
        return "项目推进已经放慢，预算冻结、事故风险或执行断点正在拖住进度。"
    if project.progress_state == "contested":
        return "项目处于持续争夺中，推进权、接口权与安全壳层都没有完全稳住。"
    if project.progress_state == "stabilizing":
        return "项目主线暂时走稳，外部压力没有完全消失，但节奏已开始收束。"
    if project_events:
        return _summarize_recent_result(world, project_events)
    return "项目仍在成形，暂未沉淀出稳定推进节奏。"


def _recent_supply_events_for_refresh(events: list[Event], supply_line) -> list[Event]:
    supply_regions = {supply_line.origin_region_id, supply_line.destination_region_id}
    return [
        event
        for event in events
        if supply_line.supply_id in event.supply_refs
        or bool(supply_regions.intersection(event.region_refs))
        or "supply" in event_theme_tags(event)
    ][-5:]


def _derive_supply_corridor_state(world: WorldState, supply_line, supply_events: list[Event]) -> str:
    profile = _relation_pressure_profile(world, supply_line.supply_id)
    if supply_line.status in {"contested", "strained"}:
        return "contested" if supply_line.status == "contested" else "strained"
    if profile["contest"] >= 2:
        return "contested"
    if profile["support"] >= 2 and supply_line.pressure == "low":
        return "stable"
    if any(_event_type_contains(event, "reroute", "redirect") for event in supply_events):
        return "rerouting"
    if any(_event_type_contains(event, "contest", "breach", "attack", "seize") for event in supply_events):
        return "contested"
    if supply_line.pressure == "low":
        return "stable"
    if supply_line.pressure == "high":
        return "strained"
    return "forming"


def _summarize_supply_corridor(world: WorldState, supply_line, supply_events: list[Event]) -> str:
    if supply_line.corridor_state == "stable":
        return "主走廊仍在运转，控制权和放行节奏暂时没有明显失序。"
    if supply_line.corridor_state == "contested":
        return "补给线仍在运转，但控制权与放行节奏都处于可见争夺中。"
    if supply_line.corridor_state == "strained":
        return "补给线持续承压，运输、储备与风险隔离都在消耗通行效率。"
    if supply_line.corridor_state == "rerouting":
        return "补给线正在被迫改道，既有通路已经不足以承接当前压力。"
    if supply_events:
        return _summarize_recent_result(world, supply_events)
    return "补给走廊仍在成形，暂未沉淀出稳定控制方式。"


def _derive_relic_contest_state(world: WorldState, relic, relic_events: list[Event]) -> str:
    profile = _relation_pressure_profile(world, relic.relic_id)
    if relic.activation_state in {"sealed", "dormant"} and not relic_events:
        return "suppressed"
    if profile["support"] >= 2 and profile["contest"] == 0 and relic.holder_ref:
        return "controlled"
    if profile["contest"] >= 2:
        return "contested"
    if any(_event_type_contains(event, "containment", "lockdown", "cordon") for event in relic_events):
        return "suppressed"
    if any(_event_type_contains(event, "contest", "breach", "infiltration", "attack", "migration") for event in relic_events):
        return "contested"
    if relic.holder_ref:
        return "controlled"
    return "forming"


def _collect_relic_contesting_refs(world: WorldState, relic, relic_events: list[Event]) -> list[str]:
    refs: list[str] = []
    if relic.holder_ref:
        _push_unique(refs, relic.holder_ref, limit=6)
    for relation in relations_for_ref(world, relic.relic_id, limit=10):
        counterparty = relation.target_ref if relation.source_ref == relic.relic_id else relation.source_ref
        if counterparty in world.factions or counterparty in world.characters:
            _push_unique(refs, counterparty, limit=6)
    for event in relic_events:
        for ref in event.actor_refs + event.faction_refs:
            if ref in world.characters or ref in world.factions:
                _push_unique(refs, ref, limit=6)
    return refs


def _summarize_relic_contest(world: WorldState, relic, relic_events: list[Event]) -> str:
    if relic.contest_state == "suppressed":
        return "异常目前主要处于封控与压制之下，外部接入窗口被明显收窄。"
    if relic.contest_state == "contested":
        return "异常接入权仍在争夺，封控、渗透与机会性介入同时存在。"
    if relic.contest_state == "controlled":
        holder = _safe_ref_label(world, relic.holder_ref)
        return f"异常暂时由 {holder} 把持，但周边争夺压力并没有完全退去。"
    if relic_events:
        return _summarize_recent_result(world, relic_events)
    return "异常周边仍在成形，尚未出现稳定主控或全面争夺。"


def _collect_event_blockers(events: list[Event], *, limit: int) -> list[str]:
    blockers: list[str] = []
    for event in reversed(events):
        for blocker in _derive_blockers_from_event(event):
            _push_unique(blockers, blocker, limit=limit)
            if len(blockers) >= limit:
                return blockers
    return blockers


def _collect_faction_objective_blockers(world: WorldState, faction, events: list[Event]) -> list[str]:
    blockers = _collect_event_blockers(events, limit=3)
    profile = _relation_pressure_profile(world, faction.faction_id)
    if profile["dependency"] >= 2:
        _push_unique(blockers, "关键依赖链过长，推进容易被卡住", limit=3)
    if profile["contest"] >= 2:
        _push_unique(blockers, "对手链持续施压，组织主轴难以完全锁定", limit=3)
    return blockers


def _collect_project_progress_blockers(world: WorldState, project, events: list[Event]) -> list[str]:
    blockers = _collect_event_blockers(events, limit=3)
    profile = _relation_pressure_profile(world, project.project_id)
    if profile["dependency"] >= 2:
        _push_unique(blockers, "项目依赖链过重，单点失衡会拖慢整体推进", limit=3)
    if profile["contest"] >= 2:
        _push_unique(blockers, "项目控制权仍在争抢，执行权难以完全落定", limit=3)
    return blockers


def _collect_supply_corridor_blockers(world: WorldState, supply_line, events: list[Event]) -> list[str]:
    blockers = _collect_event_blockers(events, limit=3)
    profile = _relation_pressure_profile(world, supply_line.supply_id)
    if profile["contest"] >= 2:
        _push_unique(blockers, "线路控制权持续摇摆，放行节奏不容易稳定", limit=3)
    if profile["dependency"] >= 1 and supply_line.pressure == "high":
        _push_unique(blockers, "沿线依赖节点过多，任何迟滞都会沿通道放大", limit=3)
    return blockers


def _recent_region_node_events(world: WorldState, node, events: list[Event]) -> list[Event]:
    linked_refs = {
        ref
        for ref in [
            node.linked_project_id,
            node.linked_supply_id,
            node.linked_relic_id,
        ]
        if ref
    }
    return [
        event
        for event in events
        if node.node_id in event.node_refs
        or node.region_id in event.region_refs
        or bool(linked_refs.intersection(event.relic_refs))
        or bool(linked_refs.intersection(event.project_refs + event.supply_refs))
        or (node.linked_project_id and "project" in event_theme_tags(event))
        or (node.linked_supply_id and "supply" in event_theme_tags(event))
    ][-5:]


def _derive_region_node_pressure(world: WorldState, node) -> str:
    levels = [_pressure_score(node.pressure)]
    if node.linked_project_id in world.projects:
        levels.append(_pressure_score(world.projects[node.linked_project_id].pressure))
    if node.linked_supply_id in world.supply_lines:
        levels.append(_pressure_score(world.supply_lines[node.linked_supply_id].pressure))
    if node.linked_relic_id in world.relics:
        levels.append(_pressure_score(world.relics[node.linked_relic_id].danger))
    region = world.regions.get(node.region_id)
    if region is not None:
        levels.append(_pressure_score(region.security))
        levels.append(_pressure_score(region.scarcity))
    profile = _relation_pressure_profile(world, node.node_id)
    if profile["contest"] >= 2:
        levels.append(3)
    if profile["support"] >= 2 and max(levels) <= 2:
        levels.append(1)
    return _pressure_label(max(levels) if levels else 2)


def _derive_region_node_contention_state(world: WorldState, node, node_events: list[Event]) -> str:
    profile = _relation_pressure_profile(world, node.node_id)
    if any(_event_type_contains(event, "breach", "crisis", "stall", "freeze", "accident") for event in node_events):
        return "blocked"
    if profile["contest"] >= 2:
        return "contested"
    if any(_event_type_contains(event, "contest", "infiltration", "attack", "seize") for event in node_events):
        return "contested"
    if node.linked_project_id in world.projects and world.projects[node.linked_project_id].progress_state in {"stalled", "contested"}:
        return world.projects[node.linked_project_id].progress_state
    if node.linked_supply_id in world.supply_lines and world.supply_lines[node.linked_supply_id].corridor_state in {"strained", "contested", "rerouting"}:
        return world.supply_lines[node.linked_supply_id].corridor_state
    if node.linked_relic_id in world.relics and world.relics[node.linked_relic_id].contest_state in {"contested", "suppressed"}:
        return world.relics[node.linked_relic_id].contest_state
    if profile["support"] >= 2 or node.pressure == "low":
        return "stabilizing"
    return "forming"


def _collect_region_node_blockers(world: WorldState, node, node_events: list[Event]) -> list[str]:
    blockers = _collect_event_blockers(node_events, limit=3)
    profile = _relation_pressure_profile(world, node.node_id)
    if profile["contest"] >= 2:
        _push_unique(blockers, "节点控制权正在被多方争抢", limit=3)
    if node.node_type == "release_gate" and node.pressure == "high":
        _push_unique(blockers, "放行节奏受补给压力牵制", limit=3)
    if node.node_type == "construction_interface" and node.pressure == "high":
        _push_unique(blockers, "施工接口承接了过高执行压力", limit=3)
    if node.node_type == "containment_checkpoint":
        _push_unique(blockers, "封锁关口持续消耗安保与处置资源", limit=3)
    return blockers


def _summarize_region_node_state(world: WorldState, node, node_events: list[Event]) -> str:
    linked_label = _safe_ref_label(world, _region_node_primary_link(node)) if _region_node_primary_link(node) else "局部压力线"
    if node.contention_state == "blocked":
        return f"{linked_label} 周边的节点已经被事故、封锁或断点拖住，短期内难以顺畅运转。"
    if node.contention_state == "contested":
        return f"{linked_label} 周边的节点处在争夺中，控制权和通行节奏都没有完全落定。"
    if node.contention_state == "strained":
        return f"{linked_label} 周边的节点仍能运转，但压力正在消耗它的吞吐和协调空间。"
    if node.contention_state == "suppressed":
        return f"{linked_label} 周边的节点被封控壳层压住，外部接入窗口明显收窄。"
    if node.contention_state == "stabilizing":
        return f"{linked_label} 周边的节点暂时走稳，仍会继续牵动附近行动。"
    if node_events:
        return _summarize_recent_result(world, node_events)
    return f"{linked_label} 周边的节点仍在成形，尚未沉淀出稳定控制方式。"


def _region_node_recent_notes(world: WorldState, node, node_events: list[Event]) -> list[str]:
    notes = [
        f"state={node.contention_state}",
        f"pressure={node.pressure}",
    ]
    if node.controller_ref:
        notes.append(f"controller={node.controller_ref}")
    for event in node_events[-3:]:
        notes.append(f"tick_{world.current_tick}:{event.event_type}@{node.region_id}")
    return notes


def _region_node_primary_link(node) -> str | None:
    return node.linked_project_id or node.linked_supply_id or node.linked_relic_id


def _region_node_contesting_factions(world: WorldState, node) -> list[str]:
    refs: list[str] = []
    linked_ref = _region_node_primary_link(node)
    if linked_ref:
        for relation in relations_for_ref(world, linked_ref, limit=12):
            counterparty = relation.target_ref if relation.source_ref == linked_ref else relation.source_ref
            if counterparty in world.factions and relation.relation_type in {"contesting", "obstructing", "opposing", "seeking_control"}:
                _push_unique(refs, counterparty, limit=6)
    region = world.regions.get(node.region_id)
    if region is not None:
        for faction_id in region.active_factions:
            _push_unique(refs, faction_id, limit=6)
    return refs


def _pressure_score(value: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(value, 2)


def _pressure_label(score: int) -> str:
    if score >= 3:
        return "high"
    if score <= 1:
        return "low"
    return "medium"


def _relation_pressure_profile(world: WorldState, ref: str) -> dict[str, int]:
    profile = {"support": 0, "contest": 0, "dependency": 0}
    for relation in relations_for_ref(world, ref, limit=16):
        if relation.status != "active":
            continue
        relation_type = relation.relation_type
        if relation_type in {
            "allied_with",
            "supports",
            "supporting",
            "stabilizes",
            "contracting",
            "financing",
            "sponsoring",
            "controls",
            "supply_influence",
            "authorizes",
            "operates_in",
            "supported_by_supply",
            "controls_node",
            "stabilizes_node",
        }:
            profile["support"] += 1
        elif relation_type in {
            "rival_to",
            "contesting",
            "obstructing",
            "opposing",
            "infiltrating",
            "seeking_control",
            "flashpoint_actor",
            "contests_node",
        }:
            profile["contest"] += 1
        elif relation_type in {"depends_on"}:
            profile["dependency"] += 1
    return profile


def _find_supply_lines_for_project(world: WorldState, project) -> list[str]:
    refs: list[str] = []
    project_regions = set(project.linked_regions)
    for supply_line in world.supply_lines.values():
        line_regions = {supply_line.origin_region_id, supply_line.destination_region_id}
        if project_regions.intersection(line_regions):
            _push_unique(refs, supply_line.supply_id, limit=4)
    return refs


def _derive_blockers_from_event(event: Event) -> list[str]:
    event_type = event.event_type.lower()
    blockers: list[str] = []
    if any(token in event_type for token in {"freeze", "financing"}):
        blockers.append("预算与融资节奏不稳")
    if any(token in event_type for token in {"security", "containment", "cordon", "lockdown"}):
        blockers.append("安保封控正在抬高执行摩擦")
    if any(token in event_type for token in {"contest", "struggle", "infiltration", "takeover"}):
        blockers.append("多方争夺导致接口权持续摇摆")
    if any(token in event_type for token in {"breach", "migration", "spillover", "lifeform"}):
        blockers.append("异常外溢风险打断正常推进")
    if any(token in event_type for token in {"supply", "reroute", "resource"}):
        blockers.append("运输与资源调配链路承压")
    if any(token in event_type for token in {"accident", "crisis", "stall"}):
        blockers.append("现场失稳拖慢整体节奏")
    if not blockers and event.severity == "high":
        blockers.append("高强度局势波动抬高了推进成本")
    return blockers


def _summarize_recent_result(world: WorldState, events: list[Event]) -> str:
    if not events:
        return "最近尚未形成稳定结果。"
    latest = events[-1]
    region_label = _safe_ref_label(world, latest.region_refs[0]) if latest.region_refs else "局部区域"
    event_type = latest.event_type.lower()
    if any(token in event_type for token in {"phase_advance", "groundbreaking", "grid_link"}):
        return f"{region_label} 最近出现了明确推进迹象，局部节奏暂时向前迈了一步。"
    if any(token in event_type for token in {"freeze", "stall", "crisis", "breach"}):
        return f"{region_label} 最近再次失稳，原本推进节奏被明显拖慢。"
    if any(token in event_type for token in {"alliance", "financing", "contract", "budget"}):
        return f"{region_label} 最近发生了一次关键接口重排，资源和执行链重新洗牌。"
    if any(token in event_type for token in {"containment", "security", "lockdown"}):
        return f"{region_label} 最近的封控动作抬高了稳定性，但也让行动空间进一步收紧。"
    return _player_localize_result_text(latest.summary)


def _player_localize_result_text(summary: str) -> str:
    text = summary.strip()
    if not text:
        return "最近形成了一次局部结果，但暂未沉淀为稳定趋势。"
    lowered = text.lower()
    if "moved to stabilize supply conditions in" in lowered:
        return "最近一次施力后，补给节奏暂时被稳住，但运输压力还没有完全退去。"
    if "moved to secure relic access in" in lowered:
        return "最近一次施力后，异常接入权被重新推到前台，争夺还会继续。"
    if "moved to secure" in lowered:
        return "最近一次施力后，关键接入权被重新拉回争夺中心。"
    if "supply and logistics through" in lowered:
        return "最近一次动作改写了补给与物流走向，后续节奏仍会继续波动。"
    if "budget" in lowered and "control" in lowered:
        return "最近一次动作触发了预算与控制链重排，推进顺序随之改变。"
    if "infiltrate" in lowered:
        return "最近一次变化显示，暗线渗透仍在推进，局势还没有真正走稳。"
    normalized = (
        text.replace("->", "到")
        .replace("_", " ")
        .replace("  ", " ")
        .strip()
    )
    if len(normalized) > 48:
        return normalized[:48].rstrip() + "..."
    return normalized


def _safe_ref_label(world: WorldState, ref: str) -> str:
    if ref in world.region_nodes:
        return world.region_nodes[ref].name
    if ref in world.regions:
        return world.regions[ref].name
    if ref in world.projects:
        return world.projects[ref].name
    if ref in world.supply_lines:
        return world.supply_lines[ref].name
    if ref in world.relics:
        return world.relics[ref].name
    if ref in world.factions:
        return world.factions[ref].name
    if ref in world.characters:
        return world.characters[ref].name
    if ref in world.dynamic_structures:
        return world.dynamic_structures[ref].name
    if ref in world.emergent_presences:
        return world.emergent_presences[ref].name
    return ref


def _find_projects_for_faction_from_world(world: WorldState, faction_id: str) -> list[str]:
    refs: list[str] = []
    for project in world.projects.values():
        if faction_id in (
            project.sponsor_refs
            + project.contractor_refs
            + project.financier_refs
            + project.opposition_refs
            + project.linked_factions
        ):
            _push_unique(refs, project.project_id, limit=6)
    return refs


def _find_supply_for_faction_from_world(world: WorldState, faction_id: str) -> list[str]:
    refs: list[str] = []
    for supply_line in world.supply_lines.values():
        if supply_line.controlling_faction_ref == faction_id or faction_id in supply_line.linked_civ_refs:
            _push_unique(refs, supply_line.supply_id, limit=6)
    return refs


def _event_type_contains(event: Event, *tokens: str) -> bool:
    event_type = event.event_type.lower()
    return any(token in event_type for token in tokens)


def _build_civilization_bias_trace(world: WorldState, civilization, civ_events: list[Event]) -> list[str]:
    posture = civilization.strategic_posture
    recent_events = civ_events[-6:]
    trace: list[str] = []
    frame = world.structure_template
    action_bias = {
        "containment_first": [
            "bias_actions=relic_control, containment, spillover_suppression",
            "bias_character_fronts=seal_migration_corridor, contain_relic_fallout",
        ],
        "megastructure_expansion": [
            "bias_actions=project_bid, financing_realignment, supply_for_build",
            "bias_character_fronts=secure_project_budget, redirect_project_financing",
        ],
        "stability_over_growth": [
            "bias_actions=alliance, infiltration, power_struggle",
            "bias_character_fronts=manage_unrest, broker_power_shift",
        ],
        "opportunistic_extraction": [
            "bias_actions=resource_reallocation, relic_contest, leverage_capture",
            "bias_character_fronts=secure_relic_access, seize_supply_leverage",
        ],
        "balanced_competition": [
            "bias_actions=distributed",
            "bias_character_fronts=expand_influence",
        ],
    }
    trace.extend(action_bias.get(posture, action_bias["balanced_competition"]))
    trace.append(
        "world_frame="
        f"axes:{'/'.join(frame.pressure_axes[:2])}"
        f"|fronts:{'/'.join(frame.dominant_fronts[:2])}"
        f"|anomaly:{frame.anomaly_bias}"
    )
    trace.append(
        "organization_climate="
        + ("/".join(frame.organization_climates[:2]) if frame.organization_climates else "none")
    )
    trace.append(
        "posture_inertia="
        f"{civilization.strategic_posture_stability}"
        f"(pending={civilization.strategic_posture_pending}, hits={civilization.strategic_posture_pending_hits})"
    )
    for event in recent_events[-3:]:
        focal_region = event.region_refs[0] if event.region_refs else "unknown_region"
        trace.append(f"recent_pull={event.event_type}@{focal_region}")
    return trace[-5:]


def _apply_structure_template_posture_nudge(world: WorldState, posture: str) -> str:
    frame = world.structure_template
    if frame.anomaly_bias == "megastructure_pressure" and "project_fronts" in frame.dominant_fronts:
        if posture in {"balanced_competition", "opportunistic_extraction"}:
            return "megastructure_expansion"
    if frame.anomaly_bias in {"biosecurity_pressure", "autonomous_system_pressure"}:
        if posture in {"balanced_competition", "stability_over_growth"}:
            return "containment_first"
    if "legitimacy_erosion" in frame.pressure_axes and "governance_fronts" in frame.dominant_fronts:
        if posture == "balanced_competition":
            return "stability_over_growth"
    if "supply_strain" in frame.pressure_axes and posture == "balanced_competition":
        return "opportunistic_extraction"
    return posture


def _apply_civilization_posture_inertia(civilization, proposed_posture: str) -> None:
    current = civilization.strategic_posture
    if proposed_posture == current:
        civilization.strategic_posture_pending = "none"
        civilization.strategic_posture_pending_hits = 0
        civilization.strategic_posture_stability = "locked" if current != "balanced_competition" else "steady"
        return

    if civilization.strategic_posture_pending == proposed_posture:
        civilization.strategic_posture_pending_hits += 1
    else:
        civilization.strategic_posture_pending = proposed_posture
        civilization.strategic_posture_pending_hits = 1

    threshold = 2 if current != "balanced_competition" else 1
    if civilization.strategic_posture_pending_hits >= threshold:
        civilization.strategic_posture = proposed_posture
        civilization.strategic_posture_pending = "none"
        civilization.strategic_posture_pending_hits = 0
        civilization.strategic_posture_stability = "redirected"
    else:
        civilization.strategic_posture_stability = "contested"


def _refresh_character_frontier_focus(character, recent_history: list[str]) -> None:
    previous_focus_ref = character.frontier_focus_ref
    focus_counter: Counter[tuple[str, str]] = Counter()
    focus_trace_map: dict[tuple[str, str], list[str]] = {}
    latest_index: dict[tuple[str, str], int] = {}
    for index, entry in enumerate(recent_history):
        focus_ref = _extract_focus_ref_from_history(entry)
        focus_type = _derive_focus_type_from_ref(focus_ref)
        focus_key = (focus_ref, focus_type)
        focus_counter[focus_key] += 1
        focus_trace_map.setdefault(focus_key, []).append(entry)
        latest_index[focus_key] = index

    if not focus_counter:
        character.frontier_focus_ref = "none"
        character.frontier_focus_type = "none"
        character.frontier_focus_shift = "steady"
        character.frontier_focus_trace = []
        character.frontier_focus_reason = "none"
        return

    focus_ref, focus_type = max(
        focus_counter,
        key=lambda item: (focus_counter[item], latest_index.get(item, -1)),
    )
    character.frontier_focus_ref = focus_ref
    character.frontier_focus_type = focus_type
    character.frontier_focus_shift = _derive_frontier_focus_shift(previous_focus_ref, focus_ref)
    character.frontier_focus_trace = focus_trace_map[(focus_ref, focus_type)][-4:]
    character.frontier_focus_reason = _derive_frontier_focus_reason(
        focus_ref,
        focus_type,
        character.frontier_theme,
        character.frontier_focus_trace,
    )


def _extract_focus_ref_from_history(entry: str) -> str:
    marker = "focal="
    if marker not in entry:
        return "regional_pressure"
    return entry.split(marker, 1)[1].rstrip("]")


def _derive_focus_type_from_ref(focus_ref: str) -> str:
    if focus_ref.startswith("project_"):
        return "project"
    if focus_ref.startswith("supply_"):
        return "supply"
    if focus_ref.startswith("relic_"):
        return "presence"
    if focus_ref.startswith("region_"):
        return "region"
    if focus_ref == "regional_pressure":
        return "pressure"
    return "unknown"


def _derive_frontier_focus_shift(previous_focus_ref: str, current_focus_ref: str) -> str:
    if previous_focus_ref in {"none", ""}:
        return "emerging"
    if previous_focus_ref == current_focus_ref:
        return "steady"
    return "redirected"


def _derive_frontier_focus_reason(
    focus_ref: str,
    focus_type: str,
    frontier_theme: str,
    focus_trace: list[str],
) -> str:
    if focus_ref == "none":
        return "none"
    latest_entry = focus_trace[-1] if focus_trace else ""
    event_type = _extract_event_type_from_history(latest_entry) if latest_entry else "unknown"
    if focus_type == "presence":
        if "megastructure" in event_type or frontier_theme == "project_operator":
            return "这个对象持续牵引项目线、预算线或建造秩序，是角色当前最稳定的前线锚点"
        if "protocol" in event_type or "archive" in event_type:
            return "这个对象持续牵引合法性与封控压力，角色会反复回到这里处理外溢风险"
        if "lifeform" in event_type or "migration" in event_type:
            return "这个对象持续制造扩散和追踪压力，角色会沿着它的活动边缘行动"
        return "这个对象反复出现在最近行动里，已经成为角色当前最稳定的异常锚点"
    if focus_type == "region":
        return "这个区域反复承接角色最近行动，已经成为他当前最主要的前线舞台"
    if focus_type == "pressure":
        return "角色当前被一类持续压力牵引，而不是被单一对象锁定"
    return "最近几步行动不断回到同一目标，因此它成为当前关注核心"


def _detect_crisis_override(events: list[Event]) -> str | None:
    for event in reversed(events):
        if _is_crisis_event(event):
            return _update_civilization_posture("balanced_competition", event)
    return None


def _resolve_frontier_focus_ref(world: WorldState, intent: Intent, event: Event) -> str:
    region_id = event.region_refs[0] if event.region_refs else intent.target_ref
    if intent.intent_type in {
        "secure_project_budget",
        "contest_project_contract",
        "redirect_project_financing",
        "suppress_site_accident_fallout",
    }:
        project_id = _find_project_id_for_region(world, region_id)
        if project_id is not None:
            return project_id
    if intent.intent_type in {"stabilize_supply", "seize_supply_leverage"}:
        supply_id = _find_supply_id_for_region(world, region_id)
        if supply_id is not None:
            return supply_id
    if event.relic_refs:
        return event.relic_refs[0]
    return "regional_pressure"


def _find_project_id_for_region(world: WorldState, region_id: str) -> str | None:
    for project in world.projects.values():
        if region_id in project.linked_regions:
            return project.project_id
    return None


def _find_supply_id_for_region(world: WorldState, region_id: str) -> str | None:
    for supply_line in world.supply_lines.values():
        if region_id in {supply_line.origin_region_id, supply_line.destination_region_id}:
            return supply_line.supply_id
    return None


def _is_crisis_event(event: Event) -> bool:
    if event.severity == "high" and event.consequence_score == "high":
        return True
    if event.severity != "high":
        return False
    event_type = event.event_type.lower()
    themes = set(event_theme_tags(event))
    if "anomaly" in themes and any(
        token in event_type for token in {"migration", "containment", "shock", "breach", "lifeform"}
    ):
        return True
    if "project" in themes and any(token in event_type for token in {"accident", "crisis", "breakthrough"}):
        return True
    return False


def _force_civilization_posture(civilization, posture: str) -> None:
    if posture == civilization.strategic_posture:
        civilization.strategic_posture_stability = "crisis_locked"
        civilization.strategic_posture_pending = "none"
        civilization.strategic_posture_pending_hits = 0
        return
    civilization.strategic_posture = posture
    civilization.strategic_posture_pending = "none"
    civilization.strategic_posture_pending_hits = 0
    civilization.strategic_posture_stability = "crisis_redirected"
