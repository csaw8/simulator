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
    observer_voices: dict[str, str] = field(default_factory=dict)
    preferred_terms: list[str] = field(default_factory=list)
    forbidden_terms: list[str] = field(default_factory=list)

    def prompt_signature(self) -> str:
        """Return a compact style line suitable for prompt context."""
        return (
            f"style_id={self.style_id}; world_style={self.world_style}; "
            f"technology_level={self.technology_level}; anomaly_mode={self.anomaly_mode}; "
            f"institution_tone={self.institution_tone}"
        )


@dataclass(slots=True)
class NarrativeLexicon:
    """Configurable display labels for narrative summaries."""

    lexicon_id: str
    dynamic_structure_player_title: str
    dynamic_structure_region_label: str
    dynamic_structure_truth_block: str
    dynamic_structure_empty_player: str
    dynamic_structure_empty_truth: str
    emergent_presence_player_title: str
    emergent_presence_region_label: str
    emergent_presence_truth_block: str
    emergent_presence_empty_player: str
    emergent_presence_empty_truth: str
    emergent_presence_linked_relic_label: str
    emergent_presence_ecological_label: str
    emergent_presence_linked_relic_count_unit: str
    emergent_presence_linked_relic_empty: str
    relic_presence_labels: dict[str, str] = field(default_factory=dict)
    relic_presence_fallback_label: str = "异常对象"
    project_display_prefix: str = "项目"
    supply_display_prefix: str = "补给线"
    node_display_prefix: str = "节点"
    dynamic_structure_display_prefix: str = "线索"
    emergent_presence_display_prefix: str = "异常生态迹象"


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
        observer_voices={
            "region_public_pressure": (
                "Use a grounded public-observer tone, emphasizing atmosphere, "
                "pressure drift, and visible social signals."
            ),
            "region_neutral": (
                "Use a neutral regional observation tone, centered on texture "
                "and public-facing pressure."
            ),
            "character_strategic": (
                "Write like a close but restrained profile of a planner under pressure, "
                "highlighting calculation, restraint, and directional intent."
            ),
            "character_opportunistic": (
                "Write like an observer noting someone who is alert to openings, "
                "with quick adjustments and unstable positioning."
            ),
            "character_reactive": (
                "Write like an observer tracking a pressured supporting figure, "
                "emphasizing reaction, adaptation, and local strain."
            ),
            "civilization_hybrid_governance": (
                "Use a macro-political tone, as if reading structural drift inside "
                "a layered governing order rather than judging individuals."
            ),
            "civilization_security_state": (
                "Use a cold institutional tone, emphasizing control, lock-in, "
                "and the cost of maintaining order."
            ),
            "civilization_default": (
                "Use a broad civilizational tone, emphasizing trajectory, governing "
                "tension, and system-level pressure."
            ),
            "relic_megastructure": (
                "Write like an observer facing an unfinished or active large-scale "
                "structure, emphasizing scale, disturbance, and organized human effort around it."
            ),
            "relic_exceptional_presence": (
                "Write like an observer facing a non-human anomaly or exceptional presence, "
                "emphasizing unease, attraction, and surrounding pressure."
            ),
            "faction_efficiency_growth": (
                "Use an organizational-intelligence tone, emphasizing throughput, "
                "leverage, and disciplined expansion."
            ),
            "faction_secrecy_legacy": (
                "Use a guarded internal-briefing tone, emphasizing concealment, "
                "controlled access, and indirect pressure."
            ),
            "faction_security_order": (
                "Use a security-apparatus tone, emphasizing stabilization, containment, "
                "and visible enforcement."
            ),
            "faction_default": (
                "Use a factional observation tone, emphasizing doctrine, positioning, "
                "and how the organization bends local conditions."
            ),
        },
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


DEFAULT_NARRATIVE_LEXICONS: dict[str, NarrativeLexicon] = {
    DEFAULT_STYLE_PROFILE_ID: NarrativeLexicon(
        lexicon_id=DEFAULT_STYLE_PROFILE_ID,
        dynamic_structure_player_title="动态线索观察",
        dynamic_structure_region_label="动态线索",
        dynamic_structure_truth_block="dynamic_structures",
        dynamic_structure_empty_player="外界暂未看出稳定动态牵连",
        dynamic_structure_empty_truth="None",
        emergent_presence_player_title="异常生态观察",
        emergent_presence_region_label="异常生态",
        emergent_presence_truth_block="emergent_presences",
        emergent_presence_empty_player="外界暂未看出稳定生态牵连",
        emergent_presence_empty_truth="None",
        emergent_presence_linked_relic_label="异常牵连",
        emergent_presence_ecological_label="生态线索",
        emergent_presence_linked_relic_count_unit="个异常牵连",
        emergent_presence_linked_relic_empty="外界暂未看出稳定异常牵连",
        relic_presence_labels={
            "relic_device": "异常装置",
            "megastructure": "巨构异常",
            "sealed_archive": "封存档案异常",
            "founding_protocol": "奠基协议异常",
            "anomalous_lifeform": "异常生命体",
        },
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
        "observer_voices": dict(profile.observer_voices),
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


def observer_voice(style_id: str | None, voice_key: str) -> str:
    """Return one configured observer voice instruction."""
    profile = get_world_style_profile(style_id)
    return profile.observer_voices.get(voice_key, profile.default_observer_voice)


def get_narrative_lexicon(style_id: str | None = None) -> NarrativeLexicon:
    """Return the narrative lexicon for a style profile."""
    normalized = (style_id or DEFAULT_STYLE_PROFILE_ID).strip() or DEFAULT_STYLE_PROFILE_ID
    return DEFAULT_NARRATIVE_LEXICONS.get(
        normalized,
        DEFAULT_NARRATIVE_LEXICONS[DEFAULT_STYLE_PROFILE_ID],
    )
