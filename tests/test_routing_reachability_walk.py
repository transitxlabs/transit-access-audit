"""Reachability tests with walking transfers."""

from __future__ import annotations

from transit_audit.routing.index import ScheduleIndex, UnknownPolicy
from transit_audit.routing.reachability import is_destination_reachable


def test_walking_links_extend_reachability() -> None:
    index = ScheduleIndex(
        policy=UnknownPolicy.SCHEDULE_ONLY,
        accessible_stop_ids={"A", "B"},
        walk_edges={"A": [("B", 120)]},
    )
    ok, travel = is_destination_reachable("A", "B", 8 * 3600, 3600, 0, 0, index)
    assert ok
    assert travel == 120
