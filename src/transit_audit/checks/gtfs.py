"""GTFS toolkit checks."""

from __future__ import annotations

from transit_audit.config import AuditConfig
from transit_audit.gtfs.reader import GtfsFeed
from transit_audit.models import Finding, Metric, Severity


def run_gtfs_checks(feed: GtfsFeed, config: AuditConfig) -> tuple[list[Finding], list[Metric]]:
    findings: list[Finding] = []
    metrics: list[Metric] = []

    required = ["agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]
    missing = [name for name in required if name.replace(".txt", "") not in feed.tables]
    if missing and config.is_check_enabled("GTFS.FILES.REQUIRED"):
        findings.append(
            Finding(
                check_id="GTFS.FILES.REQUIRED",
                severity=Severity.ERROR,
                message=f"Missing required GTFS files: {', '.join(missing)}",
                evidence={"missing": missing, "present": sorted(feed.tables.keys())},
                suggested_action="Add required GTFS schedule files before publishing.",
            )
        )

    has_calendar = feed.has_table("calendar") and not feed.table("calendar").empty
    has_calendar_dates = feed.has_table("calendar_dates") and not feed.table("calendar_dates").empty
    if (
        config.is_check_enabled("GTFS.FILES.REQUIRED")
        and not has_calendar
        and not has_calendar_dates
    ):
        findings.append(
            Finding(
                check_id="GTFS.FILES.REQUIRED",
                severity=Severity.ERROR,
                message="GTFS feed must include calendar.txt or calendar_dates.txt.",
                evidence={
                    "calendar_present": has_calendar,
                    "calendar_dates_present": has_calendar_dates,
                },
                suggested_action=(
                    "Add calendar.txt or calendar_dates.txt per GTFS schedule reference."
                ),
            )
        )

    if config.is_check_enabled("GTFS.FK.INTEGRITY"):
        trips = feed.table("trips")
        routes = feed.table("routes")
        if not trips.empty and not routes.empty:
            invalid = trips[~trips["route_id"].isin(routes["route_id"])]
            if not invalid.empty:
                findings.append(
                    Finding(
                        check_id="GTFS.FK.INTEGRITY",
                        severity=Severity.ERROR,
                        message="Trips reference missing route IDs.",
                        evidence={"trip_ids": invalid["trip_id"].astype(str).tolist()},
                        suggested_action="Fix route_id foreign keys in trips.txt.",
                    )
                )

    if config.is_check_enabled("GTFS.CALENDAR.COVERAGE"):
        calendar = feed.table("calendar")
        if not calendar.empty and "end_date" in calendar.columns:
            metrics.append(
                Metric(
                    metric_id="GTFS.CALENDAR.COVERAGE",
                    label="Active calendar services",
                    value=len(calendar),
                    metadata={"latest_end_date": str(calendar["end_date"].max())},
                    source_url="https://gtfs.org/documentation/schedule/schedule-best-practices/",
                )
            )

    if config.is_check_enabled("GTFS.FEED.URL"):
        info = feed.table("feed_info")
        if info.empty or "feed_publisher_url" not in info.columns:
            findings.append(
                Finding(
                    check_id="GTFS.FEED.URL",
                    severity=Severity.WARNING,
                    message="feed_info.txt missing publisher URL metadata.",
                    suggested_action="Publish feed_info.txt with feed_publisher_url.",
                )
            )

    return findings, metrics
