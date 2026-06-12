"""World style profile definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_STYLE_PROFILE_ID = "realistic_future_anomaly"


@dataclass(slots=True)
class WorldStyleProfile:
    """Configurable setting and tone boundary for narrative/AI output."""

    style_id: str
    world_style: str
    setting_summary: str
    technology_level: str
    anomaly_mode: str
    institution_tone: str
    default_observer_voice: str
    preferred_terms: list[str] = field(default_factory=list)
    forbidden_terms: list[str] = field(default_factory=list)

    def prompt_signature(self) -> str:
        """Return a compact style line suitable for prompt context."""
        return (
            f"style_id={self.style_id}; world_style={self.world_style}; "
            f"technology_level={self.technology_level}; anomaly_mode={self.anomaly_mode}; "
            f"institution_tone={self.institution_tone}"
        )


DEFAULT_WORLD_STYLE_PROFILES: dict[str, WorldStyleProfile] = {
    DEFAULT_STYLE_PROFILE_ID: WorldStyleProfile(
        style_id=DEFAULT_STYLE_PROFILE_ID,
        world_style="realistic future technology civilization",
        setting_summary=(
            "future civilizations under infrastructural, organizational, "
            "and anomalous pressure"
        ),
        technology_level="near_to_far_future",
        anomaly_mode="exceptional_presence",
        institution_tone="bureaucratic, infrastructural, security-conscious",
        default_observer_voice=(
            "Use a grounded outside-observer tone, emphasizing visible pressure, "
            "institutional texture, and anomalous uncertainty."
        ),
        preferred_terms=[
            "infrastructure",
            "containment",
            "anomalous pressure",
            "organizational pressure",
            "supply line",
            "megastructure",
            "public clue",
        ],
        forbidden_terms=[
            "magic",
            "spell",
            "dragon",
            "kingdom",
            "heroic destiny",
        ],
    )
}


def get_world_style_profile(style_id: str | None = None) -> WorldStyleProfile:
    """Return a known style profile, falling back to the default profile."""
    normalized = (style_id or DEFAULT_STYLE_PROFILE_ID).strip() or DEFAULT_STYLE_PROFILE_ID
    return DEFAULT_WORLD_STYLE_PROFILES.get(
        normalized,
        DEFAULT_WORLD_STYLE_PROFILES[DEFAULT_STYLE_PROFILE_ID],
    )


def style_profile_to_dict(profile: WorldStyleProfile) -> dict[str, object]:
    """Serialize a style profile to plain data."""
    return {
        "style_id": profile.style_id,
        "world_style": profile.world_style,
        "setting_summary": profile.setting_summary,
        "technology_level": profile.technology_level,
        "anomaly_mode": profile.anomaly_mode,
        "institution_tone": profile.institution_tone,
        "default_observer_voice": profile.default_observer_voice,
        "preferred_terms": list(profile.preferred_terms),
        "forbidden_terms": list(profile.forbidden_terms),
    }


def style_profile_prompt_lines(style_id: str | None = None) -> list[str]:
    """Return compact prompt lines for the selected world style profile."""
    profile = get_world_style_profile(style_id)
    return [
        f"World style: {profile.world_style}.",
        f"Setting summary: {profile.setting_summary}.",
        f"Technology level: {profile.technology_level}",
        f"Anomaly mode: {profile.anomaly_mode}",
        f"Institution tone: {profile.institution_tone}",
        "Preferred terms: " + (", ".join(profile.preferred_terms) or "None"),
        "Forbidden terms: " + (", ".join(profile.forbidden_terms) or "None"),
    ]
