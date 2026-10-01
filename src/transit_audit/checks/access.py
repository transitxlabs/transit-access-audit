"""Accessibility data coverage checks."""

from __future__ import annotations

from typing import cast

import pandas as pd

from transit_audit.config import AuditConfig
from transit_audit.gtfs.reader import GtfsFeed
from transit_audit.models import Finding, Metric, Severity
from transit_audit.routing.accessibility import resolve_stop_boarding
from transit_audit.routing.policy import GTFS_ACCESSIBILITY_SPEC, wheelchair_category

VALID_PATHWAY_MODES = {"1", "2", "3", "4", "5", "6", "7"}


def _mask_count(mask: pd.Series) -> int:
    return int(mask.sum())


def _unique_column_strings(df: pd.DataFrame, column: str) -> list[str]:
    return sorted({str(value) for value in df[column].tolist()})


def _resolve_wheelchair_boarding(stops: pd.DataFrame) -> tuple[pd.Series, list[str]]:
    """Resolve wheelchair_boarding with parent_station inheritance."""
    if stops.empty:
        return pd.Series(dtype=str), []

    resolved_map = resolve_stop_boarding(stops)
    issues: list[str] = []
    parent_map: dict[str, str] = {}
    if "parent_station" in stops.columns:
        for _, row in stops.iterrows():
            parent = str(row.get("parent_station", "")).strip()
            if parent:
                parent_map[str(row["stop_id"])] = parent

    for stop_id in resolved_map:
        chain: set[str] = set()
        current = stop_id
        while current in parent_map:
            if current in chain:
                issues.append(f"cyclic_parent:{stop_id}")
                break
            chain.add(current)
            current = parent_map[current]

    result = stops["stop_id"].astype(str).map(
        lambda stop_id: wheelchair_category(resolved_map.get(stop_id, ""))
    )
    return result, issues


def _location_type_series(stops: pd.DataFrame) -> pd.Series:
    if "location_type" not in stops.columns:
        return pd.Series("0", index=stops.index, dtype=str)
    return cast(pd.Series, stops["location_type"].astype(str).fillna("0"))


