"""Streaming event output view."""

from __future__ import annotations

from collections import Counter

from src.core.engine import StepResult
from src.events.models import Event
from src.events.query import describe_focus
from src.events.taxonomy import event_family, event_theme_tags
from src.events.visibility_rules import (
    filter_events_for_view,
    format_event_refs_for_view,
    format_event_summary_for_view,
    format_visibility_for_view,
)
from src.narrative.chronicler import format_chronicle_for_view
from src.narrative.visibility import is_player_view
from src.world.state import WorldState


def format_status(world: WorldState) -> str:
    """Format a compact world status block."""
    summary = world.summary()
    ordered_keys = [
        "seed",
        "tick",
        "granularity",
        "civilizations",
        "regions",
        "factions",
        "characters",
        "protagonists",
        "active_characters",
        "relics",
        "projects",
        "supply_lines",
        "region_nodes",
        "dynamic_structures",
        "emergent_presences",
        "ai_proposal_audits",
        "pressure_threads",
        "relations",
        "events",
        "world_frame",
    ]
    lines = ["World status:"]
    for key in ordered_keys:
        lines.append(f"  {key}: {summary[key]}")
    return "\n".join(lines)


def format_world_frame(world: WorldState, *, mode: str = "brief", view: str = "truth") -> str:
    """Format the current world structure template."""
    frame = world.structure_template
    lines = ["World frame:"]
    lines.append(f"  era_frame: {frame.era_frame}")
    lines.append(f"  pressure_axes: {', '.join(frame.pressure_axes) or 'None'}")
    lines.append(f"  dominant_fronts: {', '.join(frame.dominant_fronts) or 'None'}")
    if mode == "full":
        lines.append(
            f"  organization_climates: {', '.join(frame.organization_climates) or 'None'}"
        )
        lines.append(f"  anomaly_bias: {frame.anomaly_bias}")
        lines.append(f"  civ_path_biases: {', '.join(frame.civ_path_biases) or 'None'}")
        if not is_player_view(view):
            lines.append(f"  observer_lens: {frame.observer_lens}")
    else:
        lines.append(f"  anomaly_bias: {frame.anomaly_bias}")
    return "\n".join(lines)


def format_events(
    events: list[Event],
    world: WorldState | None = None,
    limit: int = 10,
    target_type: str | None = None,
    target_id: str | None = None,
    mode: str = "brief",
    view: str = "truth",
    focus: str | None = None,
) -> str:
    """Format recent events for CLI display."""
    selected = events[-limit:]
    if not selected:
        return "No events recorded."

    target_focus = describe_focus(target_type, target_id)
    filter_label = f", focus={focus}" if focus else ""
    lines = [f"Recent events ({target_focus}, mode={mode}, view={view}{filter_label}, {len(selected)} shown):"]
    for event in selected:
        if mode == "full":
            lines.extend(_format_full_event(event, view=view, world=world))
            continue
        lines.append(
            f"  - [{event.event_type}] "
            f"{format_event_summary_for_view(event, view=view, world=world)}"
        )
    return "\n".join(lines)


def _format_full_event(
    event: Event,
    *,
    view: str = "truth",
    world: WorldState | None = None,
) -> list[str]:
    """Render one event with structured detail."""
    player_view = is_player_view(view)
    lines = [
        f"  - [{event.event_type}] {format_event_summary_for_view(event, view=view, world=world)}",
        f"    id: {event.event_id}",
        f"    tick: {event.tick}",
        f"    granularity: {event.time_granularity}",
        f"    scope: {event.event_scope}",
        f"    family: {event_family(event)}",
        f"    themes: {', '.join(event_theme_tags(event))}",
        f"    severity: {event.severity}",
        f"    novelty: {event.novelty}",
        f"    consequence: {event.consequence_score}",
    ]
    if player_view:
        lines.append(f"    visibility: {format_visibility_for_view(event, view=view)}")
        lines.append(f"    refs: {format_event_refs_for_view(event, view=view, world=world)}")
    else:
        ref_text = format_event_refs_for_view(event, view=view, world=world)
        lines.append(f"    visibility: {format_visibility_for_view(event, view=view)}")
        lines.append(f"    refs: {ref_text}")
    return lines


def format_step_result(
    result: StepResult,
    step_index: int,
    *,
    view: str = "truth",
    world: WorldState | None = None,
) -> str:
    """Format one step result for the CLI."""
    lines = [f"Step {step_index} complete:"]
    lines.append(f"  generated_events: {len(result.events)}")
    lines.append(
        "  woke_characters: "
        f"{len(result.wake_schedule.protagonists) + len(result.wake_schedule.active_characters)}"
    )
    if not is_player_view(view):
        source_counts = Counter(intent.source for intent in result.intents.all_intents)
        if source_counts:
            source_text = ", ".join(
                f"{source}={count}" for source, count in sorted(source_counts.items())
            )
            lines.append(f"  intent_sources: {source_text}")
        if result.ai_budget_summary:
            lines.append(f"  ai_budget_summary: {result.ai_budget_summary}")
    if result.last_llm_error and not is_player_view(view):
        lines.append(f"  last_llm_error: {result.last_llm_error}")

    visible_events = filter_events_for_view(result.events, view=view)
    if visible_events:
        lines.append("  event_sample:")
        for event in visible_events[:5]:
            lines.append(
                f"    - [{event.event_type}] "
                f"{format_event_summary_for_view(event, view=view, world=world)}"
            )

    if result.intents.all_intents and not is_player_view(view):
        lines.append("  intent_sample:")
        for intent in result.intents.all_intents[:5]:
            lines.append(
                f"    - {intent.character_id}: {intent.intent_type} -> "
                f"{intent.target_ref} [source={intent.source}]"
            )
    rendered_chronicle = format_chronicle_for_view(
        result.chronicle,
        result.events,
        view=view,
        world=world,
    )
    if rendered_chronicle and rendered_chronicle.text:
        lines.append("  chronicle:")
        tier_text = f", tier={rendered_chronicle.tier}" if rendered_chronicle.tier else ""
        lines.append(
            f"    - [source={rendered_chronicle.source}{tier_text}] {rendered_chronicle.text}"
        )
        if rendered_chronicle.error and not is_player_view(view):
            lines.append(f"    - fallback_reason: {rendered_chronicle.error}")
    return "\n".join(lines)
