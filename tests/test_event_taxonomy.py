import unittest

from src.events.models import Event
from src.events.taxonomy import event_midlayer_bucket, payload_midlayer_bucket


def _event(event_type: str, *, event_scope: str = "relic") -> Event:
    return Event(
        event_id=f"test-{event_type}",
        tick=1,
        time_granularity="day",
        event_type=event_type,
        event_scope=event_scope,
        title=event_type,
        summary="",
        region_refs=["region_01"],
        faction_refs=["faction_01"],
        relic_refs=["relic_01"] if event_scope == "relic" else [],
        severity="medium",
    )


class EventTaxonomyTests(unittest.TestCase):
    def test_payload_midlayer_bucket_examples(self) -> None:
        self.assertEqual(payload_midlayer_bucket("project_bid->faction_01"), "project_shifts")
        self.assertEqual(payload_midlayer_bucket("resource_reallocation->region_01"), "supply_shocks")
        self.assertEqual(payload_midlayer_bucket("security_cordon_raised"), "security_clamps")
        self.assertEqual(payload_midlayer_bucket("unknown_action"), "other_changes")

    def test_anomaly_events_do_not_fall_into_security_bucket(self) -> None:
        self.assertEqual(event_midlayer_bucket(_event("faction_archive_breach")), "anomaly_surges")
        self.assertEqual(event_midlayer_bucket(_event("faction_protocol_breach")), "anomaly_surges")
        self.assertEqual(event_midlayer_bucket(_event("lifeform_migration_front")), "anomaly_surges")
        self.assertEqual(event_midlayer_bucket(_event("faction_lifeform_containment")), "anomaly_surges")

    def test_explicit_security_events_stay_in_security_bucket(self) -> None:
        self.assertEqual(event_midlayer_bucket(_event("protocol_emergency_lockdown")), "security_clamps")
        self.assertEqual(event_midlayer_bucket(_event("project_security_cordon", event_scope="project")), "security_clamps")

    def test_project_and_supply_events_keep_primary_buckets(self) -> None:
        self.assertEqual(event_midlayer_bucket(_event("faction_project_bid", event_scope="faction")), "project_shifts")
        self.assertEqual(event_midlayer_bucket(_event("resource_reallocation", event_scope="faction")), "supply_shocks")


if __name__ == "__main__":
    unittest.main()
