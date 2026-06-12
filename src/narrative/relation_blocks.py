"""Shared relation rendering helpers for narrative summaries."""

from __future__ import annotations

from src.narrative.labels import (
    humanize_enum_token,
    player_level_value,
    truth_relation_status_value,
    truth_relation_type_value,
)
from src.narrative.names import format_entity_ref
from src.world.relations import relations_for_ref
from src.world.state import WorldState


def truth_relation_entry(
    *,
    subject: str,
    relation_type: str,
    strength: str | None = None,
    via: str | None = None,
    flow: str | None = None,
    tick: int | None = None,
) -> str:
    bits = [f"关系={truth_relation_type_value(relation_type)}"]
    if strength is not None:
        bits.append(f"压力={player_level_value(strength)}")
    if via:
        bits.append(f"经由={via}")
    if flow:
        flow_text = {
            "outbound": "向外施力",
            "inbound": "由外回流",
            "inbound/outbound": "双向往返",
            "outbound/inbound": "双向往返",
        }.get(flow, flow)
        bits.append(f"流向={flow_text}")
    if tick is not None:
        bits.append(f"最近更新=tick {tick}")
    return f"{subject} [{', '.join(bits)}]"


def truth_relation_focus_entry(
    *,
    subject: str,
    relation_type: str,
    strength: str,
    tick: int,
    note: str = "",
    shadow: str = "",
    status: str | None = None,
) -> str:
    bits = [
        f"关系={truth_relation_type_value(relation_type)}",
        f"压力={player_level_value(strength)}",
        f"最近更新=tick {tick}",
    ]
    if status:
        bits.append(f"状态={truth_relation_status_value(status)}")
    if note:
        bits.append(f"注记={note}")
    if shadow:
        bits.append(f"残影={shadow}")
    return f"{subject} [{', '.join(bits)}]"


def relation_priority(relation_type: str) -> int:
    if relation_type in {"rival_to", "contesting", "obstructing", "opposing"}:
        return 5
    if relation_type in {"infiltrating", "seeking_control", "flashpoint_actor"}:
        return 4
    if relation_type in {"controls", "contracting", "financing", "sponsoring", "supply_influence"}:
        return 3
    if relation_type in {"allied_with", "supports", "supporting", "stabilizes"}:
        return 2
    return 1


