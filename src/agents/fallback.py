"""Fallback behavior when AI calls fail."""

from __future__ import annotations

from dataclasses import dataclass

from src.events.query import find_recent_relic_event_for_region
from src.events.taxonomy import event_theme_tags
from src.world.character import Character
from src.world.state import WorldState
from src.world.region import Region


@dataclass(slots=True)
class Intent:
    """Structured character intent."""

    character_id: str
    intent_type: str
    target_ref: str
    goal: str
    motivation: str
    risk_tolerance: str
    urgency: float
    proposed_action: str
    tone: str
    source: str = "fallback"


def build_fallback_intent(character: Character, region: Region, world: WorldState | None = None) -> Intent:
    """Return a deterministic low-fidelity intent when AI is unavailable."""
    frame_axes = world.structure_template.pressure_axes if world is not None else []
    frame_fronts = world.structure_template.dominant_fronts if world is not None else []
    anomaly_bias = world.structure_template.anomaly_bias if world is not None else "mixed_exceptional_pressure"
    if world is not None:
        relic_event = find_recent_relic_event_for_region(world, region.region_id)
        if relic_event is not None:
            if _event_type_contains(relic_event, "lifeform_migration_front"):
                return Intent(
                    character_id=character.char_id,
                    intent_type="seal_migration_corridor",
                    target_ref=region.region_id,
                    goal="Seal the lifeform migration corridor",
                    motivation="Cross-region spread will widen the front if left open",
                    risk_tolerance="medium",
                    urgency=0.9,
                    proposed_action="Harden transit seams and cut movement channels around the new front",
                    tone="urgent",
                )
            if _event_has_theme(relic_event, "project") and _event_type_contains(relic_event, "budget"):
                return Intent(
                    character_id=character.char_id,
                    intent_type="secure_project_budget",
                    target_ref=region.region_id,
                    goal="Keep the project budget from collapsing",
                    motivation="Project rollback would weaken local order and leverage",
                    risk_tolerance="medium",
                    urgency=0.87,
                    proposed_action="Protect funding nodes and pressure decision makers to release stalled capital",
                    tone="tight",
                )
            if _event_type_contains(relic_event, "accident"):
                return Intent(
                    character_id=character.char_id,
                    intent_type="suppress_site_accident_fallout",
                    target_ref=region.region_id,
                    goal="Contain the fallout from the site accident",
                    motivation="An unmanaged accident will turn the project into a wider political breach",
                    risk_tolerance="medium",
                    urgency=0.88,
                    proposed_action="Lock down exposure, isolate damage, and keep opportunists away from the site",
                    tone="urgent",
                )
            if _event_type_contains(relic_event, "financing"):
                return Intent(
                    character_id=character.char_id,
                    intent_type="redirect_project_financing",
                    target_ref=region.region_id,
                    goal="Pull the project back under reliable capital",
                    motivation="The financing front is now unstable and politically exposed",
                    risk_tolerance="medium",
                    urgency=0.85,
                    proposed_action="Redirect strained capital through aligned channels before the site loses control",
                    tone="tight",
                )
            if _event_type_contains(relic_event, "project_bid") or _event_type_contains(relic_event, "contract"):
                return Intent(
                    character_id=character.char_id,
                    intent_type="contest_project_contract",
                    target_ref=region.region_id,
                    goal="Shift execution control over the project front",
                    motivation="Contract control now determines who can shape the site",
                    risk_tolerance="high",
                    urgency=0.84,
                    proposed_action="Disrupt the current execution chain and push aligned operators into the contract layer",
                    tone="hard",
                )
            if region.security == "low" or region.political_tension == "high":
                return Intent(
                    character_id=character.char_id,
                    intent_type="contain_relic_fallout",
                    target_ref=region.region_id,
                    goal="Prevent relic fallout from breaking district order",
                    motivation="The relic conflict is already spilling into local control",
                    risk_tolerance="medium",
                    urgency=0.86,
                    proposed_action="Seal unstable approaches and suppress panic around the relic zone",
                    tone="urgent",
                )
            return Intent(
                character_id=character.char_id,
                intent_type="secure_relic_access",
                target_ref=region.region_id,
                goal="Secure leverage over the relic access corridor",
                motivation=_fallback_relic_motivation(anomaly_bias, frame_fronts),
                risk_tolerance="high",
                urgency=0.81,
                proposed_action="Place trusted operators around access routes and claim procedural control",
                tone="calculated",
            )

    if region.scarcity == "high":
        if "project_fronts" in frame_fronts or anomaly_bias == "megastructure_pressure":
            return Intent(
                character_id=character.char_id,
                intent_type="secure_project_budget",
                target_ref=region.region_id,
                goal="Keep strategic build corridors supplied",
                motivation="The wider frame treats supply strain as a project continuity problem",
                risk_tolerance="medium",
                urgency=0.84,
                proposed_action="Stabilize supply lanes that feed the most fragile build and logistics fronts",
                tone="tight",
            )
        return Intent(
            character_id=character.char_id,
            intent_type="stabilize_supply",
            target_ref=region.region_id,
            goal="Reduce regional supply pressure",
            motivation=_fallback_supply_motivation(frame_axes),
            risk_tolerance="medium",
            urgency=0.82,
            proposed_action="Mobilize available contacts to secure critical supply nodes",
            tone="restrained but urgent",
        )

    if region.political_tension == "high":
        if "governance_fronts" in frame_fronts or "legitimacy_erosion" in frame_axes:
            return Intent(
                character_id=character.char_id,
                intent_type="broker_power_shift",
                target_ref=region.region_id,
                goal="Reshape the local order before legitimacy breaks",
                motivation="The wider frame is already bending toward governance crisis and political realignment",
                risk_tolerance="high",
                urgency=0.83,
                proposed_action="Rewire local alignments and isolate actors who can turn tension into open fracture",
                tone="hard",
            )
        return Intent(
            character_id=character.char_id,
            intent_type="manage_unrest",
            target_ref=region.region_id,
            goal="Contain unrest before control breaks down",
            motivation="Rising political tension increases the risk of open conflict",
            risk_tolerance="medium",
            urgency=0.77,
            proposed_action="Reach out to key intermediaries and split hostile groups",
            tone="alert",
        )

    return Intent(
        character_id=character.char_id,
        intent_type=_fallback_default_intent(frame_axes, frame_fronts, anomaly_bias),
        target_ref=region.region_id,
        goal=_fallback_default_goal(frame_axes, frame_fronts, anomaly_bias),
        motivation=_fallback_default_motivation(frame_axes, frame_fronts, anomaly_bias),
        risk_tolerance="low",
        urgency=0.46,
        proposed_action=_fallback_default_action(frame_axes, frame_fronts, anomaly_bias),
        tone="restrained",
    )


