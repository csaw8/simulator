"""Observer-facing text generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from src.agents.llm_client import LLMClientError, build_siliconflow_client, llm_source_label
from src.agents.knowledge import build_character_knowledge_snapshot
from src.core.ai_context import related_dynamic_structure_context_lines
from src.core.ai_policy import evaluate_observer_llm_policy
from src.core.ai_tiers import resolve_observer_tier
from src.narrative.visibility import is_player_view
from src.world.presence import megastructure_origin_label, presence_class, presence_display_name
from src.world.state import WorldState

PROMPT_ROOT = Path("prompts")


@dataclass(slots=True)
class ObservationResult:
    """AI observation result for a focused watch request."""

    source: str
    text: str | None
    error: str | None = None
    tier: str | None = None


def observe_region_with_ai(
    world: WorldState,
    region_id: str,
    ai_config: dict[str, object],
    mode: str = "brief",
    view: str = "truth",
) -> ObservationResult:
    """Generate an AI-enhanced region observation when possible."""
    region = world.regions.get(region_id)
    if region is None:
        return ObservationResult(source="none", text=None, error=f"Unknown region: {region_id}")

    player_view = is_player_view(view)
    recent_events = [
        event.summary for event in world.event_stream.recent(30) if region_id in event.region_refs
    ][-6:]
    decision = evaluate_observer_llm_policy(
        ai_config,
        mode=mode,
        view=view,
        signal_score=_region_observer_signal(world, region_id, recent_events),
    )
    if not decision.allowed:
        return ObservationResult(source="none", text=None, error=decision.reason)

    client = build_siliconflow_client(ai_config)
    if client is None:
        return ObservationResult(source="none", text=None, error=f"{llm_source_label(ai_config)} client unavailable")

    civ_name = world.civilizations[region.civ_id].name if region.civ_id else "None"
    messages = _build_observer_messages(
        title=f"Region {region.name} ({region.region_id})",
        body_lines=[
            f"Civilization: {civ_name}",
            f"Type: {region.region_type}",
            f"Prosperity: {region.prosperity}",
            f"Scarcity: {region.scarcity}",
            f"Political tension: {region.political_tension}",
            f"Security: {region.security}",
            f"Infrastructure: {'Visible but uneven' if player_view else region.infrastructure}",
            f"Tech density: {'Unknown to outside observers' if player_view else region.tech_density}",
            f"Story hooks: {', '.join(region.local_story_hooks) or 'None'}",
            "Recent events:",
            *([f"- {item}" for item in recent_events] if recent_events else ["- None"]),
            "Related dynamic structures:",
            *related_dynamic_structure_context_lines(world, [region_id], view=view, limit=4),
        ],
        mode=mode,
        voice_instruction=_region_observer_voice(world, region_id),
    )
    return _run_observer_completion(client, messages, ai_config, mode)


def observe_character_with_ai(
    world: WorldState,
    character_id: str,
    ai_config: dict[str, object],
    mode: str = "brief",
    view: str = "truth",
) -> ObservationResult:
    """Generate an AI-enhanced character observation when possible."""
    character = world.characters.get(character_id)
    if character is None:
        return ObservationResult(
            source="none",
            text=None,
            error=f"Unknown character: {character_id}",
        )

    region = world.regions[character.current_region_id]
    player_view = is_player_view(view)
    knowledge = build_character_knowledge_snapshot(world, character)
    direct_events = [event.summary for event in knowledge.direct_events[-4:]]
    rumored_events = [event.summary for event in knowledge.rumored_events[-3:]]
    public_events = [event.summary for event in knowledge.public_events[-3:]]
    decision = evaluate_observer_llm_policy(
        ai_config,
        mode=mode,
        view=view,
        signal_score=_character_observer_signal(character, knowledge),
    )
    if not decision.allowed:
        return ObservationResult(source="none", text=None, error=decision.reason)

    client = build_siliconflow_client(ai_config)
    if client is None:
        return ObservationResult(source="none", text=None, error=f"{llm_source_label(ai_config)} client unavailable")

    messages = _build_observer_messages(
        title=f"Character {character.name} ({character.char_id})",
        body_lines=[
            f"Level: {character.character_level}",
            f"Status: {character.status}",
            f"Region: {region.name} ({region.region_id})",
            f"Role tags: {', '.join(character.role_tags) or 'None'}",
            f"Capability tags: {', '.join(character.capability_tags) or 'None'}",
            f"Desire tags: {', '.join(character.desire_tags) or 'None'}",
            f"Fear tags: {', '.join(character.fear_tags) or 'None'}",
            f"Notoriety: {character.notoriety}",
            f"Agency mode: {character.agency_mode}",
            f"Recent goal: {'Unknown to outside observers' if player_view else (character.recent_goal or 'None')}",
            f"Last intent: {'Unknown to outside observers' if player_view else _format_last_intent(character.last_intent)}",
            f"Visible region count: {len(knowledge.visible_region_ids)}",
            f"Flashpoint region: {knowledge.flashpoint_region_id or 'None'}",
            "Direct events:",
            *([f"- {item}" for item in direct_events] if direct_events else ["- None"]),
            "Rumored events:",
            *([f"- {item}" for item in rumored_events] if rumored_events else ["- None"]),
            "Public events:",
            *([f"- {item}" for item in public_events] if public_events else ["- None"]),
            "Related dynamic structures:",
            *related_dynamic_structure_context_lines(
                world,
                [character.current_region_id] + list(character.affiliation),
                view=view,
                limit=4,
            ),
        ],
        mode=mode,
        voice_instruction=_character_observer_voice(character),
    )
    return _run_observer_completion(client, messages, ai_config, mode)


def observe_civilization_with_ai(
    world: WorldState,
    civ_id: str,
    ai_config: dict[str, object],
    mode: str = "brief",
    view: str = "truth",
) -> ObservationResult:
    """Generate an AI-enhanced civilization observation when possible."""
    civilization = world.civilizations.get(civ_id)
    if civilization is None:
        return ObservationResult(source="none", text=None, error=f"Unknown civilization: {civ_id}")

    player_view = is_player_view(view)
    recent_events = [
        event.summary for event in world.event_stream.recent(40) if civ_id in event.civ_refs
    ][-8:]
    decision = evaluate_observer_llm_policy(
        ai_config,
        mode=mode,
        view=view,
        signal_score=_civilization_observer_signal(civilization, recent_events),
    )
    if not decision.allowed:
        return ObservationResult(source="none", text=None, error=decision.reason)

    client = build_siliconflow_client(ai_config)
    if client is None:
        return ObservationResult(source="none", text=None, error=f"{llm_source_label(ai_config)} client unavailable")

    messages = _build_observer_messages(
        title=f"Civilization {civilization.name} ({civilization.civ_id})",
        body_lines=[
            f"Status: {civilization.status}",
            f"Stage: {civilization.stage}",
            f"Governance: {civilization.governance_mode}",
            f"Cohesion: {civilization.cohesion}",
            f"Scarcity pressure: {civilization.scarcity_pressure}",
            f"Expansion pressure: {civilization.expansion_pressure}",
            f"Legitimacy: {civilization.legitimacy}",
            f"Trajectory: {', '.join(civilization.trajectory) or 'None'}",
            f"Strategic posture: {'Unknown to outside observers' if player_view else civilization.strategic_posture}",
            f"Summary tags: {', '.join(civilization.summary_tags) or 'None'}",
            "Recent events:",
            *([f"- {item}" for item in recent_events] if recent_events else ["- None"]),
            "Related dynamic structures:",
            *related_dynamic_structure_context_lines(
                world,
                civilization.key_regions[:6] + civilization.key_factions[:6],
                view=view,
                limit=4,
            ),
        ],
        mode=mode,
        voice_instruction=_civilization_observer_voice(civilization),
    )
    return _run_observer_completion(client, messages, ai_config, mode)


def observe_relic_with_ai(
    world: WorldState,
    relic_id: str,
    ai_config: dict[str, object],
    mode: str = "brief",
    view: str = "truth",
) -> ObservationResult:
    """Generate an AI-enhanced relic observation when possible."""
    relic = world.relics.get(relic_id)
    if relic is None:
        return ObservationResult(source="none", text=None, error=f"Unknown relic: {relic_id}")

    region = world.regions[relic.current_region_id]
    player_view = is_player_view(view)
    recent_events = [
        event.summary for event in world.event_stream.recent(40) if relic_id in event.relic_refs
    ][-8:]
    decision = evaluate_observer_llm_policy(
        ai_config,
        mode=mode,
        view=view,
        signal_score=_relic_observer_signal(relic, recent_events),
    )
    if not decision.allowed:
        return ObservationResult(source="none", text=None, error=decision.reason)

    client = build_siliconflow_client(ai_config)
    if client is None:
        return ObservationResult(source="none", text=None, error=f"{llm_source_label(ai_config)} client unavailable")

    messages = _build_observer_messages(
        title=f"{presence_display_name(relic)} {relic.name} ({relic.relic_id})",
        body_lines=[
            f"Type: {relic.relic_type}",
            f"Presence class: {presence_class(relic)}",
            f"Region: {region.name} ({region.region_id})",
            f"Holder: {'Unknown to outside observers' if player_view else relic.holder_ref}",
            f"Significance: {relic.significance}",
            f"Danger: {relic.danger}",
            f"Activation state: {relic.activation_state}",
            f"Origin mode: {_observer_origin_mode(relic)}",
            f"Construction state: {_observer_construction_state(relic)}",
            f"Sponsor: {'Unknown to outside observers' if player_view else (relic.sponsor_ref or 'None')}",
            f"Contractor: {'Unknown to outside observers' if player_view else (relic.contractor_ref or 'None')}",
            f"Financier: {'Unknown to outside observers' if player_view else (relic.financier_ref or 'None')}",
            f"Opposition: {'Unknown to outside observers' if player_view else (relic.opposition_ref or 'None')}",
            f"Story tags: {', '.join(relic.story_tags) or 'None'}",
            "Recent events:",
            *([f"- {item}" for item in recent_events] if recent_events else ["- None"]),
            "Related dynamic structures:",
            *related_dynamic_structure_context_lines(
                world,
                [
                    relic.relic_id,
                    relic.current_region_id,
                    relic.holder_ref or "",
                    relic.sponsor_ref or "",
                    relic.contractor_ref or "",
                    relic.financier_ref or "",
                    relic.opposition_ref or "",
                ],
                view=view,
                limit=4,
            ),
        ],
        mode=mode,
        voice_instruction=_relic_observer_voice(relic),
    )
    return _run_observer_completion(client, messages, ai_config, mode)


def observe_faction_with_ai(
    world: WorldState,
    faction_id: str,
    ai_config: dict[str, object],
    mode: str = "brief",
    view: str = "truth",
) -> ObservationResult:
    """Generate an AI-enhanced faction observation when possible."""
    faction = world.factions.get(faction_id)
    if faction is None:
        return ObservationResult(source="none", text=None, error=f"Unknown faction: {faction_id}")

    player_view = is_player_view(view)
    civilization = world.civilizations.get(faction.parent_civ_id) if faction.parent_civ_id else None
    recent_events = [
        event.summary for event in world.event_stream.recent(40) if faction_id in event.faction_refs
    ][-8:]
    decision = evaluate_observer_llm_policy(
        ai_config,
        mode=mode,
        view=view,
        signal_score=_faction_observer_signal(faction, recent_events),
    )
    if not decision.allowed:
        return ObservationResult(source="none", text=None, error=decision.reason)

    client = build_siliconflow_client(ai_config)
    if client is None:
        return ObservationResult(source="none", text=None, error=f"{llm_source_label(ai_config)} client unavailable")

    controlled_regions = [
        world.regions[region_id].name if region_id in world.regions else region_id
        for region_id in faction.controlled_regions[:6]
    ]
    key_characters = [
        world.characters[character_id].name if character_id in world.characters else character_id
        for character_id in faction.key_characters[:6]
    ]
    messages = _build_observer_messages(
        title=f"Faction {faction.name} ({faction.faction_id})",
        body_lines=[
            f"Civilization: {civilization.name if civilization else 'None'}",
            f"Type: {faction.faction_type}",
            f"Power scope: {faction.power_scope}",
            f"Influence: {faction.influence}",
            f"Influence trend: {faction.influence_trend}",
            f"Cohesion: {faction.cohesion}",
            f"Doctrine tags: {', '.join(faction.doctrine_tags) or 'None'}",
            f"Controlled regions: {', '.join(controlled_regions) or 'None'}",
            f"Key characters: {'Unknown to outside observers' if player_view else (', '.join(key_characters) or 'None')}",
            f"Rival factions: {'Unknown to outside observers' if player_view else (', '.join(faction.rival_factions) or 'None')}",
            f"Allied factions: {'Unknown to outside observers' if player_view else (', '.join(faction.allied_factions) or 'None')}",
            "Recent events:",
            *([f"- {item}" for item in recent_events] if recent_events else ["- None"]),
            "Related dynamic structures:",
            *related_dynamic_structure_context_lines(
                world,
                [faction.faction_id] + faction.controlled_regions[:6],
                view=view,
                limit=4,
            ),
        ],
        mode=mode,
        voice_instruction=_faction_observer_voice(faction),
    )
    return _run_observer_completion(client, messages, ai_config, mode)


def _run_observer_completion(
    client: object,
    messages: list[dict[str, str]],
    ai_config: dict[str, object],
    mode: str,
) -> ObservationResult:
    try:
        tier = resolve_observer_tier(ai_config, mode=mode)
        payload = client.create_json_completion_with_limits(
            messages,
            max_tokens=tier.max_tokens,
            thinking_budget=tier.thinking_budget,
        )
        text = _sanitize_observer_text(str(payload.get("text", "")).strip())
        if not text:
            raise LLMClientError("Observer JSON missing text")
        return ObservationResult(source=llm_source_label(ai_config, client), text=text, tier=tier.tier)
    except LLMClientError as exc:
        return ObservationResult(source="none", text=None, error=str(exc), tier=resolve_observer_tier(ai_config, mode=mode).tier)


def _build_observer_messages(
    title: str,
    body_lines: list[str],
    mode: str,
    voice_instruction: str | None = None,
) -> list[dict[str, str]]:
    system_rules = (PROMPT_ROOT / "system_rules.txt").read_text(encoding="utf-8").strip()
    observer_prompt = (PROMPT_ROOT / "observer_focus.txt").read_text(encoding="utf-8").strip()
    body = "\n".join(body_lines)
    if mode == "full":
        length_instruction = "Keep text under 220 Chinese characters."
        style_instruction = "Make it denser and slightly richer in texture than brief mode."
    else:
        length_instruction = "Keep text under 140 Chinese characters."
        style_instruction = "Keep it concise."
    user_prompt = "\n".join(
        [
            observer_prompt,
            "",
            "Return a JSON object with one key: text.",
            "text must be one short observation paragraph in Chinese.",
            length_instruction,
            "Do not invent authoritative facts beyond the supplied state.",
            "You may infer mood, pressure, and likely atmosphere from the supplied facts.",
            "Do not include analysis, instructions, bullet points, or think tags.",
            style_instruction,
            f"Narrative voice: {voice_instruction or 'Use a neutral outside-observer tone.'}",
            "Output only the final observation in the text field.",
            "",
            title,
            body,
        ]
    )
    return [
        {"role": "system", "content": system_rules},
        {"role": "user", "content": user_prompt},
    ]


def _format_last_intent(last_intent: dict[str, object]) -> str:
    if not last_intent:
        return "None"
    intent_type = str(last_intent.get("intent_type", "unknown"))
    target_ref = str(last_intent.get("target_ref", "unknown"))
    return f"{intent_type} -> {target_ref}"


def _sanitize_observer_text(text: str) -> str:
    """Strip leaked reasoning tags or prompt fragments from observer text."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    cleaned = cleaned.replace("</think>", "").replace("<think>", "").strip()
    return cleaned


