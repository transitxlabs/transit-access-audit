"""Build schedule indexes for accessibility-filtered routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from transit_audit.gtfs.reader import GtfsFeed, parse_hhmmss
from transit_audit.gtfs.service_calendar import active_service_ids
from transit_audit.routing.accessibility import accessible_stops, accessible_trips
from transit_audit.routing.models import UnknownPolicy


@dataclass
class TripStopTime:
    stop_id: str
    arrival_s: int
    departure_s: int
    stop_sequence: int


@dataclass
class TripSchedule:
    trip_id: str
    stops: list[TripStopTime]


@dataclass
class ScheduleIndex:
    policy: UnknownPolicy
    trips: dict[str, TripSchedule] = field(default_factory=dict)
    boardings: dict[str, list[tuple[str, int, int]]] = field(default_factory=dict)
    accessible_stop_ids: set[str] = field(default_factory=set)
    walk_edges: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    permitted_trip_ids: set[str] | None = None


def build_schedule_index(
    feed: GtfsFeed,
    service_date: date,
    policy: UnknownPolicy,
    *,
    stop_overrides: dict[str, str] | None = None,
    trip_overrides: dict[str, str] | None = None,
    inherit_from_parent: bool = True,
    walk_edges: dict[str, list[tuple[str, int]]] | None = None,
) -> ScheduleIndex:
    """Build a trip boarding index filtered by wheelchair policy."""
    stops = feed.table("stops")
    trips = feed.table("trips")
    stop_times = feed.table("stop_times")
    if stop_times.empty or trips.empty:
        return ScheduleIndex(policy=policy, walk_edges=walk_edges or {})

    active_services = active_service_ids(feed, service_date)
    active_trip_ids = set(
        trips.loc[trips["service_id"].astype(str).isin(active_services), "trip_id"].astype(str)
    )
    if policy == UnknownPolicy.SCHEDULE_ONLY:
        allowed_stops = set(stops["stop_id"].astype(str))
        allowed_trips = set(active_trip_ids)
    else:
        allowed_stops = accessible_stops(
            stops,
            policy,
            stop_overrides=stop_overrides,
            inherit_from_parent=inherit_from_parent,
        )
        allowed_trips = accessible_trips(trips, policy, trip_overrides=trip_overrides) & active_trip_ids

    filtered = stop_times[stop_times["trip_id"].astype(str).isin(allowed_trips)].copy()
    if filtered.empty:
        return ScheduleIndex(
            policy=policy,
            accessible_stop_ids=allowed_stops,
            walk_edges=walk_edges or {},
        )

    filtered["stop_sequence"] = pd.to_numeric(filtered["stop_sequence"], errors="coerce")
    filtered = filtered.dropna(subset=["stop_sequence"])
    filtered = filtered.sort_values(["trip_id", "stop_sequence"])

    index = ScheduleIndex(
        policy=policy,
        accessible_stop_ids=allowed_stops,
        walk_edges=walk_edges or {},
    )
    trip_records: dict[str, list[TripStopTime]] = {}

    for trip_id, group in filtered.groupby(filtered["trip_id"].astype(str), sort=False):
        if trip_id not in allowed_trips:
            continue
        stop_list: list[TripStopTime] = []
        trip_allowed = True
        for row in group.to_dict("records"):
            stop_id = str(row["stop_id"])
            if policy != UnknownPolicy.SCHEDULE_ONLY and stop_id not in allowed_stops:
                trip_allowed = False
                break
            arrival_s = parse_hhmmss(str(row["arrival_time"]))
            departure_s = parse_hhmmss(str(row["departure_time"]))
            stop_list.append(
                TripStopTime(
                    stop_id=stop_id,
                    arrival_s=arrival_s,
                    departure_s=departure_s,
                    stop_sequence=int(row["stop_sequence"]),
                )
            )
        if not trip_allowed or not stop_list:
            continue
        index.trips[trip_id] = TripSchedule(trip_id=trip_id, stops=stop_list)
        trip_records[trip_id] = stop_list

    for trip_id, stop_list in trip_records.items():
        for position, stop_time in enumerate(stop_list):
            index.boardings.setdefault(stop_time.stop_id, []).append(
                (trip_id, position, stop_time.departure_s)
            )

    for stop_id in index.boardings:
        index.boardings[stop_id].sort(key=lambda item: item[2])

    return index
