"""World initialization and seed generation."""

from __future__ import annotations

from random import Random

from src.world.character import Character
from src.world.civilization import Civilization
from src.world.faction import Faction
from src.world.frame import StructureTemplate
from src.world.project import ProjectNetwork
from src.world.presence import suggested_story_tags
from src.world.region import Region
from src.world.region_node import RegionNode
from src.world.relic import Relic
from src.world.state import WorldState
from src.world.supply import SupplyLine

_REGION_TYPES = [
    "arcology",
    "orbital_port",
    "industrial_belt",
    "frontier_zone",
    "research_hub",
    "agri_dome",
    "subsea_city",
    "waste_reclaim",
]
_TRAJECTORIES = [
    "platform_expansion",
    "technology_integration",
    "corporate_oligarchy",
    "military_stabilization",
    "algorithmic_governance",
    "ecological_adaptation",
]
_FACTION_TYPES = [
    "government",
    "megacorp",
    "security_force",
    "research_institute",
    "labor_union",
    "network_cell",
    "infrastructure_consortium",
    "data_cult",
    "civic_guild",
    "logistics_syndicate",
]
_RELIC_TYPES = [
    "relic_device",
    "megastructure",
    "sealed_archive",
    "founding_protocol",
    "anomalous_lifeform",
]
_AGENCY_MODES = ["reactive", "opportunistic", "strategic"]
_REGION_PREFIXES = [
    "Helion",
    "Orchid",
    "Sable",
    "Vanta",
    "Lattice",
    "Morrow",
    "Cinder",
    "Nacre",
    "Palisade",
    "Solace",
    "Axiom",
    "Kestrel",
]
_REGION_SUFFIXES = [
    "Sprawl",
    "Reach",
    "Ring",
    "Basin",
    "Yard",
    "Crown",
    "Harbor",
    "Array",
    "Fold",
    "Ward",
]
_CIV_PREFIXES = [
    "Concord",
    "Meridian",
    "Aegis",
    "Vector",
    "Prax",
    "Aurora",
    "Halcyon",
    "Novarch",
]
_CIV_SUFFIXES = [
    "Directorate",
    "Compact",
    "Syndicate",
    "Federation",
    "Mandate",
    "Union",
    "Accord",
    "Lattice",
]
_MEGASTRUCTURE_PREFIXES = [
    "Skyshield",
    "Pillar",
    "Lumen",
    "Aureline",
    "Blackglass",
    "Starwell",
    "Crownline",
    "Iron Bloom",
]
_MEGASTRUCTURE_SUFFIXES = [
    "Spine",
    "Gate",
    "Cascade",
    "Anchor",
    "Column",
    "Loop",
    "Grid",
    "Vault",
]
_PROTOCOL_PREFIXES = [
    "Foundry",
    "Civic",
    "Threshold",
    "Anchor",
    "Sentinel",
    "Quiet",
]
_PROTOCOL_SUFFIXES = [
    "Kernel",
    "Mandate",
    "Protocol",
    "Directive",
    "Mesh",
    "Stack",
]
_ARCHIVE_PREFIXES = [
    "Ashen",
    "Glass",
    "Pale",
    "Silent",
    "Vaulted",
    "Obsidian",
]
_ARCHIVE_SUFFIXES = [
    "Ledger",
    "Repository",
    "Annals",
    "Vault",
    "Record",
    "Index",
]
_LIFEFORM_PREFIXES = [
    "Mire",
    "Halo",
    "Cinder",
    "Shard",
    "Veil",
    "Drift",
]
_LIFEFORM_SUFFIXES = [
    "Swarm",
    "Bloom",
    "Pack",
    "Choir",
    "Spindle",
    "Maw",
]
_DEVICE_PREFIXES = [
    "Signal",
    "Null",
    "Ember",
    "Prism",
    "Tide",
    "Mirror",
]
_DEVICE_SUFFIXES = [
    "Engine",
    "Relay",
    "Core",
    "Lens",
    "Node",
    "Prism",
]
_PRESSURE_AXES = [
    "supply_strain",
    "legitimacy_erosion",
    "infrastructure_dependency",
    "frontier_expansion",
    "containment_fatigue",
    "capital_realignment",
    "biosecurity_risk",
    "information_instability",
]
_DOMINANT_FRONTS = [
    "project_fronts",
    "governance_fronts",
    "supply_fronts",
    "containment_fronts",
    "migration_fronts",
    "archive_shock_fronts",
]
_ORGANIZATION_CLIMATES = [
    "bureaucratic_competition",
    "security_consolidation",
    "contract_warfare",
    "quiet_infiltration",
    "managed_fragility",
    "extractive_opportunism",
]
_ANOMALY_BIASES = [
    "megastructure_pressure",
    "sealed_information_pressure",
    "autonomous_system_pressure",
    "biosecurity_pressure",
    "mixed_exceptional_pressure",
]
_CIV_PATH_BIASES = [
    "networked_hegemony",
    "scarcity_adaptation",
    "managed_expansion",
    "containment_statecraft",
    "contractual_fragmentation",
    "archive_legitimacy_cycles",
]


