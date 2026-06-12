"""World, region, and character summary helpers."""

from __future__ import annotations

from src.events.query import (
    find_character_flashpoint_events,
    find_relic_flashpoint_region,
    find_recent_relic_event_for_region,
)
from src.agents.knowledge import build_character_knowledge_snapshot
from src.narrative.ambient_detail import (
    build_region_ambient_details,
    build_relic_ambient_details,
)
from src.narrative.ambient_people import (
    build_faction_ambient_people,
    build_region_ambient_people,
)
from src.narrative import labels as summary_labels
from src.narrative import names as summary_names
from src.narrative import relation_blocks as summary_relation_blocks
from src.events.models import Event
from src.events.taxonomy import event_midlayer_bucket, event_theme_tags, payload_midlayer_bucket
from src.events.visibility_rules import (
    format_event_summary_for_view,
    player_facing_event_clue as format_player_facing_event_clue,
)
from src.narrative.visibility import is_player_view
from src.world.character import Character
from src.world.civilization import Civilization
from src.world.faction import Faction
from src.world.presence import (
    exceptional_presence_label,
    is_contemporary_megastructure,
    megastructure_origin_label,
    presence_class,
    presence_display_name,
    presence_event_family,
)
from src.world.project import ProjectNetwork
from src.world.dynamic_structure import DynamicStructure
from src.world.emergent_presence import EmergentPresence
from src.world.region_node import RegionNode
from src.world.relations import relations_for_ref
from src.world.relic import Relic
from src.world.state import WorldState
from src.world.supply import SupplyLine

_humanize_enum_token = summary_labels.humanize_enum_token
_player_level_value = summary_labels.player_level_value
_player_trend_value = summary_labels.player_trend_value
_player_level_with_trend = summary_labels.player_level_with_trend
_player_civilization_stage_value = summary_labels.player_civilization_stage_value
_truth_civilization_stage_value = summary_labels.truth_civilization_stage_value
_player_trajectory_value = summary_labels.player_trajectory_value
_player_status_value = summary_labels.player_status_value
_player_region_type_value = summary_labels.player_region_type_value
_player_governance_mode_value = summary_labels.player_governance_mode_value
_truth_governance_mode_value = summary_labels.truth_governance_mode_value
_player_military_posture_value = summary_labels.player_military_posture_value
_player_relic_type_value = summary_labels.player_relic_type_value
_player_project_type_value = summary_labels.player_project_type_value
_player_region_node_type_value = summary_labels.player_region_node_type_value
_player_exceptional_label_value = summary_labels.player_exceptional_label_value
_player_presence_class_value = summary_labels.player_presence_class_value
_player_faction_scope_value = summary_labels.player_faction_scope_value
_player_doctrine_tag_value = summary_labels.player_doctrine_tag_value
_player_doctrine_tags_value = summary_labels.player_doctrine_tags_value
_player_agency_mode_value = summary_labels.player_agency_mode_value
_player_character_level_value = summary_labels.player_character_level_value
_player_tech_profile_value = summary_labels.player_tech_profile_value
_player_belief_profile_value = summary_labels.player_belief_profile_value
_player_summary_tag_value = summary_labels.player_summary_tag_value
_player_tag_list_value = summary_labels.player_tag_list_value
_truth_trajectory_value = summary_labels.truth_trajectory_value
_truth_doctrine_tags_value = summary_labels.truth_doctrine_tags_value
_truth_relation_status_value = summary_labels.truth_relation_status_value
_truth_relation_type_value = summary_labels.truth_relation_type_value
_truth_region_anchor_type_value = summary_labels.truth_region_anchor_type_value
_truth_civilization_region_anchor_hint = summary_labels.truth_civilization_region_anchor_hint
_player_event_type_label = summary_labels.player_event_type_label
_player_ambient_role_value = summary_labels.player_ambient_role_value
_player_ambient_stance_value = summary_labels.player_ambient_stance_value
_player_ambient_detail_type_value = summary_labels.player_ambient_detail_type_value
_player_ambient_condition_value = summary_labels.player_ambient_condition_value
_player_front_tag_value = summary_labels.player_front_tag_value
_truth_story_tag_value = summary_labels.truth_story_tag_value
_truth_story_hook_value = summary_labels.truth_story_hook_value
_player_region_population_value = summary_labels.player_region_population_value
_player_character_role_value = summary_labels.player_character_role_value
_player_character_capability_value = summary_labels.player_character_capability_value
_player_character_desire_value = summary_labels.player_character_desire_value
_player_character_fear_value = summary_labels.player_character_fear_value
_player_pressure_axis_value = summary_labels.player_pressure_axis_value
_player_pressure_axes_value = summary_labels.player_pressure_axes_value
_truth_pressure_axes_value = summary_labels.truth_pressure_axes_value
_player_organization_climate_value = summary_labels.player_organization_climate_value
_player_organization_climates_value = summary_labels.player_organization_climates_value
_truth_organization_climates_value = summary_labels.truth_organization_climates_value
_truth_frontier_theme_strength_value = summary_labels.truth_frontier_theme_strength_value
_truth_frontier_theme_value = summary_labels.truth_frontier_theme_value
_truth_frontier_focus_type_value = summary_labels.truth_frontier_focus_type_value
_truth_frontier_focus_shift_value = summary_labels.truth_frontier_focus_shift_value
_truth_goal_status_value = summary_labels.truth_goal_status_value
_player_label = summary_labels.player_label
_civilization_posture_driver_label = summary_labels.civilization_posture_driver_label
_civilization_faction_bias_label = summary_labels.civilization_faction_bias_label
_civilization_character_bias_label = summary_labels.civilization_character_bias_label
_player_world_name = summary_names.player_world_name
_player_localize_text = summary_names.player_localize_text
_player_project_name = summary_names.player_project_name
_player_supply_name = summary_names.player_supply_name
_player_region_node_name = summary_names.player_region_node_name
_player_presence_display_name = summary_names.player_presence_display_name
_player_presence_name = summary_names.player_presence_name
_player_faction_type_label = summary_names.player_faction_type_label
_player_display_name = summary_names.player_display_name
_format_entity_ref = summary_names.format_entity_ref
_truth_relation_entry = summary_relation_blocks.truth_relation_entry
_truth_relation_focus_entry = summary_relation_blocks.truth_relation_focus_entry
_relation_priority = summary_relation_blocks.relation_priority
_relation_strength_priority = summary_relation_blocks.relation_strength_priority
_group_relations_by_counterparty = summary_relation_blocks.group_relations_by_counterparty
_relation_bucket_label = summary_relation_blocks.relation_bucket_label
_relation_shadow_text = summary_relation_blocks.relation_shadow_text
_humanize_relation_note = summary_relation_blocks.humanize_relation_note
_format_relation_block = summary_relation_blocks.format_relation_block
_format_structure_relation_front = summary_relation_blocks.format_structure_relation_front
_format_structure_participant_fallback = summary_relation_blocks.format_structure_participant_fallback


def _normalize_summary_focus(focus: str | None) -> str | None:
    if focus is None:
        return None
    normalized = focus.strip().lower()
    return normalized or None


def _focus_matches(focus: str | None, *aliases: str) -> bool:
    normalized = _normalize_summary_focus(focus)
    if normalized is None:
        return True
    return normalized in aliases


def _player_pressure_band(level: str) -> str:
    mapping = {
        "high": "高压",
        "medium": "中压",
        "low": "低压",
    }
    return mapping.get(level, "不明")


def _player_title(label: str, name: str) -> str:
    return f"{label}：{name}"


def _summary_title(
    world: WorldState,
    *,
    ref: str,
    player_view: bool,
    player_label: str,
    truth_title: str,
) -> str:
    if player_view:
        return _player_title(player_label, _player_display_name(world, ref))
    return truth_title


def _line(label: str, value: str) -> str:
    return f"  {label}: {value}"


def _view_line(
    *,
    player_view: bool,
    truth_label: str,
    truth_value: object,
    player_label: str | None = None,
    player_value: object | None = None,
) -> str:
    label = player_label if player_view and player_label else truth_label
    value = player_value if player_view and player_value is not None else truth_value
    return _line(label, str(value))


def _view_simple_line(
    *,
    player_view: bool,
    label: str,
    value: object,
    player_label: str | None = None,
    player_value: object | None = None,
) -> str:
    return _view_line(
        player_view=player_view,
        truth_label=label,
        truth_value=value,
        player_label=player_label or _player_label(label),
        player_value=player_value,
    )


def _truth_optional_text(items: list[object], empty_text: str) -> str:
    return ", ".join(str(item) for item in items) if items else empty_text


def _truth_tag_list_value(tags: list[str], item_mapper, empty_text: str) -> str:
    if not tags:
        return empty_text
    return "、".join(item_mapper(tag) for tag in tags)


def _truth_level_with_trend(level: str, trend: str) -> str:
    return _player_level_with_trend(level, trend)


def _truth_observation_trace_value(count: int) -> str:
    if count <= 0:
        return "尚未积累到稳定公开行动痕迹"
    if count == 1:
        return "已积累 1 段公开行动痕迹"
    return f"已积累 {count} 段公开行动痕迹"


def _player_count_line_value(count: int, unit: str, empty_text: str) -> str:
    if count <= 0:
        return empty_text
    return _player_count_hint(count, unit)


def _player_ref_count_value(refs: list[str], unit: str, empty_text: str) -> str:
    if not refs:
        return empty_text
    return _player_count_hint(len(refs), unit)


def _view_ref_line(
    world: WorldState,
    *,
    player_view: bool,
    truth_label: str,
    ref: str | None,
    player_label: str | None = None,
) -> str:
    if player_view:
        return _line(player_label or truth_label, _player_display_name(world, ref or "None"))
    return _line(truth_label, _format_entity_ref(world, ref or "None"))


def _view_count_or_refs_line(
    world: WorldState,
    *,
    player_view: bool,
    truth_label: str,
    refs: list[str],
    truth_formatter,
    player_unit: str,
    player_label: str | None = None,
    player_empty_text: str | None = None,
) -> str:
    if player_view:
        if not refs and player_empty_text:
            return _line(player_label or _player_label(truth_label), player_empty_text)
        return _line(player_label or _player_label(truth_label), _player_count_hint(len(refs), player_unit))
    rendered = truth_formatter(world, refs)
    return _line(truth_label, ", ".join(rendered) or "None")


def summarize_region(
    world: WorldState,
    region_id: str,
    event_limit: int = 5,
    mode: str = "brief",
    view: str = "truth",
    focus: str | None = None,
) -> str:
    """Return a compact region summary with recent related events."""
    region = world.regions.get(region_id)
    if region is None:
        return f"Unknown region: {region_id}"

    civ_name = world.civilizations[region.civ_id].name if region.civ_id else "None"
    related_events = [
        event for event in world.event_stream.recent(50) if region_id in event.region_refs
    ][-event_limit:]
    player_view = is_player_view(view)

    lines = [
        _summary_title(
            world,
            ref=region.region_id,
            player_view=player_view,
            player_label="地区观察",
            truth_title=f"Region {region.name} ({region.region_id})",
        )
    ]
    lines.append(
        _view_line(
            player_view=player_view,
            truth_label="归属文明",
            truth_value=_format_entity_ref(world, region.civ_id) if region.civ_id else "暂无稳定文明归属",
            player_label="归属文明",
            player_value=_player_display_name(world, region.civ_id),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="type",
            value=_player_region_type_value(region.region_type),
            player_value=_player_region_type_value(region.region_type),
        )
    )
    lines.append(_view_simple_line(player_view=player_view, label="prosperity", value=_truth_level_with_trend(region.prosperity, region.prosperity_trend), player_value=_player_level_with_trend(region.prosperity, region.prosperity_trend)))
    lines.append(_view_simple_line(player_view=player_view, label="scarcity", value=_truth_level_with_trend(region.scarcity, region.scarcity_trend), player_value=_player_level_with_trend(region.scarcity, region.scarcity_trend)))
    lines.append(_view_simple_line(player_view=player_view, label="political_tension", value=_truth_level_with_trend(region.political_tension, region.political_tension_trend), player_value=_player_level_with_trend(region.political_tension, region.political_tension_trend)))
    lines.append(_view_simple_line(player_view=player_view, label="security", value=_truth_level_with_trend(region.security, region.security_trend), player_value=_player_level_with_trend(region.security, region.security_trend)))
    if mode == "full":
        lines.append(_view_simple_line(player_view=player_view, label="infrastructure", value=_truth_level_with_trend(region.infrastructure, region.infrastructure_trend), player_value=_player_level_with_trend(region.infrastructure, region.infrastructure_trend)))
        lines.append(_view_simple_line(player_view=player_view, label="tech_density", value=_player_level_value(region.tech_density), player_value=_player_level_value(region.tech_density)))
        lines.append(_view_simple_line(player_view=player_view, label="connectivity", value=_player_level_value(region.connectivity), player_value=_player_level_value(region.connectivity)))
        lines.append(_view_simple_line(player_view=player_view, label="ecological_stress", value=_truth_level_with_trend(region.ecological_stress, region.ecological_stress_trend), player_value=_player_level_with_trend(region.ecological_stress, region.ecological_stress_trend)))
        lines.append(_view_simple_line(player_view=player_view, label="belief_temperature", value=_player_level_value(region.belief_temperature), player_value=_player_level_value(region.belief_temperature)))
        lines.append(_view_line(player_view=player_view, truth_label="人口轮廓", truth_value=_truth_tag_list_value(region.population_profile, _player_region_population_value, "尚未形成稳定人口轮廓"), player_label="人口轮廓", player_value=_player_tag_list_value(region.population_profile, _player_region_population_value)))
        lines.append(_view_simple_line(player_view=player_view, label="strategic_value", value=_player_level_value(region.strategic_value), player_value=_player_level_value(region.strategic_value)))
        lines.append(
            _player_region_activity_hint(region) if player_view
            else f"  组织盘面: {_truth_optional_text(_format_faction_refs(world, region.active_factions[:8]), '尚未钉住稳定组织盘面')}"
        )
        lines.append(
            _player_region_character_hint(region) if player_view
            else f"  人物动静: {_truth_optional_text(_format_character_refs(world, region.active_characters[:12]), '尚未钉住稳定人物动静')}"
        )
        lines.append(
            _player_region_presence_hint(region) if player_view
            else f"  异常落点: {_truth_optional_text(_format_relic_refs(world, region.resident_relics[:8]), '尚未出现稳定异常落点')}"
        )
        lines.append(
            _player_region_story_hook_hint(region) if player_view
            else f"  公开传闻: {_truth_tag_list_value(region.local_story_hooks, _truth_story_hook_value, '尚未形成稳定公开传闻')}"
        )
        lines.append(_format_region_nodes_for_region(world, region.region_id, player_view=player_view))
        lines.append(_format_pressure_threads_for_ref(world, region.region_id, player_view=player_view))
        lines.append(_format_dynamic_structure_links_for_ref(world, region.region_id, player_view=player_view))
        lines.append(_format_emergent_presence_links_for_ref(world, region.region_id, player_view=player_view))
        lines.append(_format_region_ambient_people(world, region.region_id, view=view))
        lines.append(_format_region_ambient_details(world, region.region_id, view=view))
        lines.append(
            _player_region_anomaly_fronts(world, region.region_id)
            if player_view
            else _format_region_anomaly_fronts(world, region.region_id)
        )
        lines.append(
            _player_region_organization_flashpoints(world, region.region_id)
            if player_view
            else _format_region_organization_flashpoints(world, region.region_id)
        )
        lines.append(
            _player_relation_block(world, region.region_id, label="关系迹象")
            if player_view
            else _format_relation_block(world, region.region_id, limit=10)
        )
    else:
        lines.append(
            _player_region_activity_hint(region) if player_view
            else f"  组织盘面: {_truth_optional_text(_format_faction_refs(world, region.active_factions[:5]), '尚未钉住稳定组织盘面')}"
        )
        lines.append(
            _player_region_character_hint(region) if player_view
            else f"  人物动静: {_truth_optional_text(_format_character_refs(world, region.active_characters[:8]), '尚未钉住稳定人物动静')}"
        )
        lines.append(
            _player_region_presence_hint(region) if player_view
            else f"  异常落点: {_truth_optional_text(_format_relic_refs(world, region.resident_relics[:5]), '尚未出现稳定异常落点')}"
        )
        lines.append(
            _player_region_story_hook_hint(region) if player_view
            else f"  公开传闻: {_truth_tag_list_value(region.local_story_hooks, _truth_story_hook_value, '尚未形成稳定公开传闻')}"
        )
        lines.append(_format_region_nodes_for_region(world, region.region_id, player_view=player_view))
        lines.append(_format_pressure_threads_for_ref(world, region.region_id, player_view=player_view))
        lines.append(_format_emergent_presence_links_for_ref(world, region.region_id, player_view=player_view))
    lines.append(_format_related_events(world, related_events, view=view))
    return "\n".join(lines)


def summarize_region_node(
    world: WorldState,
    node_id: str,
    event_limit: int = 5,
    mode: str = "brief",
    view: str = "truth",
    focus: str | None = None,
) -> str:
    """Return a compact region-node summary with recent related events."""
    node = world.region_nodes.get(node_id)
    if node is None:
        return f"Unknown region node: {node_id}"

    related_events = _recent_region_node_events(world, node, limit=event_limit)
    player_view = is_player_view(view)
    focus = _normalize_summary_focus(focus)

    lines = [
        _summary_title(
            world,
            ref=node.node_id,
            player_view=player_view,
            player_label="节点观察",
            truth_title=f"RegionNode {node.name} ({node.node_id})",
        )
    ]
    lines.append(
        _view_line(
            player_view=player_view,
            truth_label="节点类型",
            truth_value=_player_region_node_type_value(node.node_type),
            player_label="节点类型",
            player_value=_player_region_node_type_value(node.node_type),
        )
    )
    lines.append(_view_ref_line(world, player_view=player_view, truth_label="region", ref=node.region_id, player_label="所在地区"))
    lines.append(_view_simple_line(player_view=player_view, label="pressure", value=_player_level_value(node.pressure), player_value=_player_level_value(node.pressure)))
    lines.append(
        "  节点态势: 外界能看出这个节点仍在被周边压力牵动"
        if player_view
        else f"  节点态势: {_truth_goal_status_value(node.contention_state)}"
    )
    if mode == "full":
        if _focus_matches(focus, "summary", "front", "node", "structure"):
            lines.append(
                _view_simple_line(
                    player_view=player_view,
                    label="controller",
                    value=_format_entity_ref(world, node.controller_ref) if node.controller_ref else "尚未形成稳定控制方",
                    player_value=_player_node_controller_hint(node),
                )
            )
            lines.append(_view_simple_line(player_view=player_view, label="front_tags", value=_truth_tag_list_value(node.tags, _player_front_tag_value, "尚未形成稳定前线标签"), player_value=_player_tag_list_value(node.tags, _player_front_tag_value)))
            lines.append(
                "  节点概述: 外界只能判断这里是一个正在承压的具体接口"
                if player_view
                else f"  节点概述: {node.state_summary or '尚未沉淀出稳定节点概述'}"
            )
            lines.append(
                "  当前阻碍: 外界只能看出节点周边存在摩擦"
                if player_view
                else "  当前阻碍: " + _truth_optional_text(node.blockers[:3], "暂未识别出稳定阻碍")
            )
            lines.append(
                _player_relation_block(world, node.node_id, label="关系迹象")
                if player_view
                else _format_relation_block(world, node.node_id, limit=8)
            )
        if _focus_matches(focus, "links", "relations", "node", "structure"):
            lines.extend(_format_region_node_links(world, node, player_view=player_view))
        if _focus_matches(focus, "history", "recent", "notes", "node"):
            lines.append(_format_region_node_recent_notes(world, node, player_view=player_view))
        lines.append(_format_pressure_threads_for_ref(world, node.node_id, player_view=player_view))
        lines.append(_format_dynamic_structure_links_for_ref(world, node.node_id, player_view=player_view))
    else:
        lines.extend(_format_region_node_links(world, node, player_view=player_view))
    if _focus_matches(focus, "events", "summary", "front", "recent", "node"):
        lines.append(_format_related_events(world, related_events, view=view))
    return "\n".join(lines)


def summarize_dynamic_structure(
    world: WorldState,
    structure_id: str,
    event_limit: int = 5,
    mode: str = "brief",
    view: str = "truth",
    focus: str | None = None,
) -> str:
    """Return a compact summary for one AI-proposed dynamic structure."""
    structure = world.dynamic_structures.get(structure_id)
    if structure is None:
        return f"Unknown dynamic structure: {structure_id}"

    related_events = _recent_dynamic_structure_events(world, structure, limit=event_limit)
    player_view = is_player_view(view)
    focus = _normalize_summary_focus(focus)

    lines = [
        _summary_title(
            world,
            ref=structure.structure_id,
            player_view=player_view,
            player_label="动态线索观察",
            truth_title=f"DynamicStructure {structure.name} ({structure.structure_id})",
        )
    ]
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="type",
            value=_dynamic_structure_type_label(structure.structure_type),
            player_value=_dynamic_structure_type_label(structure.structure_type),
        )
    )
    lines.append(_view_simple_line(player_view=player_view, label="status", value=_player_status_value(structure.status), player_value=_player_status_value(structure.status)))
    lines.append(_view_simple_line(player_view=player_view, label="pressure", value=_player_level_value(structure.pressure), player_value=_player_level_value(structure.pressure)))
    lines.append(
        "  概述: 外界能看出这是一条正在牵动周边对象的临时结构线索"
        if player_view
        else f"  summary: {structure.summary}"
    )
    if mode == "full":
        if _focus_matches(focus, "summary", "structure", "front"):
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="scope_refs",
                    truth_value=_truth_optional_text(_format_entity_refs(world, structure.scope_refs[:6]), "None"),
                    player_label="影响范围",
                    player_value=_player_ref_count_value(structure.scope_refs[:6], "个可见范围", "外界暂未看出稳定影响范围"),
                )
            )
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="linked_refs",
                    truth_value=_truth_optional_text(_format_entity_refs(world, structure.linked_refs[:8]), "None"),
                    player_label="牵连对象",
                    player_value=_player_ref_count_value(structure.linked_refs[:8], "个牵连对象", "外界暂未看出稳定牵连对象"),
                )
            )
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="tags",
                    truth_value=_truth_tag_list_value(structure.tags, _humanize_enum_token, "None"),
                    player_label="可见线索",
                    player_value=_player_tag_list_value(structure.tags, _humanize_enum_token),
                )
            )
            lines.append(
                _player_relation_block(world, structure.structure_id, label="关系迹象")
                if player_view
                else _format_relation_block(world, structure.structure_id, limit=8)
            )
            lines.append(_format_pressure_threads_for_ref(world, structure.structure_id, player_view=player_view))
    if _focus_matches(focus, "events", "summary", "front", "recent", "structure"):
        lines.append(_format_related_events(world, related_events, view=view))
    return "\n".join(lines)


def summarize_emergent_presence(
    world: WorldState,
    presence_id: str,
    event_limit: int = 5,
    mode: str = "brief",
    view: str = "truth",
    focus: str | None = None,
) -> str:
    """Return a compact summary for one semi-independent emergent presence."""
    presence = world.emergent_presences.get(presence_id)
    if presence is None:
        return f"Unknown emergent presence: {presence_id}"

    related_events = _recent_emergent_presence_events(world, presence, limit=event_limit)
    player_view = is_player_view(view)
    focus = _normalize_summary_focus(focus)

    lines = [
        _summary_title(
            world,
            ref=presence.presence_id,
            player_view=player_view,
            player_label="异常生态观察",
            truth_title=f"EmergentPresence {presence.name} ({presence.presence_id})",
        )
    ]
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="type",
            value=_emergent_presence_type_label(presence.presence_type),
            player_value=_emergent_presence_type_label(presence.presence_type),
        )
    )
    lines.append(_view_simple_line(player_view=player_view, label="status", value=_player_status_value(presence.status), player_value=_player_status_value(presence.status)))
    lines.append(_view_simple_line(player_view=player_view, label="pressure", value=_player_level_value(presence.pressure), player_value=_player_level_value(presence.pressure)))
    lines.append(
        "  概述: 外界只能看见一组持续扩散或收束的异常生态迹象"
        if player_view
        else f"  summary: {presence.summary}"
    )
    if mode == "full":
        if _focus_matches(focus, "summary", "presence", "front"):
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="lifecycle_stage",
                    truth_value=_emergent_presence_stage_label(presence.lifecycle_stage),
                    player_label="生态阶段",
                    player_value=_emergent_presence_stage_label(presence.lifecycle_stage),
                )
            )
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="population_scale",
                    truth_value=_emergent_presence_scale_label(presence.population_scale),
                    player_label="可见规模",
                    player_value=_emergent_presence_scale_label(presence.population_scale),
                )
            )
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="mobility",
                    truth_value=_emergent_presence_mobility_label(presence.mobility),
                    player_label="移动迹象",
                    player_value=_emergent_presence_mobility_label(presence.mobility),
                )
            )
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="current_region_refs",
                    truth_value=_truth_optional_text(_format_entity_refs(world, presence.current_region_refs[:6]), "None"),
                    player_label="出没范围",
                    player_value=_player_ref_count_value(presence.current_region_refs[:6], "片可见范围", "外界暂未看出稳定出没范围"),
                )
            )
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="linked_relic_refs",
                    truth_value=_truth_optional_text(_format_entity_refs(world, presence.linked_relic_refs[:6]), "None"),
                    player_label="异常牵连",
                    player_value=_player_ref_count_value(presence.linked_relic_refs[:6], "个异常牵连", "外界暂未看出稳定异常牵连"),
                )
            )
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="ecological_tags",
                    truth_value=_truth_tag_list_value(presence.ecological_tags, _humanize_enum_token, "None"),
                    player_label="生态线索",
                    player_value=_player_tag_list_value(presence.ecological_tags, _humanize_enum_token),
                )
            )
            lines.append(
                _player_relation_block(world, presence.presence_id, label="关系迹象")
                if player_view
                else _format_relation_block(world, presence.presence_id, limit=8)
            )
            lines.append(_format_pressure_threads_for_ref(world, presence.presence_id, player_view=player_view))
    if _focus_matches(focus, "events", "summary", "front", "recent", "presence"):
        lines.append(_format_related_events(world, related_events, view=view))
    return "\n".join(lines)


def summarize_character(
    world: WorldState,
    character_id: str,
    event_limit: int = 5,
    mode: str = "brief",
    view: str = "truth",
    focus: str | None = None,
) -> str:
    """Return a compact character summary with recent related events."""
    character = world.characters.get(character_id)
    if character is None:
        return f"Unknown character: {character_id}"

    region = world.regions[character.current_region_id]
    related_events = [
        event
        for event in world.event_stream.recent(50)
        if character_id in event.actor_refs or character.current_region_id in event.region_refs
    ][-event_limit:]
    player_view = is_player_view(view)
    knowledge = build_character_knowledge_snapshot(world, character) if mode == "full" else None
    focus = _normalize_summary_focus(focus)

    lines = [
        _summary_title(
            world,
            ref=character.char_id,
            player_view=player_view,
            player_label="人物观察",
            truth_title=f"Character {character.name} ({character.char_id})",
        )
    ]
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="level",
            value=_player_character_level_value(character.character_level),
            player_value=_player_character_level_value(character.character_level),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="status",
            value=_player_status_value(character.status),
            player_value=_player_status_value(character.status),
        )
    )
    lines.append(
        _view_ref_line(
            world,
            player_view=player_view,
            truth_label="region",
            ref=region.region_id,
            player_label="所在地区",
        )
    )
    lines.append(
        _player_character_affiliation_hint(character)
        if player_view
        else "  affiliations: "
        + _truth_optional_text(
            _format_faction_refs(world, character.affiliation[:6]),
            "尚未形成稳定组织归属",
        )
    )
    lines.append(_view_simple_line(player_view=player_view, label="role_tags", value=_truth_tag_list_value(character.role_tags, _player_character_role_value, "尚未形成稳定身份线索"), player_value=_player_tag_list_value(character.role_tags, _player_character_role_value)))
    lines.append(_view_simple_line(player_view=player_view, label="capability_tags", value=_truth_tag_list_value(character.capability_tags, _player_character_capability_value, "尚未形成稳定能力线索"), player_value=_player_tag_list_value(character.capability_tags, _player_character_capability_value)))
    lines.append(_view_simple_line(player_view=player_view, label="desire_tags", value=_truth_tag_list_value(character.desire_tags, _player_character_desire_value, "尚未形成清晰诉求线索"), player_value=_player_tag_list_value(character.desire_tags, _player_character_desire_value)))
    lines.append(_view_simple_line(player_view=player_view, label="fear_tags", value=_truth_tag_list_value(character.fear_tags, _player_character_fear_value, "尚未形成清晰顾虑线索"), player_value=_player_tag_list_value(character.fear_tags, _player_character_fear_value)))
    lines.append(_view_simple_line(player_view=player_view, label="notoriety", value=_player_level_value(character.notoriety), player_value=_player_level_value(character.notoriety)))
    lines.append(_view_simple_line(player_view=player_view, label="initiative", value=_player_level_value(character.initiative), player_value=_player_level_value(character.initiative)))
    lines.append(_view_simple_line(player_view=player_view, label="agency_mode", value=_player_agency_mode_value(character.agency_mode), player_value=_player_agency_mode_value(character.agency_mode)))
    lines.append(
        _player_character_last_intent_hint(character)
        if player_view
        else f"  最近意图: {_format_last_intent(world, character)}"
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="observation_trace",
            value=_truth_observation_trace_value(character.observation_trace),
            player_value=_player_count_line_value(character.observation_trace, "段", "外界暂未积累到稳定行动痕迹"),
        )
    )
    if mode == "full" and _focus_matches(focus, "front", "summary", "frontline", "focus"):
        lines.append(
            _player_character_role_text(character)
            if player_view
            else _format_character_current_role(character)
        )
        lines.append(
            _player_character_active_front(world, character)
            if player_view
            else _format_character_active_front(world, character)
        )
        lines.append(
            _player_character_why_now(world, character)
            if player_view
            else _format_character_why_now(world, character)
        )
        lines.append(
            "  当前目标: 外界只能看出他正沿一条稳定前线持续施力"
            if player_view
            else f"  当前目标: {character.active_goal_summary or '尚未沉淀出稳定当前目标'}"
        )
        lines.append(
            "  目标状态: 外界只能判断这条目标线仍在变化中"
            if player_view
            else f"  目标状态: {_truth_goal_status_value(character.active_goal_status)}"
        )
        lines.append(
            "  当前阻碍: 外界只能看出推进并不顺滑"
            if player_view
            else "  当前阻碍: "
            + _truth_optional_text(character.active_goal_blockers[:3], "暂未识别出稳定阻碍")
        )
        lines.append(
            "  最近结果: 外界能感到局势刚刚发生过一次推拉"
            if player_view
            else f"  最近结果: {character.active_goal_recent_result or '最近尚未形成稳定结果'}"
        )
    if mode == "full":
        if _focus_matches(focus, "front", "summary", "frontline", "focus"):
            lines.append(_format_character_hotspots(world, character, view=view))
        lines.append(
            _player_character_frontier_theme(character)
            if player_view
            else _format_character_frontier_theme(world, character)
        )
        if _focus_matches(focus, "knowledge", "intel"):
            lines.append(
                _player_character_knowledge_hint(character)
                if player_view
                else _format_character_knowledge_snapshot(world, knowledge)
            )
        if _focus_matches(focus, "rivals", "competition", "competitors"):
            lines.append(
                _player_character_focus_competitors(world, character)
                if player_view
                else _format_character_focus_competitors_clean(world, character)
            )
        if _focus_matches(focus, "history", "moves", "timeline"):
            lines.append(
                _player_character_recent_goal_hint(character)
                if player_view
                else f"  近期目标感: {_truth_character_recent_goal(character)}"
            )
            lines.append(
                _player_character_memory_hint(character)
                if player_view
                else f"  行动惯性: {_truth_character_memory_summary(character)}"
            )
            lines.append(
                _player_character_frontier_history(character)
                if player_view
                else _format_character_frontier_history(world, character)
            )
        if _focus_matches(focus, "relations", "network"):
            lines.append(
                _player_character_relation_front(world, character)
                if player_view
                else _format_character_relation_front(world, character)
            )
            lines.append(
                _player_character_relationship_refs_hint(character)
                if player_view
                else "  relationship_refs: "
                + _truth_optional_text(
                    character.relationship_refs[:8],
                    "未形成稳定关系牵引记录",
                )
            )
            lines.append(
                _player_character_loyalty_hint(character)
                if player_view
                else f"  loyalty_map: {character.loyalty_map or '归属线索尚未沉淀成稳定映射'}"
            )
            lines.append(
                _player_relation_block(world, character.char_id, label="关系迹象")
                if player_view
                else _format_relation_block(world, character.char_id, limit=8)
            )
        if _focus_matches(focus, "meta", "internal"):
            lines.append(
                _player_character_wake_hint(character)
                if player_view
                else f"  wake_priority_seed: {character.wake_priority_seed}"
            )
    else:
        lines.append(
            _player_character_recent_goal_hint(character)
            if player_view
                else f"  近期目标感: {_truth_character_recent_goal(character)}"
        )
    if _focus_matches(focus, "events", "recent", "summary", "front", "frontline", "focus"):
        lines.append(_format_related_events(world, related_events, view=view))
    return "\n".join(lines)