def _observer_origin_mode(relic: object) -> str:
    if getattr(relic, "relic_type", "") == "megastructure":
        return megastructure_origin_label(relic)
    return getattr(relic, "origin_mode", "n/a") or "n/a"


def _observer_construction_state(relic: object) -> str:
    return getattr(relic, "construction_state", "n/a") or "n/a"


def _region_observer_signal(world: WorldState, region_id: str, recent_events: list[str]) -> int:
    region = world.regions[region_id]
    score = min(len(recent_events), 3)
    if region.scarcity == "high":
        score += 2
    elif region.scarcity == "medium":
        score += 1
    if region.political_tension == "high":
        score += 2
    elif region.political_tension == "medium":
        score += 1
    if region.security == "low":
        score += 2
    elif region.security == "medium":
        score += 1
    return score


def _character_observer_signal(character: object, knowledge: object) -> int:
    score = 0
    if getattr(character, "agency_mode", "") == "strategic":
        score += 2
    elif getattr(character, "agency_mode", "") == "opportunistic":
        score += 1
    notoriety = getattr(character, "notoriety", "low")
    if notoriety == "high":
        score += 2
    elif notoriety == "medium":
        score += 1
    score += min(len(getattr(knowledge, "direct_events", [])), 2)
    score += min(len(getattr(knowledge, "rumored_events", [])), 1)
    if getattr(knowledge, "flashpoint_region_id", None):
        score += 2
    return score