def build_world(world_config: dict[str, int]) -> WorldState:
    """Create a minimal world state from a world config dictionary."""
    seed = int(world_config["seed"])
    rng = Random(seed)
    state = WorldState(seed=seed)
    state.structure_template = _build_structure_template(rng)

    _build_regions(state, rng, int(world_config["region_count"]))
    _build_civilizations(state, rng, int(world_config["civilization_count"]))
    _assign_regions_to_civilizations(state, rng)
    _build_factions(state, rng)
    _build_characters(
        state,
        rng,
        int(world_config["protagonist_count"]),
        int(world_config["active_character_count"]),
    )
    _build_relics(state, rng, int(world_config["relic_count"]))
    _build_projects(state)
    _build_supply_lines(state, rng)
    _build_region_nodes(state)
    return state


def _build_structure_template(rng: Random) -> StructureTemplate:
    pressure_axes = rng.sample(_PRESSURE_AXES, k=3)
    dominant_fronts = rng.sample(_DOMINANT_FRONTS, k=3)
    organization_climates = rng.sample(_ORGANIZATION_CLIMATES, k=3)
    civ_path_biases = rng.sample(_CIV_PATH_BIASES, k=3)
    return StructureTemplate(
        era_frame="realistic_future_tech",
        pressure_axes=pressure_axes,
        dominant_fronts=dominant_fronts,
        organization_climates=organization_climates,
        anomaly_bias=rng.choice(_ANOMALY_BIASES),
        civ_path_biases=civ_path_biases,
        observer_lens="macro_pressure_and_public_signals",
    )


def _choose_civilization_posture(state: WorldState, rng: Random) -> str:
    options = [
        "balanced_competition",
        "megastructure_expansion",
        "containment_first",
        "stability_over_growth",
        "opportunistic_extraction",
    ]
    weights = [2, 2, 2, 2, 2]
    frame = state.structure_template
    if frame.anomaly_bias == "megastructure_pressure":
        weights[1] += 3
    if frame.anomaly_bias in {"biosecurity_pressure", "autonomous_system_pressure"}:
        weights[2] += 3
    if "supply_strain" in frame.pressure_axes or "capital_realignment" in frame.pressure_axes:
        weights[4] += 2
    if "legitimacy_erosion" in frame.pressure_axes:
        weights[3] += 2
    if "project_fronts" in frame.dominant_fronts:
        weights[1] += 2
    if "governance_fronts" in frame.dominant_fronts:
        weights[3] += 2
    if "containment_fronts" in frame.dominant_fronts or "migration_fronts" in frame.dominant_fronts:
        weights[2] += 2
    return rng.choices(options, weights=weights, k=1)[0]


