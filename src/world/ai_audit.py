"""Audit record models for AI proposals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIProposalAudit:
    """One auditable AI proposal attempt."""

    audit_id: str
    tick: int
    source: str
    proposal_type: str
    target_type: str
    target_id: str
    mode: str
    applied: bool
    accepted_refs: list[str] = field(default_factory=list)
    rejected_reasons: list[str] = field(default_factory=list)
    payload: dict[str, Any] | None = None
    error: str | None = None
    tier: str | None = None
    signal_score: int = 0
