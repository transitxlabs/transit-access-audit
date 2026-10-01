"""Extra routing tests for coverage and exactness."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from transit_audit.gtfs.reader import GtfsFeed, read_gtfs_zip
from transit_audit.routing.accessibility import accessible_stops, resolve_stop_boarding
from transit_audit.routing.bounds import _verification_change
from transit_audit.routing.index import build_schedule_index
from transit_audit.routing.models import BoundsConfig, UnknownPolicy
from transit_audit.routing.policy import wheelchair_category

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_wheelchair_zero_is_unknown_not_inaccessible() -> None:
    assert wheelchair_category("0") == "unknown"


def test_parent_inheritance_for_zero_coded_child() -> None:
    feed = read_gtfs_zip(FIXTURES / "wheelchair_inheritance.zip")
    resolved = resolve_stop_boarding(feed.table("stops"))
    assert resolved["PLAT2"] == "1"


def test_rank_verification_returns_empty_without_unknowns() -> None:
    from transit_audit.routing.bounds import rank_verification_targets

    stops = pd.DataFrame(
        {
            "stop_id": ["S1"],
            "wheelchair_boarding": ["1"],
            "stop_lat": [48.0],
            "stop_lon": [-123.0],
        }
    )
    trips = pd.DataFrame(
        {"trip_id": ["T1"], "wheelchair_accessible": ["1"], "service_id": ["WEEKDAY"]}
    )
    feed = GtfsFeed(
        path=Path("memory"),
        tables={"stops": stops, "trips": trips, "stop_times": pd.DataFrame()},
    )
    config = BoundsConfig(service_date=date(2024, 6, 3))
    assert rank_verification_targets(feed, config, [("S1", "S1")]) == []


def test_prefer_unknown_fills_origin_count_when_all_unknown() -> None:
    from transit_audit.gtfs.zip_limits import EVALUATION_ZIP_LIMITS
    from transit_audit.routing.sample import sample_od_pairs, sample_stop_ids

    calgary = Path(".cache/gtfs/calgary_transit_gtfs.zip")
    if not calgary.exists():
        return
    feed = read_gtfs_zip(
        calgary,
        EVALUATION_ZIP_LIMITS,
        only_tables={"stops", "trips", "stop_times", "calendar", "calendar_dates"},
    )
    origins = sample_stop_ids(feed, 20, 42, prefer_unknown=True)
    destinations = sample_stop_ids(feed, 40, 43, prefer_unknown=False)
    pairs = sample_od_pairs(origins, destinations, 44)
    assert len(origins) == 20
    assert len(destinations) == 40
    assert len(pairs) == 800


def test_rank_verification_with_od_results() -> None:
    from transit_audit.routing.bounds import compute_bounds, rank_verification_targets

    feed = read_gtfs_zip(FIXTURES / "bounds_route.zip")
    config = BoundsConfig(
        service_date=date(2024, 6, 3),
        departure_time="07:00:00",
        origin_count=5,
        destination_count=5,
        random_seed=0,
        rank_verification=False,
    )
    result = compute_bounds(feed, config)
    od_pairs = [(pair.origin_stop_id, pair.destination_stop_id) for pair in result.od_pairs]
    targets = rank_verification_targets(
        feed,
        config,
        od_pairs,
        od_results=result.od_pairs,
        base_mean_width=result.mean_interval_width,
    )
    assert targets
    assert targets[0].interval_width_change > 0


def test_cyclic_parent_station_inheritance() -> None:
    stops = pd.DataFrame(
        {
            "stop_id": ["A", "B"],
            "wheelchair_boarding": ["", ""],
            "parent_station": ["B", "A"],
        }
    )
    resolved = resolve_stop_boarding(stops)
    assert resolved["A"] == ""
    assert resolved["B"] == ""


def test_missing_parent_row_resolves_empty() -> None:
    stops = pd.DataFrame(
        {
            "stop_id": ["A"],
            "wheelchair_boarding": [""],
            "parent_station": ["MISSING"],
        }
    )
    assert resolve_stop_boarding(stops)["A"] == ""


def test_walk_edges_active_stop_filter() -> None:
    from transit_audit.routing.walking import build_walk_edges

    stops = pd.DataFrame(
        {
            "stop_id": ["S1", "S2"],
            "stop_lat": [48.4284, 48.4290],
            "stop_lon": [-123.3656, -123.3640],
        }
    )
    assert build_walk_edges(stops, speed_mps=1.4, radius_m=300.0, active_stop_ids={"S1"}) == {}


def test_accessible_stops_without_wheelchair_column() -> None:
    stops = pd.DataFrame({"stop_id": ["S1"], "stop_lat": [48.0], "stop_lon": [-123.0]})
    assert "S1" in accessible_stops(stops, UnknownPolicy.OPTIMISTIC)
    assert accessible_stops(stops, UnknownPolicy.PESSIMISTIC) == set()


def test_verification_change_metric() -> None:
    change, affected = _verification_change([1, 1, 0], [0, 1, 0], [1, 0, 0], total_pairs=4)
    assert change == 0.25
    assert affected == 2


def test_schedule_only_index_keeps_all_active_trips() -> None:
    feed = read_gtfs_zip(FIXTURES / "bounds_route.zip")
    index = build_schedule_index(feed, date(2024, 6, 3), UnknownPolicy.SCHEDULE_ONLY)
    assert index.trips


def test_schedule_only_includes_unknown_stops() -> None:
    stops = pd.DataFrame(
        {
            "stop_id": ["S1", "S2"],
            "wheelchair_boarding": ["", "1"],
            "stop_lat": [48.0, 48.01],
            "stop_lon": [-123.0, -123.0],
        }
    )
    optimistic = accessible_stops(stops, UnknownPolicy.OPTIMISTIC)
    pessimistic = accessible_stops(stops, UnknownPolicy.PESSIMISTIC)
    assert "S1" in optimistic and "S1" not in pessimistic
    assert "S2" in optimistic and "S2" in pessimistic
