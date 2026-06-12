"""Shared event visibility and observer-facing text policies."""

from __future__ import annotations

from src.events.models import Event
from src.events.taxonomy import event_family, event_theme_tags
from src.narrative.visibility import is_player_view
from src.world.state import WorldState

PUBLIC_VISIBILITY = "public"
VISIBLE_VISIBILITY = "visible"
RUMORED_VISIBILITY = "rumored"
COVERT_VISIBILITY = "covert"


def apply_visibility_policy(events: list[Event]) -> None:
    """Assign stable visibility tiers to newly emitted events."""
    for event in events:
        event.visibility = infer_event_visibility(event)


def infer_event_visibility(event: Event) -> str:
    """Infer a player-facing visibility tier from event features."""
    event_type = event.event_type.lower()
    scope = event.event_scope.lower()
    family = event_family(event)
    themes = set(event_theme_tags(event))

    if "infiltration" in event_type or "lockdown" in event_type or "suppression" in event_type:
        return COVERT_VISIBILITY
    if family == "anomaly" and any(token in event_type for token in {"archive", "protocol"}):
        return RUMORED_VISIBILITY
    if "financing_withdrawal" in event_type:
        return RUMORED_VISIBILITY
    if family in {"macro", "supply"}:
        return PUBLIC_VISIBILITY
    if any(token in event_type for token in {"groundbreaking", "grid_link", "migration", "site_accident"}):
        return PUBLIC_VISIBILITY
    if any(token in event_type for token in {"power_struggle", "budget", "phase_advance", "reactivation", "habitat_expansion"}):
        return PUBLIC_VISIBILITY
    if themes.intersection({"politics", "organization", "security", "project", "anomaly"}):
        return VISIBLE_VISIBILITY
    if scope in {"civilization", "region"}:
        return PUBLIC_VISIBILITY
    if scope in {"presence", "faction"}:
        return VISIBLE_VISIBILITY
    if event.relic_refs or event.actor_refs or event.faction_refs:
        return VISIBLE_VISIBILITY
    return event.visibility or VISIBLE_VISIBILITY


def filter_events_for_view(events: list[Event], *, view: str = "truth") -> list[Event]:
    """Filter events that should not appear in the requested observer view."""
    if not is_player_view(view):
        return events
    return [event for event in events if is_player_visible_event(event)]


def is_player_visible_event(event: Event) -> bool:
    visibility = normalize_event_visibility(event.visibility)
    return visibility in {PUBLIC_VISIBILITY, VISIBLE_VISIBILITY, RUMORED_VISIBILITY}


def normalize_event_visibility(raw_visibility: str | None) -> str:
    normalized = (raw_visibility or VISIBLE_VISIBILITY).strip().lower()
    if normalized in {
        PUBLIC_VISIBILITY,
        VISIBLE_VISIBILITY,
        RUMORED_VISIBILITY,
        COVERT_VISIBILITY,
    }:
        return normalized
    return VISIBLE_VISIBILITY


def format_event_summary_for_view(
    event: Event,
    *,
    view: str = "truth",
    world: WorldState | None = None,
) -> str:
    """Render an event summary according to the observer view."""
    if not is_player_view(view):
        return event.summary
    return player_facing_event_summary(event, world=world)


def format_event_refs_for_view(
    event: Event,
    *,
    view: str = "truth",
    world: WorldState | None = None,
) -> str:
    """Render event refs according to the observer view."""
    if not is_player_view(view):
        refs = collect_event_refs(event)
        return ", ".join(refs) if refs else "None"

    refs: list[str] = []
    if event.region_refs:
        refs.extend(_format_region_ref(world, ref) for ref in event.region_refs[:2])
    if event.civ_refs:
        refs.extend(_format_civ_ref(world, ref) for ref in event.civ_refs[:1])
    if event.relic_refs:
        refs.append(_format_presence_ref(world, event.relic_refs[0]))
    if not refs:
        return "公开层面暂不明确"
    if event.actor_refs or event.faction_refs:
        refs.append("行动者：遮蔽")
    return "，".join(refs)