def _civilization_observer_signal(civilization: object, recent_events: list[str]) -> int:
    score = min(len(recent_events), 4)
    if getattr(civilization, "cohesion", "") == "low":
        score += 2
    if getattr(civilization, "scarcity_pressure", "") == "high":
        score += 2
    if getattr(civilization, "expansion_pressure", "") == "high":
        score += 1
    if getattr(civilization, "legitimacy", "") == "low":
        score += 2
    return score


def _relic_observer_signal(relic: object, recent_events: list[str]) -> int:
    score = min(len(recent_events), 4)
    if getattr(relic, "significance", "") == "high":
        score += 2
    if getattr(relic, "danger", "") == "high":
        score += 2
    if getattr(relic, "activation_state", "") not in {"dormant", "sealed", "inactive"}:
        score += 1
    if getattr(relic, "relic_type", "") == "megastructure":
        score += 1
    return score


def _faction_observer_signal(faction: object, recent_events: list[str]) -> int:
    score = min(len(recent_events), 4)
    if getattr(faction, "influence", "") == "high":
        score += 2
    elif getattr(faction, "influence", "") == "medium":
        score += 1
    if getattr(faction, "cohesion", "") == "low":
        score += 1
    score += min(len(getattr(faction, "controlled_regions", [])), 2)
    return score


