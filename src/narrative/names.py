"""Display-name and entity-reference helpers for narrative summaries."""

from __future__ import annotations

from src.narrative.labels import player_region_node_type_value
from src.world.state import WorldState
from src.world.style_profile import get_narrative_lexicon


def player_world_name(name: str) -> str:
    token_map = {
        "Helion": "曦辉",
        "Orchid": "兰庭",
        "Sable": "玄墨",
        "Vanta": "暗穹",
        "Lattice": "晶格",
        "Morrow": "晨垣",
        "Cinder": "烬火",
        "Nacre": "珠壳",
        "Palisade": "栅垒",
        "Solace": "静慰",
        "Axiom": "公理",
        "Kestrel": "隼岬",
        "Sprawl": "广域",
        "Reach": "界沿",
        "Ring": "环带",
        "Basin": "盆地",
        "Yard": "场站",
        "Crown": "冠区",
        "Harbor": "港区",
        "Array": "阵列",
        "Fold": "褶区",
        "Ward": "防区",
        "Concord": "协和",
        "Meridian": "子午",
        "Aegis": "神盾",
        "Vector": "矢量",
        "Prax": "实用",
        "Aurora": "极光",
        "Halcyon": "宁澜",
        "Novarch": "新执",
        "Directorate": "理事局",
        "Compact": "联约体",
        "Syndicate": "联业体",
        "Federation": "联邦",
        "Mandate": "统领约",
        "Union": "联合体",
        "Accord": "协约",
        "Skyshield": "天幕",
        "Pillar": "天柱",
        "Lumen": "流明",
        "Aureline": "金辉",
        "Blackglass": "黑镜",
        "Starwell": "星井",
        "Crownline": "冠线",
        "Iron": "铁",
        "Bloom": "华簇",
        "Spine": "主脊",
        "Gate": "闸门",
        "Cascade": "瀑链",
        "Anchor": "锚点",
        "Column": "柱列",
        "Loop": "环轨",
        "Grid": "栅格",
        "Vault": "穹库",
        "Foundry": "铸炉",
        "Civic": "公域",
        "Threshold": "阈限",
        "Sentinel": "哨卫",
        "Quiet": "静默",
        "Kernel": "核心",
        "Protocol": "协议",
        "Directive": "指令",
        "Mesh": "网格",
        "Stack": "叠栈",
        "Ashen": "灰烬",
        "Glass": "玻镜",
        "Pale": "苍白",
        "Silent": "缄默",
        "Vaulted": "穹封",
        "Obsidian": "黑曜",
        "Ledger": "账本",
        "Repository": "典藏库",
        "Annals": "纪要",
        "Record": "档案",
        "Index": "索引",
        "Mire": "泥沼",
        "Halo": "晕环",
        "Shard": "碎棱",
        "Veil": "帷幕",
        "Drift": "漂移",
        "Swarm": "群簇",
        "Pack": "群包",
        "Choir": "合鸣",
        "Maw": "巨噬",
        "Signal": "信号",
        "Null": "零域",
        "Ember": "余烬",
        "Prism": "棱镜",
        "Tide": "潮汐",
        "Mirror": "镜面",
        "Engine": "引擎",
        "Relay": "中继",
        "Core": "核心",
        "Lens": "透镜",
        "Node": "节点",
    }
    if " -> " in name:
        return " -> ".join(player_world_name(part.strip()) for part in name.split(" -> "))
    base = name
    suffix = ""
    if "-" in name:
        candidate_base, candidate_suffix = name.rsplit("-", 1)
        if candidate_suffix.isdigit():
            base = candidate_base
            suffix = f"-{candidate_suffix}"
    translated = "".join(token_map.get(token, token) for token in base.split())
    return f"{translated}{suffix}" if translated else name


def player_project_name(name: str) -> str:
    cleaned = name.removesuffix(" Project Network").strip()
    return player_world_name(cleaned or name)


def player_supply_name(name: str) -> str:
    cleaned = name.removesuffix(" Supply Line").strip()
    return player_world_name(cleaned or name)


def player_region_node_name(world: WorldState, node) -> str:
    region_name = player_display_name(world, node.region_id)
    node_type = player_region_node_type_value(node.node_type)
    return f"{region_name}{node_type}"