def _build_faction_doctrine_tags(state: WorldState, rng: Random, faction_type: str) -> list[str]:
    faction_biases = {
        "infrastructure_consortium": ["efficiency", "efficiency", "efficiency", "growth", "growth", "growth"],
        "data_cult": ["secrecy", "secrecy", "secrecy", "secrecy", "security", "security"],
        "civic_guild": ["security", "security", "security", "efficiency", "efficiency"],
        "logistics_syndicate": ["growth", "growth", "growth", "efficiency", "efficiency", "efficiency", "secrecy"],
    }
    pool = list(faction_biases.get(faction_type, ["efficiency", "security", "growth", "secrecy"]))
    frame = state.structure_template
    if "security_consolidation" in frame.organization_climates:
        pool.extend(["security", "security", "secrecy"])
    if "contract_warfare" in frame.organization_climates:
        pool.extend(["efficiency", "growth"])
    if "extractive_opportunism" in frame.organization_climates:
        pool.extend(["growth", "secrecy"])
    if frame.anomaly_bias == "megastructure_pressure":
        pool.extend(["growth", "efficiency"])
    if frame.anomaly_bias in {"sealed_information_pressure", "autonomous_system_pressure"}:
        pool.extend(["secrecy", "security"])
    return [rng.choice(pool)]


def _initial_faction_operational_style(
    state: WorldState,
    doctrine_tags: list[str],
    faction_type: str,
    rng: Random,
) -> str:
    frame = state.structure_template
    tags = set(doctrine_tags)
    type_bias = {
        "infrastructure_consortium": ["contract_predator", "contract_predator", "adaptive_network"],
        "data_cult": ["discipline_network", "containment_cadre", "discipline_network"],
        "civic_guild": ["adaptive_network", "discipline_network", "adaptive_network"],
        "logistics_syndicate": ["extraction_broker", "extraction_broker", "contract_predator"],
    }
    biased_styles = type_bias.get(faction_type)
    if biased_styles:
        preferred = None
        if "project_fronts" in frame.dominant_fronts and "infrastructure_consortium" == faction_type:
            preferred = "contract_predator"
        elif "governance_fronts" in frame.dominant_fronts and faction_type in {"data_cult", "civic_guild"}:
            preferred = "discipline_network"
        elif "supply_fronts" in frame.dominant_fronts and faction_type == "logistics_syndicate":
            preferred = "extraction_broker"
        if preferred is not None:
            return preferred
        return rng.choice(biased_styles)
    if "project_fronts" in frame.dominant_fronts or frame.anomaly_bias == "megastructure_pressure":
        if "growth" in tags or "efficiency" in tags:
            return "contract_predator"
    if "governance_fronts" in frame.dominant_fronts and ("security" in tags or "secrecy" in tags):
        return "discipline_network"
    if frame.anomaly_bias in {"biosecurity_pressure", "autonomous_system_pressure"} and "security" in tags:
        return "containment_cadre"
    if "supply_fronts" in frame.dominant_fronts and ("growth" in tags or "efficiency" in tags):
        return "extraction_broker"
    return "adaptive_network"


def _build_regions(state: WorldState, rng: Random, count: int) -> None:
    for index in range(count):
        region_id = f"region_{index + 1:02d}"
        region = Region(
            region_id=region_id,
            name=_build_region_name(rng, index + 1),
            civ_id=None,
            region_type=rng.choice(_REGION_TYPES),
            connectivity=rng.choice(["low", "medium", "high"]),
            prosperity=rng.choice(["low", "medium", "high"]),
            scarcity=rng.choice(["low", "medium", "high"]),
            infrastructure=rng.choice(["low", "medium", "high"]),
            tech_density=rng.choice(["medium", "high"]),
            local_story_hooks=[rng.choice(["labor_unrest", "water_debt", "signal_noise"])],
        )
        state.regions[region_id] = region


def _build_civilizations(state: WorldState, rng: Random, count: int) -> None:
    region_ids = list(state.regions.keys())
    for index in range(count):
        civ_id = f"civ_{index + 1:02d}"
        origin_region_id = region_ids[index % len(region_ids)]
        civilization = Civilization(
            civ_id=civ_id,
            name=_build_civilization_name(rng, index + 1),
            origin_region_id=origin_region_id,
            status="active",
            stage=rng.choice(["city_state", "federation_empire", "high_tech_leap"]),
            trajectory=[rng.choice(_TRAJECTORIES)],
            tech_profile=["networked_infrastructure", "automation"],
            belief_profile=[rng.choice(["civic_progress", "stability_doctrine", "data_faith"])],
            summary_tags=[rng.choice(["uneasy_growth", "managed_abundance", "fraying_order"])],
            strategic_posture=_choose_civilization_posture(state, rng),
        )
        state.civilizations[civ_id] = civilization


