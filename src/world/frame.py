"""Lightweight world structure template definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class StructureTemplate:
    """A light structural frame constraining semi-free world evolution."""

    era_frame: str = "realistic_future_tech"
    pressure_axes: list[str] = field(default_factory=list)
    dominant_fronts: list[str] = field(default_factory=list)
    organization_climates: list[str] = field(default_factory=list)
    anomaly_bias: str = "mixed_exceptional_pressure"
    civ_path_biases: list[str] = field(default_factory=list)
    observer_lens: str = "macro_pressure_and_public_signals"

    def brief_signature(self) -> str:
        """Return a compact one-line signature for status displays."""
        pressure = ", ".join(self.pressure_axes[:2]) or "none"
        fronts = ", ".join(self.dominant_fronts[:2]) or "none"
        return f"axes={pressure} | fronts={fronts} | anomaly={self.anomaly_bias}"
