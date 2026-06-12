"""Lightweight ongoing pressure thread model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PressureThread:
    """A continuing situation inferred from repeated events around one object."""

    thread_id: str
    scope_ref: str
    theme: str
    status: str = "forming"
    intensity: str = "low"
    visibility: str = "visible"
    first_tick: int = 0
    updated_tick: int = 0
    event_refs: list[str] = field(default_factory=list)
    public_clues: list[str] = field(default_factory=list)
    summary: str = ""