def build_fallback_intent_from_event(
    character: Character,
    region: Region,
    relic_event: object | None,
    world: WorldState | None = None,
) -> Intent:
    """Return fallback behavior using only a local visible relic event, not global state."""
    if relic_event is None:
        return build_fallback_intent(character, region, world)
    return _intent_from_visible_event(character, region, relic_event, world=world)


def _intent_from_visible_event(
    character: Character,
    region: Region,
    relic_event: object,
    *,
    world: WorldState | None = None,
) -> Intent:
    anomaly_bias = world.structure_template.anomaly_bias if world is not None else "mixed_exceptional_pressure"
    if _event_type_contains(relic_event, "lifeform_migration_front"):
        return Intent(
            character_id=character.char_id,
            intent_type="seal_migration_corridor",
            target_ref=region.region_id,
            goal="Seal the lifeform migration corridor",
            motivation="Cross-region spread will widen the front if left open",
            risk_tolerance="medium",
            urgency=0.9,
            proposed_action="Harden transit seams and cut movement channels around the new front",
            tone="urgent",
        )
    if _event_has_theme(relic_event, "project") and _event_type_contains(relic_event, "budget"):
        return Intent(
            character_id=character.char_id,
            intent_type="secure_project_budget",
            target_ref=region.region_id,
            goal="Keep the project budget from collapsing",
            motivation="Project rollback would weaken local order and leverage",
            risk_tolerance="medium",
            urgency=0.87,
            proposed_action="Protect funding nodes and pressure decision makers to release stalled capital",
            tone="tight",
        )
    if _event_type_contains(relic_event, "accident"):
        return Intent(
            character_id=character.char_id,
            intent_type="suppress_site_accident_fallout",
            target_ref=region.region_id,
            goal="Contain the fallout from the site accident",
            motivation="An unmanaged accident will turn the project into a wider political breach",
            risk_tolerance="medium",
            urgency=0.88,
            proposed_action="Lock down exposure, isolate damage, and keep opportunists away from the site",
            tone="urgent",
        )
    if _event_type_contains(relic_event, "financing"):
        return Intent(
            character_id=character.char_id,
            intent_type="redirect_project_financing",
            target_ref=region.region_id,
            goal="Pull the project back under reliable capital",
            motivation="The financing front is now unstable and politically exposed",
            risk_tolerance="medium",
            urgency=0.85,
            proposed_action="Redirect strained capital through aligned channels before the site loses control",
            tone="tight",
        )
    if _event_type_contains(relic_event, "project_bid") or _event_type_contains(relic_event, "contract"):
        return Intent(
            character_id=character.char_id,
            intent_type="contest_project_contract",
            target_ref=region.region_id,
            goal="Shift execution control over the project front",
            motivation="Contract control now determines who can shape the site",
            risk_tolerance="high",
            urgency=0.84,
            proposed_action="Disrupt the current execution chain and push aligned operators into the contract layer",
            tone="hard",
        )
    if region.security == "low" or region.political_tension == "high":
        return Intent(
            character_id=character.char_id,
            intent_type="contain_relic_fallout",
            target_ref=region.region_id,
            goal="Prevent relic fallout from breaking district order",
            motivation="The relic conflict is already spilling into local control",
            risk_tolerance="medium",
            urgency=0.86,
            proposed_action="Seal unstable approaches and suppress panic around the relic zone",
            tone="urgent",
        )
    return Intent(
        character_id=character.char_id,
        intent_type="secure_relic_access",
        target_ref=region.region_id,
        goal="Secure leverage over the relic access corridor",
        motivation=_fallback_relic_motivation(anomaly_bias, world.structure_template.dominant_fronts if world is not None else []),
        risk_tolerance="high",
        urgency=0.81,
        proposed_action="Place trusted operators around access routes and claim procedural control",
        tone="calculated",
    )