def summarize_civilization(
    world: WorldState,
    civ_id: str,
    event_limit: int = 5,
    mode: str = "brief",
    view: str = "truth",
    focus: str | None = None,
) -> str:
    """Return a compact civilization summary with recent related events."""
    civilization = world.civilizations.get(civ_id)
    if civilization is None:
        return f"Unknown civilization: {civ_id}"

    related_events = [
        event for event in world.event_stream.recent(60) if civ_id in event.civ_refs
    ][-event_limit:]
    player_view = is_player_view(view)
    focus = _normalize_summary_focus(focus)

    lines = [
        _summary_title(
            world,
            ref=civilization.civ_id,
            player_view=player_view,
            player_label="文明观察",
            truth_title=f"Civilization {civilization.name} ({civilization.civ_id})",
        )
    ]
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="status",
            value=_player_status_value(civilization.status),
            player_value=_player_status_value(civilization.status),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="stage",
            value=_truth_civilization_stage_value(civilization.stage),
            player_value=_player_civilization_stage_value(civilization.stage),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="governance_mode",
            value=_truth_governance_mode_value(civilization.governance_mode),
            player_value=_player_governance_mode_value(civilization.governance_mode),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="world_frame_pull",
            value=_truth_pressure_axes_value(world.structure_template.pressure_axes),
            player_value=_player_pressure_axes_value(world.structure_template.pressure_axes),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="cohesion",
            value=_truth_level_with_trend(civilization.cohesion, civilization.cohesion_trend),
            player_value=_player_level_with_trend(civilization.cohesion, civilization.cohesion_trend),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="scarcity_pressure",
            value=_truth_level_with_trend(civilization.scarcity_pressure, civilization.scarcity_trend),
            player_value=_player_level_with_trend(civilization.scarcity_pressure, civilization.scarcity_trend),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="expansion_pressure",
            value=_truth_level_with_trend(civilization.expansion_pressure, civilization.expansion_trend),
            player_value=_player_level_with_trend(civilization.expansion_pressure, civilization.expansion_trend),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="legitimacy",
            value=_truth_level_with_trend(civilization.legitimacy, civilization.legitimacy_trend),
            player_value=_player_level_with_trend(civilization.legitimacy, civilization.legitimacy_trend),
        )
    )
    if mode == "full":
        if _focus_matches(focus, "summary", "front", "strategy"):
            lines.append(
                _view_simple_line(
                    player_view=player_view,
                    label="trajectory",
                    value=_truth_trajectory_value(civilization.trajectory),
                    player_value=_player_tag_list_value(civilization.trajectory, _player_trajectory_value),
                )
            )
            lines.append(
                _player_civilization_posture(civilization)
                if player_view
                else f"  strategic_posture: {_truth_civilization_posture_value(civilization.strategic_posture)}"
            )
            lines.append(
                _player_civilization_organization_model(civilization)
                if player_view
                else _format_civilization_organization_model(world, civilization)
            )
            lines.append(
                _player_civilization_fronts(world, civilization)
                if player_view
                else _format_civilization_strategic_fronts(world, civilization.civ_id)
            )
            lines.append(
                _player_civilization_strategy_explanation(civilization)
                if player_view
                else _format_civilization_strategy_explanation(world, civilization)
            )
            lines.append(
                _player_civilization_bias_effects(civilization)
                if player_view
                else _format_civilization_bias_effects(world, civilization)
            )
        if _focus_matches(focus, "structure", "project", "supply", "front"):
            lines.append(
                _player_civilization_key_regions_hint(civilization)
                if player_view
                else f"  key_regions: {', '.join(civilization.key_regions[:12]) or 'None'}"
            )
            lines.append(
                _player_civilization_key_factions_hint(civilization)
                if player_view
                else f"  key_factions: {', '.join(civilization.key_factions[:10]) or 'None'}"
            )
            lines.append(
                _view_count_or_refs_line(
                    world,
                    player_view=player_view,
                    truth_label="key_projects",
                    refs=civilization.key_projects[:8],
                    truth_formatter=_format_project_refs,
                    player_unit="项",
                    player_label="关键项目迹象",
                    player_empty_text="外界暂未看出稳定关键项目",
                )
            )
            lines.append(
                _view_count_or_refs_line(
                    world,
                    player_view=player_view,
                    truth_label="key_supply_lines",
                    refs=civilization.key_supply_lines[:8],
                    truth_formatter=_format_supply_refs,
                    player_unit="条",
                    player_label="补给线迹象",
                    player_empty_text="外界暂未看出稳定补给线索",
                )
            )
            lines.append(
                _player_civilization_project_networks(world, civilization)
                if player_view
                else _format_civilization_project_networks(world, civilization.civ_id)
            )
            lines.append(
                _player_civilization_execution_front_overview(world, civilization)
                if player_view
                else _format_civilization_execution_front_overview(world, civilization.civ_id)
            )
            lines.append(
                _player_civilization_supply_fronts(world, civilization)
                if player_view
                else _format_civilization_supply_fronts(world, civilization.civ_id)
            )
        if _focus_matches(focus, "relations", "network"):
            lines.append(
                _player_civilization_relation_front(world, civilization)
                if player_view
                else _format_civilization_relation_front(world, civilization)
            )
            lines.append(
                _player_civilization_external_relations(world, civilization)
                if player_view
                else _format_civilization_external_relations(world, civilization)
            )
            lines.append(
                _player_civilization_dependency_chain(world, civilization)
                if player_view
                else _format_civilization_dependency_chain(world, civilization)
            )
            lines.append(
                _player_civilization_sponsorship_chain(world, civilization)
                if player_view
                else _format_civilization_sponsorship_chain(world, civilization)
            )
            lines.append(
                _player_civilization_region_anchors(world, civilization)
                if player_view
                else _format_civilization_region_anchors(world, civilization)
            )
        if _focus_matches(focus, "history", "memory", "meta"):
            lines.append(
                _player_civilization_posture_stability_hint(civilization)
                if player_view
                else f"  strategic_posture_stability: {_truth_civilization_posture_stability_value(civilization)}"
            )
            lines.append(
                _player_civilization_posture_pending_hint(civilization)
                if player_view
                else f"  strategic_posture_pending: {_truth_civilization_posture_pending_value(civilization)}"
            )
            lines.append(
                _player_civilization_posture_pending_hits_hint(civilization)
                if player_view
                else f"  strategic_posture_pending_hits: {_truth_civilization_posture_pending_hits_value(civilization)}"
            )
            lines.append(
                _view_simple_line(
                    player_view=player_view,
                    label="tech_profile",
                    value=_truth_tag_list_value(civilization.tech_profile, _player_tech_profile_value, "尚未形成稳定技术画像"),
                    player_value=_player_tag_list_value(civilization.tech_profile, _player_tech_profile_value),
                )
            )
            lines.append(
                _view_simple_line(
                    player_view=player_view,
                    label="belief_profile",
                    value=_truth_tag_list_value(civilization.belief_profile, _player_belief_profile_value, "尚未形成清晰信念画像"),
                    player_value=_player_tag_list_value(civilization.belief_profile, _player_belief_profile_value),
                )
            )
            lines.append(
                _view_simple_line(
                    player_view=player_view,
                    label="military_posture",
                    value=_player_military_posture_value(civilization.military_posture),
                    player_value=_player_military_posture_value(civilization.military_posture),
                )
            )
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="key_characters",
                    truth_value=_truth_optional_text(
                        _format_character_refs(world, civilization.key_characters[:10]),
                        "尚未钉住稳定关键人物",
                    ),
                    player_label="活跃人物迹象",
                    player_value=_player_count_line_value(
                        len(civilization.key_characters),
                        "人",
                        "外界暂未看出稳定活跃人物",
                    ),
                )
            )
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="key_relics",
                    truth_value=_truth_optional_text(
                        _format_relic_refs(world, civilization.key_relics[:8]),
                        "尚未钉住稳定异常焦点",
                    ),
                    player_label="异常焦点迹象",
                    player_value=_player_count_line_value(
                        len(civilization.key_relics),
                        "个焦点",
                        "外界暂未看出稳定异常焦点",
                    ),
                )
            )
            lines.append(
                _view_simple_line(
                    player_view=player_view,
                    label="summary_tags",
                    value=_truth_tag_list_value(civilization.summary_tags, _player_summary_tag_value, "尚未形成稳定外显印象"),
                    player_value=_player_tag_list_value(civilization.summary_tags, _player_summary_tag_value),
                )
            )
            lines.append(
                _player_civilization_midlayer_changes_hint(world, civilization)
                if player_view
                else _format_civilization_midlayer_changes(world, civilization.civ_id)
            )
            lines.append(_format_pressure_threads_for_ref(world, civilization.civ_id, player_view=player_view))
            lines.append(
                _player_civilization_memory(civilization)
                if player_view
                else _format_civilization_strategy_memory(world, civilization)
            )
    else:
        lines.append(
            _view_simple_line(
                player_view=player_view,
                label="trajectory",
                value=", ".join(civilization.trajectory[:3]) or "None",
                player_value=_player_tag_list_value(civilization.trajectory[:3], _player_trajectory_value),
            )
        )
        lines.append(
            _player_civilization_key_regions_hint(civilization)
            if player_view
            else f"  key_regions: {', '.join(civilization.key_regions[:6]) or 'None'}"
        )
        lines.append(
            _view_line(
                player_view=player_view,
                truth_label="key_projects",
                truth_value=", ".join(_format_project_refs(world, civilization.key_projects[:4])) or "None",
                player_label="关键项目迹象",
                player_value=_player_ref_count_value(civilization.key_projects[:4], "项关键项目", "外界暂未看出稳定关键项目"),
            )
        )
        lines.append(
            _view_line(
                player_view=player_view,
                truth_label="key_supply_lines",
                truth_value=", ".join(_format_supply_refs(world, civilization.key_supply_lines[:4])) or "None",
                player_label="补给线迹象",
                player_value=_player_ref_count_value(civilization.key_supply_lines[:4], "条补给线", "外界暂未看出稳定补给线索"),
            )
        )
        lines.append(
            _view_line(
                player_view=player_view,
                truth_label="key_characters",
                truth_value=", ".join(civilization.key_characters[:5]) or "None",
                player_label="活跃人物迹象",
                player_value=_player_count_line_value(
                    len(civilization.key_characters),
                    "人",
                    "外界暂未看出稳定活跃人物",
                ),
            )
        )
    if _focus_matches(focus, "events", "summary", "front", "strategy", "recent"):
        lines.append(_format_related_events(world, related_events, view=view))
    return "\n".join(lines)


def summarize_relic(
    world: WorldState,
    relic_id: str,
    event_limit: int = 5,
    mode: str = "brief",
    view: str = "truth",
    focus: str | None = None,
) -> str:
    """Return a compact relic summary with recent related events."""
    relic = world.relics.get(relic_id)
    if relic is None:
        return f"Unknown relic: {relic_id}"

    region = world.regions[relic.current_region_id]
    related_events = [
        event for event in world.event_stream.recent(60) if relic_id in event.relic_refs
    ][-event_limit:]
    player_view = is_player_view(view)

    lines = [
        _summary_title(
            world,
            ref=relic.relic_id,
            player_view=player_view,
            player_label="异常观察",
            truth_title=f"{presence_display_name(relic)} {relic.name} ({relic.relic_id})",
        )
    ]
    lines.append(_view_simple_line(player_view=player_view, label="type", value=_player_relic_type_value(relic.relic_type), player_value=_player_relic_type_value(relic.relic_type)))
    lines.append(_view_simple_line(player_view=player_view, label="exceptional_label", value=_player_exceptional_label_value(exceptional_presence_label(relic)), player_value=_player_exceptional_label_value(exceptional_presence_label(relic))))
    lines.append(_view_simple_line(player_view=player_view, label="presence_class", value=_player_presence_class_value(presence_class(relic)), player_value=_player_presence_class_value(presence_class(relic))))
    lines.append(
        _view_ref_line(
            world,
            player_view=player_view,
            truth_label="region",
            ref=region.region_id,
            player_label="所在地区",
        )
    )
    lines.append(
        "  控制线索: 外界暂时看不清稳定持有方"
        if player_view
        else f"  持有方: {_format_entity_ref(world, relic.holder_ref) if relic.holder_ref else '持有方尚未稳固'}"
    )
    lines.append(_view_simple_line(player_view=player_view, label="significance", value=_player_level_value(relic.significance), player_value=_player_level_value(relic.significance)))
    lines.append(_view_simple_line(player_view=player_view, label="danger", value=_player_level_value(relic.danger), player_value=_player_level_value(relic.danger)))
    lines.append(_view_simple_line(player_view=player_view, label="activation_state", value=_player_status_value(relic.activation_state), player_value=_player_status_value(relic.activation_state)))
    if relic.relic_type == "megastructure":
        lines.append(f"  起源方式: {_humanize_enum_token(relic.origin_mode)}")
        lines.append(f"  建造状态: {_humanize_enum_token(relic.construction_state)}")
    elif relic.relic_type == "anomalous_lifeform":
        lines.append(f"  起源方式: {_humanize_enum_token(relic.origin_mode)}")
        lines.append(f"  行为状态: {_humanize_enum_token(relic.construction_state)}")
    if mode == "full":
        lines.append(
            _player_presence_profile(world, relic)
            if player_view
            else _format_presence_detail_block(world, relic)
        )
        lines.append(
            _player_relic_linked_projects(world, relic)
            if player_view
            else ("  关联项目: " + (_truth_optional_text(_format_project_refs(world, _find_projects_for_presence(world, relic.relic_id)), "尚未牵出稳定项目线")))
        )
        lines.append(_format_relic_ambient_details(world, relic.relic_id, view=view))
        lines.append(
            _player_relic_story_hint(relic)
            if player_view
            else f"  外界印象: {_truth_tag_list_value(relic.story_tags, _truth_story_tag_value, '尚未形成稳定外界印象')}"
        )
        lines.append(
            _player_relic_linked_events(relic)
            if player_view
            else _format_truth_relic_linked_events(relic)
        )
        lines.append(
            "  争夺状态: 外界只能看出这处异常周边仍不安稳"
            if player_view
            else f"  争夺状态: {_truth_goal_status_value(relic.contest_state)}"
        )
        lines.append(
            "  争夺概述: 外界能看出封控、接入与观察都还没停"
            if player_view
            else f"  争夺概述: {relic.contest_summary or '尚未沉淀出稳定争夺概述'}"
        )
        lines.append(
            "  争夺方: 外界暂时辨不清稳定参与方"
            if player_view
            else "  争夺方: "
            + _truth_optional_text(_format_entity_refs(world, relic.contesting_refs[:6]), "尚未识别出稳定争夺方")
        )
        lines.append(
            _player_relation_block(world, relic.relic_id, label="关系迹象")
            if player_view
            else _format_relation_block(world, relic.relic_id, limit=8)
        )
        lines.append(_format_pressure_threads_for_ref(world, relic.relic_id, player_view=player_view))
        lines.append(_format_dynamic_structure_links_for_ref(world, relic.relic_id, player_view=player_view))
    else:
        lines.append(
            _player_relic_story_hint(relic)
            if player_view
            else f"  外界印象: {_truth_tag_list_value(relic.story_tags[:4], _truth_story_tag_value, '尚未形成稳定外界印象')}"
        )
    lines.append(_format_related_events(world, related_events, view=view))
    return "\n".join(lines)


def summarize_faction(
    world: WorldState,
    faction_id: str,
    event_limit: int = 5,
    mode: str = "brief",
    view: str = "truth",
    focus: str | None = None,
) -> str:
    """Return a compact faction summary with recent related events."""
    faction = world.factions.get(faction_id)
    if faction is None:
        return f"Unknown faction: {faction_id}"

    civilization = world.civilizations.get(faction.parent_civ_id) if faction.parent_civ_id else None
    related_events = [
        event for event in world.event_stream.recent(60) if faction_id in event.faction_refs
    ][-event_limit:]
    player_view = is_player_view(view)
    focus = _normalize_summary_focus(focus)

    lines = [
        _summary_title(
            world,
            ref=faction.faction_id,
            player_view=player_view,
            player_label="组织观察",
            truth_title=f"Faction {faction.name} ({faction.faction_id})",
        )
    ]
    lines.append(
        _view_line(
            player_view=player_view,
            truth_label="civilization",
            truth_value=civilization.name if civilization else "None",
            player_label="所属文明",
            player_value=_player_display_name(world, faction.parent_civ_id),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="type",
            value=_player_faction_type_label(faction.faction_type),
            player_value=_player_faction_type_label(faction.faction_type),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="power_scope",
            value=_player_faction_scope_value(faction.power_scope),
            player_value=_player_faction_scope_value(faction.power_scope),
        )
    )
    lines.append(
        _line(
            "组织气候牵引" if player_view else "organization_climate_pull",
            _player_organization_climates_value(world.structure_template.organization_climates)
            if player_view
            else _truth_organization_climates_value(world.structure_template.organization_climates),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="influence",
            value=_truth_level_with_trend(faction.influence, faction.influence_trend),
            player_value=_player_level_with_trend(faction.influence, faction.influence_trend),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="cohesion",
            value=_player_level_value(faction.cohesion),
            player_value=_player_level_value(faction.cohesion),
        )
    )
    lines.append(
        _view_simple_line(
            player_view=player_view,
            label="doctrine_tags",
            value=_truth_doctrine_tags_value(faction.doctrine_tags),
            player_value=_player_doctrine_tags_value(faction.doctrine_tags),
        )
    )
    if mode == "full":
        if _focus_matches(focus, "summary", "strategy", "front"):
            lines.append(
                f"  行事风格: {_player_faction_style(faction)}"
                if player_view
                else f"  operational_style: {_truth_faction_operational_style_value(faction.operational_style)}"
            )
            lines.append(
                _player_faction_type_signature(faction)
                if player_view
                else f"  faction_niche: {_faction_type_signature(faction.faction_type)}"
            )
            lines.append(
                _player_faction_behavior_signature(faction)
                if player_view
                else _format_faction_behavior_signature(world, faction)
            )
            lines.append(
                _player_faction_organization_model(faction)
                if player_view
                else _format_faction_organization_model(world, faction)
            )
            lines.append(
                _player_faction_project_fronts(world, faction)
                if player_view
                else _format_faction_project_fronts(world, faction.faction_id)
            )
            lines.append(
                _player_faction_execution_front_overview(world, faction)
                if player_view
                else _format_faction_execution_front_overview(world, faction.faction_id)
            )
            lines.append(
                _player_faction_strategy_explanation(faction)
                if player_view
                else _format_faction_strategy_explanation(world, faction)
            )
            lines.append(
                _player_faction_supply_fronts(world, faction)
                if player_view
                else _format_faction_supply_fronts(world, faction.faction_id)
            )
            lines.append(
                _player_faction_midlayer_changes(world, faction)
                if player_view
                else _format_faction_midlayer_changes(world, faction.faction_id)
            )
            lines.append(
                "  战略目标: 外界能看出这个组织正在把动作收束到一条主轴上"
                if player_view
                else f"  战略目标: {faction.strategic_objective or '尚未沉淀出稳定战略目标'}"
            )
            lines.append(
                "  目标状态: 外界只能判断其主轴仍在变化"
                if player_view
                else f"  目标状态: {_truth_goal_status_value(faction.strategic_objective_status)}"
            )
            lines.append(
                "  当前阻碍: 外界能看出它在推进时仍有明显摩擦"
                if player_view
                else "  当前阻碍: "
                + _truth_optional_text(faction.strategic_objective_blockers[:3], "暂未识别出稳定阻碍")
            )
            lines.append(
                "  最近结果: 外界能看出这个组织刚推动过一次关键变化"
                if player_view
                else f"  最近结果: {faction.strategic_objective_recent_result or '最近尚未形成稳定结果'}"
            )
        if _focus_matches(focus, "structure", "project", "supply"):
            lines.append(
                _player_faction_controlled_regions_hint(faction)
                if player_view
                else f"  controlled_regions: {', '.join(_format_region_refs(world, faction.controlled_regions[:10])) or 'None'}"
            )
            lines.append(
                _view_count_or_refs_line(
                    world,
                    player_view=player_view,
                    truth_label="linked_projects",
                    refs=_find_projects_for_faction(world, faction.faction_id),
                    truth_formatter=_format_project_refs,
                    player_unit="项",
                    player_label="项目牵连迹象",
                    player_empty_text="外界暂未看出稳定项目牵连",
                )
            )
            lines.append(
                _view_count_or_refs_line(
                    world,
                    player_view=player_view,
                    truth_label="linked_supply_lines",
                    refs=_find_supply_for_faction(world, faction.faction_id),
                    truth_formatter=_format_supply_refs,
                    player_unit="条",
                    player_label="补给牵连迹象",
                    player_empty_text="外界暂未看出稳定补给牵连",
                )
            )
        if _focus_matches(focus, "relations", "network"):
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="rival_factions",
                    truth_value=_truth_optional_text(
                        _format_faction_refs(world, faction.rival_factions[:8]),
                        "尚未形成稳定强对手链",
                    ),
                    player_label="强对手迹象",
                    player_value=_player_count_line_value(
                        len(faction.rival_factions),
                        "个强对手",
                        "外界暂未看出稳定强对手",
                    ),
                )
            )
            lines.append(
                _view_line(
                    player_view=player_view,
                    truth_label="allied_factions",
                    truth_value=_truth_optional_text(
                        _format_faction_refs(world, faction.allied_factions[:8]),
                        "尚未形成稳定协作节点",
                    ),
                    player_label="协作节点迹象",
                    player_value=_player_count_line_value(
                        len(faction.allied_factions),
                        "个联盟节点",
                        "外界暂未看出稳定协作节点",
                    ),
                )
            )
            lines.append(
                _player_faction_relation_front(world, faction)
                if player_view
                else _format_faction_relation_front(world, faction)
            )
            lines.append(
                _player_faction_dependency_chain(world, faction)
                if player_view
                else _format_faction_dependency_chain(world, faction)
            )
            lines.append(
                _player_faction_sponsorship_chain(world, faction)
                if player_view
                else _format_faction_sponsorship_chain(world, faction)
            )
            lines.append(
                _player_faction_region_anchors(world, faction)
                if player_view
                else _format_faction_region_anchors(world, faction)
            )
            lines.append(
                _player_relation_block(world, faction.faction_id, label="关系迹象")
                if player_view
                else _format_relation_block(world, faction.faction_id, limit=8)
            )
        if _focus_matches(focus, "history", "memory", "meta"):
            lines.append(
                _player_faction_stability_hint(faction)
                if player_view
                else "  operational_style_stability: " + _faction_stability_state_label(faction)
            )
            lines.append(
                _player_faction_pending_style_hint(faction)
                if player_view
                else "  operational_style_pending: " + _truth_faction_pending_style_label(faction)
            )
            lines.append(
                _player_faction_pending_hits_hint(faction)
                if player_view
                else "  operational_style_pending_hits: " + _truth_faction_pending_hits_label(faction)
            )
            lines.append(
                _view_count_or_refs_line(
                    world,
                    player_view=player_view,
                    truth_label="key_characters",
                    refs=faction.key_characters[:10],
                    truth_formatter=_format_character_refs,
                    player_unit="名活跃人物",
                    player_label="活跃人物迹象",
                    player_empty_text="外界暂未看出稳定活跃人物",
                )
            )
            lines.append(_format_faction_ambient_people(world, faction.faction_id, view=view))
            lines.append(
                _player_faction_memory_hint(faction)
                if player_view
                else _format_faction_operational_style_memory_summary(faction)
            )
            lines.append(_format_pressure_threads_for_ref(world, faction.faction_id, player_view=player_view))
            lines.append(
                _player_faction_style_trace(faction)
                if player_view
                else _format_faction_operational_style_trace(world, faction)
            )
        lines.append(_format_dynamic_structure_links_for_ref(world, faction.faction_id, player_view=player_view))
    else:
        lines.append(
            _player_faction_controlled_regions_hint(faction)
            if player_view
            else f"  controlled_regions: {', '.join(_format_region_refs(world, faction.controlled_regions[:5])) or 'None'}"
        )
        lines.append(
            _view_count_or_refs_line(
                world,
                player_view=player_view,
                truth_label="key_characters",
                refs=faction.key_characters[:5],
                truth_formatter=_format_character_refs,
                player_unit="人",
                player_label="活跃人物迹象",
                player_empty_text="外界暂未看出稳定活跃人物",
            )
        )
    if _focus_matches(focus, "events", "summary", "strategy", "front", "recent"):
        lines.append(_format_related_events(world, related_events, view=view))
    return "\n".join(lines)


def summarize_supply_line(
    world: WorldState,
    supply_id: str,
    event_limit: int = 5,
    mode: str = "brief",
    view: str = "truth",
    focus: str | None = None,
) -> str:
    """Return a compact supply-line summary with recent related events."""
    supply_line = world.supply_lines.get(supply_id)
    if supply_line is None:
        return f"Unknown supply line: {supply_id}"

    related_events = _recent_supply_line_events(world, supply_line, limit=event_limit)
    player_view = is_player_view(view)
    focus = _normalize_summary_focus(focus)

    lines = [
        _summary_title(
            world,
            ref=supply_line.supply_id,
            player_view=player_view,
            player_label="补给线观察",
            truth_title=f"SupplyLine {supply_line.name} ({supply_line.supply_id})",
        )
    ]
    lines.append(_view_simple_line(player_view=player_view, label="status", value=_player_status_value(supply_line.status), player_value=_player_status_value(supply_line.status)))
    lines.append(_view_simple_line(player_view=player_view, label="pressure", value=_player_level_value(supply_line.pressure), player_value=_player_level_value(supply_line.pressure)))
    lines.append(
        _view_ref_line(
            world,
            player_view=player_view,
            truth_label="origin",
            ref=supply_line.origin_region_id,
            player_label="起点",
        )
    )
    lines.append(
        _view_ref_line(
            world,
            player_view=player_view,
            truth_label="destination",
            ref=supply_line.destination_region_id,
            player_label="终点",
        )
    )
    if mode == "full":
        if _focus_matches(focus, "summary", "front", "supply", "structure"):
            lines.append(
                _view_simple_line(
                    player_view=player_view,
                    label="controller",
                    value=_format_entity_ref(world, supply_line.controlling_faction_ref) if supply_line.controlling_faction_ref else "None",
                    player_value=_player_supply_controller_hint(supply_line),
                )
            )
            lines.append(_view_simple_line(player_view=player_view, label="front_tags", value=_truth_tag_list_value(supply_line.front_tags, _player_front_tag_value, "尚未形成稳定前线标签"), player_value=_player_tag_list_value(supply_line.front_tags, _player_front_tag_value)))
            lines.append(
                _view_simple_line(
                    player_view=player_view,
                    label="control_state",
                    value=_format_supply_control_state(world, supply_line),
                    player_value="外界只能看出这条补给线的控制权并不稳固",
                )
            )
            lines.append(
                _player_supply_pressure_interpretation(supply_line)
                if player_view
                else _format_supply_pressure_interpretation(supply_line)
            )
            lines.append(
                _player_supply_organization_front(supply_line)
                if player_view
                else _format_structure_relation_front(world, supply_line.supply_id, label="organization_front")
            )
            lines.append(
                "  线路状态: 外界能看出这条线路仍在变化中"
                if player_view
                else f"  线路状态: {_truth_goal_status_value(supply_line.corridor_state)}"
            )
            lines.append(
                "  线路概述: 外界能感到这条线的通行节奏并不完全稳定"
                if player_view
                else f"  线路概述: {supply_line.corridor_summary or '尚未沉淀出稳定线路概述'}"
            )
            lines.append(
                "  当前阻碍: 外界只能看出它正被多股压力拉扯"
                if player_view
                else "  当前阻碍: "
                + _truth_optional_text(supply_line.corridor_blockers[:3], "暂未识别出稳定阻碍")
            )
        if _focus_matches(focus, "history", "recent", "notes", "supply"):
            lines.append(
                _view_count_or_refs_line(
                    world,
                    player_view=player_view,
                    truth_label="linked_civs",
                    refs=supply_line.linked_civ_refs[:4],
                    truth_formatter=_format_civ_refs,
                    player_unit="个相关文明",
                    player_empty_text="外界暂未看出稳定相关文明",
                )
            )
            lines.append(_player_supply_recent_notes(supply_line) if player_view else _format_supply_recent_notes(world, supply_line, player_view=player_view))
        lines.append(_format_pressure_threads_for_ref(world, supply_line.supply_id, player_view=player_view))
        lines.append(_format_dynamic_structure_links_for_ref(world, supply_line.supply_id, player_view=player_view))
    else:
        lines.append(_view_simple_line(player_view=player_view, label="front_tags", value=_truth_tag_list_value(supply_line.front_tags[:4], _player_front_tag_value, "尚未形成稳定前线标签"), player_value=_player_tag_list_value(supply_line.front_tags[:4], _player_front_tag_value)))
    if _focus_matches(focus, "events", "summary", "front", "recent", "supply"):
        lines.append(_format_related_events(world, related_events, view=view))
    return "\n".join(lines)


def summarize_project(
    world: WorldState,
    project_id: str,
    event_limit: int = 5,
    mode: str = "brief",
    view: str = "truth",
    focus: str | None = None,
) -> str:
    """Return a compact project summary with recent related events."""
    project = world.projects.get(project_id)
    if project is None:
        return f"Unknown project: {project_id}"

    related_events = _recent_project_events(world, project, limit=event_limit)
    player_view = is_player_view(view)
    focus = _normalize_summary_focus(focus)

    lines = [
        _summary_title(
            world,
            ref=project.project_id,
            player_view=player_view,
            player_label="项目观察",
            truth_title=f"Project {project.name} ({project.project_id})",
        )
    ]
    lines.append(_view_simple_line(player_view=player_view, label="type", value=_player_project_type_value(project.project_type), player_value=_player_project_type_value(project.project_type)))
    lines.append(_view_simple_line(player_view=player_view, label="status", value=_player_status_value(project.status), player_value=_player_status_value(project.status)))
    lines.append(_view_simple_line(player_view=player_view, label="pressure", value=_player_level_value(project.pressure), player_value=_player_level_value(project.pressure)))
    lines.append(
        f"  关联地区: {', '.join(_player_display_name(world, region_id) for region_id in project.linked_regions[:6]) or '外界暂未看出稳定关联地区'}"
        if player_view
        else f"  关联地区: {_truth_optional_text(_format_region_refs(world, project.linked_regions[:6]), '尚未钉住稳定关联地区')}"
    )
    lines.append(
        f"  关联异常: {', '.join(_player_display_name(world, relic_id) for relic_id in project.linked_presence_refs[:4]) or '外界暂未看出稳定异常牵连'}"
        if player_view
        else f"  关联异常: {_truth_optional_text(_format_relic_refs(world, project.linked_presence_refs[:4]), '尚未牵出稳定异常牵连')}"
    )
    if mode == "full":
        if _focus_matches(focus, "summary", "front", "project", "structure"):
            lines.append(_view_simple_line(player_view=player_view, label="front_tags", value=_truth_tag_list_value(project.front_tags, _player_front_tag_value, "尚未形成稳定前线标签"), player_value=_player_tag_list_value(project.front_tags, _player_front_tag_value)))
            lines.append(
                _player_project_pressure_interpretation(project)
                if player_view
                else _format_project_pressure_interpretation(project)
            )
            lines.append(
                _player_project_organization_front(project)
                if player_view
                else _format_structure_relation_front(world, project.project_id, label="organization_front")
            )
            lines.append(
                "  推进状态: 外界能看出这条项目线仍在变化中"
                if player_view
                else f"  推进状态: {_truth_goal_status_value(project.progress_state)}"
            )
            lines.append(
                "  推进概述: 外界能感到项目推进与摩擦在同时上升"
                if player_view
                else f"  推进概述: {project.progress_summary or '尚未沉淀出稳定推进概述'}"
            )
            lines.append(
                "  当前阻碍: 外界只能看出执行端存在明显摩擦"
                if player_view
                else "  当前阻碍: "
                + _truth_optional_text(project.progress_blockers[:3], "暂未识别出稳定阻碍")
            )
        if _focus_matches(focus, "actors", "relations", "network", "project"):
            lines.append(_view_line(player_view=player_view, truth_label="赞助力量", truth_value=_truth_optional_text(_format_entity_refs(world, project.sponsor_refs[:5]), "未形成稳定赞助力量"), player_label="赞助力量迹象", player_value=_player_ref_count_value(project.sponsor_refs[:5], "组赞助力量", "外界暂未看出稳定赞助力量")))
            lines.append(_view_line(player_view=player_view, truth_label="执行力量", truth_value=_truth_optional_text(_format_entity_refs(world, project.contractor_refs[:5]), "未形成稳定执行力量"), player_label="执行力量迹象", player_value=_player_ref_count_value(project.contractor_refs[:5], "组执行力量", "外界暂未看出稳定执行力量")))
            lines.append(_view_line(player_view=player_view, truth_label="资金力量", truth_value=_truth_optional_text(_format_entity_refs(world, project.financier_refs[:5]), "未形成稳定资金力量"), player_label="资金力量迹象", player_value=_player_ref_count_value(project.financier_refs[:5], "组资金力量", "外界暂未看出稳定资金力量")))
            lines.append(_view_line(player_view=player_view, truth_label="阻力链", truth_value=_truth_optional_text(_format_entity_refs(world, project.opposition_refs[:5]), "未形成稳定阻力链"), player_label="阻力迹象", player_value=_player_ref_count_value(project.opposition_refs[:5], "组阻力", "外界暂未看出稳定阻力链")))
            lines.append(_view_line(player_view=player_view, truth_label="组织牵连", truth_value=_truth_optional_text(_format_faction_refs(world, project.linked_factions[:8]), "尚未钉住稳定组织牵连"), player_label="相关组织迹象", player_value=_player_ref_count_value(project.linked_factions[:8], "个相关派系", "外界暂未看出稳定组织牵连")))
            lines.append(_view_line(player_view=player_view, truth_label="文明牵连", truth_value=_truth_optional_text(_format_civ_refs(world, project.linked_civs[:4]), "尚未钉住稳定文明牵连"), player_label="相关文明迹象", player_value=_player_ref_count_value(project.linked_civs[:4], "个相关文明", "外界暂未看出稳定文明牵连")))
            lines.append(_view_line(player_view=player_view, truth_label="人物牵连", truth_value=_truth_optional_text(_format_character_refs(world, project.linked_characters[:8]), "尚未牵出稳定人物链"), player_label="相关人物迹象", player_value=_player_ref_count_value(project.linked_characters[:8], "名相关人物", "外界暂未看出稳定人物牵连")))
        if _focus_matches(focus, "history", "recent", "notes", "project"):
            lines.append(_player_project_recent_notes(project) if player_view else _format_project_recent_notes(world, project, player_view=player_view))
        lines.append(_format_pressure_threads_for_ref(world, project.project_id, player_view=player_view))
        lines.append(_format_dynamic_structure_links_for_ref(world, project.project_id, player_view=player_view))
    else:
        lines.append(_view_simple_line(player_view=player_view, label="front_tags", value=_truth_tag_list_value(project.front_tags[:4], _player_front_tag_value, "尚未形成稳定前线标签"), player_value=_player_tag_list_value(project.front_tags[:4], _player_front_tag_value)))
    if _focus_matches(focus, "events", "summary", "front", "recent", "project"):
        lines.append(_format_related_events(world, related_events, view=view))
    return "\n".join(lines)


def _format_last_intent(world: WorldState, character: Character) -> str:
    if not character.last_intent:
        return "暂无稳定意图记录"
    intent_type = character.last_intent.get("intent_type", "unknown")
    target_ref = character.last_intent.get("target_ref", "unknown")
    goal = character.last_intent.get("goal", "unknown")
    intent_text = {
        "stabilize_supply": "稳住补给线",
        "secure_relic_access": "争取异常接入权",
        "advance_project": "推进项目进度",
        "contest_control": "争夺控制权",
    }.get(intent_type, _humanize_enum_token(intent_type))
    target_text = _format_entity_ref(world, target_ref)
    goal_text = {
        "maintain_supply_order": "维持补给秩序",
        "shift_to_supply_and_hold_order": "转入补给线并稳住跨区运输秩序",
    }.get(goal, _humanize_enum_token(goal))
    return f"{intent_text}，目标指向 {target_text}，当前目的为「{goal_text}」"


def _format_region_refs(world: WorldState, region_ids: list[str]) -> list[str]:
    return [
        f"{world.regions[region_id].name} ({region_id})"
        if region_id in world.regions
        else region_id
        for region_id in region_ids
    ]


def _format_character_refs(world: WorldState, character_ids: list[str]) -> list[str]:
    return [
        f"{world.characters[character_id].name} ({character_id})"
        if character_id in world.characters
        else character_id
        for character_id in character_ids
    ]


def _format_civ_refs(world: WorldState, civ_ids: list[str]) -> list[str]:
    return [
        f"{world.civilizations[civ_id].name} ({civ_id})"
        if civ_id in world.civilizations
        else civ_id
        for civ_id in civ_ids
    ]


def _format_entity_ref_from_any(ref: str) -> str:
    if not ref or ref == "none":
        return "None"
    return ref


def _truth_character_recent_goal(character: Character) -> str:
    if not character.recent_goal:
        return "近期目标尚未收束"
    mapping = {
        "Maintain leverage over a volatile district.": "持续维持对高波动地区的杠杆影响力。",
    }
    return mapping.get(character.recent_goal, _humanize_enum_token(character.recent_goal))


def _truth_character_memory_summary(character: Character) -> str:
    if not character.memory_summary:
        return "尚未形成足够长的行动惯性"
    mapping = {
        "Long-term actor with active influence on regional direction.": "属于长期施力者，并且仍在持续影响地区走向。",
    }
    return mapping.get(character.memory_summary, _humanize_enum_token(character.memory_summary))


def _format_supply_refs(world: WorldState, supply_ids: list[str]) -> list[str]:
    return [
        f"{world.supply_lines[supply_id].name} ({supply_id})"
        if supply_id in world.supply_lines
        else supply_id
        for supply_id in supply_ids
    ]


def _format_entity_refs(world: WorldState, refs: list[str]) -> list[str]:
    return [_format_entity_ref(world, ref) for ref in refs]


def _format_project_refs(world: WorldState, project_ids: list[str]) -> list[str]:
    return [
        f"{world.projects[project_id].name} ({project_id})"
        if project_id in world.projects
        else project_id
        for project_id in project_ids
    ]


def _find_projects_for_presence(world: WorldState, relic_id: str) -> list[str]:
    return [
        project.project_id
        for project in world.projects.values()
        if relic_id in project.linked_presence_refs
    ][:8]


def _find_projects_for_faction(world: WorldState, faction_id: str) -> list[str]:
    return [
        project.project_id
        for project in world.projects.values()
        if faction_id in project.linked_factions
    ][:8]


def _find_supply_for_faction(world: WorldState, faction_id: str) -> list[str]:
    return [
        supply_line.supply_id
        for supply_line in world.supply_lines.values()
        if supply_line.controlling_faction_ref == faction_id
    ][:8]


def _format_project_recent_notes(world: WorldState, project: ProjectNetwork, *, player_view: bool) -> str:
    if player_view:
        return "  recent_notes: Obscured in player view"
    if not project.recent_notes:
        return "  recent_notes: None"
    lines = ["  recent_notes:"]
    lines.append(
        "    概述: "
        + _structural_recent_notes_summary(world, project.recent_notes, subject="project")
    )
    for note in _dedupe_recent_note_labels(world, project.recent_notes)[-3:]:
        lines.append(f"    - {note}")
    return "\n".join(lines)


def _format_supply_recent_notes(world: WorldState, supply_line: SupplyLine, *, player_view: bool) -> str:
    if player_view:
        return "  recent_notes: Obscured in player view"
    if not supply_line.recent_notes:
        return "  recent_notes: None"
    lines = ["  recent_notes:"]
    lines.append(
        "    概述: "
        + _structural_recent_notes_summary(world, supply_line.recent_notes, subject="supply")
    )
    for note in _dedupe_recent_note_labels(world, supply_line.recent_notes)[-3:]:
        lines.append(f"    - {note}")
    return "\n".join(lines)