def relation_strength_priority(strength: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(strength, 0)


def group_relations_by_counterparty(relations, focal_ref: str):
    grouped: dict[str, list] = {}
    for relation in relations:
        counterparty = relation.target_ref if relation.source_ref == focal_ref else relation.source_ref
        grouped.setdefault(counterparty, []).append(relation)
    ordered: list[tuple[str, list]] = []
    for counterparty, items in grouped.items():
        items.sort(
            key=lambda relation: (
                relation_priority(relation.relation_type),
                relation_strength_priority(relation.strength),
                relation.updated_tick,
            ),
            reverse=True,
        )
        ordered.append((counterparty, items))
    ordered.sort(key=lambda item: item[1][0].updated_tick, reverse=True)
    return ordered


def relation_bucket_label(bucket: str) -> str:
    mapping = {
        "rivalry": "对抗轴",
        "alliance": "协作轴",
        "control": "控制轴",
        "covert": "渗透轴",
        "containment": "封控轴",
        "presence": "异常轴",
        "foothold": "落点轴",
        "other": "杂项轴",
    }
    return mapping.get(bucket, "杂项轴")


def relation_shadow_text(relations: list, dominant_type: str) -> str:
    if not relations:
        return ""
    shadow_types: list[str] = []
    for relation in relations:
        if relation.relation_type == dominant_type:
            continue
        if relation.relation_type not in shadow_types:
            shadow_types.append(relation.relation_type)
    return "/".join(truth_relation_type_value(relation_type) for relation_type in shadow_types[:2])


def humanize_relation_note(notes: str) -> str:
    if not notes:
        return ""
    lowered = notes.lower()
    if "infiltrate" in lowered and "foundry kernel" in lowered:
        return "异常正在沿协议暗线向外渗透"
    if "distort" in lowered and "foundry kernel" in lowered:
        return "异常正在扭曲周边秩序与控制界面"
    if "infiltrate" in lowered:
        return "相关力量正沿暗线持续渗入"
    if "distort" in lowered:
        return "相关力量正在扭曲周边秩序"
    if "moved to stabilize supply conditions in" in lowered:
        return "角色转向稳住补给条件"
    if "moved to secure relic access in" in lowered:
        return "角色转向争取异常接入权"
    if "moved to secure" in lowered:
        return "角色转向争取关键接入权"
    if "supply and logistics through" in lowered:
        return "组织改动了补给与物流走向"
    if "budget" in lowered and "control" in lowered:
        return "预算与控制链正在被重排"
    if "-faction-" in lowered and "..." in notes:
        return "相关组织正在沿既有前线继续施压"
    note = notes.replace("->", " to ").replace("_", " ").strip()
    if len(note) > 28:
        return note[:28].rstrip() + "..."
    return note


def format_relation_block(world: WorldState, ref: str, limit: int = 8) -> str:
    relations = relations_for_ref(world, ref, limit=limit)
    if not relations:
        return "  active_relations: 暂未形成稳定活动关系"

    lines = ["  active_relations:"]
    for counterparty, pair_relations in group_relations_by_counterparty(relations, ref):
        relation = pair_relations[0]
        note_text = humanize_relation_note(relation.notes)
        shadow_text = relation_shadow_text(pair_relations, relation.relation_type)
        lines.append(
            "    - "
            + truth_relation_focus_entry(
                subject=format_entity_ref(world, counterparty),
                relation_type=relation.relation_type,
                strength=relation.strength,
                tick=relation.updated_tick,
                note=note_text,
                shadow=shadow_text,
                status=relation.status,
            )
        )
    return "\n".join(lines)


def format_structure_relation_front(world: WorldState, ref: str, *, label: str) -> str:
    relations = [
        relation
        for relation in relations_for_ref(world, ref, limit=12)
        if relation.status == "active"
    ]
    if not relations:
        fallback = format_structure_participant_fallback(world, ref)
        return fallback if fallback is not None else f"  {label}: None"
    buckets: dict[str, list[str]] = {
        "owners": [],
        "operators": [],
        "funders": [],
        "opposition": [],
        "field_pressure": [],
    }
    seen: set[str] = set()
    for relation in relations:
        counterparty = relation.target_ref if relation.source_ref == ref else relation.source_ref
        key = f"{relation.relation_type}:{counterparty}"
        if key in seen:
            continue
        seen.add(key)
        entry = (
            f"{format_entity_ref(world, counterparty)} "
            f"[关系={truth_relation_type_value(relation.relation_type)}, 压力={player_level_value(relation.strength)}]"
        )
        if relation.relation_type in {"controls", "sponsoring"}:
            buckets["owners"].append(entry)
        elif relation.relation_type in {"contracting", "operates_in"}:
            buckets["operators"].append(entry)
        elif relation.relation_type in {"financing", "supply_influence"}:
            buckets["funders"].append(entry)
        elif relation.relation_type in {"obstructing", "opposing", "contesting"}:
            buckets["opposition"].append(entry)
        else:
            buckets["field_pressure"].append(entry)
    lines = [f"  {label}:"]
    rendered = [
        ("控制/归属", buckets["owners"]),
        ("执行/驻场", buckets["operators"]),
        ("资金/补给", buckets["funders"]),
        ("阻力", buckets["opposition"]),
        ("前线压力", buckets["field_pressure"]),
    ]
    has_content = False
    for section_name, entries in rendered:
        if not entries:
            continue
        has_content = True
        lines.append(f"    - {section_name}: {'；'.join(entries[:2])}")
    if not has_content:
        fallback = format_structure_participant_fallback(world, ref)
        return fallback if fallback is not None else f"  {label}: None"
    return "\n".join(lines)


def format_structure_participant_fallback(world: WorldState, ref: str) -> str | None:
    if ref in world.projects:
        project = world.projects[ref]
        civ_entries = [
            format_entity_ref(world, civ_id)
            for civ_id in project.linked_civs[:2]
            if civ_id in world.civilizations
        ]
        faction_entries = [
            format_entity_ref(world, faction_id)
            for faction_id in project.linked_factions[:3]
            if faction_id in world.factions
        ]
        character_entries = [
            format_entity_ref(world, char_id)
            for char_id in project.linked_characters[:2]
            if char_id in world.characters
        ]
        if not civ_entries and not faction_entries and not character_entries:
            return None
        lines = ["  organization_front:"]
        if civ_entries:
            lines.append(f"    - 上层归属: {'；'.join(civ_entries)}")
        if faction_entries:
            lines.append(f"    - 前线参与方: {'；'.join(faction_entries)}")
        if character_entries:
            lines.append(f"    - 现场人物: {'；'.join(character_entries)}")
        return "\n".join(lines)
    if ref in world.supply_lines:
        supply_line = world.supply_lines[ref]
        civ_entries = [
            format_entity_ref(world, civ_id)
            for civ_id in supply_line.linked_civ_refs[:2]
            if civ_id in world.civilizations
        ]
        if not civ_entries:
            return None
        return "  organization_front:\n    - 前线参与方: " + "；".join(civ_entries)
    return None
