"""Target selection helpers for dynamic-structure proposals."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.ai_context import build_dynamic_structure_context, dynamic_structure_context_signal
from src.narrative.names import format_entity_ref
from src.world.state import WorldState


DEFAULT_DYNAMIC_TARGET_THRESHOLD = 5


@dataclass(slots=True)
class DynamicStructureTargetCandidate:
    """A scored target that may be worth a dynamic-structure proposal."""

    target_type: str
    target_id: str
    target_label: str
    signal_score: int
    recent_event_count: int
    pressure_thread_count: int
    relation_count: int
    nearby_dynamic_count: int
    recommended: bool
    reason: str


def select_dynamic_structure_targets(
    world: WorldState,
    *,
    limit: int = 10,
    threshold: int = DEFAULT_DYNAMIC_TARGET_THRESHOLD,
) -> list[DynamicStructureTargetCandidate]:
    """Return high-signal fixed-world targets for dynamic proposal sampling."""
    candidates: list[DynamicStructureTargetCandidate] = []
    for target_type, target_id in _candidate_refs(world):
        context = build_dynamic_structure_context(
            world,
            target_type=target_type,
            target_id=target_id,
        )
        if context.get("error"):
            continue
        signal_score = dynamic_structure_context_signal(context)
        recent_event_count = len(list(context.get("recent_events", [])))
        pressure_thread_count = len(list(context.get("pressure_threads", [])))
        relation_count = len(list(context.get("relations", [])))
        nearby_dynamic_count = len(list(context.get("nearby_dynamic_structures", [])))
        adjusted_score = max(0, signal_score - min(nearby_dynamic_count, 2))
        recommended = adjusted_score >= threshold
        candidates.append(
            DynamicStructureTargetCandidate(
                target_type=target_type,
                target_id=target_id,
                target_label=format_entity_ref(world, target_id),
                signal_score=adjusted_score,
                recent_event_count=recent_event_count,
                pressure_thread_count=pressure_thread_count,
                relation_count=relation_count,
                nearby_dynamic_count=nearby_dynamic_count,
                recommended=recommended,
                reason=_candidate_reason(
                    recent_event_count=recent_event_count,
                    pressure_thread_count=pressure_thread_count,
                    relation_count=relation_count,
                    nearby_dynamic_count=nearby_dynamic_count,
                    recommended=recommended,
                ),
            )
        )
    candidates.sort(
        key=lambda candidate: (
            -int(candidate.recommended),
            -candidate.signal_score,
            -candidate.recent_event_count,
            -candidate.pressure_thread_count,
            -candidate.relation_count,
            candidate.nearby_dynamic_count,
            candidate.target_type,
            candidate.target_id,
        )
    )
    return candidates[: max(1, limit)]


def format_dynamic_structure_targets(
    world: WorldState,
    *,
    limit: int = 10,
    threshold: int = DEFAULT_DYNAMIC_TARGET_THRESHOLD,
) -> str:
    """Render target candidates for CLI use."""
    candidates = select_dynamic_structure_targets(world, limit=limit, threshold=threshold)
    if not candidates:
        return "No dynamic structure target candidates."
    lines = [f"Dynamic structure target candidates ({len(candidates)} shown, threshold={threshold}):"]
    for candidate in candidates:
        marker = "recommended" if candidate.recommended else "watch"
        lines.append(
            "  - "
            f"{candidate.target_type}:{candidate.target_id} "
            f"{candidate.target_label} "
            f"[score={candidate.signal_score}, events={candidate.recent_event_count}, "
            f"threads={candidate.pressure_thread_count}, relations={candidate.relation_count}, "
            f"nearby_dynamic={candidate.nearby_dynamic_count}, {marker}] "
            f"{candidate.reason}"
        )
    return "\n".join(lines)


def _candidate_refs(world: WorldState) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    refs.extend(("region", ref) for ref in world.regions)
    refs.extend(("faction", ref) for ref in world.factions)
    refs.extend(("relic", ref) for ref in world.relics)
    refs.extend(("project", ref) for ref in world.projects)
    refs.extend(("supply", ref) for ref in world.supply_lines)
    refs.extend(("node", ref) for ref in world.region_nodes)
    return refs


def _candidate_reason(
    *,
    recent_event_count: int,
    pressure_thread_count: int,
    relation_count: int,
    nearby_dynamic_count: int,
    recommended: bool,
) -> str:
    parts: list[str] = []
    if recent_event_count >= 4:
        parts.append("dense recent events")
    elif recent_event_count > 0:
        parts.append("some recent events")
    if pressure_thread_count >= 2:
        parts.append("multiple active pressure lines")
    elif pressure_thread_count == 1:
        parts.append("one active pressure line")
    if relation_count >= 4:
        parts.append("dense relation front")
    elif relation_count > 0:
        parts.append("some relation pull")
    if nearby_dynamic_count:
        parts.append("already has nearby dynamic structure")
    if not parts:
        parts.append("low signal")
    prefix = "proposal candidate" if recommended else "observe first"
    return f"{prefix}: " + "; ".join(parts)
