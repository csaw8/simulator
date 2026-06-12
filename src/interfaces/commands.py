"""Observer command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.agents.intent_generator import generate_intents
from src.agents.scheduler import build_wake_schedule
from src.config.models import AIConfig, WorldConfig
from src.core.engine import WorldEngine, StepResult
from src.core.budget import BudgetManager
from src.core.dynamic_structure_ai import (
    format_ai_proposal_audit_summary,
    format_ai_proposal_audits,
    format_dynamic_structure_ai_result,
    propose_dynamic_structures_for_watch,
)
from src.core.dynamic_structure_targets import format_dynamic_structure_targets
from src.core.emergent_presence_proposals import (
    apply_emergent_presence_proposals,
    validate_emergent_presence_proposals,
)
from src.core.emergent_presence_ai import (
    format_emergent_presence_ai_result,
    propose_emergent_presences_for_watch,
)
from src.events.query import select_events
from src.events.taxonomy import event_matches_focus
from src.interfaces.stream_view import (
    format_events,
    format_status,
    format_step_result,
    format_world_frame,
)
from src.narrative.observer import (
    observe_character_with_ai,
    observe_civilization_with_ai,
    observe_faction_with_ai,
    observe_region_with_ai,
    observe_relic_with_ai,
)
from src.narrative.summaries import (
    summarize_character,
    summarize_civilization,
    summarize_faction,
    summarize_project,
    summarize_region,
    summarize_region_node,
    summarize_dynamic_structure,
    summarize_emergent_presence,
    summarize_relic,
    summarize_supply_line,
)
from src.narrative.visibility import PLAYER_VIEW, TRUTH_VIEW, is_player_view, normalize_view
from src.storage.snapshots import save_world_state
from src.storage.db import DEFAULT_SQLITE_PATH, export_world_to_sqlite, format_sqlite_stats
from src.world.builder import build_world


@dataclass(slots=True)
class CommandContext:
    """Runtime objects shared by CLI commands."""

    engine: WorldEngine
    world_config: WorldConfig
    ai_config: AIConfig
    snapshot_path: Path
    last_result: StepResult | None = None


def handle_command(context: CommandContext, raw_command: str) -> str:
    """Parse and execute a CLI command."""
    command = raw_command.strip()
    if not command:
        return ""

    parts = command.split()
    action = parts[0].lower()

    if action == "help":
        return (
            "Commands:\n"
            "  help              Show this help text\n"
            "  status            Show current world summary\n"
            "  frame [brief|full] [player|truth]   Show current world structure template\n"
            "  step [n] [player|truth]          Advance the world by n steps (default 1)\n"
            "  events [n] [brief|full] [player|truth] [focus=theme]            Show recent events (default 10)\n"
            "  events <type> <id> [n] [brief|full] [player|truth] [focus=theme] Show focused events for region/character/civ/faction/relic/dynamic\n"
            "  watch region <id> [brief|full] [player|truth] [focus=theme]     Observe a region\n"
            "  watch character <id> [brief|full] [player|truth] [focus=theme]  Observe a character\n"
            "  watch civ <id> [brief|full] [player|truth] [focus=theme]        Observe a civilization\n"
            "  watch faction <id> [brief|full] [player|truth] [focus=theme]    Observe a faction\n"
            "  watch project <id> [brief|full] [player|truth] [focus=theme]    Observe a project network\n"
            "  watch node <id> [brief|full] [player|truth] [focus=theme]       Observe a region node\n"
            "  watch relic <id> [brief|full] [player|truth] [focus=theme]      Observe a relic\n"
            "  watch supply <id> [brief|full] [player|truth] [focus=theme]     Observe a supply line\n"
            "  watch dynamic <id> [brief|full] [player|truth] [focus=theme]    Observe a dynamic structure\n"
            "  watch emergent <id> [brief|full] [player|truth] [focus=theme]   Observe an emergent presence\n"
            "  Add propose=dynamic or propose=emergent for dry-run proposals; use apply=dynamic or apply=emergent to write accepted proposals\n"
            "  propose emergent <region_id> [apply]  Create a bounded local emergent-presence sample\n"
            "  targets dynamic [n]     Show high-signal targets for dynamic proposal sampling\n"
            "  audit proposals [n]      Show recent AI proposal audit records\n"
            "  audit proposals summary [n]  Show aggregate proposal quality metrics\n"
            "  debug llm         Test one live SiliconFlow request on the top wake candidate\n"
            "  reset             Rebuild the world from default config\n"
            "  save              Save the current world snapshot\n"
            "  db export [path]  Export current state to SQLite query DB\n"
            "  db stats [path]   Show SQLite table counts\n"
            "  quit              Exit the CLI"
        )

    if action == "status":
        return format_status(context.engine.world)

    if action == "frame":
        return _handle_frame(context, parts)

    if action == "step":
        return _handle_step(context, parts)

    if action == "events":
        return _handle_events(context, parts)

    if action == "watch":
        return _handle_watch(context, parts)

    if action == "audit":
        return _handle_audit(context, parts)

    if action == "targets":
        return _handle_targets(context, parts)

    if action == "propose":
        return _handle_propose(context, parts)

    if action == "debug":
        return _handle_debug(context, parts)

    if action == "db":
        return _handle_db(context, parts)

    if action == "reset":
        world = build_world(context.world_config.to_dict())
        context.engine = WorldEngine(world, ai_config=context.ai_config.to_dict())
        context.last_result = None
        save_world_state(context.engine.world, context.snapshot_path)
        return "World has been reset and saved."

    if action == "save":
        save_world_state(context.engine.world, context.snapshot_path)
        return f"World saved to {context.snapshot_path}"

    if action == "quit":
        return "__QUIT__"

    return f"Unknown command: {action}. Type 'help' for available commands."


def _parse_optional_int(parts: list[str], default: int) -> int:
    """Parse a positive integer argument if present."""
    if len(parts) < 2:
        return default
    try:
        value = int(parts[1])
    except ValueError:
        return default
    return max(1, value)


def _handle_audit(context: CommandContext, parts: list[str]) -> str:
    if len(parts) < 2 or parts[1].lower() != "proposals":
        return "Usage: audit proposals [n] | audit proposals summary [n]"
    limit = 10
    if len(parts) >= 3 and parts[2].lower() == "summary":
        if len(parts) >= 4:
            try:
                limit = max(1, int(parts[3]))
            except ValueError:
                return "Usage: audit proposals [n] | audit proposals summary [n]"
        return format_ai_proposal_audit_summary(context.engine.world, limit=limit)
    if len(parts) >= 3:
        try:
            limit = max(1, int(parts[2]))
        except ValueError:
            return "Usage: audit proposals [n] | audit proposals summary [n]"
    return format_ai_proposal_audits(context.engine.world, limit=limit)


def _handle_targets(context: CommandContext, parts: list[str]) -> str:
    if len(parts) < 2 or parts[1].lower() != "dynamic":
        return "Usage: targets dynamic [n]"
    limit = 10
    if len(parts) >= 3:
        try:
            limit = max(1, int(parts[2]))
        except ValueError:
            return "Usage: targets dynamic [n]"
    return format_dynamic_structure_targets(context.engine.world, limit=limit)


def _handle_propose(context: CommandContext, parts: list[str]) -> str:
    if len(parts) < 3 or parts[1].lower() != "emergent":
        return "Usage: propose emergent <region_id> [apply]"
    region_id = parts[2]
    if region_id not in context.engine.world.regions:
        return f"Unknown region: {region_id}"
    apply = len(parts) >= 4 and parts[3].lower() == "apply"
    payload = _build_sample_emergent_presence_payload(context, region_id)
    result = (
        apply_emergent_presence_proposals(
            context.engine.world,
            payload,
            origin="manual_cli",
        )
        if apply
        else validate_emergent_presence_proposals(context.engine.world, payload)
    )
    if apply and result.accepted:
        save_world_state(context.engine.world, context.snapshot_path)
    lines = ["Emergent presence proposal:"]
    lines.append(f"  mode: {'apply' if apply else 'dry-run'}")
    lines.append(f"  accepted: {len(result.accepted)}")
    lines.append(f"  rejected: {len(result.rejected)}")
    for item in result.accepted[:3]:
        lines.append(f"    accepted_ref: {item}")
    for item in result.rejected[:3]:
        lines.append(f"    rejected_reason: {item}")
    return "\n".join(lines)


def _build_sample_emergent_presence_payload(context: CommandContext, region_id: str) -> dict[str, object]:
    world = context.engine.world
    relic_refs = [
        relic.relic_id
        for relic in world.relics.values()
        if relic.current_region_id == region_id
    ][:2]
    dynamic_refs = [
        structure.structure_id
        for structure in world.dynamic_structures.values()
        if region_id in structure.scope_refs + structure.linked_refs
    ][:2]
    return {
        "proposals": [
            {
                "action": "create",
                "presence_type": "spore_bloom",
                "name": f"Trace Bloom {region_id}",
                "summary": "A bounded anomalous ecological pressure is forming around a visible containment edge.",
                "home_region_ref": region_id,
                "current_region_refs": [region_id],
                "linked_relic_refs": relic_refs,
                "linked_dynamic_refs": dynamic_refs,
                "linked_faction_refs": [],
                "lifecycle_stage": "forming",
                "population_scale": "trace",
                "adaptation_level": "low",
                "mobility": "local",
                "pressure": "medium",
                "behavior_tags": ["reactive"],
                "sensory_tags": ["spore_haze"],
                "ecological_tags": ["biosecurity_risk"],
                "visibility": "rumored",
                "relation_type": "nests_in",
            }
        ]
    }


def _handle_db(context: CommandContext, parts: list[str]) -> str:
    if len(parts) < 2:
        return "Usage: db export [path] | db stats [path]"
    subcommand = parts[1].lower()
    path = Path(parts[2]) if len(parts) >= 3 else DEFAULT_SQLITE_PATH
    if subcommand == "export":
        export_world_to_sqlite(context.engine.world, path)
        return f"SQLite export written to {path}"
    if subcommand == "stats":
        return format_sqlite_stats(path)
    return "Usage: db export [path] | db stats [path]"


def _handle_frame(context: CommandContext, parts: list[str]) -> str:
    mode = "brief"
    view = TRUTH_VIEW
    usage = "Usage: frame [brief|full] [player|truth]"
    for token in parts[1:]:
        lowered = token.strip().lower()
        if lowered in {"brief", "full"}:
            mode = lowered
            continue
        if lowered in {PLAYER_VIEW, TRUTH_VIEW}:
            view = normalize_view(lowered)
            continue
        return usage
    return format_world_frame(context.engine.world, mode=mode, view=view)


def _handle_events(context: CommandContext, parts: list[str]) -> str:
    """Render recent events with optional focus filtering."""
    parse_result = _parse_events_args(parts)
    if parse_result["error"]:
        return parse_result["error"]

    selected = select_events(
        context.engine.world.event_stream.events,
        target_type=parse_result["target_type"],
        target_id=parse_result["target_id"],
        limit=parse_result["limit"],
        view=str(parse_result["view"]),
    )
    selected = _filter_events_by_focus(selected, focus=parse_result["focus"])
    if not selected:
        if parse_result["target_type"] and parse_result["target_id"]:
            return (
                f"No events recorded for "
                f"{parse_result['target_type']} {parse_result['target_id']}."
            )
        return "No events recorded."
    return format_events(
        selected,
        world=context.engine.world,
        limit=parse_result["limit"],
        target_type=parse_result["target_type"],
        target_id=parse_result["target_id"],
        mode=parse_result["mode"],
        view=str(parse_result["view"]),
        focus=str(parse_result["focus"]) if parse_result["focus"] else None,
    )


def _parse_events_args(parts: list[str]) -> dict[str, str | int | None]:
    """Parse `events` command arguments."""
    usage = (
        "Usage: events [n] [brief|full] [player|truth] [focus=theme] | "
        "events <region|character|civ|faction|relic|dynamic|emergent> <id> [n] [brief|full] [player|truth] [focus=theme]"
    )
    result: dict[str, str | int | None] = {
        "target_type": None,
        "target_id": None,
        "limit": 10,
        "mode": "brief",
        "view": TRUTH_VIEW,
        "focus": None,
        "error": None,
    }

    args = parts[1:]
    if not args:
        return result

    first = args[0].lower()
    if first in {"brief", "full", PLAYER_VIEW, TRUTH_VIEW} or first.isdigit():
        for token in args:
            lowered = token.lower()
            if token.isdigit():
                if result["limit"] != 10:
                    result["error"] = usage
                    return result
                result["limit"] = max(1, int(token))
                continue
            if lowered in {"brief", "full"}:
                if result["mode"] != "brief":
                    result["error"] = usage
                    return result
                result["mode"] = lowered
                continue
            if lowered in {PLAYER_VIEW, TRUTH_VIEW}:
                if result["view"] != TRUTH_VIEW:
                    result["error"] = usage
                    return result
                result["view"] = normalize_view(lowered)
                continue
            if lowered.startswith("focus="):
                if result["focus"] is not None:
                    result["error"] = usage
                    return result
                result["focus"] = lowered.split("=", 1)[1] or None
                continue
            result["error"] = usage
            return result
        return result

    if first not in {"region", "character", "civ", "faction", "relic", "dynamic", "structure", "emergent", "emergent_presence"}:
        result["error"] = "Unknown event focus. Use 'region', 'character', 'civ', 'faction', 'relic', 'dynamic', or 'emergent'."
        return result

    if len(args) < 2:
        result["error"] = usage
        return result

    result["target_type"] = first
    result["target_id"] = args[1]
    tail = args[2:]
    for token in tail:
        lowered = token.lower()
        if token.isdigit():
            if result["limit"] != 10:
                result["error"] = usage
                return result
            result["limit"] = max(1, int(token))
            continue
        if lowered in {"brief", "full"}:
            if result["mode"] != "brief":
                result["error"] = usage
                return result
            result["mode"] = lowered
            continue
        if lowered in {PLAYER_VIEW, TRUTH_VIEW}:
            if result["view"] != TRUTH_VIEW:
                result["error"] = usage
                return result
            result["view"] = normalize_view(lowered)
            continue
        if lowered.startswith("focus="):
            if result["focus"] is not None:
                result["error"] = usage
                return result
            result["focus"] = lowered.split("=", 1)[1] or None
            continue
        result["error"] = usage
        return result

    return result


def _filter_events_by_focus(events, *, focus: str | int | None):
    focus_text = str(focus).strip().lower() if focus else ""
    if not focus_text:
        return events

    return [event for event in events if event_matches_focus(event, focus_text)]


def _append_ai_observation(
    base_output: str,
    source: str,
    text: str | None,
    error: str | None,
    tier: str | None,
) -> str:
    lines = [base_output, "AI observation:"]
    lines.append(f"  source: {source}")
    if tier:
        lines.append(f"  tier: {tier}")
    if text:
        lines.append(f"  text: {text}")
    if error:
        lines.append(f"  error: {error}")
    return "\n".join(lines)


def _should_render_ai_observation_block(
    *,
    view: str,
    source: str,
    text: str | None,
    error: str | None,
) -> bool:
    if text:
        return True
    if not is_player_view(view):
        return True
    if source != "none":
        return True
    return error not in {
        "observer_view_blocked",
        "observer_mode_blocked",
        "observer_policy_disabled",
    }


def _parse_watch_mode(raw_mode: str) -> str:
    mode = raw_mode.strip().lower()
    return "full" if mode == "full" else "brief"


def _parse_watch_options(parts: list[str]) -> tuple[str, str, str | None, str | None, str | None]:
    mode = "brief"
    view = TRUTH_VIEW
    focus: str | None = None
    dynamic_proposal_mode: str | None = None
    emergent_proposal_mode: str | None = None
    for token in parts[3:]:
        lowered = token.strip().lower()
        if lowered in {"brief", "full"}:
            mode = _parse_watch_mode(lowered)
        elif lowered in {PLAYER_VIEW, TRUTH_VIEW}:
            view = normalize_view(lowered)
        elif lowered.startswith("focus="):
            focus = lowered.split("=", 1)[1] or None
        elif lowered == "propose=dynamic":
            dynamic_proposal_mode = "dry-run"
        elif lowered == "apply=dynamic":
            dynamic_proposal_mode = "apply"
        elif lowered == "propose=emergent":
            emergent_proposal_mode = "dry-run"
        elif lowered == "apply=emergent":
            emergent_proposal_mode = "apply"
    return mode, view, focus, dynamic_proposal_mode, emergent_proposal_mode


def _handle_step(context: CommandContext, parts: list[str]) -> str:
    steps, view, error = _parse_step_args(parts)
    if error:
        return error
    outputs: list[str] = []
    for step_index in range(1, steps + 1):
        context.last_result = context.engine.step()
        outputs.append(
            format_step_result(
                context.last_result,
                step_index,
                view=view,
                world=context.engine.world,
            )
        )
    save_world_state(context.engine.world, context.snapshot_path)
    return "\n".join(outputs)


def _parse_step_args(parts: list[str]) -> tuple[int, str, str | None]:
    usage = "Usage: step [n] [player|truth]"
    steps = 1
    view = TRUTH_VIEW
    for token in parts[1:]:
        lowered = token.strip().lower()
        if token.isdigit():
            if steps != 1:
                return steps, view, usage
            steps = max(1, int(token))
            continue
        if lowered in {PLAYER_VIEW, TRUTH_VIEW}:
            if view != TRUTH_VIEW:
                return steps, view, usage
            view = normalize_view(lowered)
            continue
        return steps, view, usage
    return steps, view, None


def _handle_watch(context: CommandContext, parts: list[str]) -> str:
    if len(parts) < 3:
        return (
            "Usage: watch region <id> [brief|full] [player|truth] [focus=theme] | "
            "watch character <id> [brief|full] [player|truth] [focus=theme] | "
            "watch civ <id> [brief|full] [player|truth] [focus=theme] | "
            "watch faction <id> [brief|full] [player|truth] [focus=theme] | "
            "watch project <id> [brief|full] [player|truth] [focus=theme] | "
            "watch node <id> [brief|full] [player|truth] [focus=theme] | "
            "watch relic <id> [brief|full] [player|truth] [focus=theme] | "
            "watch supply <id> [brief|full] [player|truth] [focus=theme]"
            " | watch dynamic <id> [brief|full] [player|truth] [focus=theme]"
            " | watch emergent <id> [brief|full] [player|truth] [focus=theme]"
        )

    target_type = parts[1].lower()
    target_id = parts[2]
    mode, view, focus, dynamic_proposal_mode, emergent_proposal_mode = _parse_watch_options(parts)
    event_limit = 8 if mode == "full" else 5
    ai_config = context.ai_config.to_dict()
    skip_ai_observation = focus is not None

    if target_type == "region":
        output = summarize_region(
            context.engine.world,
            target_id,
            event_limit=event_limit,
            mode=mode,
            view=view,
            focus=focus,
        )
        if not skip_ai_observation:
            ai_observation = observe_region_with_ai(
                context.engine.world,
                target_id,
                ai_config,
                mode=mode,
                view=view,
            )
            if _should_render_ai_observation_block(
                view=view,
                source=ai_observation.source,
                text=ai_observation.text,
                error=ai_observation.error,
            ):
                output = _append_ai_observation(
                    output,
                    ai_observation.source,
                    ai_observation.text,
                    ai_observation.error,
                    ai_observation.tier,
                )
        save_world_state(context.engine.world, context.snapshot_path)
        return _append_dynamic_structure_proposal_if_requested(
            context,
            output,
            target_type=target_type,
            target_id=target_id,
            mode=mode,
            view=view,
            dynamic_proposal_mode=dynamic_proposal_mode,
            emergent_proposal_mode=emergent_proposal_mode,
        )

    if target_type == "character":
        character = context.engine.world.characters.get(target_id)
        if character is not None:
            character.observation_trace += 1
        output = summarize_character(
            context.engine.world,
            target_id,
            event_limit=event_limit,
            mode=mode,
            view=view,
            focus=focus,
        )
        if not skip_ai_observation:
            ai_observation = observe_character_with_ai(
                context.engine.world,
                target_id,
                ai_config,
                mode=mode,
                view=view,
            )
            if _should_render_ai_observation_block(
                view=view,
                source=ai_observation.source,
                text=ai_observation.text,
                error=ai_observation.error,
            ):
                output = _append_ai_observation(
                    output,
                    ai_observation.source,
                    ai_observation.text,
                    ai_observation.error,
                    ai_observation.tier,
                )
        save_world_state(context.engine.world, context.snapshot_path)
        return _append_dynamic_structure_proposal_if_requested(
            context,
            output,
            target_type=target_type,
            target_id=target_id,
            mode=mode,
            view=view,
            dynamic_proposal_mode=dynamic_proposal_mode,
            emergent_proposal_mode=emergent_proposal_mode,
        )

    if target_type == "civ":
        output = summarize_civilization(
            context.engine.world,
            target_id,
            event_limit=event_limit,
            mode=mode,
            view=view,
            focus=focus,
        )
        if not skip_ai_observation:
            ai_observation = observe_civilization_with_ai(
                context.engine.world,
                target_id,
                ai_config,
                mode=mode,
                view=view,
            )
            if _should_render_ai_observation_block(
                view=view,
                source=ai_observation.source,
                text=ai_observation.text,
                error=ai_observation.error,
            ):
                output = _append_ai_observation(
                    output,
                    ai_observation.source,
                    ai_observation.text,
                    ai_observation.error,
                    ai_observation.tier,
                )
        save_world_state(context.engine.world, context.snapshot_path)
        return _append_dynamic_structure_proposal_if_requested(
            context,
            output,
            target_type=target_type,
            target_id=target_id,
            mode=mode,
            view=view,
            dynamic_proposal_mode=dynamic_proposal_mode,
            emergent_proposal_mode=emergent_proposal_mode,
        )

    if target_type == "relic":
        output = summarize_relic(
            context.engine.world,
            target_id,
            event_limit=event_limit,
            mode=mode,
            view=view,
            focus=focus,
        )
        if not skip_ai_observation:
            ai_observation = observe_relic_with_ai(
                context.engine.world,
                target_id,
                ai_config,
                mode=mode,
                view=view,
            )
            if _should_render_ai_observation_block(
                view=view,
                source=ai_observation.source,
                text=ai_observation.text,
                error=ai_observation.error,
            ):
                output = _append_ai_observation(
                    output,
                    ai_observation.source,
                    ai_observation.text,
                    ai_observation.error,
                    ai_observation.tier,
                )
        save_world_state(context.engine.world, context.snapshot_path)
        return _append_dynamic_structure_proposal_if_requested(
            context,
            output,
            target_type=target_type,
            target_id=target_id,
            mode=mode,
            view=view,
            dynamic_proposal_mode=dynamic_proposal_mode,
            emergent_proposal_mode=emergent_proposal_mode,
        )

    if target_type == "project":
        output = summarize_project(
            context.engine.world,
            target_id,
            event_limit=event_limit,
            mode=mode,
            view=view,
            focus=focus,
        )
        save_world_state(context.engine.world, context.snapshot_path)
        return _append_dynamic_structure_proposal_if_requested(
            context,
            output,
            target_type=target_type,
            target_id=target_id,
            mode=mode,
            view=view,
            dynamic_proposal_mode=dynamic_proposal_mode,
            emergent_proposal_mode=emergent_proposal_mode,
        )

    if target_type == "node":
        output = summarize_region_node(
            context.engine.world,
            target_id,
            event_limit=event_limit,
            mode=mode,
            view=view,
            focus=focus,
        )
        save_world_state(context.engine.world, context.snapshot_path)
        return _append_dynamic_structure_proposal_if_requested(
            context,
            output,
            target_type=target_type,
            target_id=target_id,
            mode=mode,
            view=view,
            dynamic_proposal_mode=dynamic_proposal_mode,
            emergent_proposal_mode=emergent_proposal_mode,
        )

    if target_type == "faction":
        output = summarize_faction(
            context.engine.world,
            target_id,
            event_limit=event_limit,
            mode=mode,
            view=view,
            focus=focus,
        )
        if not skip_ai_observation:
            ai_observation = observe_faction_with_ai(
                context.engine.world,
                target_id,
                ai_config,
                mode=mode,
                view=view,
            )
            if _should_render_ai_observation_block(
                view=view,
                source=ai_observation.source,
                text=ai_observation.text,
                error=ai_observation.error,
            ):
                output = _append_ai_observation(
                    output,
                    ai_observation.source,
                    ai_observation.text,
                    ai_observation.error,
                    ai_observation.tier,
                )
        save_world_state(context.engine.world, context.snapshot_path)
        return _append_dynamic_structure_proposal_if_requested(
            context,
            output,
            target_type=target_type,
            target_id=target_id,
            mode=mode,
            view=view,
            dynamic_proposal_mode=dynamic_proposal_mode,
            emergent_proposal_mode=emergent_proposal_mode,
        )

    if target_type == "supply":
        output = summarize_supply_line(
            context.engine.world,
            target_id,
            event_limit=event_limit,
            mode=mode,
            view=view,
            focus=focus,
        )
        save_world_state(context.engine.world, context.snapshot_path)
        return _append_dynamic_structure_proposal_if_requested(
            context,
            output,
            target_type=target_type,
            target_id=target_id,
            mode=mode,
            view=view,
            dynamic_proposal_mode=dynamic_proposal_mode,
            emergent_proposal_mode=emergent_proposal_mode,
        )

    if target_type in {"dynamic", "structure"}:
        output = summarize_dynamic_structure(
            context.engine.world,
            target_id,
            event_limit=event_limit,
            mode=mode,
            view=view,
            focus=focus,
        )
        save_world_state(context.engine.world, context.snapshot_path)
        return _append_dynamic_structure_proposal_if_requested(
            context,
            output,
            target_type=target_type,
            target_id=target_id,
            mode=mode,
            view=view,
            dynamic_proposal_mode=dynamic_proposal_mode,
            emergent_proposal_mode=emergent_proposal_mode,
        )

    if target_type in {"emergent", "emergent_presence"}:
        output = summarize_emergent_presence(
            context.engine.world,
            target_id,
            event_limit=event_limit,
            mode=mode,
            view=view,
            focus=focus,
        )
        save_world_state(context.engine.world, context.snapshot_path)
        return _append_dynamic_structure_proposal_if_requested(
            context,
            output,
            target_type=target_type,
            target_id=target_id,
            mode=mode,
            view=view,
            dynamic_proposal_mode=dynamic_proposal_mode,
            emergent_proposal_mode=emergent_proposal_mode,
        )

    return "Unknown watch target. Use 'region', 'character', 'civ', 'faction', 'project', 'node', 'relic', 'supply', 'dynamic', or 'emergent'."


def _append_dynamic_structure_proposal_if_requested(
    context: CommandContext,
    output: str,
    *,
    target_type: str,
    target_id: str,
    mode: str,
    view: str,
    dynamic_proposal_mode: str | None,
    emergent_proposal_mode: str | None,
) -> str:
    if dynamic_proposal_mode is None and emergent_proposal_mode is None:
        return output
    blocks = [output]
    if dynamic_proposal_mode is not None:
        dynamic_result = propose_dynamic_structures_for_watch(
            context.engine.world,
            target_type=target_type,
            target_id=target_id,
            ai_config=context.ai_config.to_dict(),
            mode=mode,
            view=view,
            apply=dynamic_proposal_mode == "apply",
        )
        if dynamic_proposal_mode == "apply" and dynamic_result.validation.accepted:
            save_world_state(context.engine.world, context.snapshot_path)
        blocks.append(format_dynamic_structure_ai_result(dynamic_result))
    if emergent_proposal_mode is not None:
        emergent_result = propose_emergent_presences_for_watch(
            context.engine.world,
            target_type=target_type,
            target_id=target_id,
            ai_config=context.ai_config.to_dict(),
            mode=mode,
            view=view,
            apply=emergent_proposal_mode == "apply",
        )
        if emergent_proposal_mode == "apply" and emergent_result.validation.accepted:
            save_world_state(context.engine.world, context.snapshot_path)
        blocks.append(format_emergent_presence_ai_result(emergent_result))
    return "\n".join(blocks)


def _handle_debug(context: CommandContext, parts: list[str]) -> str:
    if len(parts) < 2 or parts[1].lower() != "llm":
        return "Usage: debug llm"

    budget = BudgetManager.from_config(context.ai_config.to_dict())
    wake_schedule = build_wake_schedule(context.engine.world, budget)
    intents = generate_intents(context.engine.world, wake_schedule, context.ai_config.to_dict())
    first_intent = intents.all_intents[0] if intents.all_intents else None

    if first_intent is None:
        return "No wake candidates available for LLM debug."

    lines = ["LLM debug result:"]
    lines.append(f"  character_id: {first_intent.character_id}")
    lines.append(f"  source: {first_intent.source}")
    lines.append(f"  intent_type: {first_intent.intent_type}")
    lines.append(f"  target_ref: {first_intent.target_ref}")
    if intents.last_llm_error:
        lines.append(f"  last_llm_error: {intents.last_llm_error}")
    return "\n".join(lines)
