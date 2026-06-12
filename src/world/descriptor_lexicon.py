"""Approved descriptor tag pools for world style profiles."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.world.style_profile import (
    DEFAULT_STYLE_PROFILE_ID,
    POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
)


DESCRIPTOR_CATEGORIES = {
    "appearance",
    "function",
    "behavior",
    "sensory",
    "social_read",
    "ecological",
}

DESCRIPTOR_PROFILE_TYPES = {
    "character",
    "region_node",
    "relic",
    "project",
    "supply_line",
    "dynamic_structure",
    "emergent_presence",
}


@dataclass(frozen=True, slots=True)
class DescriptorTag:
    """One approved descriptor tag."""

    tag_id: str
    zh_label: str
    en_label: str
    category: str
    allowed_profile_types: tuple[str, ...]
    style_constraints: tuple[str, ...] = (DEFAULT_STYLE_PROFILE_ID,)
    conflict_group: str | None = None


@dataclass(frozen=True, slots=True)
class DescriptorLexicon:
    """Approved descriptor pool for one world style profile."""

    lexicon_id: str
    tags: tuple[DescriptorTag, ...] = field(default_factory=tuple)

    def tags_by_category(self, category: str) -> tuple[DescriptorTag, ...]:
        normalized = normalize_descriptor_category(category)
        return tuple(tag for tag in self.tags if tag.category == normalized)


def normalize_descriptor_category(category: str) -> str:
    """Normalize one descriptor category name."""
    normalized = str(category).strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in DESCRIPTOR_CATEGORIES:
        raise ValueError(f"unsupported descriptor category: {category!r}")
    return normalized


def normalize_descriptor_profile_type(profile_type: str) -> str:
    """Normalize one descriptor profile type."""
    normalized = str(profile_type).strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in DESCRIPTOR_PROFILE_TYPES:
        raise ValueError(f"unsupported descriptor profile type: {profile_type!r}")
    return normalized


def get_descriptor_lexicon(style_id: str | None = None) -> DescriptorLexicon:
    """Return the descriptor lexicon for a style profile."""
    normalized = (style_id or DEFAULT_STYLE_PROFILE_ID).strip() or DEFAULT_STYLE_PROFILE_ID
    return DEFAULT_DESCRIPTOR_LEXICONS.get(
        normalized,
        DEFAULT_DESCRIPTOR_LEXICONS[DEFAULT_STYLE_PROFILE_ID],
    )


def descriptor_tag(
    tag_id: str,
    *,
    category: str,
    style_id: str | None = None,
) -> DescriptorTag | None:
    """Return one approved descriptor tag by id and category."""
    normalized_category = normalize_descriptor_category(category)
    normalized_tag = normalize_descriptor_tag_id(tag_id)
    for tag in get_descriptor_lexicon(style_id).tags_by_category(normalized_category):
        if tag.tag_id == normalized_tag:
            return tag
    return None


def is_approved_descriptor_tag(
    tag_id: str,
    *,
    category: str,
    profile_type: str,
    style_id: str | None = None,
) -> bool:
    """Return whether a tag is approved for a category/profile/style boundary."""
    normalized_profile_type = normalize_descriptor_profile_type(profile_type)
    tag = descriptor_tag(tag_id, category=category, style_id=style_id)
    if tag is None:
        return False
    normalized_style = (style_id or DEFAULT_STYLE_PROFILE_ID).strip() or DEFAULT_STYLE_PROFILE_ID
    return (
        normalized_profile_type in tag.allowed_profile_types
        and normalized_style in tag.style_constraints
    )


def approved_descriptor_tag_ids(
    *,
    category: str,
    profile_type: str | None = None,
    style_id: str | None = None,
) -> tuple[str, ...]:
    """Return approved descriptor tag ids for one category and optional profile type."""
    normalized_category = normalize_descriptor_category(category)
    normalized_profile_type = (
        normalize_descriptor_profile_type(profile_type) if profile_type is not None else None
    )
    normalized_style = (style_id or DEFAULT_STYLE_PROFILE_ID).strip() or DEFAULT_STYLE_PROFILE_ID
    tag_ids: list[str] = []
    for tag in get_descriptor_lexicon(style_id).tags_by_category(normalized_category):
        if normalized_style not in tag.style_constraints:
            continue
        if normalized_profile_type is not None and normalized_profile_type not in tag.allowed_profile_types:
            continue
        tag_ids.append(tag.tag_id)
    return tuple(tag_ids)


def validate_descriptor_tags(
    tag_ids: list[str] | tuple[str, ...],
    *,
    category: str,
    profile_type: str,
    style_id: str | None = None,
) -> tuple[list[str], list[str]]:
    """Split descriptor tag ids into accepted and rejected lists."""
    accepted: list[str] = []
    rejected: list[str] = []
    for raw_tag in tag_ids:
        tag_id = normalize_descriptor_tag_id(raw_tag)
        if is_approved_descriptor_tag(
            tag_id,
            category=category,
            profile_type=profile_type,
            style_id=style_id,
        ):
            if tag_id not in accepted:
                accepted.append(tag_id)
        elif tag_id and tag_id not in rejected:
            rejected.append(tag_id)
    return accepted, rejected


def descriptor_zh_label(
    tag_id: str,
    *,
    category: str,
    style_id: str | None = None,
    fallback: str | None = None,
) -> str:
    """Return a player-facing descriptor label."""
    tag = descriptor_tag(tag_id, category=category, style_id=style_id)
    if tag is not None:
        return tag.zh_label
    return fallback if fallback is not None else normalize_descriptor_tag_id(tag_id)


def normalize_descriptor_tag_id(tag_id: str) -> str:
    """Normalize one descriptor tag id."""
    return str(tag_id).strip().lower().replace("-", "_").replace(" ", "_")[:48]


def _tag(
    tag_id: str,
    zh_label: str,
    en_label: str,
    category: str,
    allowed_profile_types: tuple[str, ...],
    *,
    style_id: str = DEFAULT_STYLE_PROFILE_ID,
    conflict_group: str | None = None,
) -> DescriptorTag:
    return DescriptorTag(
        tag_id=normalize_descriptor_tag_id(tag_id),
        zh_label=zh_label,
        en_label=en_label,
        category=normalize_descriptor_category(category),
        allowed_profile_types=allowed_profile_types,
        style_constraints=(style_id,),
        conflict_group=conflict_group,
    )


DEFAULT_DESCRIPTOR_LEXICONS: dict[str, DescriptorLexicon] = {
    DEFAULT_STYLE_PROFILE_ID: DescriptorLexicon(
        lexicon_id=DEFAULT_STYLE_PROFILE_ID,
        tags=(
            _tag(
                "scarred_surface",
                "表面带有旧损伤",
                "scarred surface",
                "appearance",
                ("region_node", "relic", "supply_line", "dynamic_structure", "emergent_presence"),
            ),
            _tag(
                "black_composite",
                "黑色复合材质",
                "black composite material",
                "appearance",
                ("region_node", "relic", "project", "supply_line"),
            ),
            _tag(
                "overbuilt_gate",
                "过度加固的闸口",
                "overbuilt gate",
                "appearance",
                ("region_node", "project", "dynamic_structure"),
            ),
            _tag(
                "sealed_drawer_bank",
                "封闭抽屉阵列",
                "sealed drawer bank",
                "appearance",
                ("region_node", "relic"),
            ),
            _tag(
                "organic_filament",
                "有机丝状结构",
                "organic filament",
                "appearance",
                ("relic", "emergent_presence"),
            ),
            _tag(
                "access_control",
                "访问控制",
                "access control",
                "function",
                ("region_node", "relic", "project", "dynamic_structure"),
            ),
            _tag(
                "containment",
                "隔离 containment",
                "containment",
                "function",
                ("region_node", "relic", "project", "dynamic_structure", "emergent_presence"),
            ),
            _tag(
                "routing",
                "路径调度",
                "routing",
                "function",
                ("region_node", "project", "supply_line"),
            ),
            _tag(
                "archive_storage",
                "档案存储",
                "archive storage",
                "function",
                ("region_node", "relic", "project"),
            ),
            _tag(
                "biosecurity_filter",
                "生物安全过滤",
                "biosecurity filter",
                "function",
                ("region_node", "relic", "project", "emergent_presence"),
            ),
            _tag(
                "cautious",
                "谨慎试探",
                "cautious",
                "behavior",
                ("character", "dynamic_structure"),
            ),
            _tag(
                "opportunistic",
                "寻找机会",
                "opportunistic",
                "behavior",
                ("character", "dynamic_structure"),
            ),
            _tag(
                "territorial",
                "领地性",
                "territorial",
                "behavior",
                ("character", "relic", "emergent_presence"),
            ),
            _tag(
                "reactive",
                "受刺激反应",
                "reactive",
                "behavior",
                ("character", "dynamic_structure", "emergent_presence"),
            ),
            _tag(
                "predatory",
                "捕食性",
                "predatory",
                "behavior",
                ("relic", "emergent_presence"),
            ),
            _tag(
                "low_hum",
                "低频嗡鸣",
                "low hum",
                "sensory",
                ("region_node", "relic", "dynamic_structure", "emergent_presence"),
            ),
            _tag(
                "cold_light",
                "冷色光",
                "cold light",
                "sensory",
                ("region_node", "relic", "project"),
            ),
            _tag(
                "ozone_smell",
                "臭氧气味",
                "ozone smell",
                "sensory",
                ("region_node", "relic", "dynamic_structure"),
            ),
            _tag(
                "signal_flicker",
                "信号闪烁",
                "signal flicker",
                "sensory",
                ("region_node", "relic", "supply_line", "dynamic_structure", "emergent_presence"),
            ),
            _tag(
                "spore_haze",
                "孢雾",
                "spore haze",
                "sensory",
                ("relic", "emergent_presence"),
            ),
            _tag(
                "trusted",
                "被信任",
                "trusted",
                "social_read",
                ("character", "region_node", "project", "supply_line"),
                conflict_group="public_trust",
            ),
            _tag(
                "feared",
                "被畏惧",
                "feared",
                "social_read",
                ("character", "relic", "dynamic_structure", "emergent_presence"),
                conflict_group="public_trust",
            ),
            _tag(
                "rumored",
                "传闻缠绕",
                "rumored",
                "social_read",
                ("character", "region_node", "relic", "project", "supply_line", "dynamic_structure", "emergent_presence"),
            ),
            _tag(
                "bureaucratic",
                "官僚化",
                "bureaucratic",
                "social_read",
                ("character", "region_node", "project", "supply_line", "dynamic_structure"),
            ),
            _tag(
                "sacred_to_locals",
                "被地方视为神圣",
                "sacred to locals",
                "social_read",
                ("region_node", "relic", "emergent_presence"),
            ),
            _tag(
                "biosecurity_risk",
                "生物安全风险",
                "biosecurity risk",
                "ecological",
                ("region_node", "relic", "dynamic_structure", "emergent_presence"),
            ),
            _tag(
                "habitat_disruption",
                "栖境扰动",
                "habitat disruption",
                "ecological",
                ("region_node", "relic", "project", "supply_line", "dynamic_structure", "emergent_presence"),
            ),
            _tag(
                "migration_pressure",
                "迁徙压力",
                "migration pressure",
                "ecological",
                ("supply_line", "dynamic_structure", "emergent_presence"),
            ),
            _tag(
                "spore_contamination",
                "孢子污染",
                "spore contamination",
                "ecological",
                ("region_node", "relic", "emergent_presence"),
            ),
            _tag(
                "containment_leakage",
                "隔离泄漏",
                "containment leakage",
                "ecological",
                ("region_node", "relic", "project", "dynamic_structure", "emergent_presence"),
            ),
        ),
    ),
    POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID: DescriptorLexicon(
        lexicon_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
        tags=(
            _tag(
                "patched_metal",
                "补丁金属外壳",
                "patched metal shell",
                "appearance",
                ("region_node", "relic", "project", "supply_line", "dynamic_structure"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
            _tag(
                "sun_bleached",
                "日晒褪色",
                "sun bleached",
                "appearance",
                ("character", "region_node", "relic", "supply_line", "emergent_presence"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
            _tag(
                "salvage_routing",
                "回收路线调度",
                "salvage routing",
                "function",
                ("region_node", "project", "supply_line"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
            _tag(
                "water_filter",
                "净水过滤",
                "water filter",
                "function",
                ("region_node", "relic", "project", "supply_line"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
            _tag(
                "guarded",
                "戒备",
                "guarded",
                "behavior",
                ("character", "dynamic_structure", "emergent_presence"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
            _tag(
                "barter_minded",
                "以交换衡量局势",
                "barter minded",
                "behavior",
                ("character", "dynamic_structure"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
            _tag(
                "dust_rattle",
                "尘土中的 rattling 声",
                "dust rattle",
                "sensory",
                ("region_node", "relic", "supply_line", "dynamic_structure", "emergent_presence"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
            _tag(
                "dry_heat",
                "干热压迫感",
                "dry heat",
                "sensory",
                ("character", "region_node", "relic", "supply_line", "emergent_presence"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
            _tag(
                "needed",
                "被需要",
                "needed",
                "social_read",
                ("character", "region_node", "project", "supply_line"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
            _tag(
                "owed_debts",
                "背负欠账",
                "owed debts",
                "social_read",
                ("character", "project", "supply_line", "dynamic_structure"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
            _tag(
                "water_stress",
                "水源压力",
                "water stress",
                "ecological",
                ("region_node", "project", "supply_line", "dynamic_structure", "emergent_presence"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
            _tag(
                "soil_exhaustion",
                "土壤耗竭",
                "soil exhaustion",
                "ecological",
                ("region_node", "relic", "project", "emergent_presence"),
                style_id=POST_COLLAPSE_FRONTIER_STYLE_PROFILE_ID,
            ),
        ),
    ),
}