def _fallback_supply_motivation(frame_axes: list[str]) -> str:
    if "capital_realignment" in frame_axes:
        return "Supply strain is now tied to wider capital and logistics realignment"
    if "infrastructure_dependency" in frame_axes:
        return "Shortage is eroding the infrastructure shell that keeps the district stable"
    return "Escalating scarcity is eroding the local order"


def _fallback_relic_motivation(anomaly_bias: str, frame_fronts: list[str]) -> str:
    if anomaly_bias == "megastructure_pressure" or "project_fronts" in frame_fronts:
        return "Control of the anomaly now shapes the wider project and infrastructure balance"
    if anomaly_bias == "sealed_information_pressure":
        return "Control over the anomaly also controls what destabilizing information can surface next"
    if anomaly_bias == "autonomous_system_pressure":
        return "Anomaly control now overlaps with deeper system access and governance leverage"
    return "Relic control now shapes the region's next balance"


def _event_has_theme(event: object, theme: str) -> bool:
    return theme in event_theme_tags(event)


def _event_type_contains(event: object, token: str) -> bool:
    return token.lower() in str(event.event_type).lower()


def _fallback_default_intent(
    frame_axes: list[str],
    frame_fronts: list[str],
    anomaly_bias: str,
) -> str:
    if "governance_fronts" in frame_fronts or "legitimacy_erosion" in frame_axes:
        return "broker_power_shift"
    if "project_fronts" in frame_fronts or anomaly_bias == "megastructure_pressure":
        return "secure_project_budget"
    if "supply_fronts" in frame_fronts or "supply_strain" in frame_axes:
        return "stabilize_supply"
    return "improve_position"


def _fallback_default_goal(
    frame_axes: list[str],
    frame_fronts: list[str],
    anomaly_bias: str,
) -> str:
    if "governance_fronts" in frame_fronts:
        return "Expand leverage over the local governing order"
    if "project_fronts" in frame_fronts or anomaly_bias == "megastructure_pressure":
        return "Secure a stronger position on the live project front"
    if "supply_fronts" in frame_fronts:
        return "Gain leverage over stressed supply corridors"
    return "Expand influence within the current order"


def _fallback_default_motivation(
    frame_axes: list[str],
    frame_fronts: list[str],
    anomaly_bias: str,
) -> str:
    if "legitimacy_erosion" in frame_axes:
        return "Political structure is soft enough that leverage can shift quickly"
    if "project_fronts" in frame_fronts or anomaly_bias == "megastructure_pressure":
        return "The current world frame rewards actors who secure project continuity and access"
    if "supply_strain" in frame_axes:
        return "Control over strained logistics is becoming the easiest route to influence"
    return "The environment is still stable enough to gain leverage"


def _fallback_default_action(
    frame_axes: list[str],
    frame_fronts: list[str],
    anomaly_bias: str,
) -> str:
    if "governance_fronts" in frame_fronts:
        return "Probe brokers, tighten alignments, and reshape who can speak for the district"
    if "project_fronts" in frame_fronts or anomaly_bias == "megastructure_pressure":
        return "Map the active build chain and secure its weakest control seams"
    if "supply_fronts" in frame_fronts:
        return "Carefully map supply chokepoints and cultivate dependence around them"
    return "Carefully probe organizations and relationships in the district"