def _assign_regions_to_civilizations(state: WorldState, rng: Random) -> None:
    civ_ids = list(state.civilizations.keys())
    for region in state.regions.values():
        civ_id = rng.choice(civ_ids)
        region.civ_id = civ_id
        state.civilizations[civ_id].key_regions.append(region.region_id)


def _build_factions(state: WorldState, rng: Random) -> None:
    for civ in state.civilizations.values():
        faction_count = rng.randint(2, 4)
        civ_region_ids = civ.key_regions or list(state.regions.keys())
        for local_index in range(faction_count):
            faction_id = f"{civ.civ_id}_faction_{local_index + 1:02d}"
            controlled_region = rng.choice(civ_region_ids)
            faction_type = rng.choice(_FACTION_TYPES)
            doctrine_tags = _build_faction_doctrine_tags(state, rng, faction_type)
            faction = Faction(
                faction_id=faction_id,
                name=f"{civ.name}-Faction-{local_index + 1:02d}",
                faction_type=faction_type,
                parent_civ_id=civ.civ_id,
                power_scope=rng.choice(["regional", "cross_regional", "civilizational"]),
                doctrine_tags=doctrine_tags,
                operational_style=_initial_faction_operational_style(state, doctrine_tags, faction_type, rng),
                controlled_regions=[controlled_region],
            )
            state.factions[faction_id] = faction
            civ.key_factions.append(faction_id)
            state.regions[controlled_region].active_factions.append(faction_id)


def _build_characters(
    state: WorldState,
    rng: Random,
    protagonist_count: int,
    active_character_count: int,
) -> None:
    region_ids = list(state.regions.keys())
    faction_ids = list(state.factions.keys())

    for index in range(protagonist_count):
        char_id = f"char_p_{index + 1:02d}"
        faction_id = rng.choice(faction_ids)
        region_id = rng.choice(region_ids)
        character = Character(
            char_id=char_id,
            name=f"Protagonist-{index + 1:02d}",
            character_level="L3",
            current_region_id=region_id,
            affiliation=[faction_id],
            role_tags=[rng.choice(["governor", "planner", "security_chief", "architect"])],
            capability_tags=[rng.choice(["persuasion", "strategy", "coordination", "analysis"])],
            desire_tags=[rng.choice(["consolidate_power", "stabilize_region", "force_reform"])],
            fear_tags=[rng.choice(["collapse", "exposure", "succession_crisis"])],
            notoriety="high",
            initiative="high",
            memory_summary="Long-term actor with active influence on regional direction.",
            recent_goal="Maintain leverage over a volatile district.",
            wake_priority_seed=80 + index,
            agency_mode="strategic",
        )
        state.characters[char_id] = character
        state.factions[faction_id].key_characters.append(char_id)
        state.regions[region_id].active_characters.append(char_id)

    for index in range(active_character_count):
        char_id = f"char_a_{index + 1:02d}"
        faction_id = rng.choice(faction_ids)
        region_id = rng.choice(region_ids)
        agency_mode = rng.choices(_AGENCY_MODES, weights=[6, 3, 1], k=1)[0]
        character = Character(
            char_id=char_id,
            name=f"Active-{index + 1:02d}",
            character_level="L2",
            current_region_id=region_id,
            affiliation=[faction_id],
            role_tags=[rng.choice(["broker", "technician", "agitator", "officer", "courier"])],
            capability_tags=[rng.choice(["repair", "coercion", "smuggling", "negotiation"])],
            desire_tags=[rng.choice(["survive", "advance", "protect_network", "profit"])],
            fear_tags=[rng.choice(["purge", "scarcity", "automation_loss", "raids"])],
            notoriety=rng.choice(["low", "medium"]),
            initiative=rng.choice(["low", "medium", "high"]),
            memory_summary="Responds to local pressures and faction incentives.",
            recent_goal="Navigate the latest shift in district conditions.",
            wake_priority_seed=20 + index,
            agency_mode=agency_mode,
        )
        state.characters[char_id] = character
        state.regions[region_id].active_characters.append(char_id)


