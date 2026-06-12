"""Prompt construction helpers."""

from __future__ import annotations

from pathlib import Path

from src.agents.knowledge import CharacterKnowledgeSnapshot
from src.core.ai_context import related_dynamic_structure_context_lines
from src.events.visibility_rules import format_event_summary_for_view
from src.world.character import Character
from src.world.state import WorldState
from src.world.style_profile import style_profile_prompt_lines

PROMPT_ROOT = Path("prompts")


def build_intent_messages(
    world: WorldState,
    character: Character,
    knowledge: CharacterKnowledgeSnapshot | None = None,
) -> list[dict[str, str]]:
    """Build SiliconFlow/DeepSeek chat messages for one character intent request."""
    system_rules = _read_prompt("system_rules.txt")
    task_prompt = _read_prompt("character_intent.txt")
    region = world.regions[character.current_region_id]
    civilization_name = (
        world.civilizations[region.civ_id].name if region.civ_id in world.civilizations else "None"
    )
    allowed_region_ids = ", ".join(sorted(world.regions.keys()))
    knowledge_overview = (
        knowledge.knowledge_overview()
        if knowledge is not None
        else {
            "direct_count": 0,
            "rumored_count": 0,
            "public_count": 0,
            "visible_region_count": 0,
            "flashpoint_region_id": None,
        }
    )
    direct_events = _knowledge_event_lines(
        world,
        knowledge.direct_events[-4:] if knowledge is not None else [],
        tier="direct",
    )
    rumored_events = _knowledge_event_lines(
        world,
        knowledge.rumored_events[-3:] if knowledge is not None else [],
        tier="rumored",
    )
    public_events = _knowledge_event_lines(
        world,
        knowledge.public_events[-4:] if knowledge is not None else [],
        tier="public",
    )

    relevant_relic_events = [
        format_event_summary_for_view(event, view="player", world=world)
        for event in (knowledge.visible_relic_events[-3:] if knowledge is not None else [])
    ][-3:]
    relic_event_lines = (
        [f"- {item}" for item in relevant_relic_events] if relevant_relic_events else ["- None"]
    )
    dynamic_structure_lines = related_dynamic_structure_context_lines(
        world,
        [character.current_region_id] + list(character.affiliation),
        view="player",
        limit=4,
    )
    has_relic_flashpoint = any(item != "- None" for item in relic_event_lines)
    if has_relic_flashpoint:
        intent_guidance_lines = [
            "Recommended intent types for this situation:",
            "- Prefer secure_relic_access when the character wants leverage, control, or gatekeeping.",
            "- Prefer contain_relic_fallout when the priority is stabilization, sealing, panic control, or damage containment.",
            "- Prefer seal_migration_corridor or track_lifeform_spread when anomalous life is crossing regions.",
            "- Prefer secure_project_budget, contest_project_contract, redirect_project_financing, or suppress_site_accident_fallout when a megastructure project front is active.",
            "- Prefer broker_power_shift only if the relic conflict is mainly being used to reorganize local power.",
            "- Avoid generic intent types if a relic flashpoint is clearly active in the supplied state.",
        ]
    else:
        intent_guidance_lines = [
            "Recommended intent types for this situation:",
            "- Prefer stabilize_supply for severe scarcity pressure.",
            "- Prefer manage_unrest for high political tension and control risk.",
            "- Prefer broker_power_shift or expand_influence when leverage-building is the main goal.",
        ]

    user_prompt = "\n".join(
        [
            *style_profile_prompt_lines(world.style_profile_id),
            f"World pressure axes: {', '.join(world.structure_template.pressure_axes) or 'None'}",
            f"Dominant fronts: {', '.join(world.structure_template.dominant_fronts) or 'None'}",
            f"Organization climates: {', '.join(world.structure_template.organization_climates) or 'None'}",
            f"Anomaly bias: {world.structure_template.anomaly_bias}",
            f"Civilization path biases: {', '.join(world.structure_template.civ_path_biases) or 'None'}",
            f"Current tick: {world.current_tick}",
            f"Character id: {character.char_id}",
            f"Character name: {character.name}",
            f"Character level: {character.character_level}",
            f"Current region id: {character.current_region_id}",
            f"Agency mode: {character.agency_mode}",
            f"Initiative: {character.initiative}",
            f"Notoriety: {character.notoriety}",
            f"Region: {region.name} ({region.region_id})",
            f"Civilization: {civilization_name}",
            f"Region scarcity: {region.scarcity}",
            f"Region political tension: {region.political_tension}",
            f"Region security: {region.security}",
            f"Affiliations: {', '.join(character.affiliation) or 'None'}",
            f"Role tags: {', '.join(character.role_tags) or 'None'}",
            f"Capabilities: {', '.join(character.capability_tags) or 'None'}",
            f"Desires: {', '.join(character.desire_tags) or 'None'}",
            f"Fears: {', '.join(character.fear_tags) or 'None'}",
            f"Recent goal: {character.recent_goal or 'None'}",
            f"Memory summary: {character.memory_summary or 'None'}",
            "Knowledge boundaries:",
            f"- Direct event count: {knowledge_overview['direct_count']}",
            f"- Rumored event count: {knowledge_overview['rumored_count']}",
            f"- Public event count: {knowledge_overview['public_count']}",
            f"- Visible region count: {knowledge_overview['visible_region_count']}",
            f"- Flashpoint region: {knowledge_overview['flashpoint_region_id'] or 'None'}",
            "Directly witnessed or locally confirmed events:",
            *(direct_events or ["- None"]),
            "Rumored pressures and incomplete reports:",
            *(rumored_events or ["- None"]),
            "Public developments visible in the wider environment:",
            *(public_events or ["- None"]),
            "Recent relic flashpoints:",
            *relic_event_lines,
            "Related dynamic structures (read-only context; do not target these ids):",
            *dynamic_structure_lines,
            *intent_guidance_lines,
            "",
            task_prompt,
            "",
            (
                "Return a JSON object with keys: intent_type, target_ref, goal, motivation, "
                "risk_tolerance, urgency, proposed_action, tone."
            ),
            "Constraints:",
            f"- target_ref must be one of these exact region ids: {allowed_region_ids}",
            "- urgency must be a number between 0.0 and 1.0",
            "- intent_type should be a short snake_case action label",
            "- goal must be at most 12 words",
            "- motivation must be at most 14 words",
            "- proposed_action must be at most 18 words",
            "- tone must be at most 4 words",
            "- Do not invent new ids, locations, or entities",
            "- If relic conflict is active nearby, it is valid to react to it through regional power, security, or access moves",
            "- When relic flashpoints are listed above, prefer secure_relic_access or contain_relic_fallout unless a project front or migration front clearly suggests a more specific response",
        ]
    )

    return [
        {"role": "system", "content": system_rules},
        {"role": "user", "content": user_prompt},
    ]


def _read_prompt(filename: str) -> str:
    path = PROMPT_ROOT / filename
    return path.read_text(encoding="utf-8").strip()


def _knowledge_event_lines(
    world: WorldState,
    events: list[object],
    *,
    tier: str,
) -> list[str]:
    lines: list[str] = []
    for event in events:
        if tier == "direct":
            text = event.summary
        else:
            text = format_event_summary_for_view(event, view="player", world=world)
        lines.append(f"- {text}")
    return lines
