import unittest

from src.config.defaults import DEFAULT_AI_CONFIG, DEFAULT_WORLD_CONFIG
from src.core.engine import WorldEngine
from src.narrative.summaries import (
    summarize_character,
    summarize_civilization,
    summarize_faction,
    summarize_project,
    summarize_region,
    summarize_region_node,
    summarize_relic,
    summarize_supply_line,
)
from src.world.builder import build_world


def _build_sample_world(steps: int = 20):
    cfg = DEFAULT_AI_CONFIG.copy()
    cfg["provider"] = "none"
    world = build_world(DEFAULT_WORLD_CONFIG)
    engine = WorldEngine(world, ai_config=cfg)
    for _ in range(steps):
        engine.step()
    return world


class NarrativeSummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.world = _build_sample_world()
        cls.region_id = next(iter(cls.world.regions))
        cls.relic_id = next(iter(cls.world.relics))
        cls.project_id = next(iter(cls.world.projects))
        cls.supply_id = next(iter(cls.world.supply_lines))
        cls.node_id = next(iter(cls.world.region_nodes))
        cls.faction_id = next(iter(cls.world.factions))
        cls.character_id = next(iter(cls.world.characters))

    def test_region_player_view_uses_clue_counts_instead_of_internal_refs(self) -> None:
        text = summarize_region(
            self.world,
            self.region_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        self.assertIn("组织盘面: 外界", text)
        self.assertIn("人物动静: 外界", text)
        self.assertIn("异常落点: 外界", text)
        self.assertIn("公开传闻: 公开层面", text)
        self.assertNotIn("组织盘面: civ_", text)
        self.assertNotIn("人物动静: char_", text)

    def test_relic_player_view_hides_raw_story_tags(self) -> None:
        text = summarize_relic(
            self.world,
            self.relic_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        self.assertIn("外界印象: 外界", text)
        self.assertNotIn("外界印象: access_doctrine", text)
        self.assertIn("争夺状态: 外界", text)
        self.assertIn("争夺概述: 外界", text)
        self.assertNotIn("争夺方: Aegis", text)

    def test_relic_truth_includes_contest_summary(self) -> None:
        text = summarize_relic(
            self.world,
            self.relic_id,
            event_limit=5,
            mode="full",
            view="truth",
        )
        self.assertIn("争夺状态:", text)
        self.assertIn("争夺概述:", text)
        self.assertIn("争夺方:", text)
        self.assertNotIn("争夺状态: contested", text)
        self.assertNotIn("争夺状态: controlled", text)

    def test_project_truth_recent_notes_are_summarized(self) -> None:
        text = summarize_project(
            self.world,
            self.project_id,
            event_limit=5,
            mode="full",
            view="truth",
        )
        self.assertIn("recent_notes:", text)
        self.assertIn("概述:", text)
        self.assertNotIn("tick_", text.split("recent_notes:", 1)[1].split("recent_events:", 1)[0])
        self.assertNotIn("organization_front: None", text)
        self.assertNotIn("recent_events:\n    - [project_security_cordon] Authorities", text)

    def test_project_player_view_weakens_progress_judgment(self) -> None:
        text = summarize_project(
            self.world,
            self.project_id,
            event_limit=5,
            mode="full",
            view="player",
            focus="summary",
        )
        self.assertIn("推进状态: 外界", text)
        self.assertIn("推进概述: 外界", text)
        self.assertIn("当前阻碍: 外界", text)
        self.assertNotIn("推进状态: 推进放慢", text)

    def test_project_truth_summary_includes_progress_state(self) -> None:
        text = summarize_project(
            self.world,
            self.project_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="summary",
        )
        self.assertIn("推进状态:", text)
        self.assertIn("推进概述:", text)
        self.assertIn("当前阻碍:", text)
        self.assertNotIn("推进状态: stalled", text)
        self.assertNotIn("推进状态: advancing", text)

    def test_supply_truth_recent_notes_are_summarized(self) -> None:
        text = summarize_supply_line(
            self.world,
            self.supply_id,
            event_limit=5,
            mode="full",
            view="truth",
        )
        self.assertIn("recent_notes:", text)
        self.assertIn("概述:", text)
        self.assertNotIn("tick_", text.split("recent_notes:", 1)[1].split("recent_events:", 1)[0])
        self.assertNotIn("施力方为 civ ", text)

    def test_supply_player_view_weakens_corridor_judgment(self) -> None:
        text = summarize_supply_line(
            self.world,
            self.supply_id,
            event_limit=5,
            mode="full",
            view="player",
            focus="summary",
        )
        self.assertIn("线路状态: 外界", text)
        self.assertIn("线路概述: 外界", text)
        self.assertIn("当前阻碍: 外界", text)
        self.assertNotIn("线路状态: 处于争夺中", text)

    def test_supply_truth_summary_includes_corridor_state(self) -> None:
        text = summarize_supply_line(
            self.world,
            self.supply_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="summary",
        )
        self.assertIn("线路状态:", text)
        self.assertIn("线路概述:", text)
        self.assertIn("当前阻碍:", text)
        self.assertNotIn("线路状态: contested", text)
        self.assertNotIn("线路状态: stable", text)

    def test_region_node_truth_summary_includes_node_state(self) -> None:
        text = summarize_region_node(
            self.world,
            self.node_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="summary",
        )
        self.assertIn("节点类型:", text)
        self.assertIn("节点态势:", text)
        self.assertIn("节点概述:", text)
        self.assertIn("当前阻碍:", text)
        self.assertNotIn("节点态势: contested", text)
        self.assertNotIn("node_type:", text)

    def test_region_node_player_view_hides_raw_node_tokens(self) -> None:
        text = summarize_region_node(
            self.world,
            self.node_id,
            event_limit=5,
            mode="full",
            view="player",
            focus="summary",
        )
        self.assertIn("节点观察：", text)
        self.assertIn("节点态势: 外界", text)
        self.assertIn("节点概述: 外界", text)
        self.assertNotIn("release_gate", text)
        self.assertNotIn("construction_interface", text)
        self.assertNotIn("access_control", text)

    def test_region_node_player_recent_events_hide_raw_event_tokens(self) -> None:
        text = summarize_region_node(
            self.world,
            self.node_id,
            event_limit=10,
            mode="full",
            view="player",
        )
        self.assertNotIn("civil scarcity shift", text)
        self.assertNotIn("lifeform quarantine panic", text)
        self.assertNotIn("project contract scramble", text)

    def test_player_clue_lines_do_not_use_none_empty_state(self) -> None:
        civ_text = summarize_civilization(
            self.world,
            next(iter(self.world.civilizations)),
            event_limit=5,
            mode="full",
            view="player",
        )
        faction_text = summarize_faction(
            self.world,
            self.faction_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        for line in civ_text.splitlines() + faction_text.splitlines():
            if "迹象:" in line or "线索:" in line or "牵连:" in line:
                self.assertNotIn(": None", line)

    def test_faction_player_local_people_are_deduped(self) -> None:
        text = summarize_faction(
            self.world,
            self.faction_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        local_lines = [
            line.strip()
            for line in text.splitlines()
            if line.startswith("    - ") and "[" in line
        ]
        self.assertEqual(len(local_lines), len(set(local_lines)))

    def test_character_truth_relations_use_textual_empty_state(self) -> None:
        text = summarize_character(
            self.world,
            self.character_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="relations",
        )
        self.assertNotIn("relationship_refs: None", text)
        self.assertNotIn("loyalty_map: None", text)

    def test_character_truth_front_includes_active_goal_block(self) -> None:
        text = summarize_character(
            self.world,
            self.character_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="front",
        )
        self.assertIn("当前目标:", text)
        self.assertIn("目标状态:", text)
        self.assertIn("当前阻碍:", text)
        self.assertIn("最近结果:", text)
        self.assertNotIn("目标状态: advancing", text)
        self.assertNotIn("目标状态: contested", text)
        self.assertNotIn("目标状态: blocked", text)

    def test_character_player_view_weakens_goal_judgment(self) -> None:
        text = summarize_character(
            self.world,
            self.character_id,
            event_limit=5,
            mode="full",
            view="player",
            focus="front",
        )
        self.assertIn("当前目标: 外界", text)
        self.assertIn("目标状态: 外界", text)
        self.assertIn("当前阻碍: 外界", text)
        self.assertIn("最近结果: 外界", text)
        self.assertNotIn("目标状态: 正在向前推进", text)

    def test_faction_truth_history_uses_memory_summary(self) -> None:
        text = summarize_faction(
            self.world,
            self.faction_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="history",
        )
        self.assertIn("风格记忆概述:", text)
        self.assertIn("风格记忆:", text)
        self.assertNotIn("tick_", text)
        self.assertNotIn("bias_actions=", text)
        self.assertNotIn("speaks little and tracks loyalties", text)
        self.assertNotIn("is keeping a narrow contact chain alive", text)

    def test_faction_truth_summary_anomaly_lines_are_humanized(self) -> None:
        text = summarize_faction(
            self.world,
            self.faction_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="summary",
        )
        self.assertNotIn("strength=high", text)

    def test_faction_truth_summary_includes_objective_block(self) -> None:
        text = summarize_faction(
            self.world,
            self.faction_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="summary",
        )
        self.assertIn("战略目标:", text)
        self.assertIn("目标状态:", text)
        self.assertIn("当前阻碍:", text)
        self.assertIn("最近结果:", text)
        self.assertNotIn("目标状态: forming", text)
        self.assertNotIn("目标状态: advancing", text)

    def test_faction_player_view_weakens_objective_judgment(self) -> None:
        text = summarize_faction(
            self.world,
            self.faction_id,
            event_limit=5,
            mode="full",
            view="player",
            focus="summary",
        )
        self.assertIn("战略目标: 外界", text)
        self.assertIn("目标状态: 外界", text)
        self.assertIn("当前阻碍: 外界", text)
        self.assertIn("最近结果: 外界", text)
        self.assertNotIn("战略目标: 把资源与组织动作继续压向核心项目线", text)

    def test_faction_truth_relations_include_causal_explanation(self) -> None:
        text = summarize_faction(
            self.world,
            self.faction_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="relations",
        )
        if "relation_front: None" in text:
            self.skipTest("sample faction has no visible relation front in this generated world")
        self.assertIn("因果解释:", text)
        self.assertNotIn("type=", text)
        self.assertNotIn("flow=", text)
        self.assertNotIn("strength=", text)
        self.assertNotIn("rival_to", text)
        self.assertNotIn("allied_with", text)

    def test_faction_truth_dependency_blocks_include_causal_explanations(self) -> None:
        text = summarize_faction(
            self.world,
            self.faction_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="relations",
        )
        for block in ("dependency_chain:", "sponsorship_chain:", "region_anchors:"):
            if f"{block} None" in text:
                continue
            segment = text.split(block, 1)[1]
            self.assertIn("因果解释:", segment)

    def test_civilization_truth_relations_do_not_use_anchor_or_via_tokens(self) -> None:
        text = summarize_civilization(
            self.world,
            next(iter(self.world.civilizations)),
            event_limit=5,
            mode="full",
            view="truth",
            focus="relations",
        )
        self.assertNotIn("anchors=", text)
        self.assertNotIn("via=", text)

    def test_summary_views_include_strategy_explanation(self) -> None:
        civ_text = summarize_civilization(
            self.world,
            next(iter(self.world.civilizations)),
            event_limit=5,
            mode="full",
            view="truth",
            focus="summary",
        )
        faction_text = summarize_faction(
            self.world,
            self.faction_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="summary",
        )
        self.assertIn("strategy_explanation:", civ_text)
        self.assertIn("strategy_explanation:", faction_text)
        self.assertIn("strategy_to_action:", faction_text)
        self.assertIn("strategy_to_execution:", faction_text)
        self.assertNotIn("organization_climate_pull: security_consolidation", faction_text)
        self.assertNotIn("tick_", faction_text)
        self.assertNotIn("strategic_posture: stability_over_growth", civ_text)
        self.assertNotIn("world_frame_pull: legitimacy_erosion", civ_text)
        self.assertNotIn("expansion pressure moved", civ_text)
        self.assertNotIn("event=", civ_text)
        self.assertNotIn("severity=", civ_text)
        self.assertNotIn("medium (steady)", civ_text)
        self.assertNotIn("high (rising)", faction_text)
        self.assertNotIn("military_stabilization", civ_text)
        self.assertNotIn("efficiency", faction_text)

    def test_player_execution_overview_does_not_render_none_phrase(self) -> None:
        civ_text = summarize_civilization(
            self.world,
            next(iter(self.world.civilizations)),
            event_limit=5,
            mode="full",
            view="player",
            focus="summary",
        )
        faction_text = summarize_faction(
            self.world,
            self.faction_id,
            event_limit=5,
            mode="full",
            view="player",
            focus="summary",
        )
        self.assertNotIn("None 上", civ_text)
        self.assertNotIn("None 上", faction_text)

    def test_civilization_player_view_hides_internal_ids_in_structure_block(self) -> None:
        text = summarize_civilization(
            self.world,
            next(iter(self.world.civilizations)),
            event_limit=5,
            mode="full",
            view="player",
            focus="structure",
        )
        self.assertNotIn("key_regions: region_", text)
        self.assertNotIn("key_factions: civ_", text)

    def test_civilization_player_view_hides_raw_macro_enums(self) -> None:
        text = summarize_civilization(
            self.world,
            next(iter(self.world.civilizations)),
            event_limit=5,
            mode="full",
            view="player",
            focus="history",
        )
        for raw_value in (
            "active",
            "high_tech_leap",
            "hybrid_governance",
            "guarded",
            "networked_infrastructure",
            "automation",
            "civic_progress",
            "managed_abundance",
            "steady",
            "declining",
            "rising",
        ):
            self.assertNotIn(raw_value, text)

    def test_civilization_truth_history_is_humanized(self) -> None:
        text = summarize_civilization(
            self.world,
            next(iter(self.world.civilizations)),
            event_limit=5,
            mode="full",
            view="truth",
            focus="history",
        )
        self.assertNotIn("tick_", text)
        self.assertNotIn("networked_infrastructure", text)
        self.assertNotIn("managed_abundance", text)
        self.assertNotIn("region 04", text)

    def test_faction_player_view_hides_raw_profile_enums(self) -> None:
        text = summarize_faction(
            self.world,
            self.faction_id,
            event_limit=5,
            mode="full",
            view="player",
            focus="summary",
        )
        for raw_value in (
            "cross_regional",
            "civilizational",
            "regional",
            "efficiency",
            "security_consolidation",
            "bureaucratic_competition",
            "growth",
            "secrecy",
        ):
            self.assertNotIn(raw_value, text)

    def test_region_player_view_hides_raw_pressure_enums(self) -> None:
        text = summarize_region(
            self.world,
            self.region_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        for raw_value in ("frontier_zone", "high", "medium", "low", "steady", "declining"):
            self.assertNotIn(raw_value, text)

    def test_relic_player_view_hides_raw_presence_enums(self) -> None:
        text = summarize_relic(
            self.world,
            self.relic_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        for raw_value in ("founding_protocol", "exceptional_system", "autonomous_system"):
            self.assertNotIn(raw_value, text)
        self.assertIn("异常“", text)

    def test_character_player_view_hides_raw_profile_enums(self) -> None:
        text = summarize_character(
            self.world,
            self.character_id,
            event_limit=5,
            mode="full",
            view="player",
            focus="front",
        )
        for raw_value in (
            "level: L",
            "status: active",
            "affiliations:",
            "last_intent:",
            "planner",
            "analysis",
            "force_reform",
            "collapse",
            "structural_focus:",
            "type: supply",
            "controller: ",
            "route: ",
        ):
            self.assertNotIn(raw_value, text)

    def test_project_player_view_hides_raw_project_tokens(self) -> None:
        text = summarize_project(
            self.world,
            self.project_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        for raw_value in (
            "Project Network",
            "megastructure_program",
            "stalled_recovery",
            "engineering_front",
            "budget_front",
            "contract_front",
        ):
            self.assertNotIn(raw_value, text)

    def test_supply_player_view_hides_raw_supply_tokens(self) -> None:
        text = summarize_supply_line(
            self.world,
            self.supply_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        for raw_value in ("Supply Line", "contested", "medium", "supply_front", "logistics_front"):
            self.assertNotIn(raw_value, text)

    def test_character_player_view_hides_affiliation_ids_and_focus_ids(self) -> None:
        text = summarize_character(
            self.world,
            self.character_id,
            event_limit=5,
            mode="full",
            view="player",
            focus="front",
        )
        faction_pull_line = next(
            (line for line in text.splitlines() if line.strip().startswith("faction_pull:")),
            "",
        )
        self.assertNotIn("affiliations: civ_", text)
        self.assertNotIn("civ_", faction_pull_line)

    def test_character_truth_front_and_relations_are_humanized(self) -> None:
        front_text = summarize_character(
            self.world,
            self.character_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="front",
        )
        rel_text = summarize_character(
            self.world,
            self.character_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="relations",
        )
        self.assertNotIn("status: active", front_text)
        self.assertNotIn("affiliations: civ_", front_text)
        self.assertNotIn("moved to", rel_text)

    def test_character_truth_focus_block_uses_humanized_labels(self) -> None:
        text = summarize_character(
            self.world,
            self.character_id,
            event_limit=5,
            mode="full",
            view="truth",
            focus="front",
        )
        for raw_value in (
            "current_role_in_world:",
            "current_focus:",
            "main_region:",
            "relic_pull:",
            "relic_reason:",
            "front_response:",
            "structural_focus:",
            "pressure_chain:",
            "frontier_theme:",
            "frontier_focus_type:",
            "frontier_focus_shift:",
            "frontier_focus_trace:",
            "frontier_theme_trace:",
            "secure relic access",
            "stabilize supply",
        ):
            self.assertNotIn(raw_value, text)

    def test_world_evolution_builds_objective_feedback_relations(self) -> None:
        world = _build_sample_world(steps=30)
        relation_types = {
            relation.relation_type
            for relation in world.relations.values()
            if relation.status == "active"
        }
        self.assertTrue(
            {"authorizes", "operates_in"}.intersection(relation_types),
            "expected organization feedback relations to be written back into world.relations",
        )
        self.assertTrue(
            {"depends_on", "supported_by_supply", "supply_influence", "seeking_control", "stabilizing"}.intersection(relation_types),
            "expected midlayer objective feedback relations to appear after longer evolution",
        )

    def test_world_evolution_populates_second_phase_state_fields(self) -> None:
        world = _build_sample_world(steps=30)
        self.assertTrue(
            any(character.active_goal_summary for character in world.characters.values()),
            "expected at least one character to accumulate an active goal summary",
        )
        self.assertTrue(
            any(faction.strategic_objective for faction in world.factions.values()),
            "expected at least one faction to accumulate a strategic objective",
        )
        self.assertTrue(
            any(project.progress_summary for project in world.projects.values()),
            "expected at least one project to accumulate a progress summary",
        )
        self.assertTrue(
            any(supply_line.corridor_summary for supply_line in world.supply_lines.values()),
            "expected at least one supply line to accumulate a corridor summary",
        )
        self.assertTrue(
            any(relic.contest_summary for relic in world.relics.values()),
            "expected at least one relic to accumulate a contest summary",
        )
        self.assertTrue(
            any(node.state_summary for node in world.region_nodes.values()),
            "expected at least one region node to accumulate a state summary",
        )
        self.assertTrue(
            any(thread.summary for thread in world.pressure_threads.values()),
            "expected pressure threads to accumulate from repeated events",
        )

    def test_pressure_threads_appear_in_player_summaries(self) -> None:
        world = _build_sample_world(steps=30)
        region_id = next(
            thread.scope_ref
            for thread in world.pressure_threads.values()
            if thread.scope_ref in world.regions
        )
        text = summarize_region(
            world,
            region_id,
            event_limit=5,
            mode="full",
            view="player",
        )
        self.assertIn("局势线索:", text)
        self.assertNotIn("pressure_threads:", text)

    def test_events_backfill_midlayer_refs(self) -> None:
        world = _build_sample_world(steps=30)
        self.assertTrue(
            any(event.project_refs for event in world.event_stream.events),
            "expected events to backfill project refs",
        )
        self.assertTrue(
            any(event.supply_refs for event in world.event_stream.events),
            "expected events to backfill supply refs",
        )
        self.assertTrue(
            any(event.node_refs for event in world.event_stream.events),
            "expected events to backfill node refs",
        )

    def test_pressure_threads_cover_midlayer_refs(self) -> None:
        world = _build_sample_world(steps=30)
        refs = {thread.scope_ref for thread in world.pressure_threads.values()}
        self.assertTrue(refs.intersection(world.projects))
        self.assertTrue(refs.intersection(world.supply_lines))
        self.assertTrue(refs.intersection(world.region_nodes))
        self.assertTrue(refs.intersection(world.relics))
        self.assertTrue(
            any(thread.public_clues for thread in world.pressure_threads.values()),
            "expected pressure threads to retain player-facing observable clues",
        )

    def test_midlayer_pressure_threads_appear_in_player_summaries_without_raw_tokens(self) -> None:
        world = _build_sample_world(steps=30)
        refs = {thread.scope_ref for thread in world.pressure_threads.values()}
        summary_cases = [
            (summarize_project, next(ref for ref in world.projects if ref in refs)),
            (summarize_supply_line, next(ref for ref in world.supply_lines if ref in refs)),
            (summarize_region_node, next(ref for ref in world.region_nodes if ref in refs)),
            (summarize_relic, next(ref for ref in world.relics if ref in refs)),
        ]
        for summary_func, ref in summary_cases:
            with self.subTest(ref=ref):
                text = summary_func(world, ref, event_limit=5, mode="full", view="player")
                self.assertIn("局势线索:", text)
                self.assertIn("最近可见：", text)
                self.assertNotIn("pressure_threads:", text)
                self.assertNotIn("project_", text)
                self.assertNotIn("supply_", text)
                self.assertNotIn("node_", text)

    def test_pressure_threads_are_pruned_per_scope_after_long_run(self) -> None:
        world = _build_sample_world(steps=100)
        refs = {thread.scope_ref for thread in world.pressure_threads.values()}
        self.assertLessEqual(
            max(
                sum(1 for thread in world.pressure_threads.values() if thread.scope_ref == ref)
                for ref in refs
            ),
            5,
        )
        self.assertLessEqual(len(world.pressure_threads), 260)

    def test_world_evolution_creates_relation_pressure_for_midlayer_objects(self) -> None:
        world = _build_sample_world(steps=30)
        project_relation_count = sum(
            1
            for relation in world.relations.values()
            if relation.status == "active" and relation.target_ref.startswith("project_")
        )
        supply_relation_count = sum(
            1
            for relation in world.relations.values()
            if relation.status == "active" and relation.target_ref.startswith("supply_")
        )
        relic_relation_count = sum(
            1
            for relation in world.relations.values()
            if relation.status == "active" and relation.target_ref.startswith("relic_")
        )
        node_relation_count = sum(
            1
            for relation in world.relations.values()
            if relation.status == "active" and relation.target_ref.startswith("node_")
        )
        self.assertGreater(project_relation_count, 0)
        self.assertGreater(supply_relation_count, 0)
        self.assertGreater(relic_relation_count, 0)
        self.assertGreater(node_relation_count, 0)


if __name__ == "__main__":
    unittest.main()
