"""Lightweight descriptor profiles stored on world objects by reference."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import TYPE_CHECKING

from src.world.descriptor_lexicon import (
    approved_descriptor_tag_ids,
    descriptor_zh_label,
    validate_descriptor_tags,
)

if TYPE_CHECKING:
    from src.world.state import WorldState


@dataclass(slots=True)
class DescriptorProfile:
    """Stable descriptive tags for one world object."""

    ref_id: str
    profile_type: str
    appearance_tags: list[str] = field(default_factory=list)
    function_tags: list[str] = field(default_factory=list)
    behavior_tags: list[str] = field(default_factory=list)
    sensory_tags: list[str] = field(default_factory=list)
    social_read_tags: list[str] = field(default_factory=list)
    ecological_tags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def initialize_descriptor_profiles(world: WorldState, rng: Random) -> None:
    """Populate missing descriptor profiles for existing fixed-model objects."""
    for ref_id in world.characters:
        world.descriptor_profiles.setdefault(
            ref_id,
            _build_profile(world, rng, ref_id, "character"),
        )
    for ref_id in world.region_nodes:
        world.descriptor_profiles.setdefault(
            ref_id,
            _build_profile(world, rng, ref_id, "region_node"),
        )
    for ref_id in world.relics:
        world.descriptor_profiles.setdefault(
            ref_id,
            _build_profile(world, rng, ref_id, "relic"),
        )
    for ref_id in world.projects:
        world.descriptor_profiles.setdefault(
            ref_id,
            _build_profile(world, rng, ref_id, "project"),
        )
    for ref_id in world.supply_lines:
        world.descriptor_profiles.setdefault(
            ref_id,
            _build_profile(world, rng, ref_id, "supply_line"),
        )
    for ref_id in world.dynamic_structures:
        world.descriptor_profiles.setdefault(
            ref_id,
            _build_profile(world, rng, ref_id, "dynamic_structure"),
        )
    for ref_id in world.emergent_presences:
        world.descriptor_profiles.setdefault(
            ref_id,
            _build_profile(world, rng, ref_id, "emergent_presence"),
        )


def ensure_descriptor_profile(
    world: WorldState,
    ref_id: str,
    profile_type: str,
) -> DescriptorProfile:
    """Return an existing descriptor profile, creating one from the fixed pool if needed."""
    profile = world.descriptor_profiles.get(ref_id)
    if profile is not None:
        return profile
    rng = Random(_descriptor_seed(world, ref_id, profile_type))
    profile = _build_profile(world, rng, ref_id, profile_type)
    world.descriptor_profiles[ref_id] = profile
    return profile


def descriptor_profile_player_labels(
    profile: DescriptorProfile,
    *,
    style_id: str | None = None,
) -> dict[str, list[str]]:
    """Return player-facing descriptor labels without exposing internal tag ids."""
    return {
        "appearance": [
            descriptor_zh_label(tag_id, category="appearance", style_id=style_id)
            for tag_id in profile.appearance_tags
        ],
        "function": [
            descriptor_zh_label(tag_id, category="function", style_id=style_id)
            for tag_id in profile.function_tags
        ],
        "behavior": [
            descriptor_zh_label(tag_id, category="behavior", style_id=style_id)
            for tag_id in profile.behavior_tags
        ],
        "sensory": [
            descriptor_zh_label(tag_id, category="sensory", style_id=style_id)
            for tag_id in profile.sensory_tags
        ],
        "social_read": [
            descriptor_zh_label(tag_id, category="social_read", style_id=style_id)
            for tag_id in profile.social_read_tags
        ],
        "ecological": [
            descriptor_zh_label(tag_id, category="ecological", style_id=style_id)
            for tag_id in profile.ecological_tags
        ],
    }


def validate_descriptor_profile(profile: DescriptorProfile, *, style_id: str | None = None) -> list[str]:
    """Return validation errors for tags outside the approved descriptor pool."""
    errors: list[str] = []
    checks = (
        ("appearance", profile.appearance_tags),
        ("function", profile.function_tags),
        ("behavior", profile.behavior_tags),
        ("sensory", profile.sensory_tags),
        ("social_read", profile.social_read_tags),
        ("ecological", profile.ecological_tags),
    )
    for category, tag_ids in checks:
        _, rejected = validate_descriptor_tags(
            tag_ids,
            category=category,
            profile_type=profile.profile_type,
            style_id=style_id,
        )
        for tag_id in rejected:
            errors.append(f"{profile.ref_id}.{category}: unsupported descriptor tag {tag_id!r}")
    return errors


def _build_profile(
    world: WorldState,
    rng: Random,
    ref_id: str,
    profile_type: str,
) -> DescriptorProfile:
    return DescriptorProfile(
        ref_id=ref_id,
        profile_type=profile_type,
        appearance_tags=_choose_tags(world, rng, "appearance", profile_type, max_count=1),
        function_tags=_choose_tags(world, rng, "function", profile_type, max_count=1),
        behavior_tags=_choose_tags(world, rng, "behavior", profile_type, max_count=1),
        sensory_tags=_choose_tags(world, rng, "sensory", profile_type, max_count=1),
        social_read_tags=_choose_tags(world, rng, "social_read", profile_type, max_count=1),
        ecological_tags=_choose_tags(world, rng, "ecological", profile_type, max_count=1),
    )


def _choose_tags(
    world: WorldState,
    rng: Random,
    category: str,
    profile_type: str,
    *,
    max_count: int,
) -> list[str]:
    candidates = list(
        approved_descriptor_tag_ids(
            category=category,
            profile_type=profile_type,
            style_id=world.style_profile_id,
        )
    )
    if not candidates:
        return []
    count = min(max_count, len(candidates))
    return rng.sample(candidates, k=count)


def _descriptor_seed(world: WorldState, ref_id: str, profile_type: str) -> int:
    token = f"{world.seed}:{world.current_tick}:{profile_type}:{ref_id}"
    value = 0
    for char in token:
        value = (value * 131 + ord(char)) % 2_147_483_647
    return value