def _region_observer_voice(world: WorldState, region_id: str) -> str:
    frame = getattr(world, "world_frame", None)
    lens = getattr(frame, "observer_lens", "macro_pressure_and_public_signals")
    if lens == "macro_pressure_and_public_signals":
        return "Use a grounded public-observer tone, emphasizing atmosphere, pressure drift, and visible social signals."
    return "Use a neutral regional observation tone, centered on texture and public-facing pressure."


def _character_observer_voice(character: object) -> str:
    agency_mode = getattr(character, "agency_mode", "reactive")
    if agency_mode == "strategic":
        return "Write like a close but restrained profile of a planner under pressure, highlighting calculation, restraint, and directional intent."
    if agency_mode == "opportunistic":
        return "Write like an observer noting someone who is alert to openings, with quick adjustments and unstable positioning."
    return "Write like an observer tracking a pressured supporting figure, emphasizing reaction, adaptation, and local strain."


def _civilization_observer_voice(civilization: object) -> str:
    governance_mode = getattr(civilization, "governance_mode", "")
    if governance_mode == "hybrid_governance":
        return "Use a macro-political tone, as if reading structural drift inside a layered governing order rather than judging individuals."
    if governance_mode == "security_state":
        return "Use a cold institutional tone, emphasizing control, lock-in, and the cost of maintaining order."
    return "Use a broad civilizational tone, emphasizing trajectory, governing tension, and system-level pressure."


def _relic_observer_voice(relic: object) -> str:
    relic_type = getattr(relic, "relic_type", "")
    if relic_type == "megastructure":
        return "Write like an observer facing an unfinished or active large-scale structure, emphasizing scale, disturbance, and organized human effort around it."
    return "Write like an observer facing a non-human anomaly or exceptional presence, emphasizing unease, attraction, and surrounding pressure."


def _faction_observer_voice(faction: object) -> str:
    doctrine_tags = set(getattr(faction, "doctrine_tags", []) or [])
    if {"efficiency", "growth"} & doctrine_tags:
        return "Use an organizational-intelligence tone, emphasizing throughput, leverage, and disciplined expansion."
    if {"secrecy", "legacy_control"} & doctrine_tags:
        return "Use a guarded internal-briefing tone, emphasizing concealment, controlled access, and indirect pressure."
    if {"security", "order"} & doctrine_tags:
        return "Use a security-apparatus tone, emphasizing stabilization, containment, and visible enforcement."
    return "Use a factional observation tone, emphasizing doctrine, positioning, and how the organization bends local conditions."