def run_access_checks(feed: GtfsFeed, config: AuditConfig) -> tuple[list[Finding], list[Metric]]:
    findings: list[Finding] = []
    metrics: list[Metric] = []
    stops = feed.table("stops")
    trips = feed.table("trips")

    if config.is_check_enabled("ACCESS.STOP.WHEELCHAIR.KNOWN") and not stops.empty:
        raw_categories = (
            stops["wheelchair_boarding"].map(wheelchair_category)
            if "wheelchair_boarding" in stops.columns
            else pd.Series(["unknown"] * len(stops), index=stops.index)
        )
        resolved, inheritance_issues = _resolve_wheelchair_boarding(stops)
        raw_unknown = int((raw_categories == "unknown").sum())
        resolved_unknown = int((resolved == "unknown").sum())

        metrics.append(
            Metric(
                metric_id="ACCESS.STOP.WHEELCHAIR.KNOWN",
                label="Stops with known wheelchair_boarding (resolved)",
                value=int(len(stops) - resolved_unknown),
                numerator=int(len(stops) - resolved_unknown),
                denominator=len(stops),
                unit="stops",
                metadata={
                    "raw_unknown_count": raw_unknown,
                    "resolved_unknown_count": resolved_unknown,
                    "raw_breakdown": raw_categories.value_counts().to_dict(),
                    "resolved_breakdown": resolved.value_counts().to_dict(),
                    "inheritance_issues": inheritance_issues,
                },
                source_url=GTFS_ACCESSIBILITY_SPEC,
            )
        )
        if resolved_unknown:
            findings.append(
                Finding(
                    check_id="ACCESS.STOP.WHEELCHAIR.KNOWN",
                    severity=Severity.WARNING,
                    message=(
                        f"{resolved_unknown} stops have unknown wheelchair_boarding "
                        "after parent inheritance."
                    ),
                    evidence={
                        "unknown_count": resolved_unknown,
                        "raw_unknown_count": raw_unknown,
                        "inheritance_issues": inheritance_issues,
                    },
                    suggested_action=(
                        "Populate wheelchair_boarding for all stops and parent stations."
                    ),
                )
            )

    if config.is_check_enabled("ACCESS.TRIP.WHEELCHAIR.KNOWN") and not trips.empty:
        if "wheelchair_accessible" not in trips.columns:
            unknown_trips = len(trips)
        else:
            unknown_trips = _mask_count(
                trips["wheelchair_accessible"].map(wheelchair_category).eq("unknown")
            )
            metrics.append(
                Metric(
                    metric_id="ACCESS.TRIP.WHEELCHAIR.KNOWN",
                    label="Trips with known wheelchair_accessible",
                    value=int(len(trips) - unknown_trips),
                    numerator=int(len(trips) - unknown_trips),
                    denominator=len(trips),
                    unit="trips",
                    source_url=GTFS_ACCESSIBILITY_SPEC,
                )
            )

    if config.is_check_enabled("ACCESS.TRIP_STOP.CONFLICT"):
        stop_times = feed.table("stop_times")
        if (
            not trips.empty
            and not stops.empty
            and not stop_times.empty
            and "wheelchair_accessible" in trips.columns
            and "wheelchair_boarding" in stops.columns
        ):
            resolved, _ = _resolve_wheelchair_boarding(stops)
            stops_with_resolved = stops.copy()
            stops_with_resolved["wheelchair_boarding_resolved"] = resolved
            merged = stop_times.merge(
                trips[["trip_id", "wheelchair_accessible"]], on="trip_id", how="left"
            ).merge(
                stops_with_resolved[
                    ["stop_id", "wheelchair_boarding", "wheelchair_boarding_resolved"]
                ],
                on="stop_id",
                how="left",
            )
            conflicts = merged[
                (merged["wheelchair_accessible"] == "1")
                & merged["wheelchair_boarding_resolved"].isin(["not_accessible", "unknown"])
            ]
            if not conflicts.empty:
                findings.append(
                    Finding(
                        check_id="ACCESS.TRIP_STOP.CONFLICT",
                        severity=Severity.WARNING,
                        message=(
                            "Accessible trips serve stops marked not accessible or unknown."
                        ),
                        evidence={
                            "trip_ids": _unique_column_strings(conflicts, "trip_id"),
                            "stop_ids": _unique_column_strings(conflicts, "stop_id"),
                        },
                        suggested_action=(
                            "Align trip wheelchair_accessible with stop wheelchair_boarding."
                        ),
                    )
                )

    if config.is_check_enabled("ACCESS.PATHWAY.PRESENCE"):
        pathways = feed.table("pathways")
        location_type = _location_type_series(stops)
        stations = stops[location_type == "1"] if not stops.empty else stops
        station_ids = set(stations["stop_id"].astype(str)) if not stations.empty else set()
        if station_ids:
            pathway_stations = (
                set(pathways["from_stop_id"].astype(str))
                | set(pathways["to_stop_id"].astype(str))
                if not pathways.empty
                else set()
            )
            missing = sorted(station_ids - pathway_stations)
            metrics.append(
                Metric(
                    metric_id="ACCESS.PATHWAY.PRESENCE",
                    label="Stations with pathway records",
                    value=len(station_ids) - len(missing),
                    numerator=len(station_ids) - len(missing),
                    denominator=len(station_ids),
                    unit="stations",
                    source_url="https://gtfs.org/documentation/schedule/examples/pathways/",
                )
            )
            if missing:
                findings.append(
                    Finding(
                        check_id="ACCESS.PATHWAY.PRESENCE",
                        severity=Severity.INFO,
                        message="Some stations lack pathway records.",
                        evidence={"station_ids": missing},
                        suggested_action="Add pathways.txt entries for station connectivity.",
                    )
                )

    if config.is_check_enabled("ACCESS.PATHWAY.CONNECTED") and feed.has_table("pathways"):
        findings.extend(_pathway_connectivity(feed))

    return findings, metrics


