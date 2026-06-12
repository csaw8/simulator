"""Helpers for managing dynamic relations in world state."""

from __future__ import annotations

from src.events.models import Event
from src.world.relation import Relation
from src.world.state import WorldState


def upsert_relation(
    world: WorldState,
    *,
    source_ref: str,
    target_ref: str,
    relation_type: str,
    event: Event,
    strength: str = "medium",
    status: str = "active",
    notes: str = "",
    tags: list[str] | None = None,
    bidirectional: bool = False,
) -> None:
    """Create or update a dynamic relation and optionally mirror it."""
    _write_relation(
        world,
        source_ref=source_ref,
        target_ref=target_ref,
        relation_type=relation_type,
        event=event,
        strength=strength,
        status=status,
        notes=notes,
        tags=tags or [],
    )
    if bidirectional:
        _write_relation(
            world,
            source_ref=target_ref,
            target_ref=source_ref,
            relation_type=relation_type,
            event=event,
            strength=strength,
            status=status,
            notes=notes,
            tags=tags or [],
        )


def relations_for_ref(
    world: WorldState,
    ref: str,
    *,
    limit: int = 8,
) -> list[Relation]:
    """Return the most recently updated relations touching one entity ref."""
    related = [
        relation
        for relation in world.relations.values()
        if relation.source_ref == ref or relation.target_ref == ref
    ]
    related.sort(key=lambda item: (item.updated_tick, item.last_event_id), reverse=True)
    return related[:limit]


def _write_relation(
    world: WorldState,
    *,
    source_ref: str,
    target_ref: str,
    relation_type: str,
    event: Event,
    strength: str,
    status: str,
    notes: str,
    tags: list[str],
) -> None:
    relation_id = _relation_id(source_ref, target_ref, relation_type)
    relation = world.relations.get(relation_id)
    if relation is None:
        relation = Relation(
            relation_id=relation_id,
            source_ref=source_ref,
            target_ref=target_ref,
            relation_type=relation_type,
        )
        world.relations[relation_id] = relation

    relation.strength = strength
    relation.status = status
    relation.updated_tick = world.current_tick
    relation.last_event_id = event.event_id
    relation.notes = notes
    relation.tags = list(dict.fromkeys(tags))


def _relation_id(source_ref: str, target_ref: str, relation_type: str) -> str:
    return f"{source_ref}->{target_ref}:{relation_type}"
