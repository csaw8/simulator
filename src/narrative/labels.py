"""Human-readable labels for narrative summaries."""

from __future__ import annotations


def humanize_enum_token(value: str) -> str:
    return value.replace("_", " ").strip() or "未明"


def player_level_value(level: str) -> str:
    mapping = {
        "high": "偏高",
        "medium": "中位",
        "low": "偏低",
    }
    return mapping.get(level, humanize_enum_token(level))


def player_trend_value(trend: str) -> str:
    mapping = {
        "rising": "还在走高",
        "steady": "暂时走稳",
        "declining": "正在回落",
        "volatile": "波动较大",
        "forming": "仍在成形",
        "breaking": "正在松动",
    }
    return mapping.get(trend, humanize_enum_token(trend))


def player_level_with_trend(level: str, trend: str) -> str:
    return f"{player_level_value(level)}（{player_trend_value(trend)}）"


def player_civilization_stage_value(stage: str) -> str:
    mapping = {
        "city_state": "城邦整合期",
        "federation_empire": "联邦扩展期",
        "high_tech_leap": "高技术跃升期",
    }
    return mapping.get(stage, humanize_enum_token(stage))


def truth_civilization_stage_value(stage: str) -> str:
    return player_civilization_stage_value(stage)


def player_trajectory_value(tag: str) -> str:
    mapping = {
        "platform_expansion": "平台扩展仍在推进",
        "technology_integration": "技术整合持续加深",
        "corporate_oligarchy": "企业权力正在继续上浮",
        "military_stabilization": "武装稳控逐步压到前台",
        "algorithmic_governance": "算法治理痕迹不断加深",
        "ecological_adaptation": "生态适应已成长期方向",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def player_status_value(status: str) -> str:
    mapping = {
        "active": "持续运转中",
        "contested": "处于争夺中",
        "fragile": "状态偏脆弱",
        "stable": "暂时稳定",
        "strained": "持续承压中",
        "sealed": "处于封存中",
        "dormant": "暂时沉寂",
        "active_buildout": "正在加速铺开",
        "contested_buildout": "一边铺开一边遭遇争夺",
        "mobilizing": "正在动员展开",
        "stalled_recovery": "修复推进受阻",
    }
    return mapping.get(status, humanize_enum_token(status))


def player_region_type_value(region_type: str) -> str:
    mapping = {
        "arcology": "高密度城核区",
        "orbital_port": "轨道港口区",
        "industrial_belt": "工业带",
        "frontier_zone": "边缘前线区",
        "research_hub": "研究枢纽区",
        "agri_dome": "农业穹顶区",
        "subsea_city": "海下城市区",
        "waste_reclaim": "回收整备区",
    }
    return mapping.get(region_type, humanize_enum_token(region_type))


def player_governance_mode_value(mode: str) -> str:
    mapping = {
        "hybrid_governance": "多路力量混合共治",
        "technocratic_council": "技术理事会主导",
        "security_directorate": "安保中枢主导",
        "mercantile_charter": "交易宪章主导",
    }
    return mapping.get(mode, humanize_enum_token(mode))


def truth_governance_mode_value(mode: str) -> str:
    return player_governance_mode_value(mode)


def player_military_posture_value(posture: str) -> str:
    mapping = {
        "guarded": "警戒维持中",
        "militarized": "武装压强偏高",
        "expeditionary": "对外投送意图明显",
        "demobilizing": "正在收缩武装姿态",
    }
    return mapping.get(posture, humanize_enum_token(posture))


def player_relic_type_value(relic_type: str) -> str:
    mapping = {
        "relic_device": "异常装置",
        "megastructure": "巨构异常",
        "sealed_archive": "封存档案异常",
        "founding_protocol": "奠基协议异常",
        "anomalous_lifeform": "异常生命体",
    }
    return mapping.get(relic_type, humanize_enum_token(relic_type))


def player_project_type_value(project_type: str) -> str:
    mapping = {
        "megastructure_program": "巨构推进项目",
        "containment_program": "封控推进项目",
        "archive_recovery_program": "档案回收项目",
        "biosecurity_program": "生物安保项目",
    }
    return mapping.get(project_type, humanize_enum_token(project_type))


def player_region_node_type_value(node_type: str) -> str:
    mapping = {
        "release_gate": "放行闸口",
        "construction_interface": "施工接口",
        "access_relay": "接入中继",
        "containment_checkpoint": "封锁关口",
    }
    return mapping.get(node_type, humanize_enum_token(node_type))


def player_exceptional_label_value(label: str) -> str:
    mapping = {
        "exceptional_system": "系统级异常",
        "exceptional_structure": "结构级异常",
        "exceptional_archive": "档案级异常",
        "exceptional_lifeform": "生命级异常",
        "exceptional_device": "装置级异常",
    }
    return mapping.get(label, humanize_enum_token(label))


def player_presence_class_value(value: str) -> str:
    mapping = {
        "megastructure": "巨构体",
        "autonomous_system": "自主系统体",
        "sealed_archive": "封存档案体",
        "anomalous_lifeform": "异常生命体",
        "relic_device": "异常装置体",
    }
    return mapping.get(value, humanize_enum_token(value))


def player_faction_scope_value(scope: str) -> str:
    mapping = {
        "local": "主要卡在单点地区",
        "regional": "主要影响一片地区",
        "cross_regional": "影响跨越多片地区",
        "civilizational": "能牵动整个文明盘面",
    }
    return mapping.get(scope, humanize_enum_token(scope))


def player_doctrine_tag_value(tag: str) -> str:
    mapping = {
        "efficiency": "效率优先",
        "growth": "扩张优先",
        "security": "安全优先",
        "secrecy": "保密优先",
        "order": "秩序优先",
        "legacy_control": "遗产控制优先",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def player_doctrine_tags_value(tags: list[str]) -> str:
    if not tags:
        return "外界暂未看清明确主张"
    return "、".join(player_doctrine_tag_value(tag) for tag in tags[:6])


def player_agency_mode_value(mode: str) -> str:
    mapping = {
        "reactive": "多为被动应对",
        "opportunistic": "偏机会性出手",
        "strategic": "带明显布局感",
    }
    return mapping.get(mode, humanize_enum_token(mode))


def player_character_level_value(level: str) -> str:
    mapping = {
        "L3": "高层关键人物",
        "L2": "中层活跃人物",
        "L1": "基层可见人物",
    }
    return mapping.get(level, level)


def player_tech_profile_value(tag: str) -> str:
    mapping = {
        "networked_infrastructure": "网络化基础设施",
        "automation": "自动化调度",
        "biotech": "生物技术渗透",
        "salvage_industry": "回收工业底盘",
        "archive_systems": "档案与记录系统",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def player_belief_profile_value(tag: str) -> str:
    mapping = {
        "civic_progress": "相信秩序可通过建设持续改良",
        "stability_doctrine": "把稳定本身视作最高前提",
        "data_faith": "相信数据与记录拥有裁决力",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def player_summary_tag_value(tag: str) -> str:
    mapping = {
        "uneasy_growth": "扩张在继续，但不安感也在累积",
        "managed_abundance": "表面供给充足，背后调度痕迹很重",
        "fraying_order": "秩序还在，但边缘已经开始起毛",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def player_tag_list_value(tags: list[str], item_mapper) -> str:
    if not tags:
        return "外界暂未看清稳定特征"
    return "、".join(item_mapper(tag) for tag in tags)


def truth_trajectory_value(tags: list[str]) -> str:
    if not tags:
        return "尚未形成稳定发展轨迹"
    return "、".join(player_trajectory_value(tag) for tag in tags[:4])


def truth_doctrine_tags_value(tags: list[str]) -> str:
    if not tags:
        return "尚未形成清晰组织主张"
    return "、".join(player_doctrine_tag_value(tag) for tag in tags[:6])


def truth_relation_status_value(status: str) -> str:
    mapping = {
        "active": "仍在生效",
        "dormant": "暂时沉寂",
        "broken": "已经断裂",
        "contested": "正在被争夺",
    }
    return mapping.get(status, humanize_enum_token(status))


def truth_relation_type_value(relation_type: str) -> str:
    mapping = {
        "controls": "控制",
        "rival_to": "敌对牵制",
        "contesting": "争夺",
        "allied_with": "联盟协作",
        "operates_in": "驻场运作",
        "seeking_control": "试图接管",
        "infiltrating": "渗透",
        "obstructing": "阻断",
        "flashpoint_actor": "热点施力",
        "financing": "融资牵引",
        "contracting": "承包执行",
        "sponsoring": "赞助背书",
        "supply_influence": "补给牵引",
        "stabilizing": "稳控",
        "supports": "支撑",
        "supporting": "支撑",
        "distorts": "扭曲渗压",
        "controls_node": "控制节点",
        "contests_node": "争夺节点",
        "stabilizes_node": "稳住节点",
        "depends_on": "依赖",
    }
    return mapping.get(relation_type, humanize_enum_token(relation_type))


def truth_region_anchor_type_value(anchor_type: str) -> str:
    mapping = {
        "core_region": "核心地区",
        "controlled_region": "既有控制区",
        "contesting": "争夺前线",
        "stabilizing": "稳控落点",
        "infiltrating": "渗透落点",
        "operates_in": "持续驻场",
    }
    return mapping.get(anchor_type, humanize_enum_token(anchor_type))


def truth_civilization_region_anchor_hint(hint: str) -> str:
    if ":" not in hint:
        return truth_region_anchor_type_value(hint)
    faction_name, relation_type = hint.split(":", 1)
    return f"{faction_name}：{truth_region_anchor_type_value(relation_type)}"


def player_event_type_label(event_type: str) -> str:
    mapping = {
        "political_shift": "政治波动",
        "security_shift": "安全波动",
        "legitimacy_shift": "合法性波动",
        "resource_shift": "资源波动",
        "civil_scarcity_shift": "供给波动",
        "expansion_shift": "扩张调整",
        "character_supply_action": "人物施压",
        "character_archive_access_action": "人物介入档案线",
        "lifeform_quarantine_panic": "生物封控恐慌",
        "protocol_infiltration": "协议渗透",
        "protocol_emergency_lockdown": "协议封锁",
        "project_contract_scramble": "合同争夺",
        "project_security_cordon": "项目封控",
        "megastructure_stall": "巨构停滞",
        "faction_power_struggle": "组织角力",
        "faction_infiltration": "组织渗透",
        "faction_archive_breach": "档案失守",
        "archive_suppression": "档案压制",
        "archive_legitimacy_shock": "档案冲击",
        "faction_resource_reallocation": "资源重排",
    }
    return mapping.get(event_type, humanize_enum_token(event_type))


def player_ambient_role_value(role: str) -> str:
    mapping = {
        "salvage runner": "回收跑线人",
        "checkpoint clerk": "关卡文员",
        "perimeter scout": "外围哨探",
        "cargo scheduler": "货运调度员",
        "dock sentinel": "泊位哨卫",
        "customs fixer": "通关协调人",
        "field captain": "前线队长",
        "checkpoint marshal": "关卡执勤官",
        "counterintel runner": "反侦察跑线人",
        "district secretary": "片区事务员",
        "permit enforcer": "许可执行员",
        "policy courier": "政令传递员",
        "systems researcher": "系统研究员",
        "containment planner": "封控筹划员",
        "data custodian": "数据保管员",
        "contract broker": "合同掮客",
        "site accountant": "现场核算员",
        "asset supervisor": "资产看护员",
    }
    return mapping.get(role, humanize_enum_token(role))


def player_ambient_stance_value(stance: str) -> str:
    mapping = {
        "settled but alert": "表面平稳但保持警惕",
        "nervous but exposed": "紧张且暴露在外",
        "careful and faction-aware": "做事谨慎且很看派系脸色",
        "practical under shortage": "在紧缺下务实应对",
        "watching the contract line closely": "紧盯合同线变化",
        "speaks little and tracks loyalties": "寡言，但一直在看忠诚流向",
        "counts cost, access, and signatures first": "先算成本、入口和签字链",
        "treats every opening like a spill risk": "把每个口子都当成外溢风险",
        "reads pressure as a material bargaining edge": "总把压力当成谈判筹码",
        "adjusts quickly to whoever controls the seam": "谁控制节点就先顺着谁调整",
    }
    return mapping.get(stance, humanize_enum_token(stance))


def player_ambient_detail_type_value(detail_type: str) -> str:
    mapping = {
        "fuel crate row": "燃料箱列",
        "checkpoint barrier": "关卡隔离栏",
        "watch beacon": "监视信标",
        "access relay": "接入中继",
        "override cradle": "越权底座",
        "control sheath": "控制护套",
        "cooling stack": "冷却堆",
        "sealed drawer bank": "封存抽屉列",
        "document crate": "文件箱组",
    }
    return mapping.get(detail_type, humanize_enum_token(detail_type))


def player_ambient_condition_value(condition: str) -> str:
    mapping = {
        "overused but functional": "过度使用但还能运转",
        "quietly contested": "表面安静但暗中有人争",
        "exposed": "暴露在外",
        "strained": "持续吃紧",
        "fragile": "状态脆弱",
        "serviceable": "还能维持使用",
        "sealed": "处于封存中",
        "locked": "锁控状态",
        "leaking": "出现外泄迹象",
        "contained": "暂时被压住",
        "active": "活跃中",
        "guarded": "受严密看护",
        "incomplete": "尚未完工",
        "live": "正在运转",
        "unstable": "状态不稳",
    }
    return mapping.get(condition, humanize_enum_token(condition))


def player_front_tag_value(tag: str) -> str:
    mapping = {
        "engineering_front": "工程前线",
        "budget_front": "预算前线",
        "contract_front": "合同前线",
        "supply_front": "补给前线",
        "logistics_front": "物流前线",
        "security_front": "安保前线",
        "political_front": "政治前线",
        "ration_front": "配给前线",
        "access_control": "放行控制",
        "construction": "施工接口",
        "access": "接入接口",
        "containment": "封控接口",
        "relic": "异常接口",
        "project": "项目接口",
        "supply": "补给接口",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def truth_story_tag_value(tag: str) -> str:
    mapping = {
        "access_doctrine": "接入权叙事",
        "signal_noise": "信号噪声传闻",
        "containment_risk": "封控失手风险",
        "budget_shadows": "预算阴影",
        "protocol_anxiety": "协议焦虑",
        "archive_panic": "档案恐慌",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def truth_story_hook_value(tag: str) -> str:
    mapping = {
        "signal_noise": "信号噪声传闻",
        "checkpoint_friction": "关卡摩擦传闻",
        "ration_strain": "配给吃紧传闻",
        "quiet_infiltration": "暗线渗透传闻",
        "protocol_anxiety": "协议焦虑传闻",
        "archive_whispers": "档案耳语",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def player_region_population_value(tag: str) -> str:
    mapping = {
        "transient_workers": "流动劳作人口偏多",
        "settled_families": "常住家庭人口稳定",
        "migrant_clusters": "迁移群体聚集明显",
        "technical_cadres": "技术岗位人口占比高",
        "militia_presence": "武装值守人口可见",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def player_character_role_value(tag: str) -> str:
    mapping = {
        "governor": "统筹型人物",
        "planner": "筹划型人物",
        "security_chief": "安保主事者",
        "architect": "建设主导者",
        "broker": "协调掮客",
        "technician": "技术执行者",
        "agitator": "动员煽动者",
        "officer": "执行干员",
        "courier": "传递节点人物",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def player_character_capability_value(tag: str) -> str:
    mapping = {
        "persuasion": "说服与斡旋",
        "strategy": "局势筹划",
        "coordination": "组织协调",
        "analysis": "情势研判",
        "repair": "修复与维持",
        "coercion": "强压推进",
        "smuggling": "隐蔽输运",
        "negotiation": "交易谈判",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def player_character_desire_value(tag: str) -> str:
    mapping = {
        "consolidate_power": "巩固手中权力",
        "stabilize_region": "稳住当前地区",
        "force_reform": "强推结构改革",
        "survive": "优先保全自身",
        "advance": "继续往上攀升",
        "protect_network": "保住既有关系网",
        "profit": "优先获取利益",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def player_character_fear_value(tag: str) -> str:
    mapping = {
        "collapse": "担心秩序崩塌",
        "exposure": "担心自身暴露",
        "succession_crisis": "担心继承失序",
        "purge": "担心清洗波及",
        "scarcity": "担心供给枯竭",
        "automation_loss": "担心被自动化替代",
        "raids": "担心突袭冲击",
    }
    return mapping.get(tag, humanize_enum_token(tag))


def player_pressure_axis_value(axis: str) -> str:
    mapping = {
        "supply_strain": "供给链紧绷",
        "legitimacy_erosion": "合法性流失",
        "infrastructure_dependency": "基础设施依赖过重",
        "frontier_expansion": "边缘扩展冲动",
        "containment_fatigue": "封控疲劳累积",
        "capital_realignment": "资本与资源正在重排",
        "biosecurity_risk": "生物安保风险上扬",
        "information_instability": "信息秩序不稳",
    }
    return mapping.get(axis, humanize_enum_token(axis))


def player_pressure_axes_value(axes: list[str]) -> str:
    if not axes:
        return "外界暂未看清主导压力"
    return "、".join(player_pressure_axis_value(axis) for axis in axes[:2])


def truth_pressure_axes_value(axes: list[str]) -> str:
    if not axes:
        return "尚未形成清晰世界牵引"
    return "、".join(player_pressure_axis_value(axis) for axis in axes[:2])


def player_organization_climate_value(climate: str) -> str:
    mapping = {
        "bureaucratic_competition": "官僚摩擦明显",
        "security_consolidation": "安保收束加重",
        "contract_warfare": "合同争夺升温",
        "quiet_infiltration": "暗线渗透活跃",
        "managed_fragility": "脆弱平衡被刻意维持",
        "extractive_opportunism": "机会性抽取盛行",
    }
    return mapping.get(climate, humanize_enum_token(climate))


def player_organization_climates_value(climates: list[str]) -> str:
    if not climates:
        return "外界暂未看清组织气候"
    return "、".join(player_organization_climate_value(climate) for climate in climates[:2])


def truth_organization_climates_value(climates: list[str]) -> str:
    if not climates:
        return "尚未形成清晰组织气候牵引"
    return "、".join(player_organization_climate_value(climate) for climate in climates[:2])


def truth_frontier_theme_strength_value(value: str) -> str:
    mapping = {
        "weak": "偏弱",
        "medium": "中位",
        "high": "偏强",
    }
    return mapping.get(value, humanize_enum_token(value))


def truth_frontier_theme_value(value: str) -> str:
    mapping = {
        "project_operator": "项目操盘者",
        "biosecurity_hunter": "异常扩散追猎者",
        "containment_stabilizer": "封控稳定执行者",
        "political_leverage_runner": "政治杠杆推动者",
        "mixed_front_operator": "多前线穿梭者",
        "none": "此前尚未形成稳定前线主题",
        "": "此前尚未形成稳定前线主题",
    }
    return mapping.get(value, humanize_enum_token(value))


def truth_frontier_focus_type_value(value: str) -> str:
    mapping = {
        "project": "项目线",
        "supply": "补给线",
        "presence": "异常存在",
        "region": "地区落点",
        "pressure": "压力类型",
        "none": "未收束",
        "": "未收束",
    }
    return mapping.get(value, humanize_enum_token(value))


def truth_frontier_focus_shift_value(value: str) -> str:
    mapping = {
        "redirected": "已发生改道",
        "steady": "暂时走稳",
        "rising": "正在加重",
        "declining": "正在回落",
        "forming": "仍在成形",
        "breaking": "正在松动",
        "none": "暂无明显变化",
        "": "暂无明显变化",
    }
    return mapping.get(value, humanize_enum_token(value))


def truth_goal_status_value(value: str) -> str:
    mapping = {
        "forming": "仍在成形",
        "advancing": "正在向前推进",
        "contested": "处于争夺中",
        "blocked": "推进受阻",
        "stabilizing": "正在转入稳控",
        "stable": "暂时稳定",
        "strained": "持续承压",
        "rerouting": "正在改道重排",
        "suppressed": "已被压制封控",
        "controlled": "已形成暂时主控",
        "stalled": "推进放慢",
        "exposed": "已暴露在前台争夺中",
        "none": "暂无稳定状态",
        "": "暂无稳定状态",
    }
    return mapping.get(value, humanize_enum_token(value))


def player_label(label: str) -> str:
    mapping = {
        "level": "可见层级",
        "status": "状态",
        "stage": "阶段",
        "type": "类别",
        "pressure": "压力",
        "trajectory": "发展轨迹",
        "governance_mode": "治理形态",
        "world_frame_pull": "世界牵引",
        "strategic_posture": "总体取向",
        "organization_model": "组织轮廓",
        "project_networks": "项目线索",
        "execution_front_overview": "执行主轴",
        "supply_fronts": "补给线索",
        "relation_front": "关系态势",
        "external_relations": "外部接口",
        "dependency_chain": "依赖迹象",
        "sponsorship_chain": "背书迹象",
        "region_anchors": "地区锚点",
        "strategic_posture_stability": "方向稳定度",
        "strategic_posture_pending": "转向征兆",
        "strategic_posture_pending_hits": "转向积累",
        "strategic_memory": "近期惯性",
        "midlayer_changes": "中层波动",
        "cohesion": "凝聚状态",
        "scarcity_pressure": "资源压力",
        "expansion_pressure": "扩张压力",
        "legitimacy": "合法性",
        "tech_profile": "技术画像",
        "belief_profile": "信念画像",
        "military_posture": "安保姿态",
        "summary_tags": "外显印象",
        "power_scope": "势力尺度",
        "influence": "影响力",
        "doctrine_tags": "公开主张",
        "role_tags": "身份线索",
        "capability_tags": "能力线索",
        "desire_tags": "诉求线索",
        "fear_tags": "顾虑线索",
        "notoriety": "名望",
        "initiative": "主动性",
        "agency_mode": "行动姿态",
        "observation_trace": "可见行动痕迹",
        "exceptional_label": "异常性质",
        "presence_class": "存在类别",
        "significance": "重要性",
        "danger": "危险度",
        "activation_state": "活跃状态",
        "story_tags": "外界印象",
        "front_tags": "前线标签",
        "recent_events": "近期动静",
        "prosperity": "繁荣度",
        "scarcity": "稀缺度",
        "political_tension": "政治压力",
        "security": "安全态势",
        "infrastructure": "基础设施",
        "tech_density": "技术密度",
        "connectivity": "连通性",
        "ecological_stress": "生态压力",
        "belief_temperature": "信念温度",
        "population_profile": "人口轮廓",
        "strategic_value": "战略价值",
        "controller": "控制线索",
        "control_state": "控制态势",
        "organization_front": "参与格局",
        "pressure_interpretation": "压力解读",
        "linked_civs": "相关文明迹象",
        "linked_factions": "相关组织迹象",
        "linked_characters": "相关人物迹象",
        "active_factions": "组织盘面",
        "active_characters": "人物动静",
        "resident_relics": "异常落点",
        "story_hooks": "公开传闻",
        "frontier_theme": "前线收束",
        "knowledge_snapshot": "掌握线索",
        "focus_competitors": "竞争迹象",
        "recent_goal": "近期目标感",
        "memory_summary": "行动惯性",
        "relationship_refs": "关系牵引",
        "loyalty_map": "归属线索",
        "wake_priority_seed": "出场势能",
        "last_intent": "最近意图迹象",
        "active_goal_summary": "当前目标",
        "active_goal_status": "目标状态",
        "active_goal_blockers": "当前阻碍",
        "active_goal_recent_result": "最近结果",
        "affiliations": "归属线索",
        "strategic_objective": "战略目标",
        "strategic_objective_status": "目标状态",
        "strategic_objective_blockers": "当前阻碍",
        "strategic_objective_recent_result": "最近结果",
        "sponsor_refs": "赞助力量迹象",
        "contractor_refs": "执行力量迹象",
        "financier_refs": "资金力量迹象",
        "opposition_refs": "阻力迹象",
        "recent_notes": "近期线索",
        "progress_state": "推进状态",
        "progress_summary": "推进概述",
        "progress_blockers": "当前阻碍",
        "corridor_state": "线路状态",
        "corridor_summary": "线路概述",
        "corridor_blockers": "当前阻碍",
        "contest_state": "争夺状态",
        "contest_summary": "争夺概述",
        "contesting_refs": "争夺方",
        "region_nodes": "地区节点",
        "node_type": "节点类型",
        "contention_state": "节点态势",
        "visibility": "可见性",
        "linked_project": "关联项目",
        "linked_supply": "关联补给",
        "linked_relic": "关联异常",
        "state_summary": "节点概述",
        "blockers": "当前阻碍",
    }
    return mapping.get(label, label)


def civilization_posture_driver_label(posture: str) -> str:
    mapping = {
        "containment_first": "异常扩散被视为头号系统风险",
        "megastructure_expansion": "巨构和基础设施扩张被视为主导增长路线",
        "stability_over_growth": "秩序维稳优先于扩张收益",
        "opportunistic_extraction": "波动局势被当作攫取杠杆的机会",
        "balanced_competition": "多线竞争并行，没有绝对优先轴",
    }
    return mapping.get(posture, "多线竞争并行，没有绝对优先轴")


def civilization_faction_bias_label(posture: str) -> str:
    mapping = {
        "containment_first": "派系更易投向封控、争夺异常控制权、压制外溢",
        "megastructure_expansion": "派系更易投向竞标、融资改道、资源向项目线集中",
        "stability_over_growth": "派系更易投向渗透、结盟、争权以维持秩序",
        "opportunistic_extraction": "派系更易投向资源调配、异常争夺、机会性夺取",
        "balanced_competition": "派系动作分布较均衡",
    }
    return mapping.get(posture, "派系动作分布较均衡")


def civilization_character_bias_label(posture: str) -> str:
    mapping = {
        "containment_first": "活跃角色更可能追封锁线、抑制线、收束异常外溢",
        "megastructure_expansion": "活跃角色更可能追预算线、合同线、融资线",
        "stability_over_growth": "活跃角色更可能追维稳线、权力重排线",
        "opportunistic_extraction": "活跃角色更可能追供给杠杆线、异常接入线",
        "balanced_competition": "活跃角色更可能保持局部扩张与试探",
    }
    return mapping.get(posture, "活跃角色更可能保持局部扩张与试探")