def format_visibility_for_view(event: Event, *, view: str = "truth") -> str:
    """Render visibility metadata according to the observer view."""
    visibility = normalize_event_visibility(event.visibility)
    if not is_player_view(view):
        return visibility
    if visibility == PUBLIC_VISIBILITY:
        return "公开"
    if visibility == RUMORED_VISIBILITY:
        return "传闻"
    if visibility == COVERT_VISIBILITY:
        return "遮蔽"
    return "可见"


def collect_event_refs(event: Event) -> list[str]:
    refs: list[str] = []
    refs.extend(f"region:{ref}" for ref in event.region_refs)
    refs.extend(f"civ:{ref}" for ref in event.civ_refs)
    refs.extend(f"character:{ref}" for ref in event.actor_refs)
    refs.extend(f"faction:{ref}" for ref in event.faction_refs)
    refs.extend(f"relic:{ref}" for ref in event.relic_refs)
    refs.extend(f"project:{ref}" for ref in event.project_refs)
    refs.extend(f"supply:{ref}" for ref in event.supply_refs)
    refs.extend(f"node:{ref}" for ref in event.node_refs)
    return refs


def player_facing_event_summary(
    event: Event,
    world: WorldState | None = None,
) -> str:
    """Return a concise public-facing event summary with light variation."""
    event_type = event.event_type.lower()
    family = event_family(event)
    themes = set(event_theme_tags(event))
    visibility = normalize_event_visibility(event.visibility)
    variant = _summary_variant(event)

    region_name = _first_region_name(world, event)
    civ_name = _first_civ_name(world, event)
    presence_name = _first_presence_name(world, event)

    if visibility == RUMORED_VISIBILITY:
        templates = [
            f"外界只捕捉到零散传闻，说明{presence_name or '某些隐蔽力量或封闭系统'}附近正在酝酿更深变化。",
            f"传闻开始堆积，像是{presence_name or '一股更深层的力量'}正在暗处推动局势偏移。",
            f"公开信息仍不完整，但越来越多迹象指向{presence_name or '某场被遮蔽的深层变化'}。",
        ]
        return templates[variant % len(templates)]
    if event.relic_refs:
        return _player_presence_summary(event, variant, world=world)
    if event.actor_refs and event.faction_refs:
        templates = [
            f"{region_name or '局部紧张地区'}出现了一轮看得见的动作，原本脆弱的平衡再次被打破。",
            f"公开层面的操作让{region_name or '这片地区'}勉强维持的局势再次偏向不稳。",
            f"看得见的行动被压上台面，{region_name or '这片区域'}更难继续维持原有平衡。",
        ]
        return templates[variant % len(templates)]
    if event.faction_refs or "organization" in themes:
        templates = [
            f"{region_name or '当地'}的派系活动在公开层面明显升温，暗示新一轮角力正在成形。",
            f"{region_name or '这片地方'}的派系动作愈发外显，围绕局部优势的争夺正在加速。",
            f"公开可见的派系调动正在变多，{region_name or '此地'}新的角力线已经开始成形。",
        ]
        return templates[variant % len(templates)]
    if "supply" in themes:
        focus = region_name or civ_name or "这片局势"
        templates = [
            f"{focus}的供给压力变化已经明显到足以被公开察觉。",
            f"{focus}的资源与物流波动开始清楚地传到公开层面。",
            f"{focus}的供给侧紧张正在外溢，连旁观者都能感到局势在收紧。",
        ]
        return templates[variant % len(templates)]
    if "security" in themes:
        focus = region_name or "这片区域"
        templates = [
            f"{focus}的安全态势出现了可见变化，说明当地的控制方式或风险水平正在调整。",
            f"{focus}的安全壳层正在变动，外界已经能察觉到风险结构的变化。",
            f"公开迹象显示，{focus}的防控节奏和风险水平正在重新排列。",
        ]
        return templates[variant % len(templates)]
    if "politics" in themes:
        focus = region_name or civ_name or "周边局势"
        templates = [
            f"{focus}的政治压力变得更加外显，周边秩序也比之前更不稳定。",
            f"{focus}的政治紧绷感已经浮到表面，原有秩序显得不再稳固。",
            f"公开氛围中的政治压强正在上升，{focus}的结构也开始显出松动。",
        ]
        return templates[variant % len(templates)]
    if "macro" in themes and "expansion" in event_type:
        focus = civ_name or "某条更远的前线"
        templates = [
            f"{focus}更大范围的扩张或推进迹象开始通过公开信号浮现出来。",
            f"{focus}一些更远处的推进动向正在显影，说明前线可能开始外移。",
            f"公开信号显示，{focus}某种更宽范围的推进势头正在逐渐成形。",
        ]
        return templates[variant % len(templates)]
    templates = [
        "世界表面出现了新的变化迹象，但更深层的原因仍被遮蔽。",
        "外界能看到局势正在挪动，却还看不清真正推动它的力量。",
        "某种新变化已经浮到表层，只是它背后的根源仍未暴露。",
    ]
    return templates[variant % len(templates)]