def player_presence_display_name(relic, style_profile_id: str | None = None) -> str:
    lexicon = get_narrative_lexicon(style_profile_id)
    return lexicon.relic_presence_labels.get(
        relic.relic_type,
        lexicon.relic_presence_fallback_label,
    )


def player_presence_name(relic, style_profile_id: str | None = None) -> str:
    return f"{player_presence_display_name(relic, style_profile_id)}“{player_world_name(relic.name)}”"


def player_faction_type_label(faction_type: str, style_profile_id: str | None = None) -> str:
    lexicon = get_narrative_lexicon(style_profile_id)
    return lexicon.faction_type_labels.get(
        faction_type,
        lexicon.faction_type_fallback_label,
    )


def player_display_name(world: WorldState, ref: str) -> str:
    lexicon = get_narrative_lexicon(world.style_profile_id)
    if ref in world.characters:
        character = world.characters[ref]
        if character.name.startswith("Protagonist-"):
            suffix = character.name.split("-", 1)[1]
            return f"关键人物-{suffix}"
        return player_world_name(character.name)
    if ref in world.factions:
        faction = world.factions[ref]
        if "-Faction-" in faction.name:
            civ_name = (
                player_world_name(world.civilizations[faction.parent_civ_id].name)
                if faction.parent_civ_id in world.civilizations
                else "所属文明"
            )
            return f"{civ_name}旗下{player_faction_type_label(faction.faction_type, world.style_profile_id)}"
        return player_world_name(faction.name)
    if ref in world.regions:
        return player_world_name(world.regions[ref].name)
    if ref in world.relics:
        return player_presence_name(world.relics[ref], world.style_profile_id)
    if ref in world.civilizations:
        return player_world_name(world.civilizations[ref].name)
    if ref in world.projects:
        return f"{lexicon.project_display_prefix}“{player_project_name(world.projects[ref].name)}”"
    if ref in world.supply_lines:
        return f"{lexicon.supply_display_prefix}“{player_supply_name(world.supply_lines[ref].name)}”"
    if ref in world.region_nodes:
        return f"{lexicon.node_display_prefix}“{player_region_node_name(world, world.region_nodes[ref])}”"
    if ref in world.dynamic_structures:
        return f"{lexicon.dynamic_structure_display_prefix}“{player_world_name(world.dynamic_structures[ref].name)}”"
    if ref in world.emergent_presences:
        return f"{lexicon.emergent_presence_display_prefix}“{player_world_name(world.emergent_presences[ref].name)}”"
    return ref


def player_localize_text(world: WorldState, text: str) -> str:
    replacements: list[tuple[str, str]] = []
    for region in world.regions.values():
        replacements.append((region.name, player_world_name(region.name)))
    for civilization in world.civilizations.values():
        replacements.append((civilization.name, player_world_name(civilization.name)))
    for relic in world.relics.values():
        replacements.append((relic.name, player_world_name(relic.name)))
    for project in world.projects.values():
        replacements.append((project.name, player_project_name(project.name)))
    for supply_line in world.supply_lines.values():
        replacements.append((supply_line.name, player_supply_name(supply_line.name)))
    for node in world.region_nodes.values():
        replacements.append((node.name, player_region_node_name(world, node)))

    localized = text
    for raw, rendered in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        if raw and raw in localized:
            localized = localized.replace(raw, rendered)
    return localized


def format_entity_ref(world: WorldState, ref: str, player_view: bool = False) -> str:
    if player_view:
        return player_display_name(world, ref)
    if ref in world.region_nodes:
        return f"{world.region_nodes[ref].name} ({ref})"
    if ref in world.characters:
        return f"{world.characters[ref].name} ({ref})"
    if ref in world.factions:
        return f"{world.factions[ref].name} ({ref})"
    if ref in world.regions:
        return f"{world.regions[ref].name} ({ref})"
    if ref in world.relics:
        return f"{world.relics[ref].name} ({ref})"
    if ref in world.civilizations:
        return f"{world.civilizations[ref].name} ({ref})"
    if ref in world.projects:
        return f"{world.projects[ref].name} ({ref})"
    if ref in world.supply_lines:
        return f"{world.supply_lines[ref].name} ({ref})"
    if ref in world.dynamic_structures:
        return f"{world.dynamic_structures[ref].name} ({ref})"
    if ref in world.emergent_presences:
        return f"{world.emergent_presences[ref].name} ({ref})"
    return ref
