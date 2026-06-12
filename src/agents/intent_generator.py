"""Structured intent generation."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.agents.fallback import Intent, build_fallback_intent_from_event
from src.agents.knowledge import CharacterKnowledgeSnapshot, build_character_knowledge_snapshot
from src.agents.llm_client import LLMClientError, build_siliconflow_client, llm_source_label
from src.agents.prompt_builder import build_intent_messages
from src.agents.scheduler import WakeSchedule
from src.core.ai_policy import evaluate_intent_llm_policy
from src.core.ai_tiers import resolve_intent_tier
from src.events.taxonomy import event_theme_tags
from src.world.character import Character
from src.world.relations import relations_for_ref
from src.world.state import WorldState


@dataclass(slots=True)
class IntentBatch:
    """Grouped structured intents for the current step."""

    protagonists: list[Intent] = field(default_factory=list)
    active_characters: list[Intent] = field(default_factory=list)
    last_llm_error: str | None = None

    @property
    def all_intents(self) -> list[Intent]:
        """Return all intents in display order."""
        return self.protagonists + self.active_characters


def generate_intents(
    state: WorldState,
    schedule: WakeSchedule,
    ai_config: dict[str, object],
) -> IntentBatch:
    """Generate intents using configured LLM provider when available, otherwise fallback logic."""
    client = build_siliconflow_client(ai_config)
    errors: list[str] = []
    protagonist_intents = [
        _build_intent_for_character(
            state=state,
            character=state.characters[candidate.character_id],
            is_protagonist=True,
            client=client,
            ai_config=ai_config,
            errors=errors,
        )
        for candidate in schedule.protagonists
    ]
    active_intents = [
        _build_intent_for_character(
            state=state,
            character=state.characters[candidate.character_id],
            is_protagonist=False,
            client=client,
            ai_config=ai_config,
            errors=errors,
        )
        for candidate in schedule.active_characters
    ]
    return IntentBatch(
        protagonists=protagonist_intents,
        active_characters=active_intents,
        last_llm_error=errors[-1] if errors else None,
    )


def _build_intent_for_character(
    state: WorldState,
    character: Character,
    is_protagonist: bool,
    client: object | None,
    ai_config: dict[str, object],
    errors: list[str],
) -> Intent:
    knowledge = build_character_knowledge_snapshot(state, character)
    posture = _find_character_civilization_posture(state, character)
    faction_style, doctrine_tags = _find_character_faction_style(state, character)
    frame = state.structure_template
    intent_signal = _intent_signal_score(state, character, knowledge)
    policy = evaluate_intent_llm_policy(
        ai_config,
        protagonist=is_protagonist,
        signal_score=intent_signal,
    )
    if client is not None and policy.allowed:
        try:
            tier = resolve_intent_tier(ai_config, protagonist=is_protagonist)
            payload = client.create_json_completion_with_limits(
                build_intent_messages(state, character, knowledge),
                max_tokens=tier.max_tokens,
                thinking_budget=tier.thinking_budget,
            )
            return _intent_from_payload(
                character,
                payload,
                source=llm_source_label(ai_config, client),
            )
        except LLMClientError as exc:
            errors.append(str(exc))
            pass

    region = state.regions[character.current_region_id]
    local_relic_event = _find_recent_relic_event_for_region(knowledge, region.region_id)
    base_intent = build_fallback_intent_from_event(character, region, local_relic_event, state)
    base_intent = _apply_faction_style_placeholder_bias(
        base_intent,
        region=region,
        faction_style=faction_style,
        doctrine_tags=doctrine_tags,
        posture=posture,
        frame=frame,
        hard_constraint=local_relic_event is not None,
    )
    flashpoint_region_id = knowledge.flashpoint_region_id
    flashpoint_region = (
        state.regions[flashpoint_region_id]
        if flashpoint_region_id is not None and flashpoint_region_id in state.regions
        else None
    )
    strategic_front_region = _find_cross_region_front(state, knowledge)
    relation_pressure = _find_character_relation_pressure(state, character)

    if not is_protagonist:
        if strategic_front_region is not None and strategic_front_region.region_id != region.region_id:
            cross_region_intent = _build_cross_region_front_intent(
                state,
                character,
                strategic_front_region.region_id,
                protagonist=False,
                posture=posture,
                knowledge=knowledge,
            )
            if cross_region_intent is not None:
                return _apply_faction_style_placeholder_bias(
                    cross_region_intent,
                    region=strategic_front_region,
                    faction_style=faction_style,
                    doctrine_tags=doctrine_tags,
                    posture=posture,
                    frame=frame,
                    hard_constraint=True,
                )
        if flashpoint_region is not None and flashpoint_region.region_id != region.region_id:
            front_intent = _build_frontline_placeholder_intent(
                state,
                character,
                flashpoint_region.region_id,
                recent_event=_find_recent_relic_event_for_region(knowledge, flashpoint_region.region_id),
                protagonist=False,
                posture=posture,
            )
            if front_intent is not None:
                return _apply_faction_style_placeholder_bias(
                    front_intent,
                    region=flashpoint_region,
                    faction_style=faction_style,
                    doctrine_tags=doctrine_tags,
                    posture=posture,
                    frame=frame,
                    hard_constraint=True,
                )
            return Intent(
                character_id=character.char_id,
                intent_type="secure_relic_access",
                target_ref=flashpoint_region.region_id,
                goal="Secure a foothold near the relic flashpoint",
                motivation="Recent relic conflict is reshaping leverage and access nearby",
                risk_tolerance="medium",
                urgency=0.71,
                proposed_action="Move toward the contested district and lock down fragile access seams",
                tone="watchful",
                source="placeholder",
            )
        return base_intent

    if strategic_front_region is not None and strategic_front_region.region_id != region.region_id:
        cross_region_intent = _build_cross_region_front_intent(
            state,
            character,
            strategic_front_region.region_id,
            protagonist=True,
            posture=posture,
            knowledge=knowledge,
        )
        if cross_region_intent is not None:
            return _apply_faction_style_placeholder_bias(
                cross_region_intent,
                region=strategic_front_region,
                faction_style=faction_style,
                doctrine_tags=doctrine_tags,
                posture=posture,
                frame=frame,
                hard_constraint=True,
            )

    if flashpoint_region is not None:
        front_intent = _build_frontline_placeholder_intent(
            state,
            character,
            flashpoint_region.region_id,
            recent_event=_find_recent_relic_event_for_region(knowledge, flashpoint_region.region_id),
            protagonist=True,
            posture=posture,
        )
        if front_intent is not None:
            return _apply_faction_style_placeholder_bias(
                front_intent,
                region=flashpoint_region,
                faction_style=faction_style,
                doctrine_tags=doctrine_tags,
                posture=posture,
                frame=frame,
                hard_constraint=True,
            )
        return _apply_faction_style_placeholder_bias(
            Intent(
            character_id=character.char_id,
            intent_type="secure_relic_access",
            target_ref=flashpoint_region.region_id,
            goal="Take control of the relic access order",
            motivation="Control around the relic will influence the next regional balance",
            risk_tolerance="high",
            urgency=0.91,
            proposed_action="Exploit the contested relic zone and impose a managed access regime",
            tone="cold and forceful",
            source="placeholder",
            ),
            region=flashpoint_region,
            faction_style=faction_style,
            doctrine_tags=doctrine_tags,
            posture=posture,
            frame=frame,
            hard_constraint=True,
        )

    relation_intent = _build_relation_pressure_intent(
        character=character,
        region=region,
        posture=posture,
        relation_pressure=relation_pressure,
        protagonist=is_protagonist,
        frame=frame,
    )
    if relation_intent is not None:
        return _apply_faction_style_placeholder_bias(
            relation_intent,
            region=region,
            faction_style=faction_style,
            doctrine_tags=doctrine_tags,
            posture=posture,
            frame=frame,
        )

    if region.political_tension == "high":
        if posture == "containment_first":
            intent = Intent(
                character_id=character.char_id,
                intent_type="contain_relic_fallout",
                target_ref=region.region_id,
                goal="Keep local disorder from escalating into an anomaly breach",
                motivation="This civilization is prioritizing containment over opportunistic power plays",
                risk_tolerance="medium",
                urgency=0.82,
                proposed_action=_political_front_action(frame, "containment"),
                tone="hard",
                source="placeholder",
            )
            return _apply_faction_style_placeholder_bias(
                intent,
                region=region,
                faction_style=faction_style,
                doctrine_tags=doctrine_tags,
                posture=posture,
                frame=frame,
            )
        if posture == "stability_over_growth":
            intent = Intent(
                character_id=character.char_id,
                intent_type="manage_unrest",
                target_ref=region.region_id,
                goal="Absorb tension before it fractures the governing order",
                motivation="The wider civilization is leaning toward order preservation over expansion",
                risk_tolerance="medium",
                urgency=0.86,
                proposed_action=_political_front_action(frame, "stability"),
                tone="restrained and calculating",
                source="placeholder",
            )
            return _apply_faction_style_placeholder_bias(
                intent,
                region=region,
                faction_style=faction_style,
                doctrine_tags=doctrine_tags,
                posture=posture,
                frame=frame,
            )
        intent = Intent(
            character_id=character.char_id,
            intent_type="broker_power_shift",
            target_ref=region.region_id,
            goal="Reorder local power relations under rising tension",
            motivation=_political_front_motivation(frame),
            risk_tolerance="high",
            urgency=0.88,
            proposed_action=_political_front_action(frame, "power_shift"),
            tone="cold and forceful",
            source="placeholder",
        )
        return _apply_faction_style_placeholder_bias(
            intent,
            region=region,
            faction_style=faction_style,
            doctrine_tags=doctrine_tags,
            posture=posture,
            frame=frame,
        )

    if region.scarcity == "high":
        if posture == "megastructure_expansion":
            intent = Intent(
                character_id=character.char_id,
                intent_type="secure_project_budget",
                target_ref=region.region_id,
                goal="Protect project momentum against scarcity-driven collapse",
                motivation="Expansion posture reframes shortage as a funding and build continuity problem",
                risk_tolerance="medium",
                urgency=0.83,
                proposed_action=_supply_front_action(frame, "project"),
                tone="hard",
                source="placeholder",
            )
            return _apply_faction_style_placeholder_bias(
                intent,
                region=region,
                faction_style=faction_style,
                doctrine_tags=doctrine_tags,
                posture=posture,
                frame=frame,
            )
        intent = Intent(
            character_id=character.char_id,
            intent_type="seize_supply_leverage",
            target_ref=region.region_id,
            goal="Turn supply crisis into durable leverage",
            motivation=_supply_front_motivation(frame),
            risk_tolerance="medium",
            urgency=0.84,
            proposed_action=_supply_front_action(frame, "leverage"),
            tone="restrained and calculating",
            source="placeholder",
        )
        return _apply_faction_style_placeholder_bias(
            intent,
            region=region,
            faction_style=faction_style,
            doctrine_tags=doctrine_tags,
            posture=posture,
            frame=frame,
        )

    intent = Intent(
        character_id=character.char_id,
        intent_type=_default_intent_for_posture(posture),
        target_ref=region.region_id,
        goal=_default_goal_for_posture(posture),
        motivation=_default_motivation_for_posture(posture, frame=frame),
        risk_tolerance="medium" if posture != "megastructure_expansion" else "high",
        urgency=0.58 if posture == "balanced_competition" else 0.68,
        proposed_action=_default_action_for_posture(posture, frame=frame),
        tone="calm" if posture == "balanced_competition" else "restrained and calculating",
        source="placeholder",
    )
    return _apply_faction_style_placeholder_bias(
        intent,
        region=region,
        faction_style=faction_style,
        doctrine_tags=doctrine_tags,
        posture=posture,
        frame=frame,
    )


def _build_frontline_placeholder_intent(
    state: WorldState,
    character: Character,
    target_region_id: str,
    recent_event: object,
    protagonist: bool,
    posture: str,
) -> Intent | None:
    if recent_event is None:
        return None

    urgency = 0.92 if protagonist else 0.76
    tone = "cold and forceful" if protagonist else "watchful"
    if _event_type_contains(recent_event, "lifeform_migration_front"):
        return Intent(
            character_id=character.char_id,
            intent_type=_lifeform_front_intent_type(protagonist, posture),
            target_ref=target_region_id,
            goal="Control the lifeform front before it widens",
            motivation=_lifeform_front_motivation(posture),
            risk_tolerance="high" if protagonist else "medium",
            urgency=urgency,
            proposed_action="Map movement corridors and lock the front into a manageable channel",
            tone=tone,
            source="placeholder",
        )
    if _event_has_theme(recent_event, "project") and _event_type_contains(recent_event, "budget"):
        return Intent(
            character_id=character.char_id,
            intent_type="redirect_project_financing" if posture == "megastructure_expansion" and protagonist else "secure_project_budget",
            target_ref=target_region_id,
            goal="Recover enough budget to keep the project alive",
            motivation=_project_front_motivation(posture, "budget"),
            risk_tolerance="medium",
            urgency=urgency,
            proposed_action="Pressure the funding chain and reopen stalled budget corridors",
            tone=tone,
            source="placeholder",
        )
    if _event_type_contains(recent_event, "project_bid") or _event_type_contains(recent_event, "contract"):
        return Intent(
            character_id=character.char_id,
            intent_type="secure_project_budget" if posture == "containment_first" and not protagonist else "contest_project_contract",
            target_ref=target_region_id,
            goal="Shift project execution into friendlier hands",
            motivation=_project_front_motivation(posture, "contract"),
            risk_tolerance="high" if protagonist else "medium",
            urgency=urgency,
            proposed_action="Undercut the current contractor and secure a stronger local execution bloc",
            tone=tone,
            source="placeholder",
        )
    if _event_type_contains(recent_event, "financing"):
        return Intent(
            character_id=character.char_id,
            intent_type="secure_project_budget" if posture == "stability_over_growth" and not protagonist else "redirect_project_financing",
            target_ref=target_region_id,
            goal="Rewire the capital path behind the project front",
            motivation=_project_front_motivation(posture, "financing"),
            risk_tolerance="medium",
            urgency=urgency,
            proposed_action="Pull capital away from hostile channels and redirect it through aligned backers",
            tone=tone,
            source="placeholder",
        )
    if _event_type_contains(recent_event, "accident"):
        return Intent(
            character_id=character.char_id,
            intent_type="contain_relic_fallout" if posture == "containment_first" and not protagonist else "suppress_site_accident_fallout",
            target_ref=target_region_id,
            goal="Stop the accident from becoming a regime-level breach",
            motivation=_project_front_motivation(posture, "accident"),
            risk_tolerance="medium",
            urgency=urgency,
            proposed_action="Isolate the damage zone and choke off rumor, sabotage, and opportunistic access",
            tone=tone,
            source="placeholder",
        )
    return None


def _find_cross_region_front(state: WorldState, knowledge: CharacterKnowledgeSnapshot):
    current_civ_id = knowledge.current_civ_id
    candidate_region_id: str | None = None
    candidate_weight = -1
    direct_ids = {event.event_id for event in knowledge.direct_events}
    rumored_ids = {event.event_id for event in knowledge.rumored_events}
    for event in reversed(knowledge.prioritized_events(limit=12)):
        if not event.region_refs:
            continue
        region_id = event.region_refs[0]
        if region_id == knowledge.current_region_id or region_id not in state.regions:
            continue
        region = state.regions[region_id]
        if current_civ_id and region.civ_id != current_civ_id:
            continue
        weight = 0
        if event.relic_refs:
            weight += 3
        if event.severity == "high":
            weight += 2
        if event.narrative_priority == "medium":
            weight += 1
        if "migration" in event.event_type or "budget" in event.event_type or "accident" in event.event_type:
            weight += 2
        if event.event_id in direct_ids:
            weight += 2
        elif event.event_id in rumored_ids:
            weight += 1
        if weight > candidate_weight:
            candidate_weight = weight
            candidate_region_id = region_id
    structural_region_id, structural_weight = _find_structural_front_region(state, knowledge)
    if structural_region_id is not None and structural_weight > candidate_weight:
        candidate_region_id = structural_region_id
    return state.regions.get(candidate_region_id) if candidate_region_id else None


def _find_structural_front_region(
    state: WorldState,
    knowledge: CharacterKnowledgeSnapshot,
) -> tuple[str | None, int]:
    current_civ_id = knowledge.current_civ_id
    current_region_id = knowledge.current_region_id
    best_region_id: str | None = None
    best_weight = -1

    for project in state.projects.values():
        if current_civ_id and current_civ_id not in project.linked_civs:
            continue
        if not project.linked_regions:
            continue
        region_id = project.linked_regions[0]
        if region_id == current_region_id or region_id not in state.regions:
            continue
        weight = _score_structural_front(
            pressure=project.pressure,
            status=project.status,
            notes=project.recent_notes[-3:],
            front_tags=project.front_tags,
        )
        if weight > best_weight:
            best_weight = weight
            best_region_id = region_id

    for supply_line in state.supply_lines.values():
        if current_civ_id and current_civ_id not in supply_line.linked_civ_refs:
            continue
        for region_id in [supply_line.origin_region_id, supply_line.destination_region_id]:
            if region_id == current_region_id or region_id not in state.regions:
                continue
            weight = _score_structural_front(
                pressure=supply_line.pressure,
                status=supply_line.status,
                notes=supply_line.recent_notes[-3:],
                front_tags=supply_line.front_tags,
            )
            if weight > best_weight:
                best_weight = weight
                best_region_id = region_id

    return best_region_id, best_weight


def _score_structural_front(
    *,
    pressure: str,
    status: str,
    notes: list[str],
    front_tags: list[str],
) -> int:
    weight = 0
    if pressure == "high":
        weight += 4
    elif pressure == "medium":
        weight += 2
    if status in {"contested", "contested_buildout", "stalled_recovery"}:
        weight += 3
    elif status in {"strained", "fragile", "active_buildout"}:
        weight += 1
    if any("security_front" == tag for tag in front_tags):
        weight += 1
    if any("supply_front" == tag for tag in front_tags):
        weight += 1
    if any("engineering_front" == tag for tag in front_tags):
        weight += 1

    joined = " ".join(notes)
    if any(
        token in joined
        for token in {
            "power_struggle_pressure",
            "construction_stall",
            "budget_crisis",
            "contract_scramble",
            "quarantine_panic_disrupted_corridor",
            "emergency_lockdown_slowed_routing",
            "control_contest",
        }
    ):
        weight += 3
    if any(
        token in joined
        for token in {
            "alliance_support",
            "alliance_backing",
            "control_secured",
            "phase_advance",
        }
    ):
        weight += 1
    return weight


def _build_cross_region_front_intent(
    state: WorldState,
    character: Character,
    target_region_id: str,
    protagonist: bool,
    posture: str,
    knowledge: CharacterKnowledgeSnapshot,
) -> Intent | None:
    recent_event = _find_recent_relic_event_for_region(knowledge, target_region_id)
    if recent_event is None:
        return _build_structural_front_intent(
            state=state,
            character=character,
            target_region_id=target_region_id,
            protagonist=protagonist,
            posture=posture,
        )
    if recent_event.event_type == "lifeform_migration_front":
        return Intent(
            character_id=character.char_id,
            intent_type=_lifeform_front_intent_type(protagonist, posture),
            target_ref=target_region_id,
            goal="Redeploy to the expanding biosecurity front",
            motivation=_lifeform_front_motivation(posture),
            risk_tolerance="high" if protagonist else "medium",
            urgency=0.93 if protagonist else 0.79,
            proposed_action="Redeploy across regional boundaries and seize the new front before it multiplies",
            tone="hard",
            source="placeholder",
        )
    if any(token in recent_event.event_type for token in {"budget", "financing", "accident", "project_bid"}):
        return Intent(
            character_id=character.char_id,
            intent_type=_cross_project_intent_type(recent_event.event_type, protagonist, posture),
            target_ref=target_region_id,
            goal="Redeploy into the live project front",
            motivation=_project_front_motivation(posture, recent_event.event_type),
            risk_tolerance="high" if protagonist else "medium",
            urgency=0.91 if protagonist else 0.77,
            proposed_action="Shift into the new project theater and reassert aligned control over the front",
            tone="hard",
            source="placeholder",
        )
    return None


def _build_structural_front_intent(
    *,
    state: WorldState,
    character: Character,
    target_region_id: str,
    protagonist: bool,
    posture: str,
) -> Intent | None:
    region = state.regions.get(target_region_id)
    if region is None:
        return None

    project = _find_project_for_region(state, target_region_id)
    if project is not None:
        if project.pressure == "high" or project.status in {"contested_buildout", "stalled_recovery"}:
            return Intent(
                character_id=character.char_id,
                intent_type="contest_project_contract" if protagonist else "secure_project_budget",
                target_ref=target_region_id,
                goal="转入高压项目线并重排执行秩序",
                motivation="该地区的项目网络已成为高压前线，继续旁观会丢失组织影响力。",
                risk_tolerance="high" if protagonist else "medium",
                urgency=0.88 if protagonist else 0.74,
                proposed_action="跨区进入项目现场，锁定预算、执行权和关键承包节点，避免前线继续失控。",
                tone="hard" if protagonist else "watchful",
                source="placeholder",
            )
        return Intent(
            character_id=character.char_id,
            intent_type="secure_project_budget",
            target_ref=target_region_id,
            goal="转入项目线并稳住推进节奏",
            motivation="该地区的项目网络正在成为组织影响力的主要落点。",
            risk_tolerance="medium",
            urgency=0.72,
            proposed_action="跨区进入项目线，补稳预算、施工和许可链，防止推进节奏被外部改写。",
            tone="restrained and calculating",
            source="placeholder",
        )

    supply_line = _find_supply_for_region(state, target_region_id)
    if supply_line is not None:
        if supply_line.pressure == "high" or supply_line.status in {"contested", "strained"}:
            return Intent(
                character_id=character.char_id,
                intent_type="seize_supply_leverage" if protagonist else "stabilize_supply",
                target_ref=target_region_id,
                goal="转入补给前线并争夺运输控制权",
                motivation="这条补给线已经成为高压走廊，谁控制它谁就能塑造后续局势。",
                risk_tolerance="medium",
                urgency=0.83 if protagonist else 0.71,
                proposed_action="沿着补给走廊跨区推进，重排仓储、路由与护送节点，把高压运输线转成可控杠杆。",
                tone="watchful",
                source="placeholder",
            )
        return Intent(
            character_id=character.char_id,
            intent_type="stabilize_supply",
            target_ref=target_region_id,
            goal="转入补给线并稳住跨区运输秩序",
            motivation="这条补给线正在变成更重要的组织支撑结构。",
            risk_tolerance="medium",
            urgency=0.66,
            proposed_action="进入补给线关键节点，重新协调储备、运输和放行秩序，防止前线再次失衡。",
            tone="restrained and calculating",
            source="placeholder",
        )
    return None


def _find_project_for_region(state: WorldState, region_id: str):
    candidates = [
        project
        for project in state.projects.values()
        if region_id in project.linked_regions
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            1 if item.pressure == "high" else 0,
            1 if item.status in {"contested_buildout", "stalled_recovery"} else 0,
            len(item.recent_notes),
        ),
        reverse=True,
    )
    return candidates[0]


def _find_supply_for_region(state: WorldState, region_id: str):
    candidates = [
        supply_line
        for supply_line in state.supply_lines.values()
        if region_id in {supply_line.origin_region_id, supply_line.destination_region_id}
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            1 if item.pressure == "high" else 0,
            1 if item.status in {"contested", "strained"} else 0,
            len(item.recent_notes),
        ),
        reverse=True,
    )
    return candidates[0]


def _cross_project_intent_type(event_type: str, protagonist: bool, posture: str) -> str:
    if "budget" in event_type:
        if posture == "megastructure_expansion" and protagonist:
            return "redirect_project_financing"
        return "secure_project_budget"
    if "financing" in event_type:
        if posture == "stability_over_growth" and not protagonist:
            return "secure_project_budget"
        return "redirect_project_financing"
    if "accident" in event_type:
        if posture == "containment_first" and not protagonist:
            return "contain_relic_fallout"
        return "suppress_site_accident_fallout"
    if posture == "containment_first" and not protagonist:
        return "secure_project_budget"
    return "contest_project_contract" if protagonist else "secure_project_budget"


def _find_character_civilization_posture(state: WorldState, character: Character) -> str:
    for faction_id in character.affiliation:
        faction = state.factions.get(faction_id)
        if faction is None or not faction.parent_civ_id:
            continue
        civilization = state.civilizations.get(faction.parent_civ_id)
        if civilization is not None:
            return civilization.strategic_posture
    region = state.regions.get(character.current_region_id)
    if region is None or not region.civ_id:
        return "balanced_competition"
    civilization = state.civilizations.get(region.civ_id)
    if civilization is None:
        return "balanced_competition"
    return civilization.strategic_posture


def _find_character_faction_style(state: WorldState, character: Character) -> tuple[str, list[str]]:
    for faction_id in character.affiliation:
        faction = state.factions.get(faction_id)
        if faction is None:
            continue
        return faction.operational_style, list(faction.doctrine_tags)
    return "adaptive_network", []


def _find_character_relation_pressure(state: WorldState, character: Character) -> dict[str, int]:
    for faction_id in character.affiliation:
        faction = state.factions.get(faction_id)
        if faction is None:
            continue
        relations = relations_for_ref(state, faction.faction_id, limit=6)
        pressure = {
            "rivalry": 0,
            "alliance": 0,
            "control": 0,
            "covert": 0,
        }
        for relation in relations:
            if relation.relation_type in {"rival_to", "contesting", "obstructing", "opposing"}:
                pressure["rivalry"] += 1
            elif relation.relation_type == "allied_with":
                pressure["alliance"] += 1
            elif relation.relation_type in {"controls", "contracting", "financing", "sponsoring", "supply_influence"}:
                pressure["control"] += 1
            elif relation.relation_type in {"infiltrating", "flashpoint_actor", "seeking_control"}:
                pressure["covert"] += 1
        return pressure
    return {"rivalry": 0, "alliance": 0, "control": 0, "covert": 0}


def _build_relation_pressure_intent(
    *,
    character: Character,
    region,
    posture: str,
    relation_pressure: dict[str, int],
    protagonist: bool,
    frame,
) -> Intent | None:
    rivalry = relation_pressure.get("rivalry", 0)
    alliance = relation_pressure.get("alliance", 0)
    control = relation_pressure.get("control", 0)
    covert = relation_pressure.get("covert", 0)

    if rivalry >= 3 and region.political_tension != "low":
        return Intent(
            character_id=character.char_id,
            intent_type="manage_unrest" if posture == "stability_over_growth" and not protagonist else "broker_power_shift",
            target_ref=region.region_id,
            goal="在多线敌对关系中重新压稳本地权力结构",
            motivation="派系关系前线已经外露，角色需要直接处理敌对链带来的本地失序。",
            risk_tolerance="high" if protagonist else "medium",
            urgency=0.87 if protagonist else 0.73,
            proposed_action=_political_front_action(frame, "power_shift"),
            tone="hard" if protagonist else "watchful",
            source="placeholder",
        )
    if control >= 2 and posture == "megastructure_expansion":
        return Intent(
            character_id=character.char_id,
            intent_type="secure_project_budget" if not protagonist else "contest_project_contract",
            target_ref=region.region_id,
            goal="把组织控制链继续压进项目和执行前线",
            motivation="派系已经开始围绕控制权布局，角色会顺着这条链条继续推进。",
            risk_tolerance="medium",
            urgency=0.79 if protagonist else 0.68,
            proposed_action="稳住执行链、预算口和承包节点，把已有控制关系转成更硬的前线支配。",
            tone="restrained and calculating",
            source="placeholder",
        )
    if alliance >= 2 and region.scarcity != "low":
        return Intent(
            character_id=character.char_id,
            intent_type="stabilize_supply",
            target_ref=region.region_id,
            goal="借助盟友网络把补给前线重新稳住",
            motivation="结盟网络已经成形，角色更适合把联盟转成实际供应能力。",
            risk_tolerance="medium",
            urgency=0.74,
            proposed_action=_supply_front_action(frame, "leverage"),
            tone="watchful",
            source="placeholder",
        )
    if covert >= 2 and rivalry <= 1:
        return Intent(
            character_id=character.char_id,
            intent_type="expand_influence",
            target_ref=region.region_id,
            goal="沿着半公开关系前线继续渗透影响力",
            motivation="派系当前更依赖潜入和热点布线，角色会优先扩展可利用接点。",
            risk_tolerance="medium",
            urgency=0.7,
            proposed_action="沿着现有中间人、热点接触点和灰色授权链继续扩张影响。",
            tone="watchful",
            source="placeholder",
        )
    return None


def _apply_faction_style_placeholder_bias(
    intent: Intent,
    *,
    region,
    faction_style: str,
    doctrine_tags: list[str],
    posture: str,
    frame,
    hard_constraint: bool = False,
) -> Intent:
    style_reason = _style_reason_suffix(faction_style, doctrine_tags)
    style_action = _style_action_suffix(faction_style)
    if hard_constraint:
        return Intent(
            character_id=intent.character_id,
            intent_type=intent.intent_type,
            target_ref=intent.target_ref,
            goal=intent.goal,
            motivation=_merge_reason(intent.motivation, style_reason),
            risk_tolerance=intent.risk_tolerance,
            urgency=intent.urgency,
            proposed_action=_merge_action(intent.proposed_action, style_action),
            tone=intent.tone,
            source=intent.source,
        )

    candidate_type = intent.intent_type
    candidate_goal = intent.goal
    candidate_action = intent.proposed_action
    candidate_tone = intent.tone

    if faction_style == "discipline_network":
        if region.political_tension == "high":
            candidate_type = "broker_power_shift" if posture != "containment_first" else "manage_unrest"
            candidate_goal = "Tighten local order through controlled leverage"
            candidate_action = _political_front_action(frame, "power_shift")
            candidate_tone = "hard"
        elif intent.intent_type in {"improve_position", "expand_influence"}:
            candidate_type = "broker_power_shift"
            candidate_goal = "Expand influence through covert alignment shifts"
            candidate_action = "Pressure brokers, split rivals, and tighten covert alignment around key intermediaries"
            candidate_tone = "watchful"
    elif faction_style == "contract_predator":
        if region.scarcity == "high" or "project_fronts" in frame.dominant_fronts:
            candidate_type = "secure_project_budget"
            candidate_goal = "Secure project leverage through budget and contract control"
            candidate_action = "Lock funding seams, protect contract leverage, and capture the most stressed execution corridor"
            candidate_tone = "tight"
        elif intent.intent_type in {"improve_position", "expand_influence", "broker_power_shift"}:
            candidate_type = "contest_project_contract"
            candidate_goal = "Capture a stronger contract position on the active front"
            candidate_action = "Undercut weak operators and move aligned contractors into the execution chain"
            candidate_tone = "hard"
    elif faction_style == "containment_cadre":
        if intent.intent_type in {"improve_position", "expand_influence", "broker_power_shift"}:
            candidate_type = "contain_relic_fallout"
            candidate_goal = "Seal unstable spillover before it spreads"
            candidate_action = "Narrow access, isolate volatile seams, and hold the district under controlled containment"
            candidate_tone = "hard"
    elif faction_style == "extraction_broker":
        if region.scarcity == "high":
            candidate_type = "seize_supply_leverage"
            candidate_goal = "Turn supply disruption into lasting leverage"
            candidate_action = _supply_front_action(frame, "leverage")
            candidate_tone = "restrained and calculating"
        elif intent.intent_type in {"improve_position", "expand_influence", "manage_unrest"}:
            candidate_type = "stabilize_supply"
            candidate_goal = "Rewire local dependence through supply access"
            candidate_action = "Reorder storage, transport, and permit chokepoints into a controllable supply chain"
            candidate_tone = "watchful"

    return Intent(
        character_id=intent.character_id,
        intent_type=candidate_type,
        target_ref=intent.target_ref,
        goal=candidate_goal,
        motivation=_merge_reason(intent.motivation, style_reason),
        risk_tolerance=intent.risk_tolerance,
        urgency=intent.urgency,
        proposed_action=_merge_action(candidate_action, style_action),
        tone=candidate_tone,
        source=intent.source,
    )


def _style_reason_suffix(faction_style: str, doctrine_tags: list[str]) -> str:
    doctrine_text = f" doctrine={','.join(doctrine_tags)}" if doctrine_tags else ""
    mapping = {
        "discipline_network": "Faction pull favors covert leverage, controlled brokers, and pressure from inside institutions.",
        "contract_predator": "Faction pull favors budget seams, contract capture, and project chokepoints.",
        "containment_cadre": "Faction pull favors sealing unstable fronts and denying uncontrolled spillover.",
        "extraction_broker": "Faction pull favors routing scarcity into durable supply leverage.",
        "adaptive_network": "Faction pull favors flexible adaptation to the strongest local opening.",
    }
    return mapping.get(faction_style, mapping["adaptive_network"]) + doctrine_text


def _style_action_suffix(faction_style: str) -> str:
    mapping = {
        "discipline_network": "Keep the move deniable and centered on a narrow broker chain.",
        "contract_predator": "Anchor the move in budgets, contracts, or execution authority.",
        "containment_cadre": "Favor seal, custody, and controlled access over open escalation.",
        "extraction_broker": "Convert logistics pressure into dependence rather than spectacle.",
        "adaptive_network": "Stay flexible and exploit whichever seam remains softest.",
    }
    return mapping.get(faction_style, mapping["adaptive_network"])


def _merge_reason(base: str, suffix: str) -> str:
    if suffix in base:
        return base
    return f"{base} {suffix}"


def _merge_action(base: str, suffix: str) -> str:
    if suffix in base:
        return base
    return f"{base} {suffix}"


def _lifeform_front_intent_type(protagonist: bool, posture: str) -> str:
    if posture == "containment_first":
        return "seal_migration_corridor" if protagonist else "contain_relic_fallout"
    if posture == "stability_over_growth" and protagonist:
        return "seal_migration_corridor"
    return "seal_migration_corridor" if protagonist else "track_lifeform_spread"


def _lifeform_front_motivation(posture: str) -> str:
    if posture == "containment_first":
        return "Civilizational posture now prioritizes sealing spread over local opportunism"
    if posture == "stability_over_growth":
        return "Uncontained spread would fracture order across multiple districts"
    if posture == "opportunistic_extraction":
        return "Tracking the moving edge of the anomaly may create exploitable leverage"
    return "Cross-region spread is redefining the local front line"


def _project_front_motivation(posture: str, event_type: str) -> str:
    if posture == "megastructure_expansion":
        return "The civilization is treating this project line as the main instrument of expansion"
    if posture == "containment_first":
        return "This front must be stabilized before project disorder spills into wider systemic risk"
    if posture == "stability_over_growth":
        return "Project turbulence is dangerous mainly because it can destabilize the governing order"
    if "financing" in event_type or "budget" in event_type:
        return "Project finance failure will collapse leverage and order"
    return "Control over the contract now shapes who owns the site"


def _event_has_theme(event: object, theme: str) -> bool:
    return theme in event_theme_tags(event)


def _event_type_contains(event: object, token: str) -> bool:
    return token.lower() in str(event.event_type).lower()


def _default_intent_for_posture(posture: str) -> str:
    mapping = {
        "containment_first": "contain_relic_fallout",
        "megastructure_expansion": "secure_project_budget",
        "stability_over_growth": "manage_unrest",
        "opportunistic_extraction": "secure_relic_access",
    }
    return mapping.get(posture, "expand_influence")


def _default_goal_for_posture(posture: str) -> str:
    mapping = {
        "containment_first": "Keep unstable fronts sealed before they spread",
        "megastructure_expansion": "Preserve build momentum across critical project lines",
        "stability_over_growth": "Hold regional order together under rising pressure",
        "opportunistic_extraction": "Turn unstable assets into durable leverage",
    }
    return mapping.get(posture, "Expand influence over critical regional flows")


def _default_motivation_for_posture(posture: str, *, frame=None) -> str:
    mapping = {
        "containment_first": "The wider order is pricing uncontrolled spillover as the main threat",
        "megastructure_expansion": "Infrastructure growth is now the preferred route to long-term dominance",
        "stability_over_growth": "The system is fragile enough that disorder matters more than growth",
        "opportunistic_extraction": "Diffuse instability creates openings for leverage and capture",
    }
    if frame is not None and "governance_fronts" in frame.dominant_fronts and posture == "balanced_competition":
        return "The wider world is drifting toward governance contest, even if this district is still quiet"
    if frame is not None and "project_fronts" in frame.dominant_fronts and posture == "megastructure_expansion":
        return "Project networks are becoming the main route through which long-term control is being built"
    if frame is not None and "supply_fronts" in frame.dominant_fronts and posture == "opportunistic_extraction":
        return "Supply corridors are turning routine logistics into durable leverage over the next order"
    return mapping.get(posture, "The situation is stable enough for low-cost influence building")


def _default_action_for_posture(posture: str, *, frame=None) -> str:
    mapping = {
        "containment_first": "Seal weak seams, restrict access, and stop unstable fronts from widening",
        "megastructure_expansion": "Reinforce budget, logistics, and execution control around the most live project line",
        "stability_over_growth": "Map fracture points, suppress cascading unrest, and lock key brokers into compliance",
        "opportunistic_extraction": "Probe unstable interfaces and convert access into durable dependence",
    }
    if frame is not None and "supply_fronts" in frame.dominant_fronts and posture == "balanced_competition":
        return "Map stressed logistics seams and establish dependence before rivals fully notice the opening"
    if frame is not None and "project_fronts" in frame.dominant_fronts and posture == "megastructure_expansion":
        return "Reinforce the most live project network and keep its budget, execution, and access corridors aligned"
    return mapping.get(posture, "Map winnable nodes and establish new dependencies")


def _political_front_motivation(frame) -> str:
    if "governance_fronts" in frame.dominant_fronts and "legitimacy_erosion" in frame.pressure_axes:
        return "The wider world is drifting toward governance fracture, making local realignment more decisive"
    return "High pressure creates both risk and a window for control"


def _political_front_action(frame, mode: str) -> str:
    if mode == "containment":
        if "managed_fragility" in frame.organization_climates:
            return "Stabilize the district, narrow rumor spread, and stop local stress from cascading into legitimacy failure"
        return "Stabilize the district, narrow rumor spread, and suppress uncontrolled spillover"
    if mode == "stability":
        if "security_consolidation" in frame.organization_climates:
            return "Pressure brokers, isolate agitators, and tighten the district's political shell before rivals capitalize"
        return "Pressure local brokers, isolate agitators, and contain cascading unrest"
    return "Coordinate key factions into a controlled realignment and lock legitimacy back into aligned hands"


def _supply_front_motivation(frame) -> str:
    if "supply_fronts" in frame.dominant_fronts and "capital_realignment" in frame.pressure_axes:
        return "Control of supply now also means control over the capital routes backing the next order"
    return "Control of supply is the fastest way to shape the next order"


def _supply_front_action(frame, mode: str) -> str:
    if mode == "project":
        return "Hold supply and budget lanes together long enough to keep the most strategic build front alive"
    if "bureaucratic_competition" in frame.organization_climates:
        return "Integrate storage, transport, and permit chokepoints before administrative rivals can rewire them"
    return "Integrate storage, transport, and security chokepoints"


def _find_recent_relic_event_for_region(
    knowledge: CharacterKnowledgeSnapshot,
    region_id: str,
):
    for event in reversed(knowledge.visible_relic_events):
        if region_id in event.region_refs:
            return event
    return None


def _intent_signal_score(
    state: WorldState,
    character: Character,
    knowledge: CharacterKnowledgeSnapshot,
) -> int:
    """Estimate whether a character currently deserves an AI intent spend."""
    region = state.regions[character.current_region_id]
    score = 0
    if character.character_level == "L3":
        score += 2
    elif character.character_level == "L2":
        score += 1

    if character.agency_mode == "strategic":
        score += 2
    elif character.agency_mode == "opportunistic":
        score += 1

    if character.notoriety == "high":
        score += 2
    elif character.notoriety == "medium":
        score += 1

    if region.political_tension == "high":
        score += 2
    elif region.political_tension == "medium":
        score += 1

    if region.scarcity == "high":
        score += 2
    elif region.scarcity == "medium":
        score += 1

    if region.security == "low":
        score += 2
    elif region.security == "medium":
        score += 1

    if knowledge.flashpoint_region_id:
        score += 2
        if knowledge.flashpoint_region_id != knowledge.current_region_id:
            score += 1

    score += min(len(knowledge.visible_relic_events), 2)
    score += min(len(knowledge.direct_events), 2)

    for event in knowledge.prioritized_events(limit=4):
        if event.severity == "high":
            score += 1
        if event.narrative_priority == "high":
            score += 1

    if character.observation_trace > 0:
        score += 1
    return score


def _intent_from_payload(character: Character, payload: dict[str, object], *, source: str) -> Intent:
    """Convert a JSON payload from the configured LLM into an Intent."""
    target_ref = str(payload.get("target_ref") or character.current_region_id)
    if not target_ref.startswith("region_"):
        target_ref = character.current_region_id

    return Intent(
        character_id=character.char_id,
        intent_type=str(payload.get("intent_type") or "improve_position"),
        target_ref=target_ref,
        goal=str(payload.get("goal") or "Act under current conditions"),
        motivation=str(payload.get("motivation") or "Respond to local pressures"),
        risk_tolerance=str(payload.get("risk_tolerance") or "medium"),
        urgency=_coerce_urgency(payload.get("urgency")),
        proposed_action=str(payload.get("proposed_action") or "Take a cautious local action"),
        tone=str(payload.get("tone") or "restrained"),
        source=source,
    )


def _coerce_urgency(value: object) -> float:
    """Coerce model urgency outputs into a numeric range."""
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    if isinstance(value, str):
        lowered = value.strip().lower()
        named_levels = {
            "low": 0.3,
            "medium": 0.6,
            "moderate": 0.6,
            "high": 0.85,
            "urgent": 0.95,
        }
        if lowered in named_levels:
            return named_levels[lowered]
        try:
            return max(0.0, min(1.0, float(lowered)))
        except ValueError:
            return 0.5
    return 0.5