def _build_relics(state: WorldState, rng: Random, count: int) -> None:
    region_ids = list(state.regions.keys())
    holders = list(state.factions.keys()) + list(state.civilizations.keys())
    for index in range(count):
        relic_id = f"relic_{index + 1:02d}"
        region_id = rng.choice(region_ids)
        relic_type = rng.choice(_RELIC_TYPES)
        holder_ref = rng.choice(holders)
        origin_mode = "legacy"
        construction_state = "unknown"
        sponsor_ref = None
        contractor_ref = None
        financier_ref = None
        opposition_ref = None
        if relic_type == "megastructure":
            (
                origin_mode,
                construction_state,
                sponsor_ref,
                contractor_ref,
                financier_ref,
                opposition_ref,
            ) = _build_megastructure_profile(
                state,
                rng,
                region_id,
                holder_ref,
            )
        elif relic_type == "anomalous_lifeform":
            origin_mode, construction_state = _build_lifeform_profile(rng)
        relic = Relic(
            relic_id=relic_id,
            name=_build_presence_name(relic_type, index + 1),
            relic_type=relic_type,
            current_region_id=region_id,
            holder_ref=holder_ref,
            significance="high" if relic_type != "relic_device" else rng.choice(["medium", "high"]),
            danger=rng.choice(["low", "medium", "high"]),
            activation_state=_build_activation_state(rng, relic_type, origin_mode, construction_state),
            origin_mode=origin_mode,
            construction_state=construction_state,
            sponsor_ref=sponsor_ref,
            contractor_ref=contractor_ref,
            financier_ref=financier_ref,
            opposition_ref=opposition_ref,
            story_tags=_build_presence_story_tags(rng, relic_type, origin_mode),
        )
        state.relics[relic_id] = relic
        state.regions[region_id].resident_relics.append(relic_id)


def _build_projects(state: WorldState) -> None:
    project_index = 1
    for relic in state.relics.values():
        if relic.relic_type != "megastructure":
            continue
        project_id = f"project_{project_index:02d}"
        project_index += 1
        region = state.regions[relic.current_region_id]
        linked_civs = [region.civ_id] if region.civ_id else []
        linked_factions = _dedupe_refs(
            [
                ref
                for ref in [
                    relic.holder_ref,
                    relic.sponsor_ref,
                    relic.contractor_ref,
                    relic.financier_ref,
                    relic.opposition_ref,
                ]
                if ref in state.factions
            ]
        )
        status = _project_status_from_relic(relic)
        pressure = _project_pressure_from_relic(relic, region)
        front_tags = _project_front_tags(relic, region)
        project = ProjectNetwork(
            project_id=project_id,
            name=f"{relic.name} Project Network",
            project_type="megastructure_program",
            status=status,
            pressure=pressure,
            sponsor_refs=_dedupe_refs([ref for ref in [relic.sponsor_ref] if ref]),
            contractor_refs=_dedupe_refs([ref for ref in [relic.contractor_ref] if ref]),
            financier_refs=_dedupe_refs([ref for ref in [relic.financier_ref] if ref]),
            opposition_refs=_dedupe_refs([ref for ref in [relic.opposition_ref] if ref]),
            linked_regions=[region.region_id],
            linked_presence_refs=[relic.relic_id],
            linked_factions=linked_factions,
            linked_civs=linked_civs,
            linked_characters=_project_characters_for_region(state, region.region_id, linked_factions),
            front_tags=front_tags,
            recent_notes=[
                f"origin_mode={relic.origin_mode}",
                f"construction_state={relic.construction_state}",
                f"activation_state={relic.activation_state}",
            ],
        )
        state.projects[project_id] = project
        if region.civ_id and region.civ_id in state.civilizations:
            state.civilizations[region.civ_id].key_projects.append(project_id)


def _project_status_from_relic(relic: Relic) -> str:
    if relic.construction_state in {"planned", "foundation"}:
        return "mobilizing"
    if relic.construction_state in {"rising", "integration", "retrofit", "reactivating"}:
        return "contested_buildout" if relic.activation_state == "contested" else "active_buildout"
    if relic.construction_state in {"operational"}:
        return "grid_attached"
    if relic.construction_state in {"degraded"}:
        return "stalled_recovery"
    return "latent"