def player_facing_event_clue(
    event: Event,
    world: WorldState | None = None,
) -> str:
    """Return a short public clue for observation summaries."""
    event_type = event.event_type.lower()
    family = event_family(event)
    themes = set(event_theme_tags(event))
    visibility = normalize_event_visibility(event.visibility)
    variant = _summary_variant(event)
    if visibility == RUMORED_VISIBILITY:
        templates = [
            "流出的消息还很零散，但表层之下显然有更深的东西在移动。",
            "只看公开传闻还拼不全全貌，但暗线显然已经开始发力。",
        ]
        return templates[variant % len(templates)]
    if event.relic_refs:
        return _player_presence_clue(event, variant, world=world)
    if event.faction_refs or "organization" in themes:
        templates = [
            "派系层面的调动和试探开始更容易被外界注意到。",
            "公开视野里能看到的派系动作正在变多。",
        ]
        return templates[variant % len(templates)]
    if "supply" in themes:
        templates = [
            "供给侧的紧张信号已经浮到公开层面。",
            "资源与物流方面的压力正在被更多人感知到。",
        ]
        return templates[variant % len(templates)]
    if family == "politics" or "politics" in themes:
        templates = [
            "公开层面能感到这里的政治压强正在继续抬升。",
            "局部秩序的紧绷感已经开始变得更容易被人察觉。",
        ]
        return templates[variant % len(templates)]
    templates = [
        "这片区域又出现了新的公开压力信号。",
        "外界能感到这里的局势再次绷紧了一些。",
    ]
    return templates[variant % len(templates)]


def _summary_variant(event: Event) -> int:
    tail = event.event_id.rsplit("_", 1)[-1]
    if tail.isdigit():
        return int(tail)
    return sum(ord(char) for char in event.event_id)


def _format_region_ref(world: WorldState | None, region_id: str) -> str:
    if world is not None and region_id in world.regions:
        return f"区域：{world.regions[region_id].name}"
    return f"区域：{region_id}"


def _format_civ_ref(world: WorldState | None, civ_id: str) -> str:
    if world is not None and civ_id in world.civilizations:
        return f"文明：{world.civilizations[civ_id].name}"
    return f"文明：{civ_id}"


def _format_presence_ref(world: WorldState | None, relic_id: str) -> str:
    if world is not None and relic_id in world.relics:
        return f"异常焦点：{world.relics[relic_id].name}"
    return f"异常焦点：{relic_id}"