def _format_project_pressure_interpretation(project: ProjectNetwork) -> str:
    notes = " ".join(project.recent_notes[-4:])
    if project.pressure == "high":
        if "budget_crisis" in notes or "construction_stall" in notes:
            return "  pressure_interpretation: 该项目已进入高压失稳阶段，预算与推进链同时承压。"
        if "contract_scramble" in notes or "project_bid" in notes:
            return "  pressure_interpretation: 该项目正处于高压争夺状态，控制权与执行权都不稳定。"
        return "  pressure_interpretation: 该项目表面仍在运转，但关键前线已经明显吃紧。"
    if project.pressure == "medium":
        if "phase_advance" in notes or "grid_linked" in notes or "groundbreaking_started" in notes:
            return "  pressure_interpretation: 该项目仍在推进，但推进过程受到持续牵制。"
        if "security_cordon_raised" in notes:
            return "  pressure_interpretation: 该项目暂时被安保收口稳住，但稳定性并不牢固。"
        return "  pressure_interpretation: 该项目处于可推进但不算轻松的中压状态。"
    if "reactivation_window" in notes:
        return "  pressure_interpretation: 该项目当前压力较低，并出现了重新启动或恢复扩张的空间。"
    return "  pressure_interpretation: 该项目当前压力较低，局势相对可控。"


def _format_supply_pressure_interpretation(supply_line: SupplyLine) -> str:
    notes = " ".join(supply_line.recent_notes[-4:])
    if supply_line.pressure == "high":
        if notes.count("quarantine_panic_disrupted_corridor") >= 2:
            return "  pressure_interpretation: 这条补给线正在反复受扰，运输节奏已经明显失稳。"
        if "emergency_lockdown_slowed_routing" in notes:
            return "  pressure_interpretation: 这条补给线被安全或管控措施拖慢，效率正在下降。"
        if "resource_reallocation" in notes:
            return "  pressure_interpretation: 这条补给线虽然仍被使用，但正在高压下被迫改道。"
        return "  pressure_interpretation: 这条补给线已处于高压状态，任何额外冲击都可能造成中断。"
    if supply_line.pressure == "medium":
        if "resource_reallocation" in notes:
            return "  pressure_interpretation: 这条补给线正在被重新分配和调整，但还没有完全失序。"
        return "  pressure_interpretation: 这条补给线存在摩擦和迟滞，但尚未演变为严重断裂。"
    return "  pressure_interpretation: 这条补给线当前运行相对平稳，短期内仍可承担运输任务。"


def _format_supply_control_state(world: WorldState, supply_line: SupplyLine) -> str:
    relations = [
        relation
        for relation in relations_for_ref(world, supply_line.supply_id, limit=12)
        if relation.status == "active"
    ]
    controllers = [
        relation.source_ref
        for relation in relations
        if relation.target_ref == supply_line.supply_id and relation.relation_type == "controls"
    ]
    contenders = [
        relation.source_ref
        for relation in relations
        if relation.target_ref == supply_line.supply_id and relation.relation_type == "contesting"
    ]
    controller = supply_line.controlling_faction_ref
    if controller and controller in contenders:
        return "现控制方已经摸到线路主阀，但仍在争夺余波中固位，控制权并不完全稳固。"
    external_contenders = [ref for ref in contenders if ref != controller]
    if controller and external_contenders:
        return "这条补给线已有明确控制方，但外部争夺仍在持续，任何额外冲击都可能引发换手。"
    if controller and supply_line.pressure == "high":
        return "这条补给线名义上仍有控制方，但线路本身已处在高压失序边缘。"
    if controllers and not controller:
        return "关系层显示这条补给线存在控制痕迹，但名义控制权已经开始模糊。"
    if external_contenders:
        return "这条补给线当前没有完全坐实的控制方，多股力量正在围绕它反复争夺。"
    if controller:
        return "这条补给线当前控制权相对清晰，主要围绕既有控制方运转。"
    return "这条补给线目前没有显著稳定控制者，更多是在惯性和局部干预下运行。"


def _format_faction_relation_front(world: WorldState, faction: Faction) -> str:
    relations = relations_for_ref(world, faction.faction_id, limit=12)
    if not relations and not faction.rival_factions and not faction.allied_factions:
        return "  relation_front: None"

    rivalry_count = 0
    alliance_count = 0
    control_count = 0
    covert_count = 0
    focal_entries: list[tuple[str, str]] = []
    grouped_relations = _group_relations_by_counterparty(relations, faction.faction_id)
    for counterparty, pair_relations in grouped_relations:
        relation = pair_relations[0]
        relation_type = relation.relation_type
        if relation_type in {"rival_to", "contesting", "obstructing", "opposing"}:
            rivalry_count += 1
        elif relation_type in {"allied_with"}:
            alliance_count += 1
        elif relation_type in {"controls", "contracting", "financing", "sponsoring", "supply_influence"}:
            control_count += 1
        elif relation_type in {"infiltrating", "seeking_control", "flashpoint_actor"}:
            covert_count += 1

        focal_entries.append(
            (
                f"{relation_type}:{counterparty}",
                _truth_relation_focus_entry(
                    subject=_format_entity_ref(world, counterparty),
                    relation_type=relation_type,
                    strength=relation.strength,
                    tick=relation.updated_tick,
                ),
            )
        )

    lines = ["  relation_front:"]
    lines.append(
        "    概述: "
        + _summarize_faction_relation_front(
            faction=faction,
            rivalry_count=rivalry_count,
            alliance_count=alliance_count,
            control_count=control_count,
            covert_count=covert_count,
        )
    )
    lines.append(
        "    结构压力: "
        f"对抗={rivalry_count}, 结盟={alliance_count}, 控制链={control_count}, 潜入/热点={covert_count}"
    )
    lines.append(f"    关系气候: {_relation_climate_text(rivalry_count, alliance_count, control_count, covert_count)}")
    lines.append(
        "    因果解释: "
        + _explain_faction_relation_front_drivers(
            world,
            faction,
            rivalry_count=rivalry_count,
            alliance_count=alliance_count,
            control_count=control_count,
            covert_count=covert_count,
        )
    )
    lines.append(
        _format_relation_axes_block(
            world,
            faction.faction_id,
            relations,
            label="主导轴线",
            limit=4,
            grouped_relations=grouped_relations,
        )
    )
    if focal_entries:
        lines.append("    当前焦点:")
        for entry in _dedupe_relation_entries(focal_entries, limit=4):
            lines.append(f"      - {entry}")
    else:
        lines.append("    当前焦点: None")
    return "\n".join(lines)


def _format_civilization_relation_front(world: WorldState, civilization: Civilization) -> str:
    faction_ids = set(civilization.key_factions)
    if not faction_ids:
        return "  relation_front: None"

    relations = []
    seen: set[str] = set()
    for faction_id in civilization.key_factions[:6]:
        for relation in relations_for_ref(world, faction_id, limit=4):
            if relation.relation_id in seen:
                continue
            seen.add(relation.relation_id)
            relations.append(relation)
    if not relations:
        return "  relation_front: None"

    internal_conflict = 0
    alliance_mesh = 0
    external_pressure = 0
    control_lines = 0
    focal_entries: list[tuple[str, str]] = []
    grouped_relations = _group_civilization_relations(world, relations, faction_ids)
    for relation_label, pair_relations in grouped_relations:
        relation = pair_relations[0]
        source_inside = relation.source_ref in faction_ids
        target_inside = relation.target_ref in faction_ids
        relation_type = relation.relation_type
        counterparty = _civilization_relation_focus_ref(relation, faction_ids)
        focus_key = relation_label if source_inside and target_inside else counterparty

        if source_inside and target_inside and relation_type in {"rival_to", "contesting"}:
            internal_conflict += 1
        elif source_inside and target_inside and relation_type == "allied_with":
            alliance_mesh += 1
        elif relation_type in {"controls", "contracting", "financing", "sponsoring", "supply_influence"}:
            control_lines += 1
        else:
            external_pressure += 1

        focal_entries.append(
            (
                f"{relation_type}:{focus_key}",
                _truth_relation_focus_entry(
                    subject=relation_label if source_inside and target_inside else _format_entity_ref(world, counterparty),
                    relation_type=relation_type,
                    strength=relation.strength,
                    tick=relation.updated_tick,
                ),
            )
        )

    lines = ["  relation_front:"]
    lines.append(
        "    概述: "
        + _summarize_civilization_relation_front(
            internal_conflict=internal_conflict,
            alliance_mesh=alliance_mesh,
            external_pressure=external_pressure,
            control_lines=control_lines,
        )
    )
    lines.append(
        "    结构压力: "
        f"内部冲突={internal_conflict}, 联盟网={alliance_mesh}, 外部压力={external_pressure}, 控制链={control_lines}"
    )
    lines.append(
        "    关系气候: "
        + _relation_climate_text(
            rivalry_count=internal_conflict,
            alliance_count=alliance_mesh,
            control_count=control_lines,
            covert_count=external_pressure,
        )
    )
    lines.append(
        "    因果解释: "
        + _explain_civilization_relation_front_drivers(
            world,
            civilization,
            internal_conflict=internal_conflict,
            alliance_mesh=alliance_mesh,
            external_pressure=external_pressure,
            control_lines=control_lines,
        )
    )
    lines.append(
        _format_relation_axes_block(
            world,
            civilization.civ_id,
            relations,
            label="主导轴线",
            limit=5,
            grouped_relations=grouped_relations,
            label_overrides={
                label: label for label, _ in grouped_relations if " <-> " in label
            },
        )
    )
    lines.append("    当前焦点:")
    for entry in _dedupe_relation_entries(focal_entries, limit=5):
        lines.append(f"      - {entry}")
    return "\n".join(lines)


def _format_civilization_external_relations(world: WorldState, civilization: Civilization) -> str:
    if not civilization.external_relations:
        return "  external_relations: None"
    lines = ["  external_relations:"]
    for ref, relation_type in list(civilization.external_relations.items())[:8]:
        lines.append(
            "    - "
            + _truth_relation_entry(
                subject=_format_entity_ref(world, ref),
                relation_type=relation_type,
            )
        )
    return "\n".join(lines)


def _format_faction_dependency_chain(world: WorldState, faction: Faction) -> str:
    relations = relations_for_ref(world, faction.faction_id, limit=12)
    relation_pairs: list[tuple[str, str, str]] = []
    for relation in relations:
        if relation.relation_type not in {"controls", "contracting", "financing", "supply_influence"}:
            continue
        counterparty = relation.target_ref if relation.source_ref == faction.faction_id else relation.source_ref
        relation_pairs.append((counterparty, relation.relation_type, relation.strength))
    project_refs: list[tuple[str, str]] = []
    project_ids = _find_projects_for_faction(world, faction.faction_id)
    for project_id in project_ids[:2]:
        project = world.projects.get(project_id)
        if project is None:
            continue
        project_refs.append(
            (f"{project.name} ({project.project_id})", project.pressure)
        )
    supply_refs: list[tuple[str, str]] = []
    supply_ids = _find_supply_for_faction(world, faction.faction_id)
    for supply_id in supply_ids[:2]:
        supply_line = world.supply_lines.get(supply_id)
        if supply_line is None:
            continue
        supply_refs.append(
            (f"{supply_line.name} ({supply_line.supply_id})", supply_line.pressure)
        )
    if not relation_pairs and not project_refs and not supply_refs:
        return "  dependency_chain: None"
    lines = ["  dependency_chain:"]
    lines.append(
        "    概述: "
        + _summarize_faction_dependency_chain(
            relation_pairs=relation_pairs,
            project_refs=project_refs,
            supply_refs=supply_refs,
        )
    )
    highlights = _build_dependency_highlights(
        world,
        relation_pairs=relation_pairs,
        project_refs=project_refs,
        supply_refs=supply_refs,
        limit=3,
    )
    if highlights:
        lines.append("    关键依赖:")
        for entry in highlights:
            lines.append(f"      - {entry}")
    lines.append(
        "    因果解释: "
        + _explain_faction_dependency_chain_drivers(
            world,
            faction,
            relation_pairs=relation_pairs,
            project_refs=project_refs,
            supply_refs=supply_refs,
        )
    )
    lines.append(
        "    压力解释: "
        + _summarize_dependency_pressure(
            relation_pairs=relation_pairs,
            project_refs=project_refs,
            supply_refs=supply_refs,
        )
    )
    return "\n".join(lines)


def _format_faction_sponsorship_chain(world: WorldState, faction: Faction) -> str:
    relations = relations_for_ref(world, faction.faction_id, limit=12)
    entries: dict[tuple[str, str], set[str]] = {}
    strengths: dict[tuple[str, str], str] = {}
    for relation in relations:
        if relation.relation_type not in {"sponsoring", "financing", "allied_with", "supports", "supporting"}:
            continue
        counterparty = relation.target_ref if relation.source_ref == faction.faction_id else relation.source_ref
        direction = "outbound" if relation.source_ref == faction.faction_id else "inbound"
        key = (counterparty, relation.relation_type)
        entries.setdefault(key, set()).add(direction)
        strengths[key] = relation.strength
    if not entries:
        return "  sponsorship_chain: None"
    lines = ["  sponsorship_chain:"]
    lines.append(
        "    因果解释: "
        + _explain_faction_sponsorship_drivers(world, faction, entries)
    )
    rendered: list[str] = []
    for (counterparty, relation_type), flows in entries.items():
        flow_text = "/".join(sorted(flows))
        rendered.append(
            "    - "
            + _truth_relation_entry(
                subject=_format_entity_ref(world, counterparty),
                relation_type=relation_type,
                strength=strengths[(counterparty, relation_type)],
                flow=flow_text,
            )
        )
    lines.extend(_dedupe_entries(rendered, limit=5))
    return "\n".join(lines)


def _format_faction_region_anchors(world: WorldState, faction: Faction) -> str:
    anchor_map: dict[str, list[str]] = {}
    for region_id in faction.controlled_regions[:4]:
        anchor_map.setdefault(region_id, []).append("controlled_region")
    relations = relations_for_ref(world, faction.faction_id, limit=12)
    for relation in relations:
        counterparty = relation.target_ref if relation.source_ref == faction.faction_id else relation.source_ref
        if counterparty not in world.regions:
            continue
        if relation.relation_type not in {"infiltrating", "contesting", "operates_in", "stabilizing"}:
            continue
        anchor_map.setdefault(counterparty, []).append(relation.relation_type)
    if not anchor_map:
        return "  region_anchors: None"
    lines = ["  region_anchors:"]
    lines.append(
        "    因果解释: "
        + _explain_faction_region_anchor_drivers(world, faction, anchor_map)
    )
    rendered = []
    for region_id, types in anchor_map.items():
        type_text = "、".join(_truth_region_anchor_type_value(anchor_type) for anchor_type in dict.fromkeys(types))
        rendered.append(f"    - {_format_entity_ref(world, region_id)} [锚点性质={type_text}]")
    lines.extend(_dedupe_entries(rendered, limit=5))
    return "\n".join(lines)


def _format_civilization_dependency_chain(world: WorldState, civilization: Civilization) -> str:
    relation_pairs: list[tuple[str, str, str, str]] = []
    for faction_id in civilization.key_factions[:6]:
        for relation in relations_for_ref(world, faction_id, limit=6):
            if relation.relation_type not in {"controls", "contracting", "financing", "supply_influence"}:
                continue
            counterparty = relation.target_ref if relation.source_ref == faction_id else relation.source_ref
            relation_pairs.append(
                (counterparty, world.factions[faction_id].name, relation.relation_type, relation.strength)
            )
    project_refs: list[tuple[str, str]] = []
    for project_id in civilization.key_projects[:3]:
        project = world.projects.get(project_id)
        if project is None:
            continue
        project_refs.append(
            (f"{project.name} ({project.project_id})", project.pressure)
        )
    supply_refs: list[tuple[str, str]] = []
    for supply_id in civilization.key_supply_lines[:3]:
        supply_line = world.supply_lines.get(supply_id)
        if supply_line is None:
            continue
        supply_refs.append(
            (f"{supply_line.name} ({supply_line.supply_id})", supply_line.pressure)
        )
    if not relation_pairs and not project_refs and not supply_refs:
        return "  dependency_chain: None"
    lines = ["  dependency_chain:"]
    lines.append(
        "    概述: "
        + _summarize_civilization_dependency_chain(
            relation_pairs=relation_pairs,
            project_refs=project_refs,
            supply_refs=supply_refs,
        )
    )
    highlights = _build_civilization_dependency_highlights(
        world,
        relation_pairs=relation_pairs,
        project_refs=project_refs,
        supply_refs=supply_refs,
        limit=4,
    )
    if highlights:
        lines.append("    关键依赖:")
        for entry in highlights:
            lines.append(f"      - {entry}")
    lines.append(
        "    因果解释: "
        + _explain_civilization_dependency_chain_drivers(
            world,
            civilization,
            relation_pairs=relation_pairs,
            project_refs=project_refs,
            supply_refs=supply_refs,
        )
    )
    lines.append(
        "    压力解释: "
        + _summarize_dependency_pressure(
            relation_pairs=[(ref, relation_type, strength) for ref, _, relation_type, strength in relation_pairs],
            project_refs=project_refs,
            supply_refs=supply_refs,
        )
    )
    return "\n".join(lines)


def _summarize_faction_dependency_chain(
    *,
    relation_pairs: list[tuple[str, str, str]],
    project_refs: list[tuple[str, str]],
    supply_refs: list[tuple[str, str]],
) -> str:
    if len(project_refs) >= 1 and len(supply_refs) >= 1:
        return "该派系的依赖链同时压在项目网络与运输路径上，组织动作已经明显需要结构支撑。"
    if len(relation_pairs) >= 2:
        return "该派系正在通过控制、承包或融资关系维持外部抓手，依赖链已开始外露。"
    if len(project_refs) >= 1:
        return "该派系当前明显挂靠在关键项目上，许多动作都要围绕工程或建设节奏展开。"
    if len(supply_refs) >= 1:
        return "该派系当前更依赖运输与补给网络，线路稳定性会直接影响其动作空间。"
    return "该派系已经出现可见依赖链，但仍主要体现在零散控制关系上。"


def _summarize_civilization_dependency_chain(
    *,
    relation_pairs: list[tuple[str, str, str, str]],
    project_refs: list[tuple[str, str]],
    supply_refs: list[tuple[str, str]],
) -> str:
    if len(project_refs) >= 2 and len(supply_refs) >= 1:
        return "该文明的依赖链已经压到项目群与补给骨架上，整体运行对结构网络的依赖很强。"
    if len(relation_pairs) >= 3:
        return "该文明的关键派系正在把控制、融资和承包关系铺成网络，外部结构依赖正在变厚。"
    if len(project_refs) >= 1:
        return "该文明当前明显依赖关键项目网络，扩张和稳定都要围绕工程节点推进。"
    if len(supply_refs) >= 1:
        return "该文明的运转更受补给主干牵引，线路压力会直接传导到整体秩序。"
    return "该文明已经出现初步结构依赖，但还没有完全固化为重型网络。"


def _build_dependency_highlights(
    world: WorldState,
    *,
    relation_pairs: list[tuple[str, str, str]],
    project_refs: list[tuple[str, str]],
    supply_refs: list[tuple[str, str]],
    limit: int,
) -> list[str]:
    entries: list[str] = []
    seen: set[str] = set()
    ordered_relations = sorted(
        relation_pairs,
        key=lambda item: (
            _dependency_ref_priority(world, item[0]),
            _relation_priority(item[1]),
            _relation_strength_priority(item[2]),
        ),
        reverse=True,
    )
    for ref, relation_type, strength in ordered_relations:
        entry = _truth_relation_entry(
            subject=_format_entity_ref(world, ref),
            relation_type=relation_type,
            strength=strength,
        )
        if entry in seen:
            continue
        seen.add(entry)
        entries.append(entry)
        if len(entries) >= limit:
            return entries
    for name, pressure in project_refs:
        entry = f"{name} [项目挂钩, 压力={_player_level_value(pressure)}]"
        if entry in seen:
            continue
        seen.add(entry)
        entries.append(entry)
        if len(entries) >= limit:
            return entries
    for name, pressure in supply_refs:
        entry = f"{name} [补给挂钩, 压力={_player_level_value(pressure)}]"
        if entry in seen:
            continue
        seen.add(entry)
        entries.append(entry)
        if len(entries) >= limit:
            return entries
    return entries


def _build_civilization_dependency_highlights(
    world: WorldState,
    *,
    relation_pairs: list[tuple[str, str, str, str]],
    project_refs: list[tuple[str, str]],
    supply_refs: list[tuple[str, str]],
    limit: int,
) -> list[str]:
    entries: list[str] = []
    seen: set[str] = set()
    ordered_relations = sorted(
        relation_pairs,
        key=lambda item: (
            _dependency_ref_priority(world, item[0]),
            _relation_priority(item[2]),
            _relation_strength_priority(item[3]),
        ),
        reverse=True,
    )
    for ref, via_name, relation_type, strength in ordered_relations:
        entry = _truth_relation_entry(
            subject=_format_entity_ref(world, ref),
            relation_type=relation_type,
            strength=strength,
            via=via_name,
        )
        if entry in seen:
            continue
        seen.add(entry)
        entries.append(entry)
        if len(entries) >= limit:
            return entries
    for name, pressure in project_refs:
        entry = f"{name} [文明项目挂钩, 压力={_player_level_value(pressure)}]"
        if entry in seen:
            continue
        seen.add(entry)
        entries.append(entry)
        if len(entries) >= limit:
            return entries
    for name, pressure in supply_refs:
        entry = f"{name} [文明补给挂钩, 压力={_player_level_value(pressure)}]"
        if entry in seen:
            continue
        seen.add(entry)
        entries.append(entry)
        if len(entries) >= limit:
            return entries
    return entries


def _summarize_dependency_pressure(
    *,
    relation_pairs: list[tuple[str, str, str]],
    project_refs: list[tuple[str, str]],
    supply_refs: list[tuple[str, str]],
) -> str:
    high_pressure_projects = sum(1 for _, pressure in project_refs if pressure == "high")
    high_pressure_supply = sum(1 for _, pressure in supply_refs if pressure == "high")
    high_strength_relations = sum(1 for _, _, strength in relation_pairs if strength == "high")
    if high_pressure_projects + high_pressure_supply >= 2:
        return "多条关键结构已经处在高压位，一旦再受扰动，行动节奏会明显失稳。"
    if high_strength_relations >= 2:
        return "当前控制链强度偏高，说明这些依赖不是装饰性联系，而是会反向塑形决策。"
    if project_refs or supply_refs:
        return "目前依赖更多体现为结构牵引，短期仍可运转，但灵活性已经开始下降。"
    return "当前依赖仍偏轻，更多像方向性牵引，还没有形成硬性锁定。"


def _explain_faction_dependency_chain_drivers(
    world: WorldState,
    faction: Faction,
    *,
    relation_pairs: list[tuple[str, str, str]],
    project_refs: list[tuple[str, str]],
    supply_refs: list[tuple[str, str]],
) -> str:
    drivers: list[str] = []
    recent_events = [
        event.event_type
        for event in reversed(world.event_stream.recent(40))
        if faction.faction_id in event.faction_refs and event.event_type.startswith("faction_")
    ][:5]
    if len(project_refs) >= 1 and any(token in event_type for event_type in recent_events for token in {"project_bid", "budget", "financing"}):
        drivers.append("近期项目竞标、预算或融资动作正在把依赖链压向工程节点")
    if len(supply_refs) >= 1 and any(token in event_type for event_type in recent_events for token in {"resource_reallocation", "alliance", "infiltration"}):
        drivers.append("补给调度和线路施压正在把它的动作空间绑到运输骨架上")
    if sum(1 for _, relation_type, _ in relation_pairs if relation_type in {"controls", "contracting", "financing"}) >= 2:
        drivers.append("控制、承包和融资关系已经开始外露成连续抓手")
    if not drivers and faction.influence == "high":
        drivers.append("影响力上升正在迫使它把零散动作沉淀为更稳定的结构依赖")
    if not drivers:
        drivers.append("当前依赖链主要来自既有控制关系的累积，还没有单一强驱动源")
    return "；".join(dict.fromkeys(drivers))


def _explain_civilization_dependency_chain_drivers(
    world: WorldState,
    civilization: Civilization,
    *,
    relation_pairs: list[tuple[str, str, str, str]],
    project_refs: list[tuple[str, str]],
    supply_refs: list[tuple[str, str]],
) -> str:
    drivers: list[str] = []
    recent_events = [
        event.event_type
        for event in reversed(world.event_stream.recent(50))
        if civilization.civ_id in event.civ_refs
    ][:6]
    if len(project_refs) >= 1 and any(token in event_type for event_type in recent_events for token in {"project", "megastructure", "budget", "financing"}):
        drivers.append("工程推进和巨构相关压力正在把文明运转压向关键项目群")
    if len(supply_refs) >= 1 and any(token in event_type for event_type in recent_events for token in {"resource", "supply", "corridor", "quarantine"}):
        drivers.append("供给和线路波动正在把整体秩序绑到补给骨架上")
    if len(relation_pairs) >= 3:
        drivers.append("关键派系已经把控制、融资和承包关系铺成可见网络")
    if not drivers and civilization.expansion_pressure == "medium":
        drivers.append("扩张与维持并行的状态正在自然抬高结构依赖")
    if not drivers:
        drivers.append("当前依赖链主要来自既有组织网络的惯性外露，还没有单一强驱动源")
    return "；".join(dict.fromkeys(drivers))


def _explain_faction_sponsorship_drivers(
    world: WorldState,
    faction: Faction,
    entries: dict[tuple[str, str], set[str]],
) -> str:
    inbound = sum(1 for flows in entries.values() if "inbound" in flows)
    outbound = sum(1 for flows in entries.values() if "outbound" in flows)
    recent_types = [
        event.event_type
        for event in reversed(world.event_stream.recent(40))
        if faction.faction_id in event.faction_refs and event.event_type.startswith("faction_")
    ][:4]
    drivers: list[str] = []
    if inbound >= 1:
        drivers.append("它最近显然在吸纳外部背书或资源接口")
    if outbound >= 1:
        drivers.append("它也在主动向外投放协作或支撑关系来稳住前线")
    if any("alliance" in event_type for event_type in recent_types):
        drivers.append("近期结盟动作正在把零散协作固化为更稳定的背书链")
    if any("financing" in event_type for event_type in recent_types):
        drivers.append("融资动作正在把关系面从单纯合作推向资源绑定")
    if not drivers:
        drivers.append("当前背书链主要来自既有合作网络的延续")
    return "；".join(dict.fromkeys(drivers))


def _explain_civilization_sponsorship_drivers(
    world: WorldState,
    civilization: Civilization,
    entries: dict[tuple[str, str, str], set[str]],
) -> str:
    inbound = sum(1 for flows in entries.values() if "inbound" in flows)
    outbound = sum(1 for flows in entries.values() if "outbound" in flows)
    recent_types = [
        event.event_type
        for event in reversed(world.event_stream.recent(50))
        if civilization.civ_id in event.civ_refs
    ][:6]
    drivers: list[str] = []
    if inbound + outbound >= 3:
        drivers.append("多个派系接口正在把背书和协作关系织成跨组织支撑网")
    elif inbound >= 1:
        drivers.append("文明内部至少有一部分结构正在主动吸纳外部支撑")
    if any("alliance" in event_type or "financing" in event_type for event_type in recent_types):
        drivers.append("近期结盟和融资波动正在把松散关系压成更稳定的支撑链")
    if not drivers:
        drivers.append("当前支撑链主要由既有派系协作惯性延续而成")
    return "；".join(dict.fromkeys(drivers))


def _explain_faction_region_anchor_drivers(
    world: WorldState,
    faction: Faction,
    anchor_map: dict[str, list[str]],
) -> str:
    controlled = sum(1 for types in anchor_map.values() if "controlled_region" in types)
    contested = sum(1 for types in anchor_map.values() if "contesting" in types)
    infiltrating = sum(1 for types in anchor_map.values() if "infiltrating" in types or "operates_in" in types)
    drivers: list[str] = []
    if controlled >= 1:
        drivers.append("既有控制区正在给它提供稳定落点")
    if contested >= 1:
        drivers.append("争夺中的地区让它不得不把影响力继续钉在前线")
    if infiltrating >= 1:
        drivers.append("渗透和驻留动作正在把短期介入沉淀成长期落点")
    if not drivers and faction.power_scope == "cross_regional":
        drivers.append("跨区活动范围正在自然推高地区锚点的数量")
    if not drivers:
        drivers.append("当前地区锚点主要来自既有活动半径的惯性累积")
    return "；".join(dict.fromkeys(drivers))


def _explain_civilization_region_anchor_drivers(
    world: WorldState,
    civilization: Civilization,
    entries: dict[str, list[str]],
) -> str:
    core_regions = sum(1 for hints in entries.values() if "core_region" in hints)
    contested = sum(1 for hints in entries.values() if any("contesting" in hint for hint in hints))
    infiltrating = sum(1 for hints in entries.values() if any("infiltrating" in hint or "operates_in" in hint for hint in hints))
    drivers: list[str] = []
    if core_regions >= 1:
        drivers.append("核心地区仍在给文明关系网提供稳定着力点")
    if contested >= 1:
        drivers.append("争夺中的边缘地区正在逼迫派系把更多力量钉在地方前线")
    if infiltrating >= 1:
        drivers.append("派系渗透和持续驻留正在把外围地区拉进文明锚点网络")
    if not drivers and civilization.expansion_pressure in {"medium", "high"}:
        drivers.append("扩张压力正在自然推高地区锚点的重要性")
    if not drivers:
        drivers.append("当前锚点网络主要由既有领土骨架的惯性延续而成")
    return "；".join(dict.fromkeys(drivers))


def _dependency_ref_priority(world: WorldState, ref: str) -> int:
    if ref in world.projects:
        return 6
    if ref in world.supply_lines:
        return 5
    if ref in world.relics:
        return 4
    if ref in world.factions:
        return 3
    if ref in world.civilizations:
        return 2
    if ref in world.regions:
        return 1
    return 0


def _format_civilization_sponsorship_chain(world: WorldState, civilization: Civilization) -> str:
    entries: dict[tuple[str, str, str], set[str]] = {}
    for faction_id in civilization.key_factions[:6]:
        for relation in relations_for_ref(world, faction_id, limit=6):
            if relation.relation_type not in {"sponsoring", "financing", "allied_with", "supports", "supporting"}:
                continue
            counterparty = relation.target_ref if relation.source_ref == faction_id else relation.source_ref
            direction = "outbound" if relation.source_ref == faction_id else "inbound"
            key = (counterparty, world.factions[faction_id].name, relation.relation_type)
            entries.setdefault(key, set()).add(direction)
    if not entries:
        return "  sponsorship_chain: None"
    lines = ["  sponsorship_chain:"]
    lines.append(
        "    因果解释: "
        + _explain_civilization_sponsorship_drivers(world, civilization, entries)
    )
    rendered: list[str] = []
    for (counterparty, via_name, relation_type), flows in entries.items():
        flow_text = "/".join(sorted(flows))
        rendered.append(
            "    - "
            + _truth_relation_entry(
                subject=_format_entity_ref(world, counterparty),
                relation_type=relation_type,
                via=via_name,
                flow=flow_text,
            )
        )
    lines.extend(_dedupe_entries(rendered, limit=6))
    return "\n".join(lines)


def _format_civilization_region_anchors(world: WorldState, civilization: Civilization) -> str:
    entries: dict[str, list[str]] = {}
    for region_id in civilization.key_regions[:6]:
        entries.setdefault(region_id, []).append("core_region")
    for faction_id in civilization.key_factions[:6]:
        for relation in relations_for_ref(world, faction_id, limit=6):
            counterparty = relation.target_ref if relation.source_ref == faction_id else relation.source_ref
            if counterparty not in world.regions:
                continue
            if relation.relation_type not in {"infiltrating", "contesting", "stabilizing", "operates_in"}:
                continue
            entries.setdefault(counterparty, []).append(
                f"{world.factions[faction_id].name}:{relation.relation_type}"
            )
    if not entries:
        return "  region_anchors: None"
    lines = ["  region_anchors:"]
    lines.append(
        "    因果解释: "
        + _explain_civilization_region_anchor_drivers(world, civilization, entries)
    )
    rendered: list[str] = []
    for region_id, hints in entries.items():
        hint_text = "；".join(_truth_civilization_region_anchor_hint(hint) for hint in dict.fromkeys(hints))
        rendered.append(f"    - {_format_entity_ref(world, region_id)} [锚点结构={hint_text}]")
    lines.extend(_dedupe_entries(rendered, limit=6))
    return "\n".join(lines)


def _group_civilization_relations(world: WorldState, relations, faction_ids: set[str]):
    grouped: dict[str, tuple[str, list]] = {}
    for relation in relations:
        source_inside = relation.source_ref in faction_ids
        target_inside = relation.target_ref in faction_ids
        if source_inside and target_inside:
            pair = tuple(sorted((relation.source_ref, relation.target_ref)))
            label = " <-> ".join(_format_entity_ref(world, ref) for ref in pair)
            key = f"internal:{pair[0]}::{pair[1]}"
        else:
            counterparty = relation.target_ref if source_inside else relation.source_ref
            label = counterparty
            key = f"external:{counterparty}"
        current = grouped.get(key)
        if current is None:
            grouped[key] = (label, [relation])
        else:
            current[1].append(relation)
    ordered: list[tuple[str, list]] = []
    for label, items in grouped.values():
        items.sort(key=_relation_sort_key, reverse=True)
        ordered.append((label, items))
    ordered.sort(key=lambda item: item[1][0].updated_tick, reverse=True)
    return ordered


def _civilization_relation_focus_ref(relation, faction_ids: set[str]) -> str:
    source_inside = relation.source_ref in faction_ids
    target_inside = relation.target_ref in faction_ids
    if source_inside and not target_inside:
        return relation.target_ref
    if target_inside and not source_inside:
        return relation.source_ref
    return relation.target_ref


def _relation_sort_key(relation) -> tuple[int, int, int]:
    return (
        _relation_priority(relation.relation_type),
        _relation_strength_priority(relation.strength),
        relation.updated_tick,
    )


def _summarize_faction_relation_front(
    *,
    faction: Faction,
    rivalry_count: int,
    alliance_count: int,
    control_count: int,
    covert_count: int,
) -> str:
    if rivalry_count >= 3 and alliance_count == 0:
        return "该派系正处于明显的多线对抗中，关系前线以正面争夺和相互牵制为主。"
    if rivalry_count >= 2 and alliance_count >= 1:
        return "该派系一边维持盟友，一边展开高强度争夺，关系前线已进入复杂缠斗状态。"
    if control_count >= 2 and rivalry_count <= 1:
        return "该派系当前更像在扩张控制链，关系前线以承包、融资或区域影响力渗透为主。"
    if covert_count >= 2 and rivalry_count <= 1:
        return "该派系当前更偏向潜入和热点施压，许多动作仍停留在半公开前线。"
    if alliance_count >= 2 and rivalry_count == 0:
        return "该派系当前的关系前线相对稳固，主要依赖结盟和协作来扩大影响。"
    if rivalry_count >= 1:
        return "该派系已经卷入可见争夺，但前线尚未完全升级为全面冲突。"
    if alliance_count >= 1:
        return "该派系当前关系面相对平稳，正在借助有限联盟维持位置。"
    if control_count >= 1:
        return "该派系的关系动作主要围绕控制权布局展开，外部冲突暂时不算尖锐。"
    if covert_count >= 1:
        return "该派系的关系动作目前偏隐蔽，更多是在热点边缘试探和布线。"
    if faction.influence == "high":
        return "该派系当前影响力较高，但关系前线暂时没有显著外露。"
    return "该派系当前关系前线较弱，外部联结和冲突都还不明显。"


def _summarize_civilization_relation_front(
    *,
    internal_conflict: int,
    alliance_mesh: int,
    external_pressure: int,
    control_lines: int,
) -> str:
    if internal_conflict >= 3 and alliance_mesh == 0:
        return "该文明内部派系冲突已经明显外露，关系前线主要表现为内部撕扯。"
    if internal_conflict >= 2 and alliance_mesh >= 1:
        return "该文明内部同时存在结盟与争权，整体关系前线处于复杂重组状态。"
    if control_lines >= 3 and internal_conflict <= 1:
        return "该文明当前更像在扩展控制链，组织关系正在向项目、融资和地区影响力延伸。"
    if external_pressure >= 3 and internal_conflict <= 1:
        return "该文明的关系前线主要承受外部压力，内部结构暂时仍能维持。"
    if alliance_mesh >= 2 and internal_conflict == 0:
        return "该文明内部组织关系相对稳固，联盟网络正在支撑整体秩序。"
    if internal_conflict >= 1:
        return "该文明已经出现可见内部摩擦，但尚未完全滑入全面内耗。"
    return "该文明当前关系前线相对平稳，但组织网络仍在持续调整。"


