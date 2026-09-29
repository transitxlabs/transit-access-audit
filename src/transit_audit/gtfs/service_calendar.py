"""GTFS calendar and frequency expansion helpers."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from transit_audit.gtfs.reader import GtfsFeed, parse_hhmmss


def _str_column(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.Series(df[column], index=df.index).astype(str)


def parse_service_date(value: str) -> date:
    cleaned = value.strip()
    if len(cleaned) == 8 and cleaned.isdigit():
        return datetime.strptime(cleaned, "%Y%m%d").date()
    return datetime.strptime(cleaned, "%Y-%m-%d").date()


def active_service_ids(feed: GtfsFeed, service_date: date) -> set[str]:
    """Return service_ids active on the given date per calendar.txt and calendar_dates.txt."""
    active: set[str] = set()
    calendar = feed.table("calendar")
    calendar_dates = feed.table("calendar_dates")
    date_str = service_date.strftime("%Y%m%d")
    weekday = service_date.weekday()  # Monday=0
    weekday_cols = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    if not calendar.empty:
        for _, row in calendar.iterrows():
            sid = str(row["service_id"])
            start = str(row.get("start_date", ""))
            end = str(row.get("end_date", ""))
            if start and end and not (start <= date_str <= end):
                continue
            if weekday < len(weekday_cols):
                flag = str(row.get(weekday_cols[weekday], "0"))
                if flag == "1":
                    active.add(sid)

    added: set[str] = set()
    removed: set[str] = set()
    if not calendar_dates.empty:
        for _, row in calendar_dates.iterrows():
            if str(row.get("date", "")) != date_str:
                continue
            sid = str(row["service_id"])
            exc = str(row.get("exception_type", ""))
            if exc == "1":
                added.add(sid)
            elif exc == "2":
                removed.add(sid)

    active |= added
    active -= removed

    if calendar.empty and not calendar_dates.empty:
        active = added - removed

    return active


def expand_frequency_departures(
    start_time: str,
    end_time: str,
    headway_secs: int,
    exact_times: str = "0",
) -> list[int]:
    """Expand a frequencies.txt row into departure seconds, including past-midnight end times."""
    start = parse_hhmmss(start_time)
    end = parse_hhmmss(end_time)
    if headway_secs <= 0:
        return []
    departures: list[int] = []
    if exact_times == "1":
        current = start
        while current <= end:
            departures.append(current)
            current += headway_secs
    else:
        current = start
        while current < end:
            departures.append(current)
            current += headway_secs
    return departures


def departures_for_trip_on_date(
    feed: GtfsFeed,
    trip_id: str,
    service_date: date,
    stop_id: str | None = None,
) -> list[int]:
    """Collect departure times for a trip at an optional stop, expanding frequencies when needed."""
    active = active_service_ids(feed, service_date)
    trips = feed.table("trips")
    trip_rows = trips[trips["trip_id"].astype(str) == str(trip_id)]
    if trip_rows.empty:
        return []
    trip = trip_rows.iloc[0]
    if active and str(trip["service_id"]) not in active:
        return []

    frequencies = feed.table("frequencies")
    if not frequencies.empty and "trip_id" in frequencies.columns:
        freq_rows = frequencies[frequencies["trip_id"].astype(str) == str(trip_id)]
    else:
        freq_rows = frequencies.iloc[0:0]
    if not freq_rows.empty:
        departures: list[int] = []
        for _, freq in freq_rows.iterrows():
            departures.extend(
                expand_frequency_departures(
                    str(freq["start_time"]),
                    str(freq["end_time"]),
                    int(str(freq["headway_secs"])),
                    str(freq.get("exact_times", "0")),
                )
            )
        return sorted(set(departures))

    stop_times = feed.table("stop_times")
    subset = stop_times.loc[stop_times["trip_id"].astype(str) == str(trip_id)]
    if stop_id is not None:
        subset = subset.loc[subset["stop_id"].astype(str) == str(stop_id)]
    if subset.empty:
        return []
    return sorted(parse_hhmmss(str(t)) for t in subset["departure_time"].astype(str))


def all_departures_at_stop(
    feed: GtfsFeed,
    stop_id: str,
    service_date: date,
    flex_route_ids: set[str],
) -> list[int]:
    """All departures at a stop on the given service date."""
    active = active_service_ids(feed, service_date)
    trips = feed.table("trips")
    stop_times = feed.table("stop_times")
    frequencies = feed.table("frequencies")

    if trips.empty:
        return []

    active_trips = trips.copy()
    if active:
        active_trips = active_trips[
            active_trips["service_id"].astype(str).isin(list(active))
        ]
    if flex_route_ids:
        route_ids = _str_column(active_trips, "route_id")
        active_trips = active_trips[~route_ids.isin(list(flex_route_ids))]

    active_trip_ids = set(active_trips["trip_id"].astype(str))
    departures: list[int] = []

    if not stop_times.empty:
        at_stop = stop_times.loc[
            (stop_times["stop_id"].astype(str) == str(stop_id))
            & (stop_times["trip_id"].astype(str).isin(list(active_trip_ids)))
        ]
        departures.extend(parse_hhmmss(str(t)) for t in at_stop["departure_time"].astype(str))

    if not frequencies.empty:
        freq_trips = frequencies.loc[
            frequencies["trip_id"].astype(str).isin(list(active_trip_ids))
        ]
        for _, freq in freq_trips.iterrows():
            trip_id = str(freq["trip_id"])
            trip_stops = stop_times[stop_times["trip_id"].astype(str) == trip_id]
            if trip_stops.empty:
                continue
            if str(stop_id) not in trip_stops["stop_id"].astype(str).tolist():
                continue
            departures.extend(
                expand_frequency_departures(
                    str(freq["start_time"]),
                    str(freq["end_time"]),
                    int(str(freq["headway_secs"])),
                    str(freq.get("exact_times", "0")),
                )
            )

    return sorted(set(departures))
