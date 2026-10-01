"""Tests for routing accessibility helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from transit_audit.gtfs.reader import read_gtfs_zip
from transit_audit.routing.accessibility import (
    accessible_stops,
    accessible_trips,
    resolve_stop_boarding,
    unknown_entities,
)
from transit_audit.routing.policy import UnknownPolicy

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_resolve_stop_boarding_inheritance() -> None:
    feed = read_gtfs_zip(FIXTURES / "wheelchair_inheritance.zip")
    resolved = resolve_stop_boarding(feed.table("stops"))
    assert resolved["PLAT1"] == "1"
    assert resolved["STN1"] == "1"


def test_unknown_entities_counts() -> None:
    feed = read_gtfs_zip(FIXTURES / "bounds_route.zip")
    unknown_stops, unknown_trips = unknown_entities(feed.table("stops"), feed.table("trips"))
    assert "S1" in unknown_stops
    assert "T1" in unknown_trips


def test_policy_stop_sets() -> None:
    feed = read_gtfs_zip(FIXTURES / "bounds_route.zip")
    stops = feed.table("stops")
    optimistic = accessible_stops(stops, UnknownPolicy.OPTIMISTIC)
    pessimistic = accessible_stops(stops, UnknownPolicy.PESSIMISTIC)
    assert "S1" in optimistic
    assert "S1" not in pessimistic


def test_policy_trip_sets() -> None:
    feed = read_gtfs_zip(FIXTURES / "bounds_route.zip")
    trips = feed.table("trips")
    optimistic = accessible_trips(trips, UnknownPolicy.OPTIMISTIC)
    pessimistic = accessible_trips(trips, UnknownPolicy.PESSIMISTIC)
    assert "T1" in optimistic
    assert "T1" not in pessimistic
    assert "T2" in optimistic and "T2" in pessimistic


def test_resolve_empty_stops() -> None:
    assert resolve_stop_boarding(pd.DataFrame()) == {}