def _explain_faction_relation_front_drivers(
    world: WorldState,
    faction: Faction,
    *,
    rivalry_count: int,
    alliance_count: int,
    control_count: int,
    covert_count: int,
) -> str:
    drivers: list[str] = []
    recent_events = [
        event
        for event in reversed(world.event_stream.recent(40))
        if faction.faction_id in event.faction_refs and event.event_type.startswith("faction_")
    ]
    recent_types = [event.event_type for event in recent_events[:4]]
    project_ids = _find_projects_for_faction(world, faction.faction_id)
    supply_ids = _find_supply_for_faction(world, faction.faction_id)
    high_pressure_projects = sum(
        1
        for project_id in project_ids[:3]
        if (project := world.projects.get(project_id)) is not None and project.pressure == "high"
    )
    high_pressure_supply = sum(
        1
        for supply_id in supply_ids[:3]
        if (supply := world.supply_lines.get(supply_id)) is not None and supply.pressure == "high"
    )

    if rivalry_count >= 2 or any("power_struggle" in event_type for event_type in recent_types):
        drivers.append("近期争权和正面牵制在抬高它的敌对面")
    if alliance_count >= 1 or any("alliance" in event_type for event_type in recent_types):
        drivers.append("结盟和背书链正在给它的关系面提供缓冲或扩张空间")
    if control_count >= 2 or any(token in event_type for event_type in recent_types for token in {"project_bid", "financing", "resource_reallocation"}):
        drivers.append("项目、融资或补给控制链正在把关系动作压向更重的结构竞争")
    if covert_count >= 1 or any("infiltration" in event_type for event_type in recent_types):
        drivers.append("渗透和热点试探让许多关系先以半公开方式外露")
    if high_pressure_projects + high_pressure_supply >= 1:
        drivers.append("高压结构节点正在反向塑形它的联盟与对抗选择")
    if not drivers and faction.influence_trend == "rising":
        drivers.append("影响力上升正在逼迫周围对象重新表态和站队")
    if not drivers:
        drivers.append("当前关系面更多来自既有组织位置的自然外露，还没有单一强驱动源")
    return "；".join(dict.fromkeys(drivers))


def _explain_civilization_relation_front_drivers(
    world: WorldState,
    civilization: Civilization,
    *,
    internal_conflict: int,
    alliance_mesh: int,
    external_pressure: int,
    control_lines: int,
) -> str:
    drivers: list[str] = []
    recent_events = [
        event
        for event in reversed(world.event_stream.recent(50))
        if civilization.civ_id in event.civ_refs
    ]
    recent_types = [event.event_type for event in recent_events[:6]]
    high_pressure_projects = sum(
        1
        for project_id in civilization.key_projects[:4]
        if (project := world.projects.get(project_id)) is not None and project.pressure == "high"
    )
    high_pressure_supply = sum(
        1
        for supply_id in civilization.key_supply_lines[:4]
        if (supply := world.supply_lines.get(supply_id)) is not None and supply.pressure == "high"
    )

    if internal_conflict >= 2 or any("power_struggle" in event_type for event_type in recent_types):
        drivers.append("内部派系争权正在持续重排这张关系网")
    if alliance_mesh >= 1 or any("alliance" in event_type for event_type in recent_types):
        drivers.append("文明内部的协作和结盟仍在努力抵消部分离散压力")
    if control_lines >= 2 or high_pressure_projects + high_pressure_supply >= 2:
        drivers.append("项目群和补给骨架的高压正在把组织关系压向更硬的控制链")
    if external_pressure >= 2:
        drivers.append("外部对象的牵制与接触面正在逼迫文明暴露更多关系接口")
    if any(token in event_type for event_type in recent_types for token in {"archive", "protocol", "lifeform", "migration"}):
        drivers.append("异常前线的波动正在穿透组织边界并重塑内外关系")
    if not drivers and civilization.legitimacy == "low":
        drivers.append("合法性偏低正在让本来隐性的关系摩擦更容易浮出表面")
    if not drivers:
        drivers.append("当前关系面主要来自既有派系网络的惯性调整，还没有单一强驱动源")
    return "；".join(dict.fromkeys(drivers))


def _summarize_character_relation_front(
    *,
    character: Character,
    foothold_count: int,
    pressure_count: int,
    presence_count: int,
    tether_count: int,
) -> str:
    if presence_count >= 2 and pressure_count >= 1:
        return "此人一边被异常或特殊存在牵引，一边在外部压力下持续调整立场。"
    if foothold_count >= 2 and pressure_count >= 1:
        return "此人已经在多个落点建立动作痕迹，并开始把这些落点转成施压位置。"
    if presence_count >= 2:
        return "此人的关系前线明显被异常目标或特殊存在牵引，动作方向较集中。"
    if pressure_count >= 2:
        return "此人当前主要卷在可见争夺里，关系前线已经带有明显对抗性。"
    if foothold_count >= 2:
        return "此人正在稳定自己的行动落点，关系层更多体现为持续渗入和驻留。"
    if tether_count >= 2:
        return "此人的关系网络还在铺开阶段，联结变多但主导方向尚未完全固定。"
    if character.frontier_focus_ref not in {"none", "", "regional_pressure"}:
        return "此人的关系牵引已经开始向当前关注前线收束。"
    return "此人的关系前线仍较轻，但已经出现可见牵引痕迹。"


def _relation_bucket_for_type(relation_type: str) -> str:
    if relation_type in {"rival_to", "contesting", "obstructing", "opposing"}:
        return "rivalry"
    if relation_type in {"allied_with", "supports", "supporting", "stabilizes"}:
        return "alliance"
    if relation_type in {"controls", "contracting", "financing", "sponsoring", "supply_influence", "influencing"}:
        return "control"
    if relation_type in {"infiltrating", "seeking_control", "flashpoint_actor", "delegitimizing", "distorts"}:
        return "covert"
    if relation_type in {"containing", "contained_by_region", "contained_by_civilization", "suppressed_by_civilization"}:
        return "containment"
    if relation_type in {"tracking", "engaged_with", "anchored_in", "originating_from", "encroaching_on", "biosecurity_threat"}:
        return "presence"
    if relation_type in {"operates_in", "stabilizing"}:
        return "foothold"
    return "other"


def _relation_climate_text(
    rivalry_count: int,
    alliance_count: int,
    control_count: int,
    covert_count: int,
) -> str:
    if rivalry_count >= 3 and covert_count >= 2:
        return "公开争夺与暗线动作同时升高，关系场处于高摩擦状态。"
    if control_count >= 3 and rivalry_count <= 1:
        return "控制链比正面冲突更强，关系场正在向组织控制和资源锁定收束。"
    if alliance_count >= 2 and rivalry_count == 0:
        return "协作关系占上风，关系场暂时更偏稳定扩张。"
    if covert_count >= 2 and rivalry_count <= 1:
        return "明面冲突有限，但暗线渗透和试探正在增厚。"
    if rivalry_count >= 2:
        return "关系场正在升温，公开层面的争夺已难以忽略。"
    if control_count >= 1 or alliance_count >= 1:
        return "关系场已有稳定结构，但还没进入全面失稳或全面对抗。"
    return "关系场仍较松散，更多是零散联结和局部牵引。"


def _format_relation_axes_block(
    world: WorldState,
    focal_ref: str,
    relations: list,
    *,
    label: str,
    limit: int,
    grouped_relations: list[tuple[str, list]] | None = None,
    label_overrides: dict[str, str] | None = None,
) -> str:
    grouped: dict[str, list[str]] = {}
    if grouped_relations is None:
        grouped_relations = _group_relations_by_counterparty(relations, focal_ref)

    for counterparty, pair_relations in grouped_relations:
        relation = pair_relations[0]
        bucket = _relation_bucket_for_type(relation.relation_type)
        grouped.setdefault(bucket, []).append(
            _format_relation_axis_entry(
                world,
                counterparty,
                relation,
                pair_relations[1:],
                label_overrides=label_overrides,
            )
        )

    if not grouped:
        return f"    {label}: None"

    priority = ["rivalry", "control", "covert", "alliance", "containment", "presence", "foothold", "other"]
    lines = [f"    {label}:"]
    used = 0
    for bucket in priority:
        entries = grouped.get(bucket)
        if not entries:
            continue
        lines.append(f"      - {_relation_bucket_label(bucket)}: {'；'.join(entries[:2])}")
        used += 1
        if used >= limit:
            break
    return "\n".join(lines)


def _format_relation_axis_entry(
    world: WorldState,
    counterparty: str,
    relation,
    shadow_relations: list,
    *,
    label_overrides: dict[str, str] | None = None,
) -> str:
    note_text = _humanize_relation_note(relation.notes)
    shadow_text = _relation_shadow_text(shadow_relations, relation.relation_type)
    target_label = label_overrides.get(counterparty, counterparty) if label_overrides else counterparty
    entity_text = (
        target_label
        if label_overrides and counterparty in label_overrides
        else _format_entity_ref(world, counterparty)
    )
    return _truth_relation_focus_entry(
        subject=entity_text,
        relation_type=relation.relation_type,
        strength=relation.strength,
        tick=relation.updated_tick,
        note=note_text,
        shadow=shadow_text,
    )


def _format_character_relation_front(world: WorldState, character: Character) -> str:
    relations = relations_for_ref(world, character.char_id, limit=12)
    if not relations and not character.relationship_refs:
        return "  relation_front: None"

    foothold_count = 0
    pressure_count = 0
    presence_count = 0
    tether_count = 0
    for relation in relations:
        bucket = _relation_bucket_for_type(relation.relation_type)
        if bucket == "foothold":
            foothold_count += 1
        elif bucket in {"rivalry", "control"}:
            pressure_count += 1
        elif bucket in {"presence", "containment", "covert"}:
            presence_count += 1
        else:
            tether_count += 1

    lines = ["  relation_front:"]
    lines.append(
        "    概述: "
        + _summarize_character_relation_front(
            character=character,
            foothold_count=foothold_count,
            pressure_count=pressure_count,
            presence_count=presence_count,
            tether_count=tether_count,
        )
    )
    lines.append(
        "    结构压力: "
        f"立足点={foothold_count}, 施压/争夺={pressure_count}, 异常牵引={presence_count}, 其余联结={tether_count}"
    )
    lines.append(
        "    关系气候: "
        + _relation_climate_text(
            rivalry_count=pressure_count,
            alliance_count=0,
            control_count=foothold_count,
            covert_count=presence_count,
        )
    )
    lines.append(_format_relation_axes_block(world, character.char_id, relations, label="当前牵引", limit=4))
    return "\n".join(lines)


def _parse_midlayer_note(note: str) -> tuple[int, str]:
    if note.startswith("tick_") and ":" in note:
        tick_part, payload = note.split(":", 1)
        try:
            return int(tick_part.removeprefix("tick_")), payload
        except ValueError:
            return -1, payload
    return -1, note


def _humanize_midlayer_note(
    payload: str,
    *,
    world: WorldState | None = None,
    focal_faction_id: str | None = None,
) -> str:
    mapping = {
        "resource_reallocation": "补给通道被重新改道",
        "project_bid": "项目执行权发生了转移",
        "budget_freeze": "预算通道被冻结",
        "financing_realignment": "融资控制链被重排",
        "site_accident_exploited": "现场事故被转化为施压筹码",
        "security_cordon_raised": "项目前线的安保封锁被收紧",
        "contract_scramble": "合同与预算归属开始混战",
        "emergency_lockdown_slowed_routing": "紧急封锁拖慢了运输路由",
        "quarantine_panic_disrupted_corridor": "隔离恐慌扰乱了补给走廊",
        "groundbreaking_started": "项目已正式破土开工",
        "phase_advance": "工程又向前推进了一个阶段",
        "grid_linked": "项目已接入更大的基础设施网络",
        "reactivation_window": "项目出现了重启窗口",
        "budget_crisis": "项目滑入预算危机",
        "construction_stall": "项目在压力下陷入停滞",
        "alliance_support": "联盟关系正在为补给前线提供支撑",
        "alliance_backing": "联盟关系正在为项目前线提供背书",
        "power_struggle_pressure": "争权冲突正在向这条前线传导压力",
        "infiltration_pressure": "渗透活动正在抬高这条前线的隐性风险",
        "control_contest": "控制权争夺已经压到项目本体",
        "control_secured": "控制权已经被重新压稳",
    }
    if "->" in payload:
        action, target = payload.split("->", 1)
        actor_hint = _midlayer_actor_hint(world, target, focal_faction_id=focal_faction_id)
        if action == "resource_reallocation":
            return f"补给改道已转向 {_midlayer_ref_display(world, target)}{actor_hint}"
        if action == "project_bid":
            return f"项目竞标结果向 {_midlayer_ref_display(world, target)}{actor_hint} 集中"
        if action == "budget_freeze":
            return f"预算冻结由 {_midlayer_ref_display(world, target)}{actor_hint} 推动"
        if action == "financing_realignment":
            return f"融资重排由 {_midlayer_ref_display(world, target)}{actor_hint} 推动"
        if action == "site_accident_exploited":
            return f"现场事故被 {_midlayer_ref_display(world, target)}{actor_hint} 利用"
        if action == "alliance_support":
            return f"联盟支撑已转向 {_midlayer_ref_display(world, target)}{actor_hint}"
        if action == "alliance_backing":
            return f"联盟背书正在向 {_midlayer_ref_display(world, target)}{actor_hint} 集中"
        if action == "power_struggle_pressure":
            return f"争权压力由 {_midlayer_ref_display(world, target)}{actor_hint} 推高"
        if action == "infiltration_pressure":
            return f"渗透压力由 {_midlayer_ref_display(world, target)}{actor_hint} 带入"
        if action == "control_contest":
            return f"控制权争夺由 {_midlayer_ref_display(world, target)}{actor_hint} 推到台前"
        if action == "control_secured":
            return f"控制权已被 {_midlayer_ref_display(world, target)}{actor_hint} 压稳"
    return mapping.get(payload, payload.replace("_", " "))


def _humanize_ref_token(token: str) -> str:
    return token.replace("_", " ")


def _midlayer_actor_hint(
    world: WorldState | None,
    actor_ref: str,
    *,
    focal_faction_id: str | None = None,
) -> str:
    if world is None:
        return ""
    faction = world.factions.get(actor_ref)
    if faction is None:
        return ""
    if focal_faction_id and faction.faction_id == focal_faction_id:
        return f"（以{_faction_type_midlayer_method(faction.faction_type)}方式）"
    return f"（{_faction_type_midlayer_role(faction.faction_type)}）"


def _faction_type_midlayer_role(faction_type: str) -> str:
    mapping = {
        "government": "行政控制方",
        "megacorp": "合同控制方",
        "security_force": "封控执行方",
        "research_institute": "技术解释方",
        "labor_union": "动员协调方",
        "network_cell": "暗线节点方",
        "infrastructure_consortium": "工程推进方",
        "data_cult": "信息垄断方",
        "civic_guild": "地方协商方",
        "logistics_syndicate": "物流调度方",
    }
    return mapping.get(faction_type, "相关组织")


def _faction_type_midlayer_method(faction_type: str) -> str:
    mapping = {
        "government": "行政压舱",
        "megacorp": "合同施压",
        "security_force": "封控收束",
        "research_institute": "技术接管",
        "labor_union": "协商动员",
        "network_cell": "暗线渗入",
        "infrastructure_consortium": "工程排期推进",
        "data_cult": "信息渗透",
        "civic_guild": "地方缝合协调",
        "logistics_syndicate": "路由重排",
    }
    return mapping.get(faction_type, "组织施压")


def _midlayer_theme(payload: str) -> str:
    return payload_midlayer_bucket(payload)


def _midlayer_theme_for_event(event: Event) -> str:
    return event_midlayer_bucket(event)


def _midlayer_theme_label(theme: str) -> str:
    labels = {
        "project_shifts": "项目变动",
        "supply_shocks": "补给冲击",
        "anomaly_surges": "异常波动",
        "security_clamps": "安保收口",
        "other_changes": "其他变化",
    }
    return labels.get(theme, theme)


def _midlayer_theme_conclusion(theme: str, items: list[tuple[int, str]]) -> str:
    if not items:
        return "当前相对平静"
    if theme == "project_shifts":
        joined = " ".join(text for _, text in items[:3])
        if "陷入停滞" in joined or "预算危机" in joined:
            return "项目前线明显失稳，并已进入高压状态"
        if "接入更大的基础设施网络" in joined or "推进了一个阶段" in joined or "破土开工" in joined:
            return "项目前线仍在推进，但推进过程带着压力"
        return "项目控制权与执行权正在持续变动"
    if theme == "supply_shocks":
        joined = " ".join(text for _, text in items[:3])
        if joined.count("扰乱了补给走廊") >= 2:
            return "补给走廊正在反复受扰，运输稳定性较差"
        if "拖慢了运输路由" in joined:
            return "补给路由正在被紧急管控拖慢"
        return "补给路线正在压力下被持续改道"
    if theme == "anomaly_surges":
        joined = " ".join(text for _, text in items[:3])
        if any(token in joined for token in {"突破", "外溢", "迁移", "扩张", "失衡"}):
            return "异常对象正在主动改写周边场域，压力已经开始向外扩散"
        if any(token in joined for token in {"压制", "封存", "夺取", "接管"}):
            return "异常对象的控制权正在被重排，局势仍未真正稳定"
        return "异常前线正在升温，局部秩序和解释权都在松动"
    if theme == "security_clamps":
        return "关键前线周围的安保姿态正在持续收紧"
    return "中层变化正在累积，但尚未形成稳定模式"


def _format_midlayer_grouped_entries(entries: list[tuple[int, str, str]]) -> str:
    if not entries:
        return "  midlayer_changes: None"
    grouped: dict[str, list[tuple[int, str]]] = {
        "project_shifts": [],
        "supply_shocks": [],
        "anomaly_surges": [],
        "security_clamps": [],
        "other_changes": [],
    }
    for tick, theme, text in _dedupe_midlayer_entries(entries):
        grouped.setdefault(theme, []).append((tick, text))

    primary_theme_count = sum(
        1
        for theme in ["project_shifts", "supply_shocks", "anomaly_surges", "security_clamps"]
        if grouped.get(theme)
    )
    lines = ["  midlayer_changes:"]
    for theme in [
        "project_shifts",
        "supply_shocks",
        "anomaly_surges",
        "security_clamps",
        "other_changes",
        ]:
        bucket = grouped.get(theme, [])
        if not bucket:
            continue
        if theme == "other_changes" and primary_theme_count > 0:
            lines.append(f"    {_midlayer_theme_label(theme)}:")
            lines.append("      概述: 杂项变化仍在累积，但当前主导局势的不是这一层")
            lines.append(f"      - {bucket[0][1]}")
            continue
        lines.append(f"    {_midlayer_theme_label(theme)}:")
        lines.append(f"      概述: {_midlayer_theme_conclusion(theme, bucket)}")
        for _, text in bucket[:4]:
            lines.append(f"      - {text}")
    if len(lines) == 1:
        return "  midlayer_changes: None"
    return "\n".join(lines)


def _dedupe_midlayer_entries(entries: list[tuple[int, str, str]]) -> list[tuple[int, str, str]]:
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[int, str, str]] = []
    for tick, theme, text in sorted(entries, key=lambda item: item[0], reverse=True):
        normalized = _normalize_midlayer_text(text)
        key = (theme, normalized)
        if key in seen:
            continue
        seen.add(key)
        unique.append((tick, theme, text))
    return unique


def _normalize_midlayer_text(text: str) -> str:
    if "] " in text:
        return text.split("] ", 1)[1]
    return text


def _event_midlayer_projection(world: WorldState, event: Event) -> str:
    focal_region = _format_entity_ref(world, event.region_refs[0]) if event.region_refs else "未知区域"
    if event.relic_refs:
        focal_object = ", ".join(_format_relic_refs(world, event.relic_refs[:1]))
    elif event.faction_refs:
        focal_object = _format_midlayer_actor_projection(world, event.faction_refs[0])
    else:
        focal_object = focal_region
    return (
        f"tick {event.tick}: {focal_object} "
        f"[强度={_player_level_value(event.severity)}, 地区={focal_region}] "
        f"{_humanize_faction_action_label(event.event_type)}"
    )


def _format_midlayer_actor_projection(world: WorldState, faction_id: str) -> str:
    faction = world.factions.get(faction_id)
    if faction is None:
        return faction_id
    return (
        f"{faction.name} ({faction.faction_id}, "
        f"{_faction_type_midlayer_role(faction.faction_type)})"
    )


def _project_faction_events_into_midlayer(world: WorldState, faction_id: str) -> list[tuple[int, str, str]]:
    entries: list[tuple[int, str, str]] = []
    for event in reversed(world.event_stream.recent(60)):
        if faction_id not in event.faction_refs:
            continue
        if not event.event_type.startswith("faction_"):
            continue
        entries.append(
            (
                event.tick,
                _midlayer_theme_for_event(event),
                _event_midlayer_projection(world, event),
            )
        )
        if len(entries) >= 6:
            break
    return entries


def _project_civ_events_into_midlayer(world: WorldState, civ_id: str) -> list[tuple[int, str, str]]:
    entries: list[tuple[int, str, str]] = []
    for event in reversed(world.event_stream.recent(80)):
        if civ_id not in event.civ_refs:
            continue
        if not event.event_type.startswith("faction_"):
            continue
        entries.append(
            (
                event.tick,
                _midlayer_theme_for_event(event),
                _event_midlayer_projection(world, event),
            )
        )
        if len(entries) >= 8:
            break
    return entries


def _format_faction_midlayer_changes(world: WorldState, faction_id: str) -> str:
    entries: list[tuple[int, str, str]] = []
    for project_id in _find_projects_for_faction(world, faction_id):
        project = world.projects.get(project_id)
        if project is None:
            continue
        for note in project.recent_notes[-3:]:
            tick, payload = _parse_midlayer_note(note)
            if tick < 0:
                continue
            entries.append(
                (
                    tick,
                    _midlayer_theme(payload),
                    f"tick {tick}: {_truth_project_brief(project)} "
                    f"{_humanize_midlayer_note(payload, world=world, focal_faction_id=faction_id)}",
                )
            )
    for supply_id in _find_supply_for_faction(world, faction_id):
        supply_line = world.supply_lines.get(supply_id)
        if supply_line is None:
            continue
        for note in supply_line.recent_notes[-3:]:
            tick, payload = _parse_midlayer_note(note)
            if tick < 0:
                continue
            entries.append(
                (
                    tick,
                    _midlayer_theme(payload),
                    f"tick {tick}: {_truth_supply_brief(supply_line)} "
                    f"{_humanize_midlayer_note(payload, world=world, focal_faction_id=faction_id)}",
                )
            )
    if not entries:
        entries.extend(_project_faction_events_into_midlayer(world, faction_id))
    return _format_midlayer_grouped_entries(entries[:12])


def _format_civilization_midlayer_changes(world: WorldState, civ_id: str) -> str:
    civ = world.civilizations.get(civ_id)
    if civ is None:
        return "  midlayer_changes: None"
    entries: list[tuple[int, str, str]] = []
    for project_id in civ.key_projects[:6]:
        project = world.projects.get(project_id)
        if project is None:
            continue
        for note in project.recent_notes[-3:]:
            tick, payload = _parse_midlayer_note(note)
            if tick < 0:
                continue
            entries.append(
                (
                    tick,
                    _midlayer_theme(payload),
                    f"tick {tick}: {_truth_project_brief(project)} "
                    f"{_humanize_midlayer_note(payload, world=world)}",
                )
            )
    for supply_id in civ.key_supply_lines[:6]:
        supply_line = world.supply_lines.get(supply_id)
        if supply_line is None:
            continue
        for note in supply_line.recent_notes[-3:]:
            tick, payload = _parse_midlayer_note(note)
            if tick < 0:
                continue
            entries.append(
                (
                    tick,
                    _midlayer_theme(payload),
                    f"tick {tick}: {_truth_supply_brief(supply_line)} "
                    f"{_humanize_midlayer_note(payload, world=world)}",
                )
            )
    if not entries:
        entries.extend(_project_civ_events_into_midlayer(world, civ_id))
    return _format_midlayer_grouped_entries(entries[:16])


def _format_region_ambient_people(world: WorldState, region_id: str, *, view: str) -> str:
    people = build_region_ambient_people(world, region_id, limit=3)
    if not people:
        return "  周边人物: 外界暂未看出稳定周边人物轮廓" if is_player_view(view) else "  周边人物: 暂未形成稳定一线人物轮廓"
    player_view = is_player_view(view)
    lines = ["  周边人物:"] if player_view else ["  周边人物:"]
    for person in people:
        if player_view:
            lines.append(
                f"    - {_player_ambient_role_value(person.role)} [{_player_ambient_stance_value(person.stance)}]"
            )
        else:
            lines.append(
                f"    - {person.handle}: {_player_ambient_role_value(person.role)} "
                f"[姿态={_player_ambient_stance_value(person.stance)}, 压力线={_truth_ambient_pressure_value(person.pressure_link)}]"
            )
            lines.append(f"      activity: {_truth_ambient_activity_value(world, person.activity)}")
    return "\n".join(lines)


def _format_region_ambient_details(world: WorldState, region_id: str, *, view: str) -> str:
    details = build_region_ambient_details(world, region_id, limit=3)
    if not details:
        return "  周边物件: 外界暂未看出稳定周边物件轮廓" if is_player_view(view) else "  周边物件: 暂未形成稳定周边物件轮廓"
    player_view = is_player_view(view)
    lines = ["  周边物件:"] if player_view else ["  周边物件:"]
    for detail in details:
        if player_view:
            lines.append(
                f"    - {_player_ambient_detail_type_value(detail.detail_type)} [{_player_ambient_condition_value(detail.condition)}]"
            )
        else:
            lines.append(
                f"    - {detail.label}: {_player_ambient_detail_type_value(detail.detail_type)} "
                f"[状态={_player_ambient_condition_value(detail.condition)}, 压力线={_truth_ambient_pressure_value(detail.pressure_link)}]"
            )
            lines.append(f"      note: {_truth_ambient_detail_note(world, detail.note)}")
    return "\n".join(lines)


def _format_faction_ambient_people(world: WorldState, faction_id: str, *, view: str) -> str:
    people = build_faction_ambient_people(world, faction_id, limit=6)
    unique_people = []
    seen_people: set[tuple[str, str]] = set()
    for person in people:
        key = (person.role, person.stance)
        if key in seen_people:
            continue
        seen_people.add(key)
        unique_people.append(person)
        if len(unique_people) >= 3:
            break
    people = unique_people
    if not people:
        return "  一线人物: 外界暂未看出稳定一线人物轮廓" if is_player_view(view) else "  local_operators: None"
    player_view = is_player_view(view)
    lines = ["  一线人物:"] if player_view else ["  local_operators:"]
    for person in people:
        if player_view:
            lines.append(
                f"    - {_player_ambient_role_value(person.role)} [{_player_ambient_stance_value(person.stance)}]"
            )
        else:
            lines.append(
                f"    - {person.handle}: {_player_ambient_role_value(person.role)} "
                f"[姿态={_player_ambient_stance_value(person.stance)}, 压力线={_truth_ambient_pressure_value(person.pressure_link)}]"
            )
            lines.append(f"      activity: {_truth_ambient_activity_value(world, person.activity)}")
    return "\n".join(lines)


def _format_relic_ambient_details(world: WorldState, relic_id: str, *, view: str) -> str:
    details = build_relic_ambient_details(world, relic_id, limit=3)
    if not details:
        return "  周边物件: 外界暂未看出稳定周边物件轮廓" if is_player_view(view) else "  周边物件: 暂未形成稳定周边物件轮廓"
    player_view = is_player_view(view)
    lines = ["  周边物件:"] if player_view else ["  周边物件:"]
    for detail in details:
        if player_view:
            lines.append(
                f"    - {_player_ambient_detail_type_value(detail.detail_type)} [{_player_ambient_condition_value(detail.condition)}]"
            )
        else:
            lines.append(
                f"    - {detail.label}: {_player_ambient_detail_type_value(detail.detail_type)} "
                f"[状态={_player_ambient_condition_value(detail.condition)}, 压力线={_truth_ambient_pressure_value(detail.pressure_link)}]"
            )
            lines.append(f"      note: {_truth_ambient_detail_note(world, detail.note)}")
    return "\n".join(lines)


def _format_character_knowledge_snapshot(world: WorldState, knowledge) -> str:
    if knowledge is None:
        return "  knowledge_snapshot: None"
    overview = knowledge.knowledge_overview()
    lines = ["  knowledge_snapshot:"]
    lines.append(
        "    overview: "
        f"direct={overview['direct_count']}, "
        f"rumored={overview['rumored_count']}, "
        f"public={overview['public_count']}, "
        f"visible_regions={overview['visible_region_count']}"
    )
    lines.append(
        "    flashpoint_region: "
        + (_format_entity_ref(world, overview["flashpoint_region_id"]) if overview["flashpoint_region_id"] else "None")
    )
    lines.append(
        "    visible_regions: "
        + (", ".join(_format_region_refs(world, knowledge.visible_region_ids[:6])) or "None")
    )
    lines.append(_format_knowledge_event_block(world, "direct", knowledge.direct_events[-4:], direct=True))
    lines.append(_format_knowledge_event_block(world, "rumored", knowledge.rumored_events[-4:], direct=False))
    lines.append(_format_knowledge_event_block(world, "public", knowledge.public_events[-4:], direct=False))
    return "\n".join(lines)


def _format_knowledge_event_block(
    world: WorldState,
    label: str,
    events: list[Event],
    *,
    direct: bool,
) -> str:
    lines = [f"    {label}_events:"]
    if not events:
        lines.append("      - None")
        return "\n".join(lines)
    for event in events:
        summary = event.summary if direct else format_event_summary_for_view(event, view="player", world=world)
        summary = _player_localize_text(world, summary)
        event_label = _player_event_type_label(event.event_type) if direct else _player_event_type_label(event.event_type)
        lines.append(f"      - [{event_label}] {summary}")
    return "\n".join(lines)


def _humanize_faction_style_trace_item(item: str) -> str:
    if item.startswith("bias_actions="):
        raw_actions = item.split("=", 1)[1]
        actions = [
            _humanize_faction_action_label(f"faction_{token.strip()}")
            for token in raw_actions.split(",")
            if token.strip()
        ]
        return "主要动作偏向: " + ("、".join(actions) if actions else "尚未稳定")
    if item.startswith("organization_logic="):
        logic = item.split("=", 1)[1]
        mapping = {
            "covert leverage and order shaping": "更偏向通过隐性杠杆塑形秩序",
            "security enforcement and compliance": "更偏向通过安保执行与合规压力推进",
            "contract capture and financial steering": "更偏向通过合同与资金链改写前线",
            "public coordination and civic bargaining": "更偏向通过公开协调与地方协商推进",
        }
        return "组织施力逻辑: " + mapping.get(logic, _humanize_enum_token(logic))
    if item.startswith("world_frame="):
        payload = item.split("=", 1)[1]
        parts = dict(
            segment.split(":", 1)
            for segment in payload.split("|")
            if ":" in segment
        )
        climates = parts.get("climates", "")
        fronts = parts.get("fronts", "")
        anomaly = parts.get("anomaly", "")
        rendered: list[str] = []
        if climates:
            rendered.append(
                "组织气候="
                + _truth_organization_climates_value([token for token in climates.split("/") if token])
            )
        if fronts:
            rendered.append(
                "前线重心="
                + "、".join(_truth_front_family_value(token) for token in fronts.split("/") if token)
            )
        if anomaly:
            rendered.append("异常牵引=" + _truth_front_family_value(anomaly))
        return "世界牵引框架: " + "；".join(rendered or [payload])
    if item.startswith("style_inertia="):
        payload = item.split("=", 1)[1]
        stability = payload.split("(", 1)[0]
        suffix = payload[len(stability):]
        stability_text = _humanize_enum_token(stability)
        if stability == "locked":
            stability_text = "已锁定"
        elif stability == "steady":
            stability_text = "基本稳定"
        elif stability == "contested":
            stability_text = "正在被争夺"
        elif stability == "redirected":
            stability_text = "刚被改道"
        elif stability == "forming":
            stability_text = "仍在成形"
        suffix = suffix.replace("pending=", "待转向=").replace("hits=", "积累=").replace("none", "无")
        return "风格惯性: " + stability_text + suffix
    return item


def _truth_civilization_bias_trace_item(world: WorldState, item: str) -> str:
    if item.startswith("world_frame="):
        payload = item.split("=", 1)[1]
        parts = dict(
            segment.split(":", 1)
            for segment in payload.split("|")
            if ":" in segment
        )
        rendered: list[str] = []
        axes = parts.get("axes", "")
        fronts = parts.get("fronts", "")
        anomaly = parts.get("anomaly", "")
        if axes:
            rendered.append(
                "压力轴="
                + _truth_pressure_axes_value([token for token in axes.split("/") if token])
            )
        if fronts:
            rendered.append(
                "前线重心="
                + "、".join(_truth_front_family_value(token) for token in fronts.split("/") if token)
            )
        if anomaly:
            rendered.append("异常牵引=" + _truth_front_family_value(anomaly))
        return "世界牵引: " + "；".join(rendered or [payload])
    if item.startswith("organization_climate="):
        climates = item.split("=", 1)[1]
        return "组织气候: " + _truth_organization_climates_value([token for token in climates.split("/") if token])
    if item.startswith("posture_inertia="):
        payload = item.split("=", 1)[1]
        stability = payload.split("(", 1)[0]
        suffix = payload[len(stability):]
        stability_text = {
            "crisis_locked": "危机锁定",
            "steady": "基本稳定",
            "contested": "正在被争夺",
            "redirected": "刚被改道",
            "forming": "仍在成形",
        }.get(stability, _humanize_enum_token(stability))
        suffix = suffix.replace("pending=", "待转向=").replace("hits=", "积累=").replace("none", "无")
        return "战略惯性: " + stability_text + suffix
    if item.startswith("recent_pull="):
        payload = item.split("=", 1)[1]
        if "@" in payload:
            event_type, target = payload.split("@", 1)
            target_text = "未知区域" if target == "unknown_region" else _format_entity_ref(world, target)
            return f"近期牵引: {_player_event_type_label(event_type)} -> {target_text}"
    return item


def _truth_civilization_strategy_memory_item(world: WorldState, item: str) -> str:
    tick, payload = _parse_midlayer_note(item)
    tick_prefix = f"tick {tick}: " if tick >= 0 else ""
    if "@" not in payload:
        return tick_prefix + payload
    action, target = payload.split("@", 1)
    target_text = "未知区域" if target == "unknown_region" else _format_entity_ref(world, target)
    if action.startswith("front_"):
        relation_type = action.removeprefix("front_")
        return f"{tick_prefix}前线牵引转向 {_truth_relation_type_value(relation_type)} -> {target_text}"
    if action.startswith("internal_"):
        relation_type = action.removeprefix("internal_")
        return f"{tick_prefix}内部关系转向 {_truth_relation_type_value(relation_type)} -> {target_text}"
    return f"{tick_prefix}{_player_event_type_label(action)} -> {target_text}"


def _truth_character_trace_item(item: str, world: WorldState | None = None) -> str:
    tick, payload = _parse_midlayer_note(item)
    tick_prefix = f"tick {tick}: " if tick >= 0 else ""
    if "|" in payload and "[event=" not in payload and "->" not in payload:
        action, event_name = payload.split("|", 1)
        normalized_action = action.strip().replace("_", " ")
        action_text = {
            "secure relic access": "反复转向争取异常接入权",
            "stabilize supply": "反复转向稳住补给节奏",
        }.get(normalized_action, _humanize_enum_token(normalized_action))
        normalized_event = event_name.strip().replace("_", " ")
        return tick_prefix + f"{{action_text}}".format(action_text=action_text) + f"，关联事件={_player_event_type_label(normalized_event.replace(' ', '_'))}"
    event_name = ""
    focal_ref = ""
    if "[event=" in payload:
        payload, event_part = payload.split("[event=", 1)
        if ", focal=" in event_part:
            event_name, focal_part = event_part.split(", focal=", 1)
            focal_ref = focal_part.rstrip("]")
        else:
            event_name = event_part.rstrip("]")
    payload = payload.strip()
    action = payload
    target_ref = ""
    if "->" in payload:
        action, target_ref = payload.split("->", 1)
    action = action.strip()
    target_ref = target_ref.strip()
    action_text = {
        "stabilize_supply": "转向稳住补给节奏",
        "secure_relic_access": "转向争取异常接入权",
    }.get(action, _humanize_enum_token(action))
    bits = [action_text]
    if target_ref:
        target_text = _format_entity_ref(world, target_ref) if world is not None else _humanize_enum_token(target_ref)
        bits.append(f"落点={target_text}")
    if event_name:
        bits.append(f"触发事件={_player_event_type_label(event_name.strip())}")
    if focal_ref:
        focal_text = _format_entity_ref(world, focal_ref) if world is not None else _humanize_enum_token(focal_ref)
        bits.append(f"焦点对象={focal_text}")
    return tick_prefix + "，".join(bits)