def _project_pressure_from_relic(relic: Relic, region: Region) -> str:
    if relic.activation_state == "contested" or region.security == "low":
        return "high"
    if region.scarcity == "high" or region.political_tension == "high":
        return "medium"
    return "low"


def _project_front_tags(relic: Relic, region: Region) -> list[str]:
    tags = ["engineering_front", "budget_front", "contract_front"]
    if relic.financier_ref:
        tags.append("finance_front")
    if region.security == "low":
        tags.append("security_front")
    if region.scarcity == "high":
        tags.append("supply_front")
    return tags


def _project_characters_for_region(
    state: WorldState,
    region_id: str,
    linked_factions: list[str],
) -> list[str]:
    linked_set = set(linked_factions)
    results: list[str] = []
    for character in state.characters.values():
        if character.current_region_id != region_id:
            continue
        if linked_set.intersection(character.affiliation):
            results.append(character.char_id)
    return results[:6]


def _dedupe_refs(refs: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        result.append(ref)
    return result


def _build_supply_lines(state: WorldState, rng: Random) -> None:
    supply_index = 1
    for civilization in state.civilizations.values():
        civ_regions = [
            state.regions[region_id]
            for region_id in civilization.key_regions
            if region_id in state.regions
        ]
        if len(civ_regions) < 2:
            continue
        ordered_regions = sorted(civ_regions, key=lambda region: (region.connectivity, region.region_id))
        pairs: list[tuple[Region, Region]] = []
        for index in range(min(2, len(ordered_regions) - 1)):
            origin = ordered_regions[index]
            destination = ordered_regions[-(index + 1)]
            if origin.region_id == destination.region_id:
                continue
            pairs.append((origin, destination))
        for origin, destination in pairs:
            controlling_faction_ref = _choose_supply_controller(state, civilization.civ_id, origin.region_id, destination.region_id, rng)
            pressure = _supply_pressure(origin, destination)
            status = _supply_status(origin, destination)
            supply_id = f"supply_{supply_index:02d}"
            supply_index += 1
            line = SupplyLine(
                supply_id=supply_id,
                name=f"{origin.name} -> {destination.name} Supply Line",
                origin_region_id=origin.region_id,
                destination_region_id=destination.region_id,
                status=status,
                pressure=pressure,
                controlling_faction_ref=controlling_faction_ref,
                linked_civ_refs=[civilization.civ_id],
                front_tags=_supply_front_tags(origin, destination),
                recent_notes=[
                    f"origin_connectivity={origin.connectivity}",
                    f"destination_scarcity={destination.scarcity}",
                    f"controller={controlling_faction_ref or 'none'}",
                ],
            )
            state.supply_lines[supply_id] = line
            civilization.key_supply_lines.append(supply_id)


def _build_region_nodes(state: WorldState) -> None:
    node_index = 1
    for supply_line in state.supply_lines.values():
        for region_id in (supply_line.origin_region_id, supply_line.destination_region_id):
            node_id = f"node_{node_index:02d}"
            node_index += 1
            state.region_nodes[node_id] = RegionNode(
                node_id=node_id,
                name=f"{state.regions[region_id].name} Release Gate",
                node_type="release_gate",
                region_id=region_id,
                linked_supply_id=supply_line.supply_id,
                controller_ref=supply_line.controlling_faction_ref,
                pressure=supply_line.pressure,
                tags=["supply", "access_control"],
                recent_notes=[f"linked_supply={supply_line.supply_id}"],
            )

    for project in state.projects.values():
        region_id = project.linked_regions[0] if project.linked_regions else None
        if region_id is None or region_id not in state.regions:
            continue
        node_id = f"node_{node_index:02d}"
        node_index += 1
        state.region_nodes[node_id] = RegionNode(
            node_id=node_id,
            name=f"{state.regions[region_id].name} Construction Interface",
            node_type="construction_interface",
            region_id=region_id,
            linked_project_id=project.project_id,
            controller_ref=(project.contractor_refs or project.sponsor_refs or project.financier_refs or [None])[0],
            pressure=project.pressure,
            tags=["project", "construction"],
            recent_notes=[f"linked_project={project.project_id}"],
        )

    for relic in state.relics.values():
        node_type = "access_relay"
        tags = ["relic", "access"]
        if relic.activation_state == "contested" or relic.danger == "high":
            node_type = "containment_checkpoint"
            tags = ["relic", "containment"]
        node_id = f"node_{node_index:02d}"
        node_index += 1
        state.region_nodes[node_id] = RegionNode(
            node_id=node_id,
            name=f"{state.regions[relic.current_region_id].name} {_node_type_name(node_type)}",
            node_type=node_type,
            region_id=relic.current_region_id,
            linked_relic_id=relic.relic_id,
            controller_ref=relic.holder_ref,
            pressure=relic.danger,
            tags=tags,
            recent_notes=[f"linked_relic={relic.relic_id}"],
        )


def _node_type_name(node_type: str) -> str:
    names = {
        "access_relay": "Access Relay",
        "containment_checkpoint": "Containment Checkpoint",
    }
    return names.get(node_type, "Node")


def _choose_supply_controller(
    state: WorldState,
    civ_id: str,
    origin_region_id: str,
    destination_region_id: str,
    rng: Random,
) -> str | None:
    candidates = [
        faction.faction_id
        for faction in state.factions.values()
        if faction.parent_civ_id == civ_id
        and (origin_region_id in faction.controlled_regions or destination_region_id in faction.controlled_regions)
    ]
    if not candidates:
        return None
    return rng.choice(candidates)


def _supply_pressure(origin: Region, destination: Region) -> str:
    if origin.security == "low" or destination.security == "low":
        return "high"
    if origin.scarcity == "high" or destination.scarcity == "high":
        return "high"
    if destination.political_tension == "high":
        return "medium"
    return "low"


def _supply_status(origin: Region, destination: Region) -> str:
    if origin.security == "low" or destination.security == "low":
        return "contested"
    if destination.scarcity == "high":
        return "strained"
    if origin.connectivity == "high":
        return "stable"
    return "fragile"


def _supply_front_tags(origin: Region, destination: Region) -> list[str]:
    tags = ["supply_front", "logistics_front"]
    if destination.scarcity == "high":
        tags.append("ration_front")
    if origin.security == "low" or destination.security == "low":
        tags.append("security_front")
    if destination.political_tension == "high":
        tags.append("political_front")
    return tags


def _build_presence_name(relic_type: str, index: int) -> str:
    if relic_type == "megastructure":
        return _compose_indexed_name(_MEGASTRUCTURE_PREFIXES, _MEGASTRUCTURE_SUFFIXES, index)
    if relic_type == "founding_protocol":
        return _compose_indexed_name(_PROTOCOL_PREFIXES, _PROTOCOL_SUFFIXES, index)
    if relic_type == "sealed_archive":
        return _compose_indexed_name(_ARCHIVE_PREFIXES, _ARCHIVE_SUFFIXES, index)
    if relic_type == "anomalous_lifeform":
        return _compose_indexed_name(_LIFEFORM_PREFIXES, _LIFEFORM_SUFFIXES, index)
    return _compose_indexed_name(_DEVICE_PREFIXES, _DEVICE_SUFFIXES, index)


def _build_region_name(rng: Random, index: int) -> str:
    return _compose_rng_name(rng, _REGION_PREFIXES, _REGION_SUFFIXES, index)


def _build_civilization_name(rng: Random, index: int) -> str:
    return _compose_rng_name(rng, _CIV_PREFIXES, _CIV_SUFFIXES, index)


def _compose_rng_name(rng: Random, prefixes: list[str], suffixes: list[str], index: int) -> str:
    prefix = rng.choice(prefixes)
    suffix = rng.choice(suffixes)
    return f"{prefix} {suffix}-{index:02d}"


def _compose_indexed_name(prefixes: list[str], suffixes: list[str], index: int) -> str:
    prefix = prefixes[(index - 1) % len(prefixes)]
    suffix = suffixes[((index - 1) // len(prefixes)) % len(suffixes)]
    return f"{prefix} {suffix}-{index:02d}"


def _build_presence_story_tags(rng: Random, relic_type: str, origin_mode: str) -> list[str]:
    tags = [rng.choice(suggested_story_tags(relic_type))]
    if relic_type == "megastructure":
        extra_tags = {
            "legacy": "deep_time_infrastructure",
            "contemporary": "live_construction",
            "hybrid": "retrofit_ambition",
        }
        tags.append(extra_tags.get(origin_mode, "scale_shock"))
    elif relic_type == "anomalous_lifeform":
        extra_tags = {
            "lab_origin": "containment_failure",
            "wild_mutation": "ecological_intrusion",
            "engineered_swarm": "distributed_intelligence",
        }
        tags.append(extra_tags.get(origin_mode, "biosecurity_breach"))
    return tags


def _build_megastructure_profile(
    state: WorldState,
    rng: Random,
    region_id: str,
    holder_ref: str,
) -> tuple[str, str, str | None, str | None, str | None, str | None]:
    faction_ids = list(state.factions.keys())
    civ_id = state.regions[region_id].civ_id
    origin_mode = rng.choices(
        ["legacy", "contemporary", "hybrid"],
        weights=[5, 3, 2],
        k=1,
    )[0]
    if origin_mode == "legacy":
        construction_state = rng.choices(
            ["degraded", "reactivating", "operational"],
            weights=[4, 2, 1],
            k=1,
        )[0]
        sponsor_ref = None
        contractor_ref = None
        financier_ref = None
        opposition_ref = rng.choice(faction_ids) if faction_ids and rng.random() < 0.35 else None
    elif origin_mode == "contemporary":
        construction_state = rng.choices(
            ["planned", "foundation", "rising", "integration"],
            weights=[3, 3, 2, 1],
            k=1,
        )[0]
        sponsor_ref = civ_id or holder_ref
        contractor_ref = rng.choice(faction_ids) if faction_ids else holder_ref
        financier_ref = sponsor_ref if rng.random() < 0.65 else holder_ref
        opposition_ref = rng.choice(faction_ids) if faction_ids and rng.random() < 0.45 else None
    else:
        construction_state = rng.choices(
            ["degraded", "retrofit", "integration"],
            weights=[2, 3, 2],
            k=1,
        )[0]
        sponsor_ref = holder_ref
        contractor_ref = rng.choice(faction_ids) if faction_ids else holder_ref
        financier_ref = civ_id or holder_ref
        opposition_ref = rng.choice(faction_ids) if faction_ids and rng.random() < 0.40 else None
    return (
        origin_mode,
        construction_state,
        sponsor_ref,
        contractor_ref,
        financier_ref,
        opposition_ref,
    )


def _build_lifeform_profile(rng: Random) -> tuple[str, str]:
    origin_mode = rng.choices(
        ["lab_origin", "wild_mutation", "engineered_swarm"],
        weights=[3, 4, 2],
        k=1,
    )[0]
    if origin_mode == "lab_origin":
        state = rng.choices(["contained", "roaming", "breeding"], weights=[3, 3, 1], k=1)[0]
    elif origin_mode == "wild_mutation":
        state = rng.choices(["nesting", "roaming", "breeding"], weights=[2, 3, 2], k=1)[0]
    else:
        state = rng.choices(["distributed", "roaming", "breeding"], weights=[3, 2, 2], k=1)[0]
    return origin_mode, state


def _build_activation_state(
    rng: Random,
    relic_type: str,
    origin_mode: str,
    construction_state: str,
) -> str:
    if relic_type != "megastructure":
        if relic_type == "anomalous_lifeform":
            if construction_state in {"contained"}:
                return "sealed"
            if construction_state in {"breeding", "distributed"}:
                return "contested"
            return rng.choice(["dormant", "contested"])
        return rng.choice(["dormant", "contested", "sealed"])
    if origin_mode == "contemporary":
        if construction_state in {"planned", "foundation"}:
            return "dormant"
        if construction_state == "integration":
            return rng.choice(["sealed", "dormant"])
        return rng.choice(["dormant", "sealed", "contested"])
    if origin_mode == "hybrid":
        if construction_state == "degraded":
            return rng.choice(["dormant", "sealed"])
        return rng.choice(["sealed", "contested", "dormant"])
    if construction_state == "operational":
        return rng.choice(["sealed", "dormant"])
    if construction_state == "reactivating":
        return rng.choice(["dormant", "contested"])
    return rng.choice(["dormant", "sealed", "contested"])