def _player_presence_summary(
    event: Event,
    variant: int,
    *,
    world: WorldState | None = None,
) -> str:
    family = _infer_presence_family(event)
    region_name = _first_region_name(world, event) or "这片区域"
    presence_name = _first_presence_name(world, event) or "异常焦点"
    templates_by_family = {
        "megastructure": [
            f"{presence_name}周边再次传出可见波动，{region_name}的注意力迅速重新收紧。",
            f"围绕{presence_name}的工程或运转动静再次浮上表面，{region_name}的紧张感明显升高。",
            f"{presence_name}附近又起波动，外界视线被重新拉回{region_name}的施工或运转前线。",
        ],
        "founding_protocol": [
            f"{presence_name}似乎再次牵动了局部秩序，{region_name}公开层面已经能感到控制结构在晃动。",
            f"围绕{presence_name}的异常动静再次外溢，{region_name}的治理气氛明显收紧。",
            f"看不见的系统层又起了波纹，{region_name}开始察觉秩序底板正在被{presence_name}触碰。",
        ],
        "sealed_archive": [
            f"{presence_name}再次传出动静，{region_name}周边局势因此显得更不安稳。",
            f"围绕{presence_name}的波动重新浮到表层，外界开始担心旧资料会改写{region_name}的现状。",
            f"{presence_name}似乎又被触动，{region_name}的空气里多了一层不安。",
        ],
        "anomalous_lifeform": [
            f"{presence_name}相关区域再次出现可见异动，{region_name}周边的紧张感迅速抬升。",
            f"{presence_name}的活动迹象重新浮现，外界对{region_name}扩散风险的警惕明显增强。",
            f"{presence_name}前线又有动静，{region_name}周边人群很难继续保持平静。",
        ],
        "relic_device": [
            f"{presence_name}再次引发可见扰动，{region_name}周边焦点因此重新收紧。",
            f"{presence_name}附近又起波动，外界注意力被重新拉回{region_name}。",
            f"围绕{presence_name}的动静再次浮上表面，{region_name}的紧张感明显升高。",
        ],
    }
    templates = templates_by_family.get(family, templates_by_family["relic_device"])
    return templates[variant % len(templates)]


def _player_presence_clue(
    event: Event,
    variant: int,
    *,
    world: WorldState | None = None,
) -> str:
    family = _infer_presence_family(event)
    presence_name = _first_presence_name(world, event) or "异常焦点"
    clues_by_family = {
        "megastructure": [
            f"{presence_name}再次出现了可见动静。",
            f"围绕{presence_name}的大型工程前线又一次传出明显波动。",
        ],
        "founding_protocol": [
            f"{presence_name}附近再次出现了不易解释的外部波纹。",
            f"看不见的协议层似乎又一次被{presence_name}牵动。",
        ],
        "sealed_archive": [
            f"{presence_name}周边又一次传出异样消息。",
            f"被压住的旧资料似乎又借着{presence_name}向表层渗出影响。",
        ],
        "anomalous_lifeform": [
            f"{presence_name}活动前线再次出现了可见异动。",
            f"{presence_name}的扩散或迁移迹象又被外界捕捉到。",
        ],
        "relic_device": [
            f"{presence_name}再次出现了可见动静。",
            f"{presence_name}周边又一次传出明显波动。",
        ],
    }
    clues = clues_by_family.get(family, clues_by_family["relic_device"])
    return clues[variant % len(clues)]


def _infer_presence_family(event: Event) -> str:
    event_type = event.event_type.lower()
    if "megastructure" in event_type or "project" in event_type or "site_" in event_type:
        return "megastructure"
    if "protocol" in event_type:
        return "founding_protocol"
    if "archive" in event_type:
        return "sealed_archive"
    if "lifeform" in event_type or "migration" in event_type or "biosecurity" in event_type:
        return "anomalous_lifeform"
    return "relic_device"


def _first_region_name(world: WorldState | None, event: Event) -> str | None:
    if world is None or not event.region_refs:
        return None
    region = world.regions.get(event.region_refs[0])
    return region.name if region is not None else event.region_refs[0]


def _first_civ_name(world: WorldState | None, event: Event) -> str | None:
    if world is None or not event.civ_refs:
        return None
    civ = world.civilizations.get(event.civ_refs[0])
    return civ.name if civ is not None else event.civ_refs[0]


def _first_presence_name(world: WorldState | None, event: Event) -> str | None:
    if world is None or not event.relic_refs:
        return None
    relic = world.relics.get(event.relic_refs[0])
    return relic.name if relic is not None else event.relic_refs[0]