def _pathway_connectivity(feed: GtfsFeed) -> list[Finding]:
    pathways = feed.table("pathways")
    stops = feed.table("stops")
    if pathways.empty or stops.empty:
        return []

    findings: list[Finding] = []
    stop_ids = set(stops["stop_id"].astype(str))
    location_type = _location_type_series(stops)
    entrances = set(stops[location_type == "2"]["stop_id"].astype(str))
    platforms = set(
        stops[(location_type == "0") | (location_type == "4")]["stop_id"].astype(str)
    )

    invalid_rows: list[dict[str, str]] = []
    directed: dict[str, set[str]] = {}
    undirected: dict[str, set[str]] = {}

    for _, row in pathways.iterrows():
        src = str(row["from_stop_id"])
        dst = str(row["to_stop_id"])
        mode = str(row.get("pathway_mode", ""))
        bidir = str(row.get("is_bidirectional", "1"))
        trav = str(row.get("traversal_time", "")).strip()

        row_issues: list[str] = []
        if src not in stop_ids:
            row_issues.append("invalid_from_stop_id")
        if dst not in stop_ids:
            row_issues.append("invalid_to_stop_id")
        if mode not in VALID_PATHWAY_MODES:
            row_issues.append("invalid_pathway_mode")
        if trav == "" or not trav.isdigit() or int(trav) < 0:
            row_issues.append("invalid_traversal_time")
        if bidir not in {"0", "1"}:
            row_issues.append("invalid_is_bidirectional")

        if row_issues:
            invalid_rows.append(
                {
                    "pathway_id": str(row.get("pathway_id", "")),
                    "issues": ",".join(row_issues),
                }
            )
            continue

        directed.setdefault(src, set()).add(dst)
        undirected.setdefault(src, set()).add(dst)
        undirected.setdefault(dst, set()).add(src)
        if bidir == "1":
            directed.setdefault(dst, set()).add(src)

    if invalid_rows:
        findings.append(
            Finding(
                check_id="ACCESS.PATHWAY.CONNECTED",
                severity=Severity.WARNING,
                message="Pathway records contain invalid references or fields.",
                evidence={"invalid_pathways": invalid_rows},
                suggested_action=(
                    "Fix pathway_mode, traversal_time, is_bidirectional, and stop references."
                ),
            )
        )

    isolated = [node for node, neighbors in undirected.items() if not neighbors]
    if isolated:
        findings.append(
            Finding(
                check_id="ACCESS.PATHWAY.CONNECTED",
                severity=Severity.WARNING,
                message="Pathway graph has isolated nodes.",
                evidence={"stop_ids": sorted(isolated)},
                suggested_action="Connect pathway nodes to entrances and platforms.",
            )
        )

    dead_ends: list[str] = []
    for node, neighbors in directed.items():
        if not neighbors or not any(directed.get(n) for n in neighbors):
            dead_ends.append(node)

    if dead_ends:
        findings.append(
            Finding(
                check_id="ACCESS.PATHWAY.CONNECTED",
                severity=Severity.INFO,
                message="Pathway directed graph has one-way dead ends.",
                evidence={"stop_ids": sorted(set(dead_ends))},
                suggested_action="Review is_bidirectional flags and pathway directionality.",
            )
        )

    if entrances and platforms:
        unreachable_stations: list[str] = []
        has_parent = "parent_station" in stops.columns
        for station_id in stops[location_type == "1"]["stop_id"].astype(str):
            if has_parent:
                children = stops.loc[
                    stops["parent_station"].astype(str) == station_id
                ]
                child_types = _location_type_series(children)
                station_entrances = set(children[child_types == "2"]["stop_id"].astype(str))
                station_platforms = set(
                    children[child_types.isin(["0", "4"])]["stop_id"].astype(str)
                )
            else:
                station_entrances = set()
                station_platforms = set()

            if station_id in entrances:
                station_entrances.add(station_id)

            if not station_entrances or not station_platforms:
                continue

            reachable: set[str] = set()
            for entrance in station_entrances:
                stack = [entrance]
                while stack:
                    node = stack.pop()
                    if node in reachable:
                        continue
                    reachable.add(node)
                    stack.extend(directed.get(node, set()) - reachable)

            if not station_platforms.issubset(reachable):
                unreachable_stations.append(station_id)

        if unreachable_stations:
            findings.append(
                Finding(
                    check_id="ACCESS.PATHWAY.CONNECTED",
                    severity=Severity.WARNING,
                    message=(
                        "Some stations have platforms not reachable from entrances "
                        "via directed pathways."
                    ),
                    evidence={"station_ids": sorted(unreachable_stations)},
                    suggested_action="Add directed pathways from entrances to platforms.",
                )
            )

    return findings
