"""Resolve GTFS wheelchair accessibility under routing policies."""

from __future__ import annotations

import pandas as pd

from transit_audit.routing.policy import UnknownPolicy, is_accessible, wheelchair_category


def resolve_stop_boarding(
    stops: pd.DataFrame,
    *,
    stop_overrides: dict[str, str] | None = None,
    inherit_from_parent: bool = True,
) -> dict[str, str]:
    """Resolve stop ``wheelchair_boarding`` with optional parent-station inheritance."""
    if stops.empty:
        return {}

    overrides = stop_overrides or {}
    values = {str(row["stop_id"]): overrides.get(str(row["stop_id"]),
              str(row.get("wheelchair_boarding", ""))) for row in stops.to_dict("records")}
    parents = {str(row["stop_id"]): str(row.get("parent_station", "")).strip()
               for row in stops.to_dict("records")} if inherit_from_parent else {}
    resolved: dict[str, str] = {}
    for stop_id in values:
        current = stop_id
        seen: set[str] = set()
        value = values[current]
        while wheelchair_category(value) == "unknown" and parents.get(current):
            seen.add(current)
            current = parents[current]
            if current in seen or current not in values:
                value = ""
                break
            value = values[current]
        resolved[stop_id] = value
    return resolved


def accessible_stops(
    stops: pd.DataFrame,
    policy: UnknownPolicy,
    *,
    stop_overrides: dict[str, str] | None = None,
    inherit_from_parent: bool = True,
) -> set[str]:
    resolved = resolve_stop_boarding(
        stops,
        stop_overrides=stop_overrides,
        inherit_from_parent=inherit_from_parent,
    )
    return {
        stop_id
        for stop_id, raw in resolved.items()
        if is_accessible(raw, policy)
    }


def accessible_trips(
    trips: pd.DataFrame,
    policy: UnknownPolicy,
    *,
    trip_overrides: dict[str, str] | None = None,
) -> set[str]:
    if trips.empty:
        return set()
    overrides = trip_overrides or {}
    allowed: set[str] = set()
    for _, row in trips.iterrows():
        trip_id = str(row["trip_id"])
        raw = overrides.get(trip_id, str(row.get("wheelchair_accessible", "")))
        if is_accessible(raw, policy):
            allowed.add(trip_id)
    return allowed


def unknown_entities(stops: pd.DataFrame, trips: pd.DataFrame) -> tuple[list[str], list[str]]:
    unknown_stops: list[str] = []
    resolved = resolve_stop_boarding(stops)
    for stop_id, raw in resolved.items():
        if wheelchair_category(raw) == "unknown":
            unknown_stops.append(stop_id)

    unknown_trips: list[str] = []
    if not trips.empty and "wheelchair_accessible" in trips.columns:
        for _, row in trips.iterrows():
            if wheelchair_category(str(row.get("wheelchair_accessible", ""))) == "unknown":
                unknown_trips.append(str(row["trip_id"]))
    elif not trips.empty:
        unknown_trips = trips["trip_id"].astype(str).tolist()

    return sorted(unknown_stops), sorted(unknown_trips)


def resolved_stop_categories(stops: pd.DataFrame) -> pd.Series:
    """Return resolved wheelchair categories for audit checks."""
    resolved = resolve_stop_boarding(stops)
    return pd.Series({stop_id: wheelchair_category(raw) for stop_id, raw in resolved.items()})