def _humanize_faction_style_memory_item(world: WorldState, item: str) -> str:
    tick, payload = _parse_midlayer_note(item)
    tick_prefix = f"tick {tick}: " if tick >= 0 else ""
    if "@" not in payload:
        return tick_prefix + payload
    action, target = payload.split("@", 1)
    target_text = _format_entity_ref(world, target)
    if action.startswith("relation_"):
        relation_type = action.removeprefix("relation_")
        return f"{tick_prefix}关系动作转向 {_truth_relation_type_value(relation_type)} -> {target_text}"
    if action.startswith("faction_"):
        action_label = _humanize_faction_action_label(action)
        return f"{tick_prefix}组织动作触发「{action_label}」于 {target_text}"
    return f"{tick_prefix}{payload}"


def _truth_ambient_pressure_value(pressure_link: str) -> str:
    mapping = {
        "contract capture": "合同截流",
        "covert leverage": "隐性杠杆",
        "containment control": "封控收束",
        "supply routing": "补给改道",
        "alignment maintenance": "联盟维护",
        "order management": "秩序压舱",
        "distributed local pressure": "分布式地方压力",
        "project corridor stress": "项目走廊压力",
        "biosecurity drift": "生物安防漂移",
        "disclosure panic": "披露恐慌",
        "system trust fracture": "系统信任裂缝",
        "ration strain": "配给紧绷",
        "brokered tension": "协商紧张",
        "supply leverage": "补给杠杆",
        "routine district pressure": "常态地区压力",
        "routine district wear": "常态地区磨损",
        "silent override risk": "静默越权风险",
    }
    return mapping.get(pressure_link, _humanize_enum_token(pressure_link))


def _truth_ambient_activity_value(world: WorldState, activity: str) -> str:
    localized = _player_localize_text(world, activity)
    role_mappings = {
        "salvage runner": "回收跑线人",
        "checkpoint clerk": "关卡文员",
        "perimeter scout": "外围哨探",
        "cargo scheduler": "货运调度员",
        "dock sentinel": "泊位哨卫",
        "customs fixer": "通关协调人",
    }
    for source, target in role_mappings.items():
        localized = localized.replace(source, target)
    if " is keeping a narrow contact chain alive in " in localized:
        _, tail = localized.split(" is keeping a narrow contact chain alive in ", 1)
        region_text = tail.split(" while testing which brokers can be bent.", 1)[0]
        return f"正在{region_text}一带维持一条收束的联络链，同时试探哪些中间人可以被压弯。"
    if " is trying to turn budget paperwork and execution bottlenecks in " in localized:
        _, tail = localized.split(" is trying to turn budget paperwork and execution bottlenecks in ", 1)
        region_text = tail.split(" into durable control.", 1)[0]
        return f"正试图把{region_text}的预算文书和执行瓶颈，转成可持续控制权。"
    if " is treating access, custody, and containment procedure as the real terrain of power in " in localized:
        _, tail = localized.split(" is treating access, custody, and containment procedure as the real terrain of power in ", 1)
        region_text = tail.rstrip(".")
        return f"正把{region_text}的接入、看管和封控流程，当成真正的权力地形。"
    if " is mapping storage, transport, and permit chokepoints in " in localized:
        _, tail = localized.split(" is mapping storage, transport, and permit chokepoints in ", 1)
        region_text = tail.split(" for later leverage.", 1)[0]
        return f"正在摸排{region_text}的仓储、运输和许可卡口，为后续施压做准备。"

    replacements = {
        " is quietly rerouting crews and permits around the live construction seam.": "正在围绕仍在运转的施工接缝，悄悄改动人手和许可流向。",
        " is treating movement logs and checkpoints as early warning tools against spread.": "正在把通行记录和检查点当成提前预警扩散的工具。",
        " is filtering names, records, and questions before they can harden into a public line.": "正在拦截名字、记录和问询，避免它们过早凝成公开叙事。",
        " is double-checking access channels and watching for silent override behavior.": "正在反复核对接入通道，并盯着是否出现静默越权。",
        " is trading favors and queues to keep shortages from becoming open disorder.": "正在通过人情和排队顺序换取缓冲，避免紧缺直接演成失序。",
        " is reacting to ": "正在应对 ",
        " without enough authority to fully control it.": "，但手里没有足够权限把局面彻底压住。",
        " is trying to turn budget paperwork and execution bottlenecks in ": "正试图把 ",
        " into durable control.": "里的预算文书和执行瓶颈，转成可持续控制权。",
        " is keeping a narrow contact chain alive in ": "正在 ",
        " while testing which brokers can be bent.": "维持一条收束的联络链，同时试探哪些中间人可以被压弯。",
        " is treating access, custody, and containment procedure as the real terrain of power in ": "正把 ",
        " as the real terrain of power in ": "视为真正的权力地形：",
        " is mapping storage, transport, and permit chokepoints in ": "正在摸排 ",
        " for later leverage.": "中的仓储、运输和许可卡口，为后续施压做准备。",
        " is moving through ": "正在穿行于 ",
        " is adjusting to ": "正在顺着 ",
        " around ": " 调整自身动作，围绕 ",
        " and waiting for a cleaner opening.": "等待更干净的切入口。",
        " with one eye on broker chains and one on loyalty shifts.": "，一边盯中间人链，一边盯忠诚流向。",
    }
    text = localized
    for source, target in replacements.items():
        text = text.replace(source, target)
    if "正在 " in text:
        text = text[text.index("正在 "):]
    return text


def _truth_ambient_detail_note(world: WorldState, note: str) -> str:
    localized = _player_localize_text(world, note)
    detail_mappings = {
        "fuel crate row": "燃料箱列",
        "checkpoint barrier": "关卡隔离栏",
        "access relay": "接入中继",
        "override cradle": "越权底座",
        "control sheath": "控制护套",
    }
    for source, target in detail_mappings.items():
        localized = localized.replace(source, target)
    replacements = {
        " is absorbing the ordinary wear of routine district wear in ": " 正在承受来自日常地区磨损的持续消耗，地点位于 ",
        " is treated as a possible path for hidden protocol authority.": " 被视为一条可能通向隐性协议控制权的入口。",
        " near ": " 靠近 ",
        "silent override risk": "静默越权风险",
    }
    text = localized
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _format_faction_operational_style_trace(world: WorldState, faction: Faction) -> str:
    lines = ["  风格轨迹:"]
    if faction.operational_style_trace:
        for item in faction.operational_style_trace[-5:]:
            lines.append(f"    - {_humanize_faction_style_trace_item(item)}")
    else:
        lines.append("    - 暂无稳定风格轨迹")
    if faction.operational_style_memory:
        lines.append("  风格记忆:")
        for item in faction.operational_style_memory[-5:]:
            lines.append(f"    - {_humanize_faction_style_memory_item(world, item)}")
    else:
        lines.append("  风格记忆: 暂未形成稳定记忆")
    return "\n".join(lines)


def _format_faction_operational_style_memory_summary(faction: Faction) -> str:
    if not faction.operational_style_memory:
        return "  风格记忆概述: 暂未形成稳定风格记忆"
    recent = " ".join(faction.operational_style_memory[-5:])
    if "relation_" in recent and "faction_" in recent:
        summary = "近期记忆同时包含组织动作和关系回流，说明其风格已不只是单点出手。"
    elif "relation_" in recent:
        summary = "近期记忆主要由关系回流构成，说明其施力方式正在向稳定关系结构沉淀。"
    elif "faction_" in recent:
        summary = "近期记忆主要由组织动作构成，说明其风格仍在通过重复动作固化。"
    else:
        summary = "近期记忆已开始积累，但还没有完全收束成单一组织习性。"
    return "  风格记忆概述: " + summary


def _format_character_hotspots(world: WorldState, character: Character, view: str = "truth") -> str:
    flashpoint_events = find_character_flashpoint_events(world, character, limit=4)
    flashpoint_region_id = find_relic_flashpoint_region(world, character)
    faction_refs = [faction_id for faction_id in character.affiliation if faction_id in world.factions]
    player_view = is_player_view(view)

    lines = ["  可见焦点:"] if player_view else ["  当前焦点:"]
    if flashpoint_region_id and flashpoint_region_id in world.regions:
        region = world.regions[flashpoint_region_id]
        lines.append(
            f"    主要地区: {_player_display_name(world, region.region_id)}"
            if player_view
            else f"    主要地区: {region.name} ({region.region_id})"
        )
        relic_event = find_recent_relic_event_for_region(world, region.region_id)
        if relic_event is not None:
            relic_names = (
                [_player_display_name(world, relic_id) for relic_id in relic_event.relic_refs]
                if player_view
                else _format_relic_refs(world, relic_event.relic_refs)
            )
            lines.append(
                f"    异常牵引: {', '.join(relic_names) or '未知异常'}"
                if player_view
                else f"    异常牵引: {', '.join(relic_names) or '未知异常'}（来源={_player_event_type_label(relic_event.event_type)}）"
            )
            lines.append(
                f"    异常线索: {_player_relic_reason_for_view(world, relic_event)}"
                if player_view
                else f"    异常缘由: {_format_truth_event_summary(world, relic_event)}"
            )
        else:
            lines.append("    异常牵引: None" if player_view else "    异常牵引: 暂未形成稳定异常牵引")
        lines.append(_format_character_front_clues(world, region.region_id) if player_view else _format_character_front_response(world, character, region.region_id))
    else:
        lines.append("    主要地区: None" if player_view else "    主要地区: 暂未出现稳定主地区")
        lines.append("    异常牵引: None" if player_view else "    异常牵引: 暂未形成稳定异常牵引")
        lines.append("    前线线索: None" if player_view else "    前线响应: 暂未形成稳定响应")

    if faction_refs:
        faction_summaries = []
        for faction_id in faction_refs[:3]:
            faction = world.factions[faction_id]
            faction_summaries.append(
                _player_display_name(world, faction_id)
                if player_view
                else f"{faction.name} ({faction.faction_id})"
            )
        lines.append(
            f"    组织牵引: {', '.join(faction_summaries)}"
            if player_view
            else f"    组织牵引: {', '.join(faction_summaries)}"
        )
    else:
        lines.append("    组织牵引: None" if player_view else "    组织牵引: 尚未出现稳定组织牵引")

    structural_focus = _format_character_structural_focus(world, character, player_view=player_view)
    if structural_focus:
        lines.append(structural_focus)

    if flashpoint_events:
        lines.append("    压力线索:" if player_view else "    压力链:")
        for event in flashpoint_events:
            if player_view:
                lines.append(f"      - [{_player_event_type_label(event.event_type)}] {_player_localize_text(world, _player_event_clue_for_view(world, event))}")
                continue
            focus_bits: list[str] = []
            if event.relic_refs:
                focus_bits.append("异常=" + ", ".join(_format_relic_refs(world, event.relic_refs)))
            if event.faction_refs:
                focus_bits.append("组织=" + ", ".join(_format_faction_refs(world, event.faction_refs[:2])))
            focus_text = f" [{'；'.join(focus_bits)}]" if focus_bits else ""
            lines.append(f"      - [{_player_event_type_label(event.event_type)}] {_format_truth_event_summary(world, event)}{focus_text}")
    else:
        lines.append("    压力线索: None" if player_view else "    压力链: 暂未积累成链")

    return "\n".join(lines)


def _format_character_structural_focus(
    world: WorldState,
    character: Character,
    *,
    player_view: bool,
) -> str:
    focus_ref = character.frontier_focus_ref
    focus_type = character.frontier_focus_type
    focus_block_label = "    可见结构牵引:" if player_view else "    结构牵引:"
    if focus_type == "project":
        project = world.projects.get(focus_ref)
        if project is None:
            return "    可见结构牵引: None" if player_view else "    结构牵引: 暂未形成稳定结构焦点"
        lines = [focus_block_label]
        if player_view:
            lines.append("      焦点类型: 项目线")
            lines.append(f"      焦点对象: {_player_project_name(project.name)}")
            lines.append(f"      当前态势: {_player_status_value(project.status)}")
            lines.append(f"      当前压力: {_player_pressure_band(project.pressure)}")
            lines.append("      前线线索: 外界能看出这条项目线正在牵住少数固定推进前线")
        else:
            lines.append("      焦点类型: 项目线")
            lines.append(f"      焦点对象: {project.name} ({project.project_id})")
            lines.append(f"      当前态势: {_player_status_value(project.status)}")
            lines.append(f"      当前压力: {_player_level_value(project.pressure)}")
            lines.append(f"      牵引前线: {_truth_tag_list_value(project.front_tags[:4], _player_front_tag_value, '前线标签尚不清晰')}")
        lines.append(
            "      牵引原因: 公开层面能看出角色正被这条项目线持续牵引"
            if player_view
            else f"      牵引原因: {_clean_character_focus_reason_text(character)}"
        )
        lines.append(
            f"      压力解读: 该项目当前呈{_player_pressure_band(project.pressure)}状态，公开层面已能感到推进压力"
            if player_view
            else f"      压力解读: {_project_pressure_text(project)}"
        )
        lines.extend(_format_structural_recent_changes(project.recent_notes, player_view=player_view, world=world))
        return "\n".join(lines)
    if focus_type == "supply":
        supply_line = world.supply_lines.get(focus_ref)
        if supply_line is None:
            return "    可见结构牵引: None" if player_view else "    结构牵引: 暂未形成稳定结构焦点"
        lines = [focus_block_label]
        if player_view:
            lines.append("      焦点类型: 补给线")
            lines.append(f"      焦点对象: {_player_supply_name(supply_line.name)}")
            lines.append(
                "      线路走向: "
                f"{_player_display_name(world, supply_line.origin_region_id)} -> "
                f"{_player_display_name(world, supply_line.destination_region_id)}"
            )
            lines.append(f"      当前态势: {_player_status_value(supply_line.status)}")
            lines.append(f"      当前压力: {_player_pressure_band(supply_line.pressure)}")
            lines.append(
                "      控制线索: "
                + (
                    _player_display_name(world, supply_line.controlling_faction_ref)
                    if supply_line.controlling_faction_ref
                    else "外界暂未看清稳定控制方"
                )
            )
        else:
            lines.append("      焦点类型: 补给线")
            lines.append(f"      焦点对象: {supply_line.name} ({supply_line.supply_id})")
            lines.append(
                "      线路走向: "
                f"{_format_entity_ref(world, supply_line.origin_region_id)} -> "
                f"{_format_entity_ref(world, supply_line.destination_region_id)}"
            )
            lines.append(f"      当前态势: {_player_status_value(supply_line.status)}")
            lines.append(f"      当前压力: {_player_level_value(supply_line.pressure)}")
            lines.append(
                "      控制方: "
                + (
                    _format_entity_ref(world, supply_line.controlling_faction_ref)
                    if supply_line.controlling_faction_ref
                    else "控制方尚未稳固"
                )
            )
        lines.append(
            "      牵引原因: 公开层面能看出角色正被这条补给线持续牵引"
            if player_view
            else f"      牵引原因: {_clean_character_focus_reason_text(character)}"
        )
        lines.append(
            f"      压力解读: 这条补给线当前呈{_player_pressure_band(supply_line.pressure)}状态，公开层面已能感到运输压力"
            if player_view
            else f"      压力解读: {_supply_pressure_text(supply_line)}"
        )
        lines.extend(_format_structural_recent_changes(supply_line.recent_notes, player_view=player_view, world=world))
        return "\n".join(lines)
    return ""


def _format_structural_recent_changes(
    notes: list[str],
    *,
    player_view: bool,
    world: WorldState | None = None,
) -> list[str]:
    if player_view:
        if not notes:
            return ["      近期变化线索: 外界暂未积累到连续结构波动"]
        return ["      近期变化线索: 外界已能感到这条结构线近期连续受扰，但施力细节仍不完全清楚"]
    if not notes:
        return ["      近期变化: 暂未记录到连续结构波动"]
    lines = ["      近期变化:"]
    for note in notes[-3:]:
        _, payload = _parse_midlayer_note(note)
        lines.append(f"        - {_clean_humanize_midlayer_note(payload, world=world)}")
    return lines


def _dedupe_recent_note_labels(world: WorldState | None, notes: list[str]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for note in notes:
        _, payload = _parse_midlayer_note(note)
        label = _clean_humanize_midlayer_note(payload, world=world)
        if label in seen:
            continue
        seen.add(label)
        labels.append(label)
    return labels


def _structural_recent_notes_summary(
    world: WorldState | None,
    notes: list[str],
    *,
    subject: str,
) -> str:
    if not notes:
        return "近期没有持续结构波动"
    labels = _dedupe_recent_note_labels(world, notes[-6:])
    joined = " ".join(labels)
    if subject == "project":
        if any(token in joined for token in {"预算危机", "陷入停滞", "安保封锁被收紧"}):
            return "该项目近期反复受压，推进链、预算链或安保壳层都出现了持续紧绷。"
        if any(token in joined for token in {"推进了一个阶段", "破土开工", "接入更大的基础设施网络"}):
            return "该项目近期仍在推进，但推进过程伴随明显牵制。"
        return "该项目近期存在连续变动，执行秩序没有完全稳住。"
    if any(token in joined for token in {"扰乱了补给走廊", "拖慢了运输路由"}):
        return "这条补给线近期反复受扰，运输与放行节奏已经持续承压。"
    if any(token in joined for token in {"资源改道", "获得盟友支撑"}):
        return "这条补给线近期正在被重新调度，控制方也在借外部支撑稳住线路。"
    return "这条补给线近期存在连续波动，但尚未进入完全断裂状态。"


def _project_pressure_text(project: ProjectNetwork) -> str:
    return _format_project_pressure_interpretation(project).split(": ", 1)[1]


def _supply_pressure_text(supply_line: SupplyLine) -> str:
    return _format_supply_pressure_interpretation(supply_line).split(": ", 1)[1]


def _clean_humanize_midlayer_note(payload: str, *, world: WorldState | None = None) -> str:
    mapping = {
        "resource_reallocation": "补给通道被重新改道",
        "project_bid": "项目执行权发生了转移",
        "budget_freeze": "预算通道被冻结",
        "financing_realignment": "融资控制链被重排",
        "site_accident_exploited": "现场事故被转化为施压筹码",
        "security_cordon_raised": "项目前线的安保封锁被收紧",
        "contract_scramble": "合同与预算归属开始混乱",
        "emergency_lockdown_slowed_routing": "紧急封锁拖慢了运输路由",
        "quarantine_panic_disrupted_corridor": "隔离恐慌扰乱了补给走廊",
        "groundbreaking_started": "项目已正式破土开工",
        "phase_advance": "工程又向前推进了一个阶段",
        "grid_linked": "项目已接入更大的基础设施网络",
        "reactivation_window": "项目出现了重启窗口",
        "budget_crisis": "项目滑入预算危机",
        "construction_stall": "项目在压力下陷入停滞",
        "alliance_support": "联盟关系正在为补给前线提供支撑",
        "alliance_backing": "联盟关系正在为项目线提供背书",
        "power_struggle_pressure": "争权冲突正在向这条前线传导压力",
        "infiltration_pressure": "渗透活动正在抬高这条前线的隐性风险",
        "control_contest": "控制权争夺已经压到项目本体",
        "control_secured": "控制权已经被重新压稳",
        "character_budget_secured": "角色出手稳住了预算链",
        "character_contract_contested": "角色直接下场争夺合同执行权",
        "character_financing_redirected": "角色重排了融资去向",
        "character_accident_suppressed": "角色压住了事故余波",
        "character_supply_stabilized": "角色出手稳定了补给节奏",
        "character_supply_leverage": "角色夺取了补给杠杆",
    }
    if "->" in payload:
        action, target = payload.split("->", 1)
        if action in mapping:
            return f"{mapping[action]}，施力方为 {_midlayer_ref_display(world, target)}"
    return mapping.get(payload, payload.replace("_", " "))


def _midlayer_ref_display(world: WorldState | None, token: str) -> str:
    if world is not None:
        return _format_entity_ref(world, token)
    return _humanize_ref_token(token)


def _player_civilization_posture(civilization: Civilization) -> str:
    mapping = {
        "containment_first": "更偏向先压住异常外溢与失控风险",
        "megastructure_expansion": "更偏向把资源压向工程和基础设施前线",
        "stability_over_growth": "更偏向先稳秩序，再谈扩张",
        "opportunistic_extraction": "更偏向从波动局势里攫取杠杆",
        "balanced_competition": "仍在多条线上同时试探",
    }
    return "  总体取向: " + mapping.get(civilization.strategic_posture, "公开层面只能看出其仍在多线调整")


def _truth_civilization_posture_value(posture: str) -> str:
    mapping = {
        "containment_first": "优先压住异常与失控风险",
        "megastructure_expansion": "优先把资源压向巨构与基础设施扩张",
        "stability_over_growth": "优先稳住秩序，再谈增长与外扩",
        "opportunistic_extraction": "优先把波动局势转成杠杆收益",
        "balanced_competition": "多线并行竞争，暂无绝对优先轴",
    }
    return mapping.get(posture, _humanize_enum_token(posture))


def _player_civilization_key_regions_hint(civilization: Civilization) -> str:
    count = len(civilization.key_regions)
    if count <= 0:
        return "  关键地区迹象: 外界暂未看出其稳定关键地区"
    if count == 1:
        return "  关键地区迹象: 外界能看出其当前重心压在 1 处关键地区"
    return f"  关键地区迹象: 外界可辨认出约 {_player_count_hint(count, '处关键地区')}"


def _player_civilization_key_factions_hint(civilization: Civilization) -> str:
    count = len(civilization.key_factions)
    if count <= 0:
        return "  核心组织迹象: 外界暂未看出其稳定核心组织层"
    if count == 1:
        return "  核心组织迹象: 外界能看出其有 1 个较清晰的核心执行组织"
    return f"  核心组织迹象: 外界已能辨认出约 {_player_count_hint(count, '个核心组织节点')}"


def _format_civilization_organization_model(world: WorldState, civilization: Civilization) -> str:
    project_count = len(civilization.key_projects)
    supply_count = len(civilization.key_supply_lines)
    faction_count = len(civilization.key_factions)
    external_count = len(civilization.external_relations)
    lines = ["  organization_model:"]
    lines.append(f"    governance_engine: {_civilization_governance_engine_label(civilization)}")
    lines.append(f"    execution_chain: {_civilization_execution_chain_label(project_count, supply_count, faction_count)}")
    lines.append(f"    territorial_base: {_civilization_territorial_base_label(civilization)}")
    lines.append(f"    risk_absorption: {_civilization_risk_absorption_label(civilization)}")
    lines.append(f"    external_posture: {_civilization_external_posture_label(external_count, civilization)}")
    return "\n".join(lines)


def _format_civilization_strategy_explanation(world: WorldState, civilization: Civilization) -> str:
    drivers: list[str] = []
    recent_events = [
        event.event_type
        for event in reversed(world.event_stream.recent(50))
        if civilization.civ_id in event.civ_refs
    ][:6]
    if civilization.key_projects:
        drivers.append("关键项目群正在给它提供少数可以持续押注的执行主轴")
    if civilization.key_supply_lines:
        drivers.append("补给骨架正在限制它能承受多大范围的前线外扩")
    if any(token in event_type for event_type in recent_events for token in {"archive", "protocol", "lifeform", "migration"}):
        drivers.append("异常前线的持续扰动正在不断把战略注意力拉回治理与收束")
    if civilization.legitimacy == "low":
        drivers.append("合法性偏低使它更难采用高风险外扩，只能先稳住内部秩序")
    if not drivers and civilization.strategic_posture == "balanced_competition":
        drivers.append("目前没有单一前线足够压倒其他方向，所以长期策略仍保持多线试探")
    elif not drivers:
        drivers.append("当前长期策略主要被既有组织惯性维持，外部约束尚未逼出新的主导方向")
    return "  strategy_explanation: " + "；".join(dict.fromkeys(drivers))


def _civilization_execution_transition_text(
    *,
    civilization: Civilization,
    project_entries: list[tuple[str, int]],
    supply_entries: list[tuple[str, int]],
) -> str:
    if civilization.strategic_posture == "stability_over_growth":
        if project_entries and not supply_entries:
            return "维稳优先的长期策略，正在被翻译成对少数高压项目节点的重点守控。"
        if supply_entries and not project_entries:
            return "维稳优先的长期策略，正在被翻译成对关键补给节奏的优先收束。"
    if civilization.strategic_posture == "megastructure_expansion" and project_entries:
        return "扩张型长期策略已经明显下传到工程执行面，项目节点成为现实主轴。"
    if civilization.strategic_posture == "containment_first":
        return "封控优先的长期策略，正在把执行主轴往异常前线和收束节点压。"
    if project_entries and supply_entries:
        return "长期策略已经不只停留在姿态层，而是同时压进工程与补给两套执行骨架。"
    if project_entries:
        return "长期策略当前主要通过项目节点下传到执行面。"
    if supply_entries:
        return "长期策略当前主要通过补给节点下传到执行面。"
    return "长期策略仍更多停留在组织姿态层，执行主轴尚未完全坐实。"


def _player_civilization_fronts(world: WorldState, civilization: Civilization) -> str:
    return (
        "  前线体感: "
        f"外界可辨认出 {max(1, min(3, len(civilization.key_regions)))} 条以上重要前线，"
        f"整体体感偏{_player_pressure_band(civilization.scarcity_pressure if civilization.scarcity_pressure == 'high' else civilization.expansion_pressure)}"
    )


def _player_civilization_bias_effects(civilization: Civilization) -> str:
    return "  外显偏向: 公开层面能看出其资源投放和组织动作正在向少数关键线集中"


def _player_civilization_strategy_explanation(civilization: Civilization) -> str:
    return "  策略解读: 外界能感到其长期策略并非随机摇摆，而是在少数关键风险和结构约束之间反复取舍"


def _player_civilization_project_networks(world: WorldState, civilization: Civilization) -> str:
    if not civilization.key_projects:
        fallback_count = len(_project_civ_project_events(world, civilization.civ_id))
        if fallback_count > 0:
            return f"  项目线索: 外界已能感到约 {_player_count_hint(fallback_count, '条项目压力线')}"
        return "  项目线索: 外界暂未辨认出稳定项目网络"
    return f"  项目线索: 外界已能辨认出 {_player_count_hint(len(civilization.key_projects), '条项目线')}"


def _player_civilization_supply_fronts(world: WorldState, civilization: Civilization) -> str:
    if not civilization.key_supply_lines:
        fallback_count = len(_project_civ_supply_events(world, civilization.civ_id))
        if fallback_count > 0:
            return f"  补给线索: 外界已能感到约 {_player_count_hint(fallback_count, '条补给压力线')}"
        return "  补给线索: 外界暂未辨认出稳定补给前线"
    return f"  补给线索: 外界已能辨认出 {_player_count_hint(len(civilization.key_supply_lines), '条补给线')}"


def _player_civilization_execution_front_overview(
    world: WorldState,
    civilization: Civilization,
) -> str:
    project_count = len(civilization.key_projects)
    supply_count = len(civilization.key_supply_lines)
    if project_count <= 0 and supply_count <= 0:
        return "  执行主轴: 外界暂未辨认出其稳定执行主轴"
    if project_count <= 0:
        return (
            "  执行主轴: "
            f"外界能看出其正在主要调度 {_player_count_hint(supply_count, '条补给线')}，"
            "执行重心已向少数关键运输节点收束"
        )
    if supply_count <= 0:
        return (
            "  执行主轴: "
            f"外界能看出其正在主要调度 {_player_count_hint(project_count, '条项目线')}，"
            "执行重心已向少数关键工程节点收束"
        )
    return (
        "  执行主轴: "
        f"外界能看出其正在同时调度约 {_player_count_hint(project_count, '条项目线')} 与 "
        f"{_player_count_hint(supply_count, '条补给线')}，执行重心已向少数关键节点收束"
    )


def _player_civilization_relation_front(world: WorldState, civilization: Civilization) -> str:
    allied_count = 0
    rival_count = 0
    relation_count = 0
    for faction_id in civilization.key_factions[:4]:
        relations = relations_for_ref(world, faction_id, limit=4)
        relation_count += len(relations)
        for relation in relations:
            if relation.relation_type in {"allied_with", "supports", "supporting", "sponsoring", "financing"}:
                allied_count += 1
            elif relation.relation_type in {"rival_to", "contesting", "obstructing", "opposing"}:
                rival_count += 1
    if relation_count <= 0:
        return "  关系态势: 外界尚未看出清晰的关系阵列"
    if allied_count > 0 and rival_count > 0 and relation_count >= 8:
        return "  关系态势: 公开层面已能看出其内部外部关系同时升温，像一张持续收紧的关系网"
    if rival_count > 0 and allied_count <= 0:
        return "  关系态势: 外界更容易先看到它与外部或内部对手的摩擦在升高"
    if allied_count > 0 and rival_count <= 0:
        return "  关系态势: 外界更容易先看到它正借少数稳定协作关系稳住局势"
    if relation_count >= 8:
        return "  关系态势: 公开层面能感到其关系网络正在变厚，但合作与对抗的主次仍未完全显形"
    return "  关系态势: 公开层面能感到联盟与对抗关系正在同时增厚"


def _player_civilization_external_relations(world: WorldState, civilization: Civilization) -> str:
    count = len(civilization.external_relations)
    if count <= 0:
        return "  外部接口: 外界暂未辨认出稳定外部接口"
    if count >= 4:
        return "  外部接口: 外界已能看出其同时牵着多条外部接口，组织边界并不封闭"
    return "  外部接口: 外界能看出其存在少数持续外部接口，但对象与方向仍不透明"


def _player_civilization_dependency_chain(world: WorldState, civilization: Civilization) -> str:
    project_count = len(civilization.key_projects)
    supply_count = len(civilization.key_supply_lines)
    if project_count <= 0 and supply_count <= 0:
        return "  依赖迹象: 外界暂未看出其存在稳定结构依赖"
    if project_count >= 1 and supply_count >= 1:
        return "  依赖迹象: 外界能看出其运行已经同时挂在项目与补给骨架上"
    if project_count >= 1:
        return "  依赖迹象: 外界能看出其动作明显依赖少数关键项目节点"
    return "  依赖迹象: 外界能看出其动作明显依赖少数关键补给线路"


def _player_civilization_sponsorship_chain(world: WorldState, civilization: Civilization) -> str:
    relation_count = 0
    for faction_id in civilization.key_factions[:6]:
        relation_count += sum(
            1
            for relation in relations_for_ref(world, faction_id, limit=6)
            if relation.relation_type in {"sponsoring", "financing", "allied_with", "supports", "supporting"}
        )
    if relation_count <= 0:
        return "  背书迹象: 外界暂未看出稳定背书链"
    if relation_count >= 4:
        return "  背书迹象: 外界能看出其背书、融资与协作链正在互相缠绕"
    return "  背书迹象: 外界能感到其背后存在有限但持续的支撑链"


def _player_civilization_region_anchors(world: WorldState, civilization: Civilization) -> str:
    region_count = len(civilization.key_regions)
    if region_count <= 0:
        return "  地区锚点: 外界暂未看出其稳定锚点"
    if region_count >= 4:
        return "  地区锚点: 外界已能辨认出多个持续受其影响的关键地区"
    return "  地区锚点: 外界能看出其影响力正压在少数关键地区上"


def _player_civilization_organization_model(civilization: Civilization) -> str:
    lines = ["  组织轮廓:"]
    lines.append("    治理核心: 外界能看出其有一套稳定治理核心在推动全局")
    if civilization.key_projects or civilization.key_supply_lines:
        lines.append("    执行链路: 外界能看出其会把前线压力转成项目与补给调度")
    else:
        lines.append("    执行链路: 外界暂未看出其稳定执行链")
    lines.append("    控制重心: 外界能感到其控制重心正向少数关键地区收束")
    lines.append("    吸震方式: 外界能看出其仍在试图把冲击挡在组织外层")
    return "\n".join(lines)


def _player_civilization_memory(civilization: Civilization) -> str:
    if not civilization.strategic_memory:
        return "  近期惯性: 公开层面还看不出稳定战略惯性"
    if len(civilization.strategic_memory) >= 6:
        return "  近期惯性: 外界已能感到其近期数步动作在反复沿着同一压力方向累积"
    return "  近期惯性: 外界已能感到其最近数步动作存在持续惯性"


def _player_civilization_posture_stability_hint(civilization: Civilization) -> str:
    return "  方向稳定度: 外界能感到其总体方向正在趋稳，但细部调整仍在继续"


def _player_civilization_posture_pending_hint(civilization: Civilization) -> str:
    if civilization.expansion_trend == "rising" or civilization.scarcity_trend == "rising":
        return "  转向征兆: 外界能感到其正在酝酿下一轮资源或前线重排"
    return "  转向征兆: 外界暂未看出其即将发生明显战略转向"


def _player_civilization_posture_pending_hits_hint(civilization: Civilization) -> str:
    return "  转向积累: 外界只能感到某些推动力正在累积，但还不足以坐实转向"


def _player_civilization_midlayer_changes_hint(world: WorldState, civilization: Civilization) -> str:
    if civilization.key_projects or civilization.key_supply_lines:
        return "  中层波动: 外界能看到其项目、补给或组织前线近期都在持续波动"
    return "  中层波动: 外界能感到中层结构正在变化，但还没有显出稳定轮廓"


def _player_faction_style(faction: Faction) -> str:
    mapping = {
        "discipline_network": "行事偏隐蔽、持续施压",
        "contract_predator": "更常围绕项目、预算和执行秩序发力",
        "containment_cadre": "更常围绕封控和压制外溢发力",
        "extraction_broker": "更常围绕资源与补给杠杆发力",
        "adaptive_network": "动作更灵活，偏机会主义调整",
    }
    return mapping.get(faction.operational_style, "公开层面只能看出其动作风格正在成形")


def _format_faction_behavior_signature(world: WorldState, faction: Faction) -> str:
    recent_events = [
        event
        for event in world.event_stream.recent(60)
        if faction.faction_id in event.faction_refs and event.event_type.startswith("faction_")
    ][-6:]
    lines = ["  behavior_signature:"]
    lines.append(f"    default_method: {_faction_default_method_text(faction)}")
    lines.append(f"    preferred_levers: {_faction_preferred_levers_text(faction)}")
    lines.append(
        "    strategy_to_action: "
        + _faction_behavior_transition_text(world, faction, recent_events)
    )
    if recent_events:
        lines.append(
            "    recent_pattern: "
            + ", ".join(_humanize_faction_action_label(event.event_type) for event in recent_events[-3:])
        )
    else:
        lines.append("    recent_pattern: 尚未积累到足够组织动作")
    return "\n".join(lines)


def _faction_default_method_text(faction: Faction) -> str:
    type_map = {
        "government": "更倾向借行政位阶、秩序收束和地区控制来推进目标",
        "megacorp": "更倾向借合同、预算和执行链条来争夺控制权",
        "security_force": "更倾向借封控、安保与强制稳定来压制波动",
        "research_institute": "更倾向借试验权限、知识解释权和技术节点来扩张影响",
        "labor_union": "更倾向借基层动员、协商压力和生产节点来施力",
        "network_cell": "更倾向借渗透、节点串联和灰色协调来推进目标",
        "infrastructure_consortium": "更倾向借工程推进、维护协调和建设排期来夺取主动",
        "data_cult": "更倾向借档案控制、信号解释和隐性渗透来塑造局势",
        "civic_guild": "更倾向借地方协商、秩序缝合和服务分配来稳住影响力",
        "logistics_syndicate": "更倾向借路由调度、仓储放行和运输节奏来握住杠杆",
    }
    return type_map.get(faction.faction_type, "更倾向通过重复组织动作逐步扩大影响")


def _faction_preferred_levers_text(faction: Faction) -> str:
    style_map = {
        "discipline_network": "渗透、争权、持续压迫局部秩序",
        "contract_predator": "项目竞标、预算冻结、融资抽离",
        "containment_cadre": "封控、争夺异常控制权、压制外溢",
        "extraction_broker": "资源调配、运输改道、资金杠杆",
        "adaptive_network": "结盟、试探、局部换边和机会主义再布局",
    }
    return style_map.get(faction.operational_style, "组织杠杆仍在形成中")


def _faction_behavior_transition_text(world: WorldState, faction: Faction, recent_events: list[Event]) -> str:
    recent_types = [event.event_type for event in recent_events[-3:]]
    if faction.operational_style == "discipline_network":
        if any("power_struggle" in event_type for event_type in recent_types):
            return "长期渗透和布线策略，当前正被翻译成更直接的争权动作。"
        return "长期渗透取向让它更偏好先布线、再逐步抬高公开压力。"
    if faction.operational_style == "contract_predator":
        return "长期围绕合同和预算取势的策略，正在不断下传为项目与融资动作。"
    if faction.operational_style == "containment_cadre":
        return "长期封控优先的策略，正在下传为压制外溢和收紧前线的具体动作。"
    if faction.operational_style == "extraction_broker":
        return "长期资源杠杆取向，正在下传为补给改道、资金抽离和机会性调度。"
    return "长期机动试探的策略，正在被翻译成结盟、换边和局部试压。"


def _faction_type_signature(faction_type: str) -> str:
    mapping = {
        "government": "偏行政治理与合法性维持的常规统治组织",
        "megacorp": "偏合同、资产与执行权控制的商业组织",
        "security_force": "偏安保、封控与风险压制的强制组织",
        "research_institute": "偏知识生产、系统试验与技术解释权的研究组织",
        "labor_union": "偏基层动员、生产协商与分配谈判的群体组织",
        "network_cell": "偏隐蔽渗透、灰色协调与节点施压的轻网络组织",
        "infrastructure_consortium": "偏工程整合、维护协调与跨区建设推进的重执行组织",
        "data_cult": "偏档案、信号、记忆与解释权垄断的半信念型组织",
        "civic_guild": "偏市政协商、地方服务与秩序缝合的城市中介组织",
        "logistics_syndicate": "偏物流路由、仓储放行与运输杠杆的补给型组织",
    }
    return mapping.get(faction_type, faction_type)


def _format_faction_organization_model(world: WorldState, faction: Faction) -> str:
    project_count = len(_find_projects_for_faction(world, faction.faction_id))
    supply_count = len(_find_supply_for_faction(world, faction.faction_id))
    lines = ["  organization_model:"]
    lines.append(f"    organizational_niche: {_faction_type_signature(faction.faction_type)}")
    lines.append(f"    command_shape: {_faction_command_shape_label(faction)}")
    lines.append(f"    execution_base: {_faction_execution_base_label(faction, project_count, supply_count)}")
    lines.append(f"    pressure_method: {_faction_pressure_method_label(faction)}")
    lines.append(f"    dependency_profile: {_faction_dependency_profile_label(project_count, supply_count, faction)}")
    lines.append(f"    stability_state: {_faction_stability_state_label(faction)}")
    return "\n".join(lines)


def _format_faction_strategy_explanation(world: WorldState, faction: Faction) -> str:
    drivers: list[str] = []
    recent_events = [
        event.event_type
        for event in reversed(world.event_stream.recent(40))
        if faction.faction_id in event.faction_refs and event.event_type.startswith("faction_")
    ][:5]
    if _find_projects_for_faction(world, faction.faction_id):
        drivers.append("项目节点正在给它提供把抽象影响力落到现实结构上的稳定入口")
    if _find_supply_for_faction(world, faction.faction_id):
        drivers.append("补给线接口正在决定它能把施压延伸到多远")
    if any(token in event_type for event_type in recent_events for token in {"infiltration", "power_struggle", "alliance"}):
        drivers.append("近期组织动作正在把既有打法继续固化成可重复的施力路径")
    if faction.influence_trend == "rising":
        drivers.append("影响力上升让它更有动力把短期动作沉淀成长期组织习性")
    if not drivers and faction.operational_style == "adaptive_network":
        drivers.append("当前没有哪条结构线足够稳固，所以它仍保留较高机动性和换挡空间")
    elif not drivers:
        drivers.append("当前长期组织策略主要靠既有风格惯性维持，还没有被新约束彻底改写")
    return "  strategy_explanation: " + "；".join(dict.fromkeys(drivers))


def _faction_execution_transition_text(
    *,
    faction: Faction,
    project_entries: list[tuple[str, int]],
    supply_entries: list[tuple[str, int]],
) -> str:
    if project_entries and not supply_entries:
        return "它的长期组织打法正在优先借项目或异常节点落地，因此执行面先收束到工程主轴。"
    if supply_entries and not project_entries:
        return "它的长期组织打法更依赖线路和放行节点，因此执行面先收束到补给主轴。"
    if project_entries and supply_entries:
        return "它的长期组织打法已经不只停留在关系层，正在同时压到项目和补给两类现实结构上。"
    if faction.operational_style == "discipline_network":
        return "它的长期组织打法仍偏向关系渗透，执行主轴暂未完全固化到具体结构。"
    return "它的长期组织打法正在寻找更稳定的结构落点，执行主轴尚未完全坐实。"


def _player_faction_project_fronts(world: WorldState, faction: Faction) -> str:
    project_count = len(_find_projects_for_faction(world, faction.faction_id))
    if project_count <= 0:
        fallback_project_entries, fallback_anomaly_entries = _project_faction_front_events(
            world,
            faction.faction_id,
        )
        fallback_count = len(fallback_project_entries) + len(fallback_anomaly_entries)
        if fallback_count > 0:
            return f"  项目施力线: 外界已能感到约 {_player_count_hint(fallback_count, '条项目或异常施力线')}"
        return "  项目施力线: 外界暂未看出其稳定项目施力点"
    return f"  项目施力线: 外界已能辨认出 {_player_count_hint(project_count, '条项目施力线')}"


def _player_faction_supply_fronts(world: WorldState, faction: Faction) -> str:
    supply_count = len(_find_supply_for_faction(world, faction.faction_id))
    if supply_count <= 0:
        fallback_count = len(_project_faction_supply_events(world, faction.faction_id))
        if fallback_count > 0:
            return f"  补给施力线: 外界已能感到约 {_player_count_hint(fallback_count, '条补给施力线')}"
        return "  补给施力线: 外界暂未看出其稳定补给施力点"
    return f"  补给施力线: 外界已能辨认出 {_player_count_hint(supply_count, '条补给施力线')}"


def _player_faction_execution_front_overview(world: WorldState, faction: Faction) -> str:
    project_count = len(_find_projects_for_faction(world, faction.faction_id))
    supply_count = len(_find_supply_for_faction(world, faction.faction_id))
    if project_count <= 0 and supply_count <= 0:
        return "  执行主轴: 外界暂未看出其稳定执行主轴"
    if project_count <= 0:
        return (
            "  执行主轴: "
            f"外界能看出其把施力点压在约 {_player_count_hint(supply_count, '条补给线')}上，"
            "执行动作已向少数关键运输节点收束"
        )
    if supply_count <= 0:
        return (
            "  执行主轴: "
            f"外界能看出其把施力点压在约 {_player_count_hint(project_count, '条项目线')}上，"
            "执行动作已开始向少数关键工程前线收束"
        )
    return (
        "  执行主轴: "
        f"外界能看出其把施力点压在约 {_player_count_hint(project_count, '条项目线')}与 "
        f"{_player_count_hint(supply_count, '条补给线')}上，执行动作已开始向少数关键前线收束"
    )


def _player_faction_midlayer_changes(world: WorldState, faction: Faction) -> str:
    return "  中层波动: 外界能看到其近期动作开始落到具体前线上，但细节仍不透明"


def _player_faction_strategy_explanation(faction: Faction) -> str:
    return "  策略解读: 外界能看出其并非随机出手，而是在重复某种稳定组织打法"


def _player_faction_controlled_regions_hint(faction: Faction) -> str:
    count = len(faction.controlled_regions)
    if count <= 0:
        return "  地区落点: 外界暂未看出其稳定控制落点"
    if count == 1:
        return "  地区落点: 外界能看出其当前稳定压住 1 处地区落点"
    return f"  地区落点: 外界已能辨认出约 {_player_count_hint(count, '处稳定落点')}"


def _player_faction_relation_front(world: WorldState, faction: Faction) -> str:
    ally_count = len(faction.allied_factions)
    rival_count = len(faction.rival_factions)
    if rival_count <= 0 and ally_count <= 0:
        return "  关系态势: 外界尚未看出稳定联盟或敌对关系"
    if rival_count >= 2 and ally_count >= 1:
        return "  关系态势: 公开层面能看出其已卷入多方关系缠斗，合作与对抗同时存在"
    if rival_count >= 2:
        return "  关系态势: 公开层面更容易先看到它与多方对手持续摩擦，关系面明显发紧"
    if ally_count >= 2 and rival_count <= 0:
        return "  关系态势: 公开层面能看出其正在借少数稳定协作关系扩张影响"
    if ally_count >= 1 and rival_count >= 1:
        return "  关系态势: 公开层面能看出其同时处在合作与对抗网络里"
    if rival_count >= 1:
        return "  关系态势: 外界能看出其已被卷入至少一条明确敌对线"
    return "  关系态势: 外界能看出其正借有限盟友或背书关系稳住行动空间"


def _player_faction_dependency_chain(world: WorldState, faction: Faction) -> str:
    project_count = len(_find_projects_for_faction(world, faction.faction_id))
    supply_count = len(_find_supply_for_faction(world, faction.faction_id))
    if project_count <= 0 and supply_count <= 0:
        fallback_project_entries, fallback_anomaly_entries = _project_faction_front_events(world, faction.faction_id)
        fallback_supply = _project_faction_supply_events(world, faction.faction_id)
        if not fallback_project_entries and not fallback_anomaly_entries and not fallback_supply:
            return "  依赖迹象: 外界暂未看出其稳定依赖链"
        return "  依赖迹象: 外界能看出其动作开始反复挂在少数前线节点上"
    if project_count >= 1 and supply_count >= 1:
        return "  依赖迹象: 外界能看出其既依赖项目推进，也依赖补给调度"
    if project_count >= 1:
        return "  依赖迹象: 外界能看出其明显挂靠在少数项目节点上"
    return "  依赖迹象: 外界能看出其明显挂靠在少数补给节点上"


def _player_faction_sponsorship_chain(world: WorldState, faction: Faction) -> str:
    relation_count = sum(
        1
        for relation in relations_for_ref(world, faction.faction_id, limit=12)
        if relation.relation_type in {"sponsoring", "financing", "allied_with", "supports", "supporting"}
    )
    if relation_count <= 0:
        return "  背书迹象: 外界暂未看出稳定背书链"
    if relation_count >= 3:
        return "  背书迹象: 外界能感到其背后存在多重背书或协作支撑"
    return "  背书迹象: 外界能看出其并非单独行动，但支撑链仍只露出少数接口"


def _player_faction_region_anchors(world: WorldState, faction: Faction) -> str:
    if not faction.controlled_regions:
        return "  地区锚点: 外界暂未看出其稳定落点"
    if len(faction.controlled_regions) >= 3:
        return "  地区锚点: 外界已能辨认出其在多个地区拥有稳定落点"
    return "  地区锚点: 外界能看出其影响力正压在少数固定地区上"


def _player_faction_memory_hint(faction: Faction) -> str:
    if not faction.operational_style_memory:
        return "  行动惯性: 外界暂未看出其存在稳定行动惯性"
    if len(faction.operational_style_memory) >= 6:
        return "  行动惯性: 外界已能感到其近几轮动作在反复沿着同一组织习性展开"
    return "  行动惯性: 外界能感到其最近动作里已经出现重复的组织习性"


def _player_faction_organization_model(faction: Faction) -> str:
    lines = ["  组织轮廓:"]
    lines.append("    生态位置: 外界已能看出其大致扮演的组织生态位")
    if faction.controlled_regions:
        lines.append("    指挥形态: 外界能看出其存在稳定指挥核心和固定活动底盘")
    else:
        lines.append("    指挥形态: 外界看出其更像游移网络，而非厚重机构")
    if faction.rival_factions or faction.allied_factions:
        lines.append("    施压方式: 外界能看出其通过关系网络而非单点行动施压")
    else:
        lines.append("    施压方式: 外界暂未看出其成熟施压模式")
    lines.append("    稳定程度: 外界能感到其组织风格正在逐步固化")
    return "\n".join(lines)


def _player_faction_stability_hint(faction: Faction) -> str:
    return "  风格稳定度: 外界能感到其动作风格正在逐步固化"


def _player_faction_pending_style_hint(faction: Faction) -> str:
    if faction.influence_trend == "rising":
        return "  风格换挡征兆: 外界能感到其施力方式还在继续加码或外扩"
    return "  风格换挡征兆: 外界暂未看出其动作风格即将发生明显换挡"


def _player_faction_pending_hits_hint(faction: Faction) -> str:
    return "  风格积累: 外界只能感到某些触发条件在累积，但还不足以看清变化方向"


def _player_character_relation_front(world: WorldState, character: Character) -> str:
    relation_count = len(relations_for_ref(world, character.char_id, limit=8))
    if relation_count <= 0 and not character.relationship_refs:
        return "  关系态势: 外界暂未看出此人形成稳定关系前线"
    if character.frontier_focus_type == "presence":
        return "  关系态势: 外界能看出此人与某类异常目标之间存在持续牵引"
    if character.frontier_focus_type in {"project", "supply"}:
        return "  关系态势: 外界能看出此人的关系动作正向一条具体前线收束"
    if relation_count >= 4:
        return "  关系态势: 外界已能辨认出此人正在多个落点间反复布线和施压"
    return "  关系态势: 外界能看出此人已经形成若隐若现的稳定牵引"


def _player_character_last_intent_hint(character: Character) -> str:
    if character.frontier_focus_type in {"project", "supply", "presence"}:
        return "  最近意图迹象: 外界能看出此人的最近动作正围绕一条具体前线收束"
    if character.notoriety == "high":
        return "  最近意图迹象: 外界能看出此人最近有过一次较明显的主动施力"
    return "  最近意图迹象: 外界暂未看清其最近一次明确意图"


def _player_character_affiliation_hint(character: Character) -> str:
    count = len(character.affiliation)
    if count <= 0:
        return "  归属线索: 外界暂未看出其稳定归属"
    if count == 1:
        return "  归属线索: 外界能看出其背后有一个相对稳定的组织归属"
    return f"  归属线索: 外界能看出其同时牵连约 {_player_count_hint(count, '个组织节点')}"


def _player_character_knowledge_hint(character: Character) -> str:
    if character.frontier_focus_type in {"project", "supply", "presence"}:
        return "  掌握线索: 外界能看出此人掌握的线索正向当前前线集中"
    return "  掌握线索: 外界暂时看不清他掌握了哪些内部线索"


def _player_character_recent_goal_hint(character: Character) -> str:
    if character.frontier_focus_type in {"project", "supply", "presence"}:
        return "  近期目标感: 外界能看出他近期动作具有较强的单线收束感"
    if character.agency_mode == "strategic":
        return "  近期目标感: 外界能看出他最近并非随波逐流，而是在持续推进某个方向"
    return "  近期目标感: 外界暂未看清其最近的稳定目标"


def _player_character_memory_hint(character: Character) -> str:
    if character.observation_trace >= 2:
        return "  行动惯性: 外界能感到他的动作并非零散反应，而是在重复某种熟悉路径"
    return "  行动惯性: 外界暂未积累到足够多的连续行为痕迹"


def _player_character_relationship_refs_hint(character: Character) -> str:
    count = len(character.relationship_refs)
    if count <= 0:
        return "  关系牵引: 外界暂未看出其稳定关系链"
    if count >= 4:
        return "  关系牵引: 外界能看出他已经卷入一张较厚的人际牵引网"
    return "  关系牵引: 外界能看出他已形成少量持续关系牵引"


def _player_character_loyalty_hint(character: Character) -> str:
    if character.affiliation:
        return "  归属线索: 外界能看出其背后存在稳定归属，但忠诚边界并不完全透明"
    return "  归属线索: 外界暂未看出其存在明确归属"


def _player_character_wake_hint(character: Character) -> str:
    if character.character_level == "L3":
        return "  出场势能: 外界能看出此人总在关键时刻重新浮到前台"
    return "  出场势能: 外界暂未看出此人拥有稳定的前线优先级"


def _player_faction_type_signature(faction: Faction) -> str:
    return "  生态位置: 外界已能看出其在秩序、工程、知识或物流网络中的大致位置"


def _player_faction_behavior_signature(faction: Faction) -> str:
    return "  行事特征: 外界已能看出其更常通过某几类固定动作反复施压，但具体施力链条仍不透明"


def _player_faction_style_trace(faction: Faction) -> str:
    return "  风格轨迹: 公开层面只能看出其动作风格正在重复出现并逐步固定"


def _humanize_faction_action_label(event_type: str) -> str:
    mapping = {
        "faction_infiltration": "渗透扩线",
        "faction_alliance": "结盟串联",
        "faction_alliance_locking": "锁定联盟结构",
        "faction_alliance_consolidation": "内部收束",
        "faction_power_struggle": "争权夺点",
        "faction_resource_reallocation": "资源改道",
        "faction_relic_contest": "争夺异常控制权",
        "faction_relic_control": "锁定异常控制权",
        "faction_project_bid": "抢项目执行权",
        "faction_budget_freeze": "冻结预算链",
        "faction_financing_withdrawal": "抽离融资",
        "faction_site_accident": "借事故施压",
        "faction_megastructure_stall": "拖慢巨构推进",
        "faction_megastructure_phase_advance": "推动巨构阶段前进",
        "faction_protocol_breach": "突破协议边界",
        "faction_protocol_takeover": "夺取协议控制权",
        "faction_archive_breach": "突破封存档案",
        "faction_archive_suppression": "压制档案外泄",
        "faction_lifeform_containment": "压制异常生物外溢",
        "faction_lifeform_provocation": "刺激异常生物失衡",
    }
    return mapping.get(event_type, event_type.replace("faction_", "").replace("_", " "))


def _player_supply_controller_hint(supply_line: SupplyLine) -> str:
    if supply_line.controlling_faction_ref:
        return "存在明确控制方，但公开层面不完全稳定"
    return "控制方不明或仍在争夺"


def _player_supply_pressure_interpretation(supply_line: SupplyLine) -> str:
    return (
        "  压力解读: "
        f"这条补给线当前呈{_player_pressure_band(supply_line.pressure)}状态，"
        "外界已能感到运输与放行节奏正在收紧。"
    )


def _player_supply_recent_notes(supply_line: SupplyLine) -> str:
    if not supply_line.recent_notes:
        return "  近期线索: 外界暂未积累到连续前线迹象"
    return "  近期线索: 公开线索显示这条线近期连续受扰，且压力并非一次性波动"


def _player_supply_organization_front(supply_line: SupplyLine) -> str:
    if supply_line.controlling_faction_ref and supply_line.status in {"contested", "fragile", "strained"}:
        return "  参与格局: 外界能看出这条补给线已有实际控制者，但争夺和摩擦还没有完全结束"
    if supply_line.controlling_faction_ref:
        return "  参与格局: 外界能看出这条补给线存在较明确的组织控制痕迹"
    if supply_line.pressure == "high":
        return "  参与格局: 外界能感到多股力量正在围绕这条补给线施压，但主导者尚不清晰"
    return "  参与格局: 外界只能看出这里存在组织介入痕迹，具体归属仍不透明"


def _player_project_pressure_interpretation(project: ProjectNetwork) -> str:
    return (
        "  压力解读: "
        f"该项目当前呈{_player_pressure_band(project.pressure)}状态，"
        "外界能感到执行秩序、推进节奏或资源保障正在吃紧。"
    )


def _player_project_recent_notes(project: ProjectNetwork) -> str:
    if not project.recent_notes:
        return "  近期线索: 外界暂未积累到连续项目波动"
    return "  近期线索: 公开线索显示该项目近期连续波动，且不止一股力量在施压"


def _player_project_organization_front(project: ProjectNetwork) -> str:
    actor_count = (
        len(project.sponsor_refs)
        + len(project.contractor_refs)
        + len(project.financier_refs)
        + len(project.opposition_refs)
    )
    if actor_count <= 0 and project.linked_factions:
        return "  参与格局: 外界能看出该项目周围已经聚起多方参与者，但分工和归属还不透明"
    if len(project.opposition_refs) >= 2:
        return "  参与格局: 外界能看出该项目已卷入多方角力，执行与阻力同时存在"
    if actor_count >= 3:
        return "  参与格局: 外界能看出该项目背后存在较完整的组织分工链"
    if actor_count >= 1:
        return "  参与格局: 外界能看出该项目背后已有明确组织介入"
    return "  参与格局: 外界暂未辨认出稳定组织分工，但能感到项目并非自发运转"


def _player_region_activity_hint(region) -> str:
    count = len(region.active_factions)
    if count <= 0:
        return "  组织盘面: 外界暂未看出稳定组织盘面"
    if count >= 4:
        return "  组织盘面: 外界已能感到多股组织力量长期停留在这里"
    return f"  组织盘面: 外界能辨认出约 {_player_count_hint(count, '股活跃组织力量')}"


def _player_region_character_hint(region) -> str:
    count = len(region.active_characters)
    if count <= 0:
        return "  人物动静: 外界暂未积累到持续人物活动痕迹"
    if count >= 6:
        return "  人物动静: 外界已能感到这里的人物活动明显变密，且不止一条线在推进"
    return f"  人物动静: 外界能辨认出约 {_player_count_hint(count, '名持续活跃人物')}"


def _player_region_presence_hint(region) -> str:
    count = len(region.resident_relics)
    if count <= 0:
        return "  异常落点: 外界暂未看出稳定异常落点"
    return f"  异常落点: 外界能感到约 {_player_count_hint(count, '处异常落点')} 正在牵动局势"


def _player_region_story_hook_hint(region) -> str:
    count = len(region.local_story_hooks)
    if count <= 0:
        return "  公开传闻: 外界暂未积累到稳定传闻主题"
    if count >= 3:
        return "  公开传闻: 公开层面已经围绕这里形成多条持续传闻"
    return "  公开传闻: 公开层面已出现少数反复被提起的局势传闻"


def _player_region_anomaly_fronts(world: WorldState, region_id: str) -> str:
    related_events = [
        event
        for event in world.event_stream.recent(60)
        if region_id in event.region_refs and event.relic_refs
    ]
    if not related_events:
        return "  异常前线: 外界暂未辨认出稳定异常前线"
    containment = sum(1 for event in related_events[-8:] if _is_containment_front(event))
    project = 0
    active = 0
    for event in related_events[-8:]:
        relic = world.relics.get(event.relic_refs[0]) if event.relic_refs else None
        if relic is None:
            continue
        if _is_project_front(event, relic):
            project += 1
        elif not _is_containment_front(event):
            active += 1
    parts: list[str] = []
    if active > 0:
        parts.append("活跃异常迹象正在反复浮现")
    if containment > 0:
        parts.append("封控或压制动作明显增多")
    if project > 0:
        parts.append("异常与工程前线开始互相牵连")
    joined = "，".join(parts) if parts else "异常迹象仍较零散"
    return f"  异常前线: 外界能感到{joined}"


def _player_region_organization_flashpoints(world: WorldState, region_id: str) -> str:
    related_events = [
        event
        for event in world.event_stream.recent(60)
        if region_id in event.region_refs and event.faction_refs
    ]
    if not related_events:
        return "  组织热点: 外界暂未看出稳定组织热点"
    high_severity = sum(1 for event in related_events[-8:] if event.severity == "high")
    if high_severity >= 3:
        return "  组织热点: 外界已能看出多股组织力量正在这里持续碰撞"
    if high_severity >= 1:
        return "  组织热点: 外界能看出这里存在几个反复升温的组织热点"
    return "  组织热点: 外界能感到组织活动在增多，但热点尚未完全坐实"


def _player_presence_profile(world: WorldState, relic: Relic) -> str:
    family = presence_event_family(relic)
    if family == "megastructure":
        return "  异常轮廓: 外界能看出这是一条会牵动工程、资源或秩序分配的重型前线"
    if family == "autonomous_system":
        return "  异常轮廓: 外界能看出它正在影响协议、控制或治理秩序，但机制仍不透明"
    if family == "sealed_archive":
        return "  异常轮廓: 外界能看出它与信息泄露、合法性波动或记忆冲击有关"
    if family == "anomalous_lifeform":
        return "  异常轮廓: 外界能看出它与扩散、封控和生态压力有关，活动边界并不稳定"
    return "  异常轮廓: 外界能看出这里存在非同寻常的异常压力，但本体尚不清晰"


def _player_relic_linked_projects(world: WorldState, relic: Relic) -> str:
    count = len(_find_projects_for_presence(world, relic.relic_id))
    if count <= 0:
        if relic.relic_type == "megastructure":
            return "  项目牵连迹象: 外界能感到它与工程推进有关，但看不清稳定项目链"
        return "  项目牵连迹象: 外界暂未看出其已卷入稳定项目网络"
    return f"  项目牵连迹象: 外界已能辨认出约 {_player_count_hint(count, '条相关项目线')}"


def _player_relic_linked_events(relic: Relic) -> str:
    if not relic.linked_events:
        return "  公开波动: 外界暂未积累到连续事件线索"
    return "  公开波动: 公开线索显示它近期反复被卷入关键波动，但完整链条仍不透明"


def _player_relic_story_hint(relic: Relic) -> str:
    family = presence_event_family(relic)
    if family == "megastructure":
        return "  外界印象: 外界多把它视作工程秩序、资源分配或地区排期的长期焦点"
    if family == "autonomous_system":
        return "  外界印象: 外界多把它与协议权限、治理异常或控制失衡联系在一起"
    if family == "sealed_archive":
        return "  外界印象: 外界多把它与档案泄露、记忆扰动或合法性震荡联系在一起"
    if family == "anomalous_lifeform":
        return "  外界印象: 外界多把它与扩散、封控和生态失衡联系在一起"
    return "  外界印象: 外界只知道它反复牵动局势，但还说不清属于哪类异常"


def _format_truth_relic_linked_events(relic: Relic) -> str:
    if not relic.linked_events:
        return "  linked_events: None"
    count = len(relic.linked_events)
    recent_count = min(count, 3)
    return (
        "  linked_events: "
        f"累计记录 {count} 条关联事件，最近仍有 {recent_count} 条在持续回流到这个异常对象。"
    )


def _format_character_front_clues(world: WorldState, region_id: str) -> str:
    recent_events = [
        event for event in reversed(world.event_stream.recent(40)) if region_id in event.region_refs
    ]
    if not recent_events:
        return "    前线线索: None"
    focal_event = recent_events[0]
    focal_relics = (
        ", ".join(_player_display_name(world, relic_id) for relic_id in focal_event.relic_refs[:2])
        or "区域压力"
    )
    return "\n".join(
        [
            "    前线线索:",
            f"      可见焦点: {focal_relics}",
            f"      可见变化: {_player_event_clue_for_view(world, focal_event)}",
        ]
    )


def _player_relic_reason_for_view(world: WorldState, event: Event) -> str:
    if event.relic_refs:
        names = ", ".join(_player_display_name(world, relic_id) for relic_id in event.relic_refs[:2])
        return f"{names}最近反复出现在公开线索里，外部观察者很容易把它视为当前焦点。"
    return "这一带最近反复出现异常线索，局势显然正在向某个压力核心收拢。"


def _player_event_clue_for_view(world: WorldState, event: Event) -> str:
    return format_player_facing_event_clue(event, world=world)


def _recent_project_events(
    world: WorldState,
    project: ProjectNetwork,
    *,
    limit: int,
) -> list[Event]:
    scored: list[tuple[int, Event]] = []
    presence_refs = set(project.linked_presence_refs)
    faction_refs = set(project.linked_factions)
    region_refs = set(project.linked_regions)
    for event in world.event_stream.recent(80):
        score = 0
        themes = set(event_theme_tags(event))
        region_hits = len(region_refs.intersection(event.region_refs))
        presence_hit = bool(presence_refs.intersection(event.relic_refs))
        faction_hit = bool(faction_refs.intersection(event.faction_refs))
        direct_hit = project.project_id in event.project_refs
        if direct_hit:
            score += 6
        if presence_hit:
            score += 4
        if faction_hit and ("project" in themes or region_hits):
            score += 2
        if region_hits:
            score += 1 + region_hits
        if "project" in themes:
            score += 2
        if score <= 0 or not (
            direct_hit
            or presence_hit
            or ("project" in themes and (region_hits > 0 or faction_hit))
        ):
            continue
        scored.append((score * 1000 + event.tick, event))
    return [event for _, event in sorted(scored, key=lambda item: item[0])[-limit:]]


def _recent_supply_line_events(
    world: WorldState,
    supply_line: SupplyLine,
    *,
    limit: int,
) -> list[Event]:
    scored: list[tuple[int, Event]] = []
    endpoints = {supply_line.origin_region_id, supply_line.destination_region_id}
    for event in world.event_stream.recent(80):
        score = 0
        themes = set(event_theme_tags(event))
        region_hits = len(endpoints.intersection(event.region_refs))
        faction_hit = bool(
            supply_line.controlling_faction_ref
            and supply_line.controlling_faction_ref in event.faction_refs
        )
        direct_hit = supply_line.supply_id in event.supply_refs
        if direct_hit:
            score += 6
        if region_hits >= 2:
            score += 4
        elif region_hits == 1 and "supply" in themes:
            score += 2
        if faction_hit and ("supply" in themes or region_hits > 0):
            score += 2
        if "supply" in themes:
            score += 2
        if score <= 0 or not (
            direct_hit
            or ("supply" in themes and (region_hits > 0 or faction_hit))
        ):
            continue
        scored.append((score * 1000 + event.tick, event))
    return [event for _, event in sorted(scored, key=lambda item: item[0])[-limit:]]


def _player_facing_relic_reason(world: WorldState, event: Event) -> str:
    if event.relic_refs:
        names = ", ".join(_format_relic_refs(world, event.relic_refs[:2]))
        return f"{names} 最近反复出现在事件里，周边局势明显变得不稳定。"
    return "这一带最近反复出现异常迹象，局势正在持续偏移。"


def _player_facing_event_clue(world: WorldState, event: Event) -> str:
    if event.relic_refs:
        names = ", ".join(_format_relic_refs(world, event.relic_refs[:2]))
        return f"{names} 周边又出现了一次高可见度异动。"
    if event.faction_refs:
        return "局部权力活动变得更频繁，表层秩序正在波动。"
    if "resource" in event.event_type or "supply" in event.event_type:
        return "供给和物流层面出现了新的紧张信号。"
    return "这片区域出现了新的公开压力信号。"


def _format_relic_refs(world: WorldState, relic_ids: list[str]) -> list[str]:
    return [
        f"{world.relics[relic_id].name} ({relic_id})"
        if relic_id in world.relics
        else relic_id
        for relic_id in relic_ids
    ]


def _format_region_anomaly_fronts(world: WorldState, region_id: str) -> str:
    related_events = [
        event
        for event in world.event_stream.recent(80)
        if region_id in event.region_refs and event.relic_refs
    ]
    if not related_events:
        return "  anomaly_fronts: None"

    active_entries: list[str] = []
    containment_entries: list[str] = []
    project_entries: list[str] = []
    for event in related_events[-8:]:
        for relic_id in event.relic_refs:
            relic = world.relics.get(relic_id)
            if relic is None:
                continue
            family = presence_event_family(relic)
            pressure_axis = _derive_pressure_axis(world, region_id, event, relic)
            origin_ref = _extract_origin_ref(world, relic_id)
            entry = (
                f"{presence_display_name(relic)} {relic.name} ({relic_id}) "
                f"[family={family}, pressure={pressure_axis}, via={event.event_type}]"
            )
            if _is_containment_front(event):
                if origin_ref and origin_ref != region_id:
                    containment_entries.append(
                        f"    - {entry}, origin={_format_entity_ref(world, origin_ref)}"
                    )
                else:
                    containment_entries.append(f"    - {entry}")
            elif _is_project_front(event, relic):
                if origin_ref and origin_ref != region_id:
                    project_entries.append(
                        f"    - {entry}, origin={_format_entity_ref(world, origin_ref)}"
                    )
                else:
                    project_entries.append(f"    - {entry}")
            else:
                if origin_ref and origin_ref != region_id:
                    active_entries.append(
                        f"    - {entry}, origin={_format_entity_ref(world, origin_ref)}"
                    )
                else:
                    active_entries.append(f"    - {entry}")

    if not active_entries and not containment_entries and not project_entries:
        return "  anomaly_fronts: None"

    lines = ["  anomaly_fronts:"]
    if active_entries:
        lines.append("    active_front:")
        lines.extend(_dedupe_entries(active_entries, limit=4))
    else:
        lines.append("    active_front: None")
    if containment_entries:
        lines.append("    containment_front:")
        lines.extend(_dedupe_entries(containment_entries, limit=4))
    else:
        lines.append("    containment_front: None")
    if project_entries:
        lines.append("    project_front:")
        lines.extend(_dedupe_entries(project_entries, limit=4))
    else:
        lines.append("    project_front: None")
    return "\n".join(lines)


def _format_region_organization_flashpoints(world: WorldState, region_id: str) -> str:
    related_events = [
        event
        for event in world.event_stream.recent(80)
        if region_id in event.region_refs and event.faction_refs
    ]
    if not related_events:
        return "  organization_flashpoints: None"

    entries: list[str] = []
    for event in related_events[-10:]:
        focal_refs = (
            ", ".join(_format_relic_refs(world, event.relic_refs[:2]))
            if event.relic_refs
            else "地区压力"
        )
        factions = ", ".join(_format_faction_refs(world, event.faction_refs[:3])) or "未明组织"
        entries.append(
            f"    - {factions} [事件={_player_event_type_label(event.event_type)}, 焦点={focal_refs}, 压力={_player_level_value(event.severity)}]"
        )

    if not entries:
        return "  organization_flashpoints: None"

    lines = ["  organization_flashpoints:"]
    lines.extend(_dedupe_entries(entries, limit=5))
    return "\n".join(lines)


def _format_faction_project_fronts(world: WorldState, faction_id: str) -> str:
    relation_entries = relations_for_ref(world, faction_id, limit=16)
    related_events = [
        event
        for event in world.event_stream.recent(100)
        if faction_id in event.faction_refs and event.relic_refs
    ]
    if not related_events and not relation_entries:
        return "  project_fronts: None"

    project_entries: list[str] = []
    anomaly_entries: list[str] = []
    for event in related_events[-10:]:
        relic = world.relics.get(event.relic_refs[0]) if event.relic_refs else None
        if relic is None:
            continue
        target_name = f"{relic.name} ({relic.relic_id})"
        region_name = (
            _format_entity_ref(world, event.region_refs[0]) if event.region_refs else "Unknown region"
        )
        entry = (
            f"    - {target_name} [event={event.event_type}, region={region_name}, severity={event.severity}]"
        )
        if relic.relic_type == "megastructure" or "project" in event.event_type or "budget" in event.event_type or "accident" in event.event_type:
            project_entries.append(entry)
        else:
            anomaly_entries.append(entry)

    for relation in relation_entries:
        counterparty = relation.target_ref if relation.source_ref == faction_id else relation.source_ref
        relic = world.relics.get(counterparty)
        if relic is None:
            continue
        entry = _truth_faction_project_front_entry(world, relic, relation)
        if relic.relic_type == "megastructure" and relation.relation_type in {
            "contracting",
            "financing",
            "sponsoring",
            "obstructing",
            "opposing",
            "controls",
        }:
            project_entries.append(entry)
        elif relation.relation_type in {"contesting", "controls", "tracking", "containing"}:
            anomaly_entries.append(entry)

    if not project_entries and not anomaly_entries:
        fallback_project_entries, fallback_anomaly_entries = _project_faction_front_events(
            world,
            faction_id,
        )
        project_entries.extend(fallback_project_entries)
        anomaly_entries.extend(fallback_anomaly_entries)
    if not project_entries and not anomaly_entries:
        return "  project_fronts: None"

    lines = ["  project_fronts:"]
    if project_entries:
        lines.append("    engineering_lines:")
        lines.extend(_dedupe_entries(project_entries, limit=4))
    else:
        lines.append("    engineering_lines: None")
    if anomaly_entries:
        lines.append("    anomaly_lines:")
        lines.extend(_dedupe_entries(anomaly_entries, limit=4))
    else:
        lines.append("    anomaly_lines: None")
    return "\n".join(lines)


def _format_faction_supply_fronts(world: WorldState, faction_id: str) -> str:
    supply_ids = _find_supply_for_faction(world, faction_id)
    if not supply_ids:
        fallback_entries = _project_faction_supply_events(world, faction_id)
        if not fallback_entries:
            return "  supply_fronts: None"
        lines = ["  supply_fronts:"]
        lines.extend(fallback_entries[:4])
        return "\n".join(lines)
    lines = ["  supply_fronts:"]
    for supply_id in supply_ids[:4]:
        supply_line = world.supply_lines.get(supply_id)
        if supply_line is None:
            continue
        lines.append(
            _truth_faction_supply_front_entry(world, supply_line)
        )
    return "\n".join(lines)


def _format_faction_execution_front_overview(world: WorldState, faction_id: str) -> str:
    faction = world.factions.get(faction_id)
    if faction is None:
        return "  execution_front_overview: None"
    project_ids = _find_projects_for_faction(world, faction_id)[:6]
    supply_ids = _find_supply_for_faction(world, faction_id)[:6]
    fallback_project_entries, fallback_anomaly_entries = _project_faction_front_events(world, faction_id)
    fallback_supply_entries = _project_faction_supply_events(world, faction_id)
    if not project_ids and not supply_ids and not fallback_project_entries and not fallback_supply_entries:
        return "  execution_front_overview: None"

    project_entries: list[tuple[str, int]] = []
    for project_id in project_ids:
        project = world.projects.get(project_id)
        if project is None:
            continue
        score = _pressure_rank(project.pressure) + (1 if project.status in {"contested_buildout", "stalled_recovery"} else 0)
        project_entries.append((_truth_front_node_brief(project.name, status=project.status, pressure=project.pressure), score))

    supply_entries: list[tuple[str, int]] = []
    for supply_id in supply_ids:
        supply_line = world.supply_lines.get(supply_id)
        if supply_line is None:
            continue
        score = _pressure_rank(supply_line.pressure) + (1 if supply_line.status in {"contested", "fragile", "strained"} else 0)
        supply_entries.append((_truth_front_node_brief(supply_line.name, status=supply_line.status, pressure=supply_line.pressure), score))

    if not project_entries and fallback_project_entries:
        project_entries = [(entry.removeprefix("    - "), 2) for entry in fallback_project_entries[:2]]
    if not supply_entries and fallback_supply_entries:
        supply_entries = [(entry.removeprefix("    - "), 2) for entry in fallback_supply_entries[:2]]
    if not project_entries and fallback_anomaly_entries:
        project_entries = [(entry.removeprefix("    - "), 2) for entry in fallback_anomaly_entries[:2]]
    if not project_entries and not supply_entries:
        return "  execution_front_overview: None"

    hottest = sorted(project_entries + supply_entries, key=lambda item: item[1], reverse=True)
    lines = ["  execution_front_overview:"]
    lines.append(
        "    execution_axis: "
        + _faction_execution_axis_text(
            faction=faction,
            project_count=len(project_entries),
            supply_count=len(supply_entries),
        )
    )
    if project_entries:
        lines.append(
            "    project_axis: " + "；".join(entry[0] for entry in sorted(project_entries, key=lambda item: item[1], reverse=True)[:2])
        )
    else:
        lines.append("    project_axis: None")
    if supply_entries:
        lines.append(
            "    supply_axis: " + "；".join(entry[0] for entry in sorted(supply_entries, key=lambda item: item[1], reverse=True)[:2])
        )
    else:
        lines.append("    supply_axis: None")
    lines.append("    unstable_node: " + hottest[0][0])
    lines.append(
        "    lever_read: " + _faction_execution_lever_text(faction)
    )
    lines.append(
        "    command_read: "
        + _faction_execution_read_text(
            project_entries=project_entries,
            supply_entries=supply_entries,
        )
    )
    lines.append(
        "    strategy_to_execution: "
        + _faction_execution_transition_text(
            faction=faction,
            project_entries=project_entries,
            supply_entries=supply_entries,
        )
    )
    return "\n".join(lines)


def _format_civilization_strategic_fronts(world: WorldState, civ_id: str) -> str:
    related_events = [
        event
        for event in world.event_stream.recent(120)
        if civ_id in event.civ_refs and (event.relic_refs or event.faction_refs or len(event.region_refs) > 1)
    ]
    if not related_events:
        return "  strategic_fronts: None"

    expansion_lines: list[str] = []
    containment_lines: list[str] = []
    pressure_lines: list[str] = []
    for event in related_events[-14:]:
        focal_region = _format_entity_ref(world, event.region_refs[0]) if event.region_refs else "未知区域"
        focal_relic = ", ".join(_format_relic_refs(world, event.relic_refs[:2])) if event.relic_refs else "区域压力面"
        entry = "    - " + _truth_front_event_projection(world, focus=focal_relic, region=focal_region, event=event)
        if _is_civilization_expansion_line(event, world):
            expansion_lines.append(entry)
        elif _is_civilization_containment_line(event):
            containment_lines.append(entry)
        else:
            pressure_lines.append(entry)

    if not expansion_lines and not containment_lines and not pressure_lines:
        return "  strategic_fronts: None"

    lines = ["  strategic_fronts:"]
    if expansion_lines:
        lines.append("    expansion_lines:")
        lines.extend(_dedupe_entries(expansion_lines, limit=4))
    else:
        lines.append("    expansion_lines: None")
    if containment_lines:
        lines.append("    containment_lines:")
        lines.extend(_dedupe_entries(containment_lines, limit=4))
    else:
        lines.append("    containment_lines: None")
    if pressure_lines:
        lines.append("    pressure_lines:")
        lines.extend(_dedupe_entries(pressure_lines, limit=4))
    else:
        lines.append("    pressure_lines: None")
    return "\n".join(lines)


def _format_civilization_project_networks(world: WorldState, civ_id: str) -> str:
    project_ids = world.civilizations[civ_id].key_projects[:6] if civ_id in world.civilizations else []
    if not project_ids:
        fallback_entries = _project_civ_project_events(world, civ_id)
        if not fallback_entries:
            return "  project_networks: None"
        lines = ["  project_networks:"]
        lines.extend(fallback_entries[:5])
        return "\n".join(lines)
    lines = ["  project_networks:"]
    for project_id in project_ids:
        project = world.projects.get(project_id)
        if project is None:
            continue
        lines.append(_truth_civilization_project_network_entry(project))
    return "\n".join(lines)


def _format_civilization_supply_fronts(world: WorldState, civ_id: str) -> str:
    supply_ids = world.civilizations[civ_id].key_supply_lines[:6] if civ_id in world.civilizations else []
    if not supply_ids:
        fallback_entries = _project_civ_supply_events(world, civ_id)
        if not fallback_entries:
            return "  supply_fronts: None"
        lines = ["  supply_fronts:"]
        lines.extend(fallback_entries[:5])
        return "\n".join(lines)
    lines = ["  supply_fronts:"]
    for supply_id in supply_ids:
        supply_line = world.supply_lines.get(supply_id)
        if supply_line is None:
            continue
        lines.append(_truth_civilization_supply_front_entry(world, supply_line))
    return "\n".join(lines)


def _format_civilization_execution_front_overview(world: WorldState, civ_id: str) -> str:
    civilization = world.civilizations.get(civ_id)
    if civilization is None:
        return "  execution_front_overview: None"
    project_ids = civilization.key_projects[:6]
    supply_ids = civilization.key_supply_lines[:6]
    if not project_ids and not supply_ids:
        return "  execution_front_overview: None"

    project_entries: list[tuple[str, int, str]] = []
    for project_id in project_ids:
        project = world.projects.get(project_id)
        if project is None:
            continue
        score = _pressure_rank(project.pressure) + (1 if project.status in {"contested_buildout", "stalled_recovery"} else 0)
        project_entries.append(
            (
                _truth_front_node_brief(project.name, status=project.status, pressure=project.pressure),
                score,
                project_id,
            )
        )

    supply_entries: list[tuple[str, int, str]] = []
    for supply_id in supply_ids:
        supply_line = world.supply_lines.get(supply_id)
        if supply_line is None:
            continue
        score = _pressure_rank(supply_line.pressure) + (1 if supply_line.status in {"contested", "fragile"} else 0)
        supply_entries.append(
            (
                _truth_front_node_brief(supply_line.name, status=supply_line.status, pressure=supply_line.pressure),
                score,
                supply_id,
            )
        )

    if not project_entries and not supply_entries:
        return "  execution_front_overview: None"

    hottest = sorted(project_entries + supply_entries, key=lambda item: item[1], reverse=True)
    lines = ["  execution_front_overview:"]
    lines.append(
        "    execution_axis: "
        + _civilization_execution_axis_text(project_count=len(project_entries), supply_count=len(supply_entries))
    )
    if project_entries:
        lines.append(
            "    project_axis: " + "；".join(entry[0] for entry in sorted(project_entries, key=lambda item: item[1], reverse=True)[:2])
        )
    else:
        lines.append("    project_axis: None")
    if supply_entries:
        lines.append(
            "    supply_axis: " + "；".join(entry[0] for entry in sorted(supply_entries, key=lambda item: item[1], reverse=True)[:2])
        )
    else:
        lines.append("    supply_axis: None")
    lines.append("    unstable_node: " + hottest[0][0])
    lines.append(
        "    command_read: "
        + _civilization_execution_read_text(
            project_entries=project_entries,
            supply_entries=supply_entries,
        )
    )
    lines.append(
        "    strategy_to_execution: "
        + _civilization_execution_transition_text(
            civilization=civilization,
            project_entries=project_entries,
            supply_entries=supply_entries,
        )
    )
    return "\n".join(lines)


def _truth_project_brief(project: ProjectNetwork) -> str:
    return (
        f"{project.name} "
        f"[状态={_player_status_value(project.status)}, 压力={_player_level_value(project.pressure)}]"
    )


def _truth_supply_brief(supply_line: SupplyLine) -> str:
    return (
        f"{supply_line.name} "
        f"[状态={_player_status_value(supply_line.status)}, 压力={_player_level_value(supply_line.pressure)}]"
    )


def _truth_faction_project_front_entry(world: WorldState, relic: Relic, relation) -> str:
    relation_text = _truth_relation_type_value(relation.relation_type)
    strength_text = _player_level_value(relation.strength)
    return (
        f"    - {_format_entity_ref(world, relic.relic_id)} "
        f"[关系线={relation_text}, 压力={strength_text}, 最近更新=tick {relation.updated_tick}]"
    )


def _truth_faction_supply_front_entry(world: WorldState, supply_line: SupplyLine) -> str:
    controller = (
        _format_entity_ref(world, supply_line.controlling_faction_ref)
        if supply_line.controlling_faction_ref
        else "控制方尚不稳固"
    )
    return (
        "    - "
        f"{supply_line.name} "
        f"[状态={_player_status_value(supply_line.status)}, 压力={_player_level_value(supply_line.pressure)}, "
        f"路线={_format_entity_ref(world, supply_line.origin_region_id)} -> {_format_entity_ref(world, supply_line.destination_region_id)}, "
        f"控制线={controller}]"
    )


def _truth_front_node_brief(name: str, *, status: str, pressure: str) -> str:
    return f"{name} [状态={_player_status_value(status)}, 压力={_player_level_value(pressure)}]"


def _truth_civilization_project_network_entry(project: ProjectNetwork) -> str:
    fronts = "、".join(_humanize_enum_token(tag) for tag in project.front_tags[:4]) or "前线标签尚不清晰"
    return (
        "    - "
        f"{project.name} "
        f"[状态={_player_status_value(project.status)}, 压力={_player_level_value(project.pressure)}, 前线={fronts}]"
    )


def _truth_civilization_supply_front_entry(world: WorldState, supply_line: SupplyLine) -> str:
    controller = (
        _format_entity_ref(world, supply_line.controlling_faction_ref)
        if supply_line.controlling_faction_ref
        else "控制方尚不稳固"
    )
    return (
        "    - "
        f"{supply_line.name} "
        f"[状态={_player_status_value(supply_line.status)}, 压力={_player_level_value(supply_line.pressure)}, 控制线={controller}]"
    )


def _pressure_rank(level: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(level, 0)


def _civilization_execution_axis_text(*, project_count: int, supply_count: int) -> str:
    if project_count >= 2 and supply_count >= 2:
        return "项目推进与补给调度双线并行，属于较厚的上层执行面。"
    if project_count >= 2:
        return "执行重点更偏向工程、合同和建设链。"
    if supply_count >= 2:
        return "执行重点更偏向通道、运输和调拨控制。"
    if project_count >= 1 and supply_count >= 1:
        return "项目与补给都已卷入，但尚未形成完整双线体系。"
    if project_count >= 1:
        return "当前主要靠少数关键项目节点牵动整体动作。"
    return "当前主要靠少数关键补给线路牵动整体动作。"


def _civilization_execution_read_text(
    *,
    project_entries: list[tuple[str, int, str]],
    supply_entries: list[tuple[str, int, str]],
) -> str:
    high_projects = sum(1 for _, score, _ in project_entries if score >= 4)
    high_supply = sum(1 for _, score, _ in supply_entries if score >= 4)
    if high_projects >= 1 and high_supply >= 1:
        return "工程与运输都在承压，说明文明上层已经进入边推进边控险的执行状态。"
    if high_projects >= 1:
        return "主要压力集中在项目推进链，上层更像在守工程主轴。"
    if high_supply >= 1:
        return "主要压力集中在补给通道，上层更像在守运输与分配主轴。"
    return "关键执行节点虽然可见，但整体仍保有一定调度余裕。"


def _faction_execution_axis_text(
    *,
    faction: Faction,
    project_count: int,
    supply_count: int,
) -> str:
    if project_count >= 2 and supply_count >= 1:
        return "项目执行与补给调度双线推进，已经具备较厚的落地执行面。"
    if project_count >= 2:
        return "执行重心主要压在工程、合同和建设推进上。"
    if supply_count >= 2:
        return "执行重心主要压在运输、调拨与通道控制上。"
    if project_count >= 1 and supply_count >= 1:
        return "项目与补给都已卷入，但当前仍以局部主轴为中心运转。"
    if project_count >= 1:
        return "当前主要靠少数项目节点把组织影响力压到现实结构上。"
    if "logistics" in faction.faction_type or "efficiency" in faction.doctrine_tags:
        return "当前主要靠少数补给线路维持执行抓手。"
    return "当前主要靠有限补给节点维持执行连续性。"


def _faction_execution_lever_text(faction: Faction) -> str:
    if faction.operational_style == "contract_predator":
        return "更依赖合同、预算和执行权换手来夺取主动。"
    if faction.operational_style == "extraction_broker":
        return "更依赖调拨、运输与资源改道来施加影响。"
    if faction.operational_style == "containment_cadre":
        return "更依赖封控、压稳节点和限制外溢来维持执行。"
    if faction.operational_style == "discipline_network":
        return "更依赖持续渗透和局部争权，把前线一点点推向自己。"
    return "执行杠杆较混合，会在项目、补给和地区节点之间切换施力。"


def _faction_execution_read_text(
    *,
    project_entries: list[tuple[str, int]],
    supply_entries: list[tuple[str, int]],
) -> str:
    high_projects = sum(1 for _, score in project_entries if score >= 4)
    high_supply = sum(1 for _, score in supply_entries if score >= 4)
    if high_projects >= 1 and high_supply >= 1:
        return "项目与补给同时承压，说明该派系已经进入边扩张边稳执行链的状态。"
    if high_projects >= 1:
        return "主要压力集中在项目执行链，说明其动作更像在守或抢工程主轴。"
    if high_supply >= 1:
        return "主要压力集中在补给线，说明其动作更像在守或抢运输主轴。"
    if project_entries or supply_entries:
        return "执行节点虽然可见，但当前仍保有一定调度余裕。"
    return "其执行前线仍偏薄，更多依赖临时动作而非稳定结构。"


def _format_civilization_strategy_memory(world: WorldState, civilization: Civilization) -> str:
    if not civilization.strategic_memory:
        return "  strategic_memory: None"
    lines = ["  strategic_memory:"]
    for item in civilization.strategic_memory[-6:]:
        lines.append(f"    - {_truth_civilization_strategy_memory_item(world, item)}")
    return "\n".join(lines)


def _format_civilization_bias_effects(world: WorldState, civilization: Civilization) -> str:
    posture = civilization.strategic_posture
    lines = ["  strategic_bias_effects:"]
    lines.append(f"    posture_driver: {_civilization_posture_driver_label(posture)}")
    lines.append(f"    faction_weight_bias: {_civilization_faction_bias_label(posture)}")
    lines.append(f"    character_front_bias: {_civilization_character_bias_label(posture)}")
    affected_fronts = _find_civilization_bias_fronts(world, civilization.civ_id)
    if affected_fronts:
        lines.append("    active_bias_fronts:")
        for item in affected_fronts[:4]:
            lines.append(f"      - {item}")
    else:
        lines.append("    active_bias_fronts: None")
    if civilization.strategic_bias_trace:
        lines.append("    bias_trace:")
        for item in civilization.strategic_bias_trace[-5:]:
            lines.append(f"      - {_truth_civilization_bias_trace_item(world, item)}")
    else:
        lines.append("    bias_trace: None")
    return "\n".join(lines)


def _project_faction_front_events(
    world: WorldState,
    faction_id: str,
) -> tuple[list[str], list[str]]:
    project_entries: list[tuple[str, str]] = []
    anomaly_entries: list[tuple[str, str]] = []
    for event in reversed(world.event_stream.recent(80)):
        if faction_id not in event.faction_refs or not event.event_type.startswith("faction_"):
            continue
        cluster_key = _front_cluster_key(world, event)
        entry = _format_front_projection_entry(world, event)
        if _event_projects_front(event):
            project_entries.append((cluster_key, entry))
        elif _event_anomaly_front(event):
            anomaly_entries.append((cluster_key, entry))
    return _compress_clustered_entries(project_entries, limit=4), _compress_clustered_entries(anomaly_entries, limit=4)


def _project_faction_supply_events(world: WorldState, faction_id: str) -> list[str]:
    entries: list[tuple[str, str]] = []
    for event in reversed(world.event_stream.recent(80)):
        if faction_id not in event.faction_refs or not event.event_type.startswith("faction_"):
            continue
        if not _event_supply_front(event):
            continue
        entries.append((_front_cluster_key(world, event), _format_supply_projection_entry(world, event)))
    return _compress_clustered_entries(entries, limit=4)


def _project_civ_project_events(world: WorldState, civ_id: str) -> list[str]:
    entries: list[tuple[str, str]] = []
    for event in reversed(world.event_stream.recent(100)):
        if civ_id not in event.civ_refs or not event.event_type.startswith("faction_"):
            continue
        if not _event_projects_front(event):
            continue
        entries.append((_front_cluster_key(world, event), _format_front_projection_entry(world, event)))
    return _compress_clustered_entries(entries, limit=5)


def _project_civ_supply_events(world: WorldState, civ_id: str) -> list[str]:
    entries: list[tuple[str, str]] = []
    for event in reversed(world.event_stream.recent(100)):
        if civ_id not in event.civ_refs or not event.event_type.startswith("faction_"):
            continue
        if not _event_supply_front(event):
            continue
        entries.append((_front_cluster_key(world, event), _format_supply_projection_entry(world, event)))
    return _compress_clustered_entries(entries, limit=5)


def _event_projects_front(event: Event) -> bool:
    event_type = event.event_type.lower()
    themes = set(event_theme_tags(event))
    return bool(
        event.relic_refs
        or "project" in themes
        or any(
            token in event_type
            for token in {"project", "budget", "financing", "archive", "protocol", "megastructure"}
        )
    )


def _event_supply_front(event: Event) -> bool:
    event_type = event.event_type.lower()
    themes = set(event_theme_tags(event))
    return "supply" in themes or any(
        token in event_type
        for token in {"resource_reallocation", "financing_withdrawal", "route", "corridor"}
    )


def _event_anomaly_front(event: Event) -> bool:
    event_type = event.event_type.lower()
    themes = set(event_theme_tags(event))
    return bool(
        event.relic_refs
        or "anomaly" in themes
        or any(token in event_type for token in {"relic", "lifeform", "containment", "breach"})
    )


def _format_front_projection_entry(world: WorldState, event: Event) -> str:
    focal_region = _format_entity_ref(world, event.region_refs[0]) if event.region_refs else "未知区域"
    if event.relic_refs:
        focus = ", ".join(_format_relic_refs(world, event.relic_refs[:1]))
    elif event.faction_refs:
        focus = _format_midlayer_actor_projection(world, event.faction_refs[0])
    else:
        focus = focal_region
    return "    - " + _truth_front_event_projection(world, focus=focus, region=focal_region, event=event)


def _format_supply_projection_entry(world: WorldState, event: Event) -> str:
    focal_region = _format_entity_ref(world, event.region_refs[0]) if event.region_refs else "未知区域"
    actor = (
        _format_midlayer_actor_projection(world, event.faction_refs[0])
        if event.faction_refs
        else "未知施力方"
    )
    return "    - " + _truth_front_event_projection(world, focus=actor, region=focal_region, event=event)


def _front_cluster_key(world: WorldState, event: Event) -> str:
    if event.relic_refs:
        return f"relic:{event.relic_refs[0]}"
    if event.region_refs:
        return f"region:{event.region_refs[0]}"
    if event.faction_refs:
        return f"faction:{event.faction_refs[0]}"
    return event.event_type


def _truth_front_event_projection(
    world: WorldState,
    *,
    focus: str,
    region: str,
    event: Event,
) -> str:
    event_label = _player_event_type_label(event.event_type)
    severity_text = _player_level_value(event.severity)
    summary_text = _format_truth_event_summary(world, event)
    return f"{focus} [{event_label}，压力={severity_text}，地区={region}] {summary_text}"


def _compress_clustered_entries(entries: list[tuple[str, str]], limit: int) -> list[str]:
    if not entries:
        return []
    grouped: dict[str, list[str]] = {}
    for cluster_key, text in entries:
        grouped.setdefault(cluster_key, []).append(text)

    compressed: list[str] = []
    for cluster_key, items in grouped.items():
        first = items[0]
        compressed.append(first)
        if len(items) > 1:
            compressed.append(f"    - 同一前线另有 {len(items) - 1} 次相近波动")
        if len(compressed) >= limit:
            break
    return compressed[:limit]


def _civilization_governance_engine_label(civilization: Civilization) -> str:
    mapping = {
        "hybrid_governance": "混合治理核心，能够在技术、组织与地方力量之间做再分配",
        "technocratic_council": "技术官僚式治理核心，偏重计算、分配和系统调度",
        "security_directorate": "安保导向治理核心，偏重封控、秩序与风险压制",
        "mercantile_charter": "交易宪章式治理核心，偏重合同、交换与扩张杠杆",
    }
    return mapping.get(civilization.governance_mode, civilization.governance_mode)


def _civilization_execution_chain_label(project_count: int, supply_count: int, faction_count: int) -> str:
    if project_count >= 2 and supply_count >= 2:
        return "通过项目网络和补给网络双线执行，属于较厚的组织执行链"
    if project_count >= 2:
        return "执行链主要压在工程、建设和基础设施推进上"
    if supply_count >= 2:
        return "执行链主要压在运输、调拨与通道控制上"
    if faction_count >= 3:
        return "执行链更依赖多个派系节点协同，而非稳定物理网络"
    return "执行链仍偏薄，更多依赖局部节点临时驱动"


def _civilization_territorial_base_label(civilization: Civilization) -> str:
    if len(civilization.key_regions) >= 4:
        return "控制重心分布在多个关键地区，属于多节点维持型文明"
    if len(civilization.key_regions) >= 2:
        return "控制重心集中在少数关键地区，通过重点节点维持整体秩序"
    return "控制底盘较窄，更依赖单点核心区保持组织连续性"


def _civilization_risk_absorption_label(civilization: Civilization) -> str:
    if civilization.strategic_posture == "containment_first":
        return "优先把风险拦在外层，宁可牺牲扩张速度也要避免失控"
    if civilization.strategic_posture == "stability_over_growth":
        return "优先吸收秩序冲击，把动荡限制在可管理范围内"
    if civilization.strategic_posture == "megastructure_expansion":
        return "愿意承受较高局部压力，以换取长期工程主导权"
    if civilization.strategic_posture == "opportunistic_extraction":
        return "倾向把波动转为杠杆，风险吸收能力带有明显机会主义色彩"
    return "仍在扩张与稳态之间反复平衡，风险吸收方式尚未完全收束"


def _civilization_external_posture_label(external_count: int, civilization: Civilization) -> str:
    if external_count >= 3:
        return "外部接口较多，说明其组织边界并不封闭，持续受外压与交换影响"
    if external_count >= 1:
        return "外部接口存在，但目前仍以内部组织协调为主"
    if civilization.legitimacy == "low":
        return "几乎不依赖外部接口，更多在内部合法性压力下自我收口"
    return "组织边界相对内向，主要依赖内部网络完成运转"


def _faction_command_shape_label(faction: Faction) -> str:
    if faction.power_scope == "civilizational" and faction.controlled_regions:
        return "存在稳定上层指挥节点，并能跨区维持动作连续性"
    if len(faction.controlled_regions) >= 2:
        return "以多个地区落点构成分布式指挥结构"
    if faction.controlled_regions:
        return "以少数据点为核心，指挥形态偏集中"
    return "更像轻量网络，依赖移动节点和机会性接入"


def _faction_execution_base_label(faction: Faction, project_count: int, supply_count: int) -> str:
    if project_count >= 2 and supply_count >= 1:
        return "同时抓项目执行和补给控制，属于能把前线压力落地的厚组织"
    if project_count >= 2:
        return "主要通过项目、合同和建设流程把影响力落到现实结构上"
    if supply_count >= 2:
        return "主要通过补给调度、路由控制和资源再分配施力"
    if faction.key_characters:
        return "仍较依赖关键人物节点推动执行"
    return "执行底盘偏薄，更依赖事件窗口而非长期结构"


def _faction_pressure_method_label(faction: Faction) -> str:
    mapping = {
        "discipline_network": "偏向持续渗透、隐蔽施压和纪律性布线",
        "contract_predator": "偏向围绕合同、预算和执行权争夺施压",
        "containment_cadre": "偏向以安保、封控和事故压制来稳住外溢",
        "extraction_broker": "偏向通过资源、补给和调拨杠杆施压",
        "adaptive_network": "偏向根据局势变化快速改换落点和施压方式",
    }
    return mapping.get(faction.operational_style, faction.operational_style)


def _truth_faction_operational_style_value(style: str) -> str:
    mapping = {
        "discipline_network": "纪律化渗透网络",
        "contract_predator": "合同与预算捕食型打法",
        "containment_cadre": "封控压稳型打法",
        "extraction_broker": "资源与补给经纪型打法",
        "adaptive_network": "自适应切线网络",
    }
    return mapping.get(style, _humanize_enum_token(style))


def _faction_dependency_profile_label(project_count: int, supply_count: int, faction: Faction) -> str:
    if project_count >= 2 and supply_count >= 2:
        return "同时依赖工程链和运输链，组织厚度较高但维护成本也更高"
    if project_count >= 2:
        return "对项目链依赖更强，若执行秩序失稳，组织动作会明显受限"
    if supply_count >= 2:
        return "对补给链依赖更强，若路由或放行收紧，组织动作会快速迟滞"
    if faction.rival_factions or faction.allied_factions:
        return "对关系网络依赖较高，组织稳定性受联盟和对抗格局牵制"
    return "依赖结构仍偏轻，能灵活转向，但持续经营能力有限"


def _faction_stability_state_label(faction: Faction) -> str:
    mapping = {
        "locked": "当前风格已经固化，组织行为具有较强连续性",
        "steady": "当前风格基本稳定，但仍保留一定弹性",
        "contested": "组织内部或外围压力正在争夺主导风格",
        "redirected": "组织风格刚被改道，后续数步仍可能继续偏转",
        "forming": "组织风格仍在形成，动作模式尚未完全固定",
    }
    return mapping.get(faction.operational_style_stability, faction.operational_style_stability)


def _truth_civilization_posture_stability_value(civilization: Civilization) -> str:
    mapping = {
        "crisis_locked": "当前战略已经被危机锁住，短期很难脱离既定压力轴",
        "steady": "当前战略基本稳定，但仍保留有限调整空间",
        "contested": "内部不同战略方向仍在争夺主导权",
        "redirected": "战略刚被改道，后续数步仍可能继续偏转",
        "forming": "整体战略仍在成形，尚未完全稳固",
    }
    return mapping.get(civilization.strategic_posture_stability, _humanize_enum_token(civilization.strategic_posture_stability))


def _truth_civilization_posture_pending_value(civilization: Civilization) -> str:
    mapping = {
        "none": "暂未出现明确转向征兆",
        "containment_first": "正在向异常压制与封控优先偏转",
        "megastructure_expansion": "正在向工程扩张优先偏转",
        "stability_over_growth": "正在向维稳优先偏转",
        "opportunistic_extraction": "正在向机会性攫取偏转",
        "balanced_competition": "正在回到多线并行的均衡竞争",
    }
    return mapping.get(civilization.strategic_posture_pending, _humanize_enum_token(civilization.strategic_posture_pending))


def _truth_civilization_posture_pending_hits_value(civilization: Civilization) -> str:
    hits = civilization.strategic_posture_pending_hits
    if hits <= 0:
        return "0（转向积累尚未形成）"
    return f"{hits}（转向迹象已连续累积）"


def _truth_faction_pending_style_label(faction: Faction) -> str:
    mapping = {
        "none": "暂未出现明确转向征兆",
        "project_bias": "正在向项目/工程线偏移",
        "supply_bias": "正在向补给/调拨线偏移",
        "security_bias": "正在向安保/封控线偏移",
        "political_bias": "正在向政治/组织角力线偏移",
        "anomaly_bias": "正在向异常控制与解释权线偏移",
    }
    return mapping.get(faction.operational_style_pending, _humanize_enum_token(faction.operational_style_pending))


def _truth_faction_pending_hits_label(faction: Faction) -> str:
    hits = faction.operational_style_pending_hits
    if hits <= 0:
        return "0（转向积累尚未形成）"
    return f"{hits}（转向迹象已连续累积）"


def _truth_front_family_value(token: str) -> str:
    mapping = {
        "supply_fronts": "补给前线",
        "governance_fronts": "治理前线",
        "project_fronts": "项目/工程前线",
        "anomaly_fronts": "异常前线",
        "megastructure_pressure": "巨构压力",
    }
    return mapping.get(token, _humanize_enum_token(token))


def _format_presence_detail_block(world: WorldState, relic: Relic) -> str:
    family = presence_event_family(relic)
    region = world.regions[relic.current_region_id]
    related_events = [
        event for event in world.event_stream.recent(60) if relic.relic_id in event.relic_refs
    ]
    recent_types = [event.event_type for event in related_events[-4:]]

    lines = ["  存在画像:"]
    if family == "megastructure":
        phase_tendency = "仍在失稳波动"
        if any(
            event_type in {"megastructure_phase_advance", "megastructure_groundbreaking", "megastructure_grid_link", "megastructure_reactivation"}
            for event_type in recent_types
        ):
            phase_tendency = "仍在向前推进"
        elif any("stall" in event_type or "crisis" in event_type for event_type in recent_types):
            phase_tendency = "推进明显受阻"
        sponsor_name = _format_entity_ref(world, relic.sponsor_ref) if relic.sponsor_ref else "尚未形成稳定赞助方"
        contractor_name = _format_entity_ref(world, relic.contractor_ref) if relic.contractor_ref else "尚未形成稳定执行方"
        financier_name = _format_entity_ref(world, relic.financier_ref) if relic.financier_ref else "尚未形成稳定资金方"
        opposition_name = _format_entity_ref(world, relic.opposition_ref) if relic.opposition_ref else "尚未出现稳定阻力方"
        lines.append(f"    阶段走势: {phase_tendency}")
        lines.append(f"    起源轮廓: {megastructure_origin_label(relic)}")
        lines.append(f"    建设态势: {_humanize_enum_token(relic.construction_state)}")
        lines.append(f"    赞助方: {sponsor_name}")
        lines.append(f"    执行方: {contractor_name}")
        lines.append(f"    资金方: {financier_name}")
        lines.append(f"    阻力方: {opposition_name}")
        lines.append(f"    基建耦合: {_player_level_value(region.infrastructure)}")
        lines.append(f"    繁荣耦合: {_player_level_value(region.prosperity)}")
        lines.append(f"    建造方向: {'当代扩展工程' if is_contemporary_megastructure(relic) else '旧时代遗构修复'}")
        lines.append(f"    运行压力: 安保={_player_level_value(region.security)}，稀缺={_player_level_value(region.scarcity)}")
    elif family == "autonomous_system":
        governance_pressure = "治理压力偏高" if region.political_tension == "high" else "治理压力中位"
        if any("lockdown" in event_type for event_type in recent_types):
            governance_pressure = "治理压力暂被封控压住"
        lines.append(f"    治理压力: {governance_pressure}")
        lines.append(f"    合法性表层: {_player_level_value(world.civilizations[region.civ_id].legitimacy) if region.civ_id in world.civilizations else '未知'}")
        lines.append(f"    安保表层: {_player_level_value(region.security)}")
        lines.append(f"    协议状态: {_player_status_value(relic.activation_state)}")
    elif family == "sealed_archive":
        disclosure_pressure = "披露压力偏高" if any("shock" in event_type for event_type in recent_types) else "披露压力暂被压住"
        lines.append(f"    披露压力: {disclosure_pressure}")
        lines.append(f"    合法性表层: {_player_level_value(world.civilizations[region.civ_id].legitimacy) if region.civ_id in world.civilizations else '未知'}")
        lines.append(f"    政治裂缝: {_player_level_value(region.political_tension)}")
        lines.append(f"    档案状态: {_player_status_value(relic.activation_state)}")
    elif family == "anomalous_lifeform":
        behavior_pressure = "生物安防压力正在升高" if any("expansion" in event_type for event_type in recent_types) else "生物安防压力暂被压住"
        lines.append(f"    起源轮廓: {_humanize_enum_token(relic.origin_mode)}")
        lines.append(f"    行为态势: {_humanize_enum_token(relic.construction_state)}")
        lines.append(f"    生物安防压力: {behavior_pressure}")
        lines.append(f"    生态表层: {_player_level_value(region.ecological_stress)}")
        lines.append(f"    安保表层: {_player_level_value(region.security)}")
        lines.append(f"    稀缺余波: {_player_level_value(region.scarcity)}")
    else:
        lines.append(f"    接入压力: {_player_status_value(relic.activation_state)}")
        lines.append(f"    地区安保: {_player_level_value(region.security)}")
        lines.append(f"    地区紧张度: {_player_level_value(region.political_tension)}")
    return "\n".join(lines)


def _dedupe_relation_entries(entries: list[tuple[str, str]], limit: int) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for key, text in entries:
        if key in seen:
            continue
        seen.add(key)
        unique.append(text)
    return unique[:limit]


def _format_faction_refs(world: WorldState, faction_ids: list[str]) -> list[str]:
    return [
        f"{world.factions[faction_id].name} ({faction_id})"
        if faction_id in world.factions
        else faction_id
        for faction_id in faction_ids
    ]


def _format_region_nodes_for_region(world: WorldState, region_id: str, *, player_view: bool) -> str:
    nodes = [
        node
        for node in world.region_nodes.values()
        if node.region_id == region_id
    ][:6]
    if player_view:
        if not nodes:
            return "  地区节点: 外界暂未看出稳定设施节点"
        node_types = "、".join(_player_region_node_type_value(node.node_type) for node in nodes[:4])
        return f"  地区节点: 外界能看出 {len(nodes)} 个关键接口，主要包括{node_types}"
    if not nodes:
        return "  地区节点: 尚未形成稳定设施节点"
    entries = [
        f"{node.name} ({node.node_id}, {_player_region_node_type_value(node.node_type)}, {_truth_goal_status_value(node.contention_state)})"
        for node in nodes
    ]
    return "  地区节点: " + "；".join(entries)


def _recent_region_node_events(world: WorldState, node: RegionNode, *, limit: int) -> list[Event]:
    linked_refs = {
        ref
        for ref in [
            node.linked_project_id,
            node.linked_supply_id,
            node.linked_relic_id,
        ]
        if ref
    }
    events = []
    for event in world.event_stream.recent(80):
        if node.node_id in event.node_refs:
            events.append(event)
            continue
        if linked_refs.intersection(event.project_refs + event.supply_refs + event.relic_refs):
            events.append(event)
            continue
        if node.region_id in event.region_refs:
            events.append(event)
            continue
        if node.linked_relic_id and node.linked_relic_id in event.relic_refs:
            events.append(event)
            continue
        if node.linked_project_id and "project" in event_theme_tags(event):
            events.append(event)
            continue
        if node.linked_supply_id and "supply" in event_theme_tags(event):
            events.append(event)
            continue
        if linked_refs.intersection(event.actor_refs + event.faction_refs + event.civ_refs):
            events.append(event)
    return events[-limit:]


def _recent_dynamic_structure_events(
    world: WorldState,
    structure: DynamicStructure,
    *,
    limit: int,
) -> list[Event]:
    linked_refs = set(structure.scope_refs + structure.linked_refs)
    events: list[Event] = []
    for event in world.event_stream.recent(80):
        if structure.structure_id in event.dynamic_structure_refs:
            events.append(event)
            continue
        event_refs = set(
            event.region_refs
            + event.civ_refs
            + event.actor_refs
            + event.faction_refs
            + event.relic_refs
            + event.project_refs
            + event.supply_refs
            + event.node_refs
            + event.dynamic_structure_refs
        )
        if linked_refs.intersection(event_refs):
            events.append(event)
    return events[-limit:]


def _recent_emergent_presence_events(
    world: WorldState,
    presence: EmergentPresence,
    *,
    limit: int,
) -> list[Event]:
    linked_refs = set(
        presence.current_region_refs
        + presence.linked_relic_refs
        + presence.linked_dynamic_refs
        + presence.linked_faction_refs
    )
    events: list[Event] = []
    for event in world.event_stream.recent(80):
        if presence.presence_id in event.emergent_presence_refs:
            events.append(event)
            continue
        event_refs = set(
            event.region_refs
            + event.civ_refs
            + event.actor_refs
            + event.faction_refs
            + event.relic_refs
            + event.project_refs
            + event.supply_refs
            + event.node_refs
            + event.dynamic_structure_refs
            + event.emergent_presence_refs
        )
        if linked_refs.intersection(event_refs):
            events.append(event)
    return events[-limit:]


def _dynamic_structure_type_label(structure_type: str) -> str:
    mapping = {
        "local_group": "局部群体",
        "incident_site": "事件现场",
        "rumor_network": "传闻网络",
        "proxy_cell": "代理单元",
        "anomaly_trace": "异常痕迹",
    }
    return mapping.get(structure_type, _humanize_enum_token(structure_type))


def _emergent_presence_type_label(presence_type: str) -> str:
    mapping = {
        "spore_bloom": "孢子潮",
        "migrant_swarm": "迁移群",
        "mycelial_mat": "菌毯基质",
        "feral_cluster": "野化群落",
        "signal_biota": "信号生物群",
    }
    return mapping.get(presence_type, _humanize_enum_token(presence_type))


def _emergent_presence_stage_label(stage: str) -> str:
    mapping = {
        "forming": "正在成形",
        "spreading": "正在扩散",
        "nesting": "正在筑巢",
        "adapting": "正在适应封控",
        "retreating": "正在退缩",
        "dormant": "暂时休眠",
    }
    return mapping.get(stage, _humanize_enum_token(stage))


def _emergent_presence_scale_label(scale: str) -> str:
    mapping = {
        "trace": "零散痕迹",
        "cluster": "小型群簇",
        "colony": "稳定群落",
        "swarm": "群潮规模",
        "regional": "地区级扩散",
    }
    return mapping.get(scale, _humanize_enum_token(scale))


def _emergent_presence_mobility_label(mobility: str) -> str:
    mapping = {
        "fixed": "基本固着",
        "local": "局部移动",
        "migrating": "出现迁移",
        "distributed": "分布式活动",
    }
    return mapping.get(mobility, _humanize_enum_token(mobility))


def _format_emergent_presence_links_for_ref(
    world: WorldState,
    ref: str,
    *,
    player_view: bool,
) -> str:
    presences = [
        presence
        for presence in world.emergent_presences.values()
        if presence.status != "archived"
        and ref in set(
            presence.current_region_refs
            + presence.linked_relic_refs
            + presence.linked_dynamic_refs
            + presence.linked_faction_refs
            + presence.influence_refs
        )
    ]
    if player_view:
        presences = [
            presence
            for presence in presences
            if presence.visibility in {"public", "visible", "rumored"}
        ]
    presences.sort(
        key=lambda presence: (
            _pressure_thread_intensity_rank(presence.pressure),
            presence.updated_tick,
            presence.presence_id,
        ),
        reverse=True,
    )
    if not presences:
        return "  异常生态: 外界暂未看出稳定生态牵连" if player_view else "  emergent_presences: None"

    if player_view:
        type_text = "、".join(
            _emergent_presence_type_label(presence.presence_type)
            for presence in presences[:3]
        )
        strongest = presences[0]
        return (
            f"  异常生态: 外界能看出 {len(presences)} 组生态牵连，"
            f"主要像是{type_text}，最高压力约为{_player_level_value(strongest.pressure)}"
        )

    lines = ["  emergent_presences:"]
    for presence in presences[:5]:
        lines.append(
            "    - "
            f"{_format_entity_ref(world, presence.presence_id)} "
            f"[type={presence.presence_type}, status={presence.status}, "
            f"stage={presence.lifecycle_stage}, pressure={presence.pressure}, "
            f"visibility={presence.visibility}] {presence.summary}"
        )
    return "\n".join(lines)


def _format_dynamic_structure_links_for_ref(
    world: WorldState,
    ref: str,
    *,
    player_view: bool,
) -> str:
    structures = [
        structure
        for structure in world.dynamic_structures.values()
        if structure.status != "archived"
        and ref in set(structure.scope_refs + structure.linked_refs + structure.influence_refs)
    ]
    if player_view:
        structures = [
            structure
            for structure in structures
            if structure.visibility in {"public", "visible", "rumored"}
        ]
    structures.sort(
        key=lambda structure: (
            _pressure_thread_intensity_rank(structure.pressure),
            structure.updated_tick,
            structure.structure_id,
        ),
        reverse=True,
    )
    if not structures:
        return "  动态线索: 外界暂未看出稳定动态牵连" if player_view else "  dynamic_structures: None"

    if player_view:
        type_text = "、".join(
            _dynamic_structure_type_label(structure.structure_type)
            for structure in structures[:3]
        )
        strongest = structures[0]
        return (
            f"  动态线索: 外界能看出 {len(structures)} 条动态牵连，"
            f"主要像是{type_text}，最高压力约为{_player_level_value(strongest.pressure)}"
        )

    lines = ["  dynamic_structures:"]
    for structure in structures[:5]:
        lines.append(
            "    - "
            f"{_format_entity_ref(world, structure.structure_id)} "
            f"[type={structure.structure_type}, status={structure.status}, "
            f"pressure={structure.pressure}, visibility={structure.visibility}] "
            f"{structure.summary}"
        )
    return "\n".join(lines)


def _player_node_controller_hint(node: RegionNode) -> str:
    if node.controller_ref:
        return "外界能看出这里存在相对明确的控制方"
    return "外界暂时看不出稳定控制方"


def _format_region_node_links(world: WorldState, node: RegionNode, *, player_view: bool) -> list[str]:
    lines: list[str] = []
    if node.linked_project_id:
        lines.append(
            _view_ref_line(
                world,
                player_view=player_view,
                truth_label="linked_project",
                ref=node.linked_project_id,
                player_label="关联项目",
            )
        )
    if node.linked_supply_id:
        lines.append(
            _view_ref_line(
                world,
                player_view=player_view,
                truth_label="linked_supply",
                ref=node.linked_supply_id,
                player_label="关联补给",
            )
        )
    if node.linked_relic_id:
        lines.append(
            _view_ref_line(
                world,
                player_view=player_view,
                truth_label="linked_relic",
                ref=node.linked_relic_id,
                player_label="关联异常",
            )
        )
    if not lines:
        lines.append("  关联对象: 外界暂未看出稳定牵连" if player_view else "  关联对象: 尚未绑定稳定对象")
    return lines


def _format_region_node_recent_notes(world: WorldState, node: RegionNode, *, player_view: bool) -> str:
    if player_view:
        return "  近期线索: 外界只能看出节点状态仍在被局势反复牵动"
    if not node.recent_notes:
        return "  recent_notes: 暂无连续节点记录"
    cleaned = [
        _truth_region_node_note(world, note)
        for note in node.recent_notes[-6:]
    ]
    return "  recent_notes:\n    概述: " + "；".join(cleaned)


def _truth_region_node_note(world: WorldState, note: str) -> str:
    if note.startswith("state="):
        return "态势=" + _truth_goal_status_value(note.split("=", 1)[1])
    if note.startswith("pressure="):
        return "压力=" + _player_level_value(note.split("=", 1)[1])
    if note.startswith("controller="):
        return "控制方=" + _format_entity_ref(world, note.split("=", 1)[1])
    if "@" in note and ":" in note:
        event_part = note.split(":", 1)[1].split("@", 1)[0]
        return "事件牵动=" + _player_event_type_label(event_part)
    return _humanize_enum_token(note)


def _extract_origin_ref(world: WorldState, relic_id: str) -> str | None:
    for relation in relations_for_ref(world, relic_id, limit=12):
        if relation.relation_type == "originating_from" and relation.target_ref in world.regions:
            return relation.target_ref
    return None


def _format_character_front_response(
    world: WorldState,
    character: Character,
    region_id: str,
) -> str:
    candidate_events = [
        event
        for event in reversed(world.event_stream.recent(60))
        if region_id in event.region_refs
        and (
            character.char_id in event.actor_refs
            or any(faction_id in event.faction_refs for faction_id in character.affiliation)
            or event.relic_refs
        )
    ]
    if not candidate_events:
        return "    前线响应: 暂未形成稳定响应"

    focal_event = candidate_events[0]
    front_type = _derive_front_type(focal_event, world)
    focal_relics = ", ".join(_format_relic_refs(world, focal_event.relic_refs[:2])) or "regional pressure"
    pressure_axis = _derive_event_pressure(world, region_id, focal_event)
    front_type_text = {
        "project_front": "项目前线",
        "containment_front": "封控前线",
        "anomaly_front": "异常前线",
        "supply_front": "补给前线",
        "organization_front": "组织前线",
    }.get(front_type, _humanize_enum_token(front_type))
    pressure_axis_text = {
        "construction_order": "工程秩序",
        "supply_pressure": "补给压力",
        "governance_legitimacy": "治理合法性",
        "political_legitimacy": "政治合法性",
        "biosecurity_front": "生物安防",
        "ecological_intrusion": "生态侵入",
        "anomalous_pressure": "异常压力",
        "political_control": "政治控制",
        "regional_pressure": "地区压力",
    }.get(pressure_axis, _humanize_enum_token(pressure_axis))
    return "\n".join(
        [
            "    前线响应:",
            f"      前线性质: {front_type_text}",
            f"      焦点对象: {focal_relics}",
            f"      压力轴线: {pressure_axis_text}",
            f"      响应缘由: {_format_truth_event_summary(world, focal_event)}",
        ]
    )


def _format_character_frontier_history(world: WorldState, character: Character) -> str:
    if not character.frontier_history:
        return "  行动轨迹: 暂未积累到可追踪的前线动作"
    lines = ["  行动轨迹:"]
    for item in character.frontier_history[-6:]:
        lines.append(f"    - {_truth_character_trace_item(item, world)}")
    return "\n".join(lines)


def _format_character_frontier_theme(world: WorldState, character: Character) -> str:
    if character.frontier_theme == "none":
        return "  前线主题: 暂未形成稳定前线主题"
    focus_reason = _clean_character_focus_reason_text(character)
    lines = [f"  前线主题: {_format_character_current_role(character).split(': ', 1)[1]}"]
    lines.append(f"  主题强度: {_truth_frontier_theme_strength_value(character.frontier_theme_strength)}")
    lines.append(f"  主题变化: {_player_trend_value(character.frontier_theme_shift)}")
    lines.append(f"  上一主题: {_truth_frontier_theme_value(character.frontier_previous_theme)}")
    lines.append(f"  焦点对象: {_truth_frontier_focus_ref(world, character.frontier_focus_ref)}")
    lines.append(f"  焦点类型: {_truth_frontier_focus_type_value(character.frontier_focus_type)}")
    lines.append(f"  焦点变化: {_truth_frontier_focus_shift_value(character.frontier_focus_shift)}")
    lines.append(f"  焦点缘由: {focus_reason}")
    if character.frontier_focus_trace:
        lines.append("  焦点轨迹:")
        for item in character.frontier_focus_trace[-4:]:
            lines.append(f"    - {_truth_character_trace_item(item, world)}")
    else:
        lines.append("  焦点轨迹: 暂未形成连续切换记录")
    if character.frontier_theme_trace:
        lines.append("  主题轨迹:")
        for item in character.frontier_theme_trace[-4:]:
            lines.append(f"    - {_truth_character_trace_item(item, world)}")
    else:
        lines.append("  主题轨迹: 暂未记录到连续主题变化")
    return "\n".join(lines)


def _truth_frontier_focus_ref(world: WorldState, ref: str) -> str:
    if ref in {"none", "", "regional_pressure"}:
        return "尚未固定为单一对象"
    return _format_entity_ref(world, ref)


def _format_character_current_role(character: Character) -> str:
    mapping = {
        "project_operator": "项目操盘者",
        "biosecurity_hunter": "异常扩散追猎者",
        "containment_stabilizer": "封控稳定执行者",
        "political_leverage_runner": "政治杠杆推动者",
        "mixed_front_operator": "多前线穿梭者",
        "none": "None",
    }
    return "  当前世界角色: " + mapping.get(character.frontier_theme, character.frontier_theme)


def _player_character_role_text(character: Character) -> str:
    mapping = {
        "project_operator": "  行动侧重: 更常围绕项目线和执行秩序行动",
        "biosecurity_hunter": "  行动侧重: 更常围绕异常扩散与封堵边界行动",
        "containment_stabilizer": "  行动侧重: 更常围绕封控、压制与稳定局势行动",
        "political_leverage_runner": "  行动侧重: 更常围绕权力与杠杆转移行动",
        "mixed_front_operator": "  行动侧重: 行动方向较分散，常在多条线之间切换",
        "none": "  行动侧重: 外界暂时看不清其稳定行动方向",
    }
    return mapping.get(character.frontier_theme, "  行动侧重: 外界只能看出此人仍在活跃施力")


def _format_character_active_front(world: WorldState, character: Character) -> str:
    focus_ref = character.frontier_focus_ref
    focus_type = character.frontier_focus_type
    if focus_ref in {"none", ""}:
        return "  active_front: 暂未形成稳定前线"
    if focus_type == "project" and focus_ref in world.projects:
        project = world.projects[focus_ref]
        return f"  active_front: 项目线::{project.name} [状态={_player_status_value(project.status)}, 压力={_player_level_value(project.pressure)}]"
    if focus_type == "supply" and focus_ref in world.supply_lines:
        supply = world.supply_lines[focus_ref]
        return f"  active_front: 补给线::{supply.name} [状态={_player_status_value(supply.status)}, 压力={_player_level_value(supply.pressure)}]"
    return f"  active_front: {_humanize_enum_token(focus_type)}::{_format_entity_ref(world, focus_ref)}"


def _player_character_active_front(world: WorldState, character: Character) -> str:
    focus_ref = character.frontier_focus_ref
    focus_type = character.frontier_focus_type
    if focus_ref in {"none", ""}:
        return "  当前前线: 外界暂时看不清他真正盯住的前线"
    if focus_type == "project" and focus_ref in world.projects:
        project = world.projects[focus_ref]
        return f"  当前前线: 项目线 [{_player_pressure_band(project.pressure)}]"
    if focus_type == "supply" and focus_ref in world.supply_lines:
        supply = world.supply_lines[focus_ref]
        return f"  当前前线: 补给线 [{_player_pressure_band(supply.pressure)}]"
    if focus_type == "presence":
        return "  当前前线: 异常前线 [存在可见牵引]"
    return "  当前前线: 某条仍在升温的局部前线"


def _format_character_why_now(world: WorldState, character: Character) -> str:
    bits = [ _clean_character_focus_reason_text(character) ]
    if character.frontier_focus_type == "project" and character.frontier_focus_ref in world.projects:
        project = world.projects[character.frontier_focus_ref]
        bits.append(_project_pressure_text(project))
    elif character.frontier_focus_type == "supply" and character.frontier_focus_ref in world.supply_lines:
        supply = world.supply_lines[character.frontier_focus_ref]
        bits.append(_supply_pressure_text(supply))
    return "  why_now: " + " | ".join(bit for bit in bits if bit)


def _player_character_why_now(world: WorldState, character: Character) -> str:
    focus_type = character.frontier_focus_type
    if focus_type == "project" and character.frontier_focus_ref in world.projects:
        project = world.projects[character.frontier_focus_ref]
        return (
            "  为何此刻: 外界能看出这名角色正在被项目推进压力、执行秩序或预算波动牵住。"
            f" 当前体感为{_player_pressure_band(project.pressure)}。"
        )
    if focus_type == "supply" and character.frontier_focus_ref in world.supply_lines:
        supply = world.supply_lines[character.frontier_focus_ref]
        return (
            "  为何此刻: 外界能看出这名角色正在围绕运输、放行或资源分配节点活动。"
            f" 当前体感为{_player_pressure_band(supply.pressure)}。"
        )
    if focus_type == "presence":
        return "  为何此刻: 可见线索显示，他正被某个异常焦点反复牵回同一条前线。"
    return "  为何此刻: 公开层面的压力线正在把他的动作收束到同一方向。"


def _player_character_frontier_theme(character: Character) -> str:
    return "  前线收束: 外界能看出他近期的动作在逐渐收束成一条稳定前线"


def _player_character_focus_competitors(world: WorldState, character: Character) -> str:
    focus_ref = character.frontier_focus_ref
    if focus_ref in {"none", "", "regional_pressure"}:
        return "  竞争迹象: 外界尚未看出稳定竞争格局"
    return _format_character_focus_competitors_clean(world, character)


def _player_character_frontier_history(character: Character) -> str:
    if not character.frontier_history:
        return "  行动轨迹: 外界尚未积累到足够行动痕迹"
    return f"  行动轨迹: 公开可见的关键动作约 {min(len(character.frontier_history), 6)} 次，且方向正在收束"


def _player_count_hint(count: int, unit: str) -> str:
    if count <= 0:
        return "None"
    if count == 1:
        return f"1 {unit}"
    if count <= 3:
        return f"{count} {unit}"
    return f"{count}+ {unit}"


def _player_relation_block(world: WorldState, ref: str, *, label: str) -> str:
    relation_count = len(relations_for_ref(world, ref, limit=12))
    if relation_count <= 0:
        return f"  {label}: 外界尚未看出稳定关系链"
    return f"  {label}: 外界能看出这里已经形成 {relation_count} 条以上的持续关系痕迹"


def _format_pressure_threads_for_ref(world: WorldState, ref: str, *, player_view: bool) -> str:
    threads = [
        thread
        for thread in world.pressure_threads.values()
        if thread.scope_ref == ref and thread.status != "dormant"
    ]
    if player_view:
        threads = [
            thread for thread in threads
            if thread.visibility in {"public", "visible", "rumored"}
        ]
    threads.sort(
        key=lambda thread: (
            _pressure_thread_intensity_rank(thread.intensity),
            thread.updated_tick,
        ),
        reverse=True,
    )
    if not threads:
        return "  局势线索: 外界暂未看出稳定连续线索" if player_view else "  pressure_threads: None"

    if player_view:
        theme_text = "、".join(_pressure_thread_theme_label(thread.theme) for thread in threads[:3])
        strongest = threads[0]
        clue_text = _pressure_thread_player_clue_text(threads)
        line = (
            f"  局势线索: 外界能看出 {len(threads)} 条持续线索，"
            f"主要集中在{theme_text}，最高压力约为{_player_level_value(strongest.intensity)}"
        )
        return f"{line}；最近可见：{clue_text}" if clue_text else line

    lines = ["  pressure_threads:"]
    for thread in threads[:5]:
        lines.append(
            "    - "
            f"{_pressure_thread_theme_label(thread.theme)} "
            f"[status={_pressure_thread_status_label(thread.status)}, "
            f"intensity={_player_level_value(thread.intensity)}, "
            f"updated=tick {thread.updated_tick}] {thread.summary}"
        )
    return "\n".join(lines)


def _pressure_thread_player_clue_text(threads) -> str:
    clues: list[str] = []
    for thread in threads:
        for clue in thread.public_clues:
            if clue and clue not in clues:
                clues.append(clue)
            if len(clues) >= 2:
                return "；".join(clues)
    return "；".join(clues)


def _pressure_thread_intensity_rank(intensity: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(intensity, 0)


def _pressure_thread_theme_label(theme: str) -> str:
    mapping = {
        "project": "项目线",
        "supply": "补给线",
        "anomaly": "异常线",
        "politics": "政治线",
        "security": "安保线",
        "organization": "组织线",
        "macro": "宏观压力",
    }
    return mapping.get(theme, _humanize_enum_token(theme))


def _pressure_thread_status_label(status: str) -> str:
    mapping = {
        "forming": "成形中",
        "active": "持续发酵",
        "escalating": "正在升温",
        "cooling": "开始降温",
        "dormant": "暂时沉底",
    }
    return mapping.get(status, _humanize_enum_token(status))


def _clean_character_focus_reason_text(character: Character) -> str:
    if character.frontier_focus_type == "project":
        return "角色当前正沿着项目网络推进，预算、合同和执行链已经成为他的主要追逐目标。"
    if character.frontier_focus_type == "supply":
        return "角色当前正沿着补给走廊推进，运输、储备和放行节点正在持续牵引他的行动。"
    if character.frontier_focus_type == "presence":
        return "角色当前被某个异常存在持续牵引，正在围绕它处理扩散、封控或控制权问题。"
    if character.frontier_focus_type == "region":
        return "角色最近的行动不断回到同一地区，这里已经变成他的主要施力点。"
    if character.frontier_focus_type == "pressure":
        return "角色当前是在跟随一类持续压力移动，而不是被单一对象固定住。"
    return character.frontier_focus_reason


def _character_focus_reason_text(character: Character) -> str:
    if character.frontier_focus_type == "project":
        return "角色当前正沿着项目网络推进，预算、合同和执行链已经成为他的主要追逐目标。"
    if character.frontier_focus_type == "supply":
        return "角色当前正沿着补给走廊推进，运输、储备和放行节点正在持续牵引他的行动。"
    return character.frontier_focus_reason


def _format_character_focus_competitors_clean(world: WorldState, character: Character) -> str:
    focus_ref = character.frontier_focus_ref
    focus_type = character.frontier_focus_type
    if focus_ref in {"none", "", "regional_pressure"}:
        return "  竞争迹象: 外界暂未看出稳定竞争格局"

    seen_refs: set[str] = {character.char_id}
    direct_rivals: list[str] = []
    institutional_owners: list[str] = []
    opportunistic_intruders: list[str] = []

    def push_entry(ref: str, *, via: str, bucket: str) -> None:
        if ref == character.char_id or ref in seen_refs:
            return
        if ref not in world.characters and ref not in world.factions:
            return
        seen_refs.add(ref)
        entry = f"      - {_player_display_name(world, ref)} [{via}]"
        if bucket == "direct_rivals":
            direct_rivals.append(entry)
        elif bucket == "institutional_owners":
            institutional_owners.append(entry)
        else:
            opportunistic_intruders.append(entry)

    for relation in relations_for_ref(world, focus_ref, limit=12):
        counterparty = relation.target_ref if relation.source_ref == focus_ref else relation.source_ref
        push_entry(
            counterparty,
            via=f"via=relation:{relation.relation_type}, strength={relation.strength}, tick={relation.updated_tick}",
            bucket=_focus_competitor_bucket_for_relation(relation.relation_type),
        )

    if focus_type == "project":
        project = world.projects.get(focus_ref)
        if project is not None:
            refs = (
                project.contractor_refs[:3]
                + project.financier_refs[:3]
                + project.opposition_refs[:3]
                + project.linked_characters[:4]
            )
            for ref in refs:
                bucket = "direct_rivals" if ref in project.opposition_refs else "institutional_owners"
                push_entry(ref, via="via=project_link", bucket=bucket)
    elif focus_type == "supply":
        supply_line = world.supply_lines.get(focus_ref)
        if supply_line is not None and supply_line.controlling_faction_ref:
            push_entry(
                supply_line.controlling_faction_ref,
                via=f"via=supply_control, tick={world.current_tick}",
                bucket="institutional_owners",
            )

    for event in reversed(world.event_stream.recent(80)):
        hit = False
        if focus_type == "presence":
            hit = focus_ref in event.relic_refs
        elif focus_type == "project":
            project = world.projects.get(focus_ref)
            hit = project is not None and bool(set(event.region_refs).intersection(project.linked_regions))
        elif focus_type == "supply":
            supply_line = world.supply_lines.get(focus_ref)
            hit = supply_line is not None and bool(
                set(event.region_refs).intersection(
                    {supply_line.origin_region_id, supply_line.destination_region_id}
                )
            )
        if not hit:
            continue
        for ref in event.actor_refs + event.faction_refs:
            push_entry(
                ref,
                via=f"via=event:{event.event_type}, severity={event.severity}, tick={event.tick}",
                bucket=_focus_competitor_bucket_for_event(event.event_type),
            )
        if len(direct_rivals) + len(institutional_owners) + len(opportunistic_intruders) >= 6:
            break

    if not direct_rivals and not institutional_owners and not opportunistic_intruders:
        return "  竞争迹象: 外界暂未看出稳定竞争格局"

    lines = ["  竞争迹象:"]
    lines.append(
        "    竞争态势概览: "
        + _clean_focus_competitor_pressure_summary(
            len(direct_rivals),
            len(institutional_owners),
            len(opportunistic_intruders),
        )
    )
    lines.append("    正面竞争者:" if direct_rivals else "    正面竞争者: 外界暂未看出")
    if direct_rivals:
        lines.extend(direct_rivals[:3])
    lines.append("    既有控制者:" if institutional_owners else "    既有控制者: 外界暂未看出")
    if institutional_owners:
        lines.extend(institutional_owners[:3])
    lines.append("    机会介入者:" if opportunistic_intruders else "    机会介入者: 外界暂未看出")
    if opportunistic_intruders:
        lines.extend(opportunistic_intruders[:3])
    return "\n".join(lines)


def _clean_focus_competitor_pressure_summary(
    direct_rival_count: int,
    institutional_owner_count: int,
    opportunistic_intruder_count: int,
) -> str:
    if direct_rival_count >= 2 and opportunistic_intruder_count >= 1:
        return "目标已经进入多人混战，正面争夺和外围介入都在升高。"
    if institutional_owner_count >= 2 and direct_rival_count == 0:
        return "目标有相对稳定的控制链，争夺主要表现为内部重排。"
    if institutional_owner_count >= 1 and direct_rival_count >= 1:
        return "目标同时存在占有者和挑战者，已经是明确的控制权前线。"
    if opportunistic_intruder_count >= 2 and institutional_owner_count == 0:
        return "目标主控不稳，机会性介入者正在持续涌入。"
    if direct_rival_count >= 1:
        return "目标已经出现正面争夺，竞争正在公开化。"
    if institutional_owner_count >= 1:
        return "目标已有明确控制链，外部竞争暂时没有压过既有结构。"
    return "目标周围存在零散介入者，但尚未形成稳定主控或全面混战。"


def _format_character_focus_competitors(world: WorldState, character: Character) -> str:
    focus_ref = character.frontier_focus_ref
    if focus_ref in {"none", "", "regional_pressure"}:
        return "  focus_competitors: None"

    seen_refs: set[str] = {character.char_id}
    direct_rivals: list[str] = []
    institutional_owners: list[str] = []
    opportunistic_intruders: list[str] = []

    for relation in relations_for_ref(world, focus_ref, limit=12):
        counterparty = relation.target_ref if relation.source_ref == focus_ref else relation.source_ref
        if counterparty == character.char_id or counterparty in seen_refs:
            continue
        if counterparty not in world.characters and counterparty not in world.factions:
            continue
        seen_refs.add(counterparty)
        entry = (
            "      - "
            f"{_format_entity_ref(world, counterparty)} "
            f"[via=relation:{relation.relation_type}, strength={relation.strength}, tick={relation.updated_tick}]"
        )
        bucket = _focus_competitor_bucket_for_relation(relation.relation_type)
        if bucket == "direct_rivals":
            direct_rivals.append(entry)
        elif bucket == "institutional_owners":
            institutional_owners.append(entry)
        else:
            opportunistic_intruders.append(entry)

    for event in reversed(world.event_stream.recent(80)):
        if focus_ref not in event.relic_refs:
            continue
        competitors = event.actor_refs + event.faction_refs
        for ref in competitors:
            if ref == character.char_id or ref in seen_refs:
                continue
            if ref not in world.characters and ref not in world.factions:
                continue
            seen_refs.add(ref)
            entry = (
                "      - "
                f"{_format_entity_ref(world, ref)} "
                f"[via=event:{event.event_type}, severity={event.severity}, tick={event.tick}]"
            )
            bucket = _focus_competitor_bucket_for_event(event.event_type)
            if bucket == "direct_rivals":
                direct_rivals.append(entry)
            elif bucket == "institutional_owners":
                institutional_owners.append(entry)
            else:
                opportunistic_intruders.append(entry)
        if len(direct_rivals) + len(institutional_owners) + len(opportunistic_intruders) >= 6:
            break

    if not direct_rivals and not institutional_owners and not opportunistic_intruders:
        return "  focus_competitors: None"

    lines = ["  focus_competitors:"]
    lines.append(
        "    competitor_pressure_summary: "
        + _summarize_focus_competitor_pressure(
            len(direct_rivals),
            len(institutional_owners),
            len(opportunistic_intruders),
        )
    )
    if direct_rivals:
        lines.append("    direct_rivals:")
        lines.extend(direct_rivals[:3])
    else:
        lines.append("    direct_rivals: None")
    if institutional_owners:
        lines.append("    institutional_owners:")
        lines.extend(institutional_owners[:3])
    else:
        lines.append("    institutional_owners: None")
    if opportunistic_intruders:
        lines.append("    opportunistic_intruders:")
        lines.extend(opportunistic_intruders[:3])
    else:
        lines.append("    opportunistic_intruders: None")
    return "\n".join(lines)


def _focus_competitor_bucket_for_relation(relation_type: str) -> str:
    if relation_type in {"contesting", "rival_to", "obstructing", "opposing"}:
        return "direct_rivals"
    if relation_type in {"controls", "contracting", "financing", "sponsoring", "seeking_control"}:
        return "institutional_owners"
    return "opportunistic_intruders"


def _focus_competitor_bucket_for_event(event_type: str) -> str:
    event_type = event_type.lower()
    if any(token in event_type for token in {"power_struggle", "contest", "attack", "breach"}):
        return "direct_rivals"
    if any(token in event_type for token in {"takeover", "phase_advance", "budget", "financing", "access_action"}):
        return "institutional_owners"
    return "opportunistic_intruders"


def _summarize_focus_competitor_pressure(
    direct_rival_count: int,
    institutional_owner_count: int,
    opportunistic_intruder_count: int,
) -> str:
    if direct_rival_count >= 2 and opportunistic_intruder_count >= 1:
        return "当前对象处于多人混战状态，正面争夺已经形成，旁路介入者也在持续加压"
    if institutional_owner_count >= 2 and direct_rival_count == 0:
        return "当前对象存在相对稳定的制度性占有，争夺更多表现为控制链内部重排"
    if institutional_owner_count >= 1 and direct_rival_count >= 1:
        return "当前对象同时存在占有者和挑战者，属于明确的控制权争夺前线"
    if opportunistic_intruder_count >= 2 and institutional_owner_count == 0:
        return "当前对象主控并不稳固，机会性介入者正在不断涌入并重塑局势"
    if direct_rival_count >= 1:
        return "当前对象已经出现正面争夺，竞争正在从潜伏转向公开对抗"
    if institutional_owner_count >= 1:
        return "当前对象已有明确控制链，外部竞争暂时没有压过既有占有结构"
    return "当前对象周围存在零散介入者，但尚未形成稳定主控或全面混战"


def _derive_pressure_axis(
    world: WorldState,
    region_id: str,
    event: Event,
    relic: Relic,
) -> str:
    themes = set(event_theme_tags(event))
    family = presence_event_family(relic)
    region = world.regions[region_id]
    if family == "megastructure":
        if "project" in themes:
            return "construction_order"
        if "supply" in themes or region.scarcity == "high":
            return "supply_pressure"
        return "infrastructure_control"
    if family == "autonomous_system":
        return "governance_legitimacy"
    if family == "sealed_archive":
        return "political_legitimacy"
    if family == "anomalous_lifeform":
        if "migration" in event.event_type.lower():
            return "biosecurity_front"
        return "ecological_intrusion"
    return "anomalous_pressure"


def _derive_event_pressure(world: WorldState, region_id: str, event: Event) -> str:
    if event.relic_refs:
        relic = world.relics.get(event.relic_refs[0])
        if relic is not None:
            return _derive_pressure_axis(world, region_id, event, relic)
    themes = set(event_theme_tags(event))
    if "project" in themes:
        return "construction_order"
    if "politics" in themes or "organization" in themes:
        return "political_control"
    if "supply" in themes:
        return "supply_pressure"
    return "regional_pressure"


def _derive_front_type(event: Event, world: WorldState) -> str:
    themes = set(event_theme_tags(event))
    if event.relic_refs:
        relic = world.relics.get(event.relic_refs[0])
        if relic is not None and relic.relic_type == "megastructure":
            return "project_front"
        if _is_containment_front(event):
            return "containment_front"
        return "anomaly_front"
    if "project" in themes:
        return "project_front"
    if "supply" in themes:
        return "supply_front"
    return "organization_front"


def _is_containment_front(event: Event) -> bool:
    event_type = event.event_type.lower()
    themes = set(event_theme_tags(event))
    return (
        "containment" in event_type
        or "suppression" in event_type
        or "lockdown" in event_type
        or ("security" in themes and "anomaly" in themes)
    )


def _is_project_front(event: Event, relic: Relic) -> bool:
    return relic.relic_type == "megastructure" or "project" in event_theme_tags(event)


def _is_civilization_expansion_line(event: Event, world: WorldState) -> bool:
    if "groundbreaking" in event.event_type or "grid_link" in event.event_type:
        return True
    if "project_bid" in event.event_type or "secure_project_budget" in event.event_type:
        return True
    if event.relic_refs:
        relic = world.relics.get(event.relic_refs[0])
        return relic is not None and relic.relic_type == "megastructure" and not _is_containment_front(event)
    return False


def _is_civilization_containment_line(event: Event) -> bool:
    if _is_containment_front(event):
        return True
    return "migration" in event.event_type or "lifeform" in event.event_type or "fallout" in event.event_type


def _dedupe_entries(entries: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for entry in entries:
        if entry in seen:
            continue
        seen.add(entry)
        unique.append(entry)
    return unique[:limit]


def _format_truth_event_summary(world: WorldState, event: Event) -> str:
    event_type = event.event_type.lower()
    themes = set(event_theme_tags(event))
    region_name = (
        _format_entity_ref(world, event.region_refs[0])
        if event.region_refs
        else "局部区域"
    )
    relic_name = (
        _format_entity_ref(world, event.relic_refs[0])
        if event.relic_refs
        else "异常焦点"
    )
    civ_name = (
        _format_entity_ref(world, event.civ_refs[0])
        if event.civ_refs
        else "相关文明"
    )

    if "resource_shift" in event_type:
        return f"{region_name} 的资源与稀缺压力出现了可见变动。"
    if "expansion_shift" in event_type:
        return f"{civ_name} 的扩张压力与外推进度出现了新的调整。"
    if "legitimacy_shift" in event_type:
        return f"{civ_name} 的合法性与秩序信心正在发生新的偏移。"
    if "security_cordon" in event_type or "lockdown" in event_type:
        return f"{region_name} 的安保封锁被明显抬高，项目表层控制增强，但局势也更脆。"
    if "stall" in event_type or "crisis" in event_type:
        return f"{relic_name} 在 {region_name} 再次失稳或停滞，正在把局地压力继续往上拖。"
    if "phase_advance" in event_type or "groundbreaking" in event_type or "grid_link" in event_type:
        return f"{relic_name} 所在的项目推进线出现了新的阶段性进展。"
    if "alliance" in event_type or "financing" in event_type:
        return f"{civ_name} 周边的协作或资金链出现了新的重排信号。"
    if "supply" in themes:
        return f"{region_name} 周边的运输与放行节奏正在变化。"
    if "project" in themes:
        return f"{relic_name} 所牵出的项目网络正在发生新的结构波动。"
    if "security" in themes:
        return f"{region_name} 的控制方式与风险壳层正在重新排列。"
    if "politics" in themes or "organization" in themes:
        return f"{region_name} 周边的组织角力正在继续升温。"
    return _player_localize_text(world, event.summary)


def _format_related_events(
    world: WorldState,
    events: list[Event],
    *,
    view: str = "truth",
) -> str:
    player_view = is_player_view(view)
    if not events:
        if player_view:
            return _line(_player_label("recent_events"), "外界暂未积累到连续公开动静")
        return _line("近期动静", "暂无连续事件回流")
    lines = [_line(_player_label("recent_events") if player_view else "近期动静", "").rstrip()]
    for event in events:
        summary_text = (
            format_event_summary_for_view(event, view=view, world=world)
            if player_view
            else _format_truth_event_summary(world, event)
        )
        summary_text = _player_localize_text(world, summary_text)
        lines.append(
            f"    - [{_player_event_type_label(event.event_type)}] "
            f"{summary_text}"
        )
    return "\n".join(lines)


def _find_civilization_bias_fronts(world: WorldState, civ_id: str) -> list[str]:
    entries: list[str] = []
    for event in reversed(world.event_stream.recent(100)):
        if civ_id not in event.civ_refs:
            continue
        focal_region = _format_entity_ref(world, event.region_refs[0]) if event.region_refs else "未知区域"
        if event.relic_refs:
            focal = ", ".join(_format_relic_refs(world, event.relic_refs[:2]))
        elif event.faction_refs:
            focal = ", ".join(_format_faction_refs(world, event.faction_refs[:2]))
        else:
            focal = "区域压力面"
        entries.append(_truth_front_event_projection(world, focus=focal, region=focal_region, event=event))
    return _dedupe_entries(entries, limit=4)
