"""Check registry and orchestration."""

from __future__ import annotations

from transit_audit.checks.access import run_access_checks
from transit_audit.checks.flex import run_flex_checks
from transit_audit.checks.gtfs import run_gtfs_checks
from transit_audit.checks.service import run_service_checks
from transit_audit.config import AuditConfig
from transit_audit.gtfs.reader import GtfsFeed
from transit_audit.models import Finding, Metric

CHECK_SOURCES: dict[str, str] = {
    "GTFS.FILES.REQUIRED": "https://gtfs.org/documentation/schedule/reference/",
    "GTFS.FK.INTEGRITY": "https://gtfs.org/documentation/schedule/reference/",
    "GTFS.CALENDAR.COVERAGE": "https://gtfs.org/documentation/schedule/schedule-best-practices/",
    "GTFS.FEED.URL": "https://gtfs.org/documentation/schedule/schedule-best-practices/",
    "ACCESS.STOP.WHEELCHAIR.KNOWN": "https://gtfs.org/documentation/schedule/reference/",
    "ACCESS.TRIP.WHEELCHAIR.KNOWN": "https://gtfs.org/documentation/schedule/reference/",
    "ACCESS.TRIP_STOP.CONFLICT": "derived",
    "ACCESS.PATHWAY.PRESENCE": "https://gtfs.org/documentation/schedule/examples/pathways/",
    "ACCESS.PATHWAY.CONNECTED": "https://gtfs.org/documentation/schedule/examples/pathways/",
    "ACCESS.LEVEL.REQUIRED": "https://gtfs.org/documentation/schedule/reference/",
    "ACCESS.SERVICE.WEIGHTED": "derived",
    "SERVICE.DEPARTURES_PER_HOUR": "https://nap.nationalacademies.org/catalog/24766/transit-capacity-and-quality-of-service-manual-third-edition",
    "SERVICE.MEDIAN_HEADWAY": "https://nap.nationalacademies.org/catalog/24766/transit-capacity-and-quality-of-service-manual-third-edition",
    "SERVICE.MAX_GAP": "https://nap.nationalacademies.org/catalog/24766/transit-capacity-and-quality-of-service-manual-third-edition",
    "SERVICE.BAND_SPAN": "https://nap.nationalacademies.org/catalog/24766/transit-capacity-and-quality-of-service-manual-third-edition",
    "SERVICE.DAILY_SPAN": "https://nap.nationalacademies.org/catalog/24766/transit-capacity-and-quality-of-service-manual-third-edition",
    "SERVICE.DAYS_PER_WEEK": "https://gtfs.org/documentation/schedule/reference/",
    "SERVICE.FREQUENT_COVERAGE": "https://nap.nationalacademies.org/catalog/24766/transit-capacity-and-quality-of-service-manual-third-edition",
    "PROXIMITY.POPULATION_WITHIN_400M": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2310031401",
    "PROXIMITY.POPULATION_WITHIN_500M": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2310031401",
    "PROXIMITY.POPULATION_WITHIN_800M": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2310031401",
    "EQUITY.COVERAGE_GAP": "https://www150.statcan.gc.ca/n1/pub/18-001-x/18-001-x2024005-eng.htm",
    "EQUITY.HEADWAY_GAP": "https://doi.org/10.3390/urbansci10060309",
    "EQUITY.SUPPLY_RATIO": "derived",
    "EQUITY.SPAN_GAP": "derived",
    "FLEX.PRESENCE": "https://gtfs.org/getting-started/features/flexible-services/",
    "FLEX.BOOKING_RULES": "https://gtfs.org/getting-started/features/flexible-services/",
    "FLEX.ZONE.GEOMETRY": "https://gtfs.org/getting-started/features/flexible-services/",
}


def run_all_checks(
    feed: GtfsFeed,
    config: AuditConfig,
    flex_route_ids: set[str],
) -> tuple[list[Finding], list[Metric]]:
    findings: list[Finding] = []
    metrics: list[Metric] = []

    for runner in (run_gtfs_checks, run_access_checks, run_flex_checks):
        f, m = runner(feed, config)
        findings.extend(f)
        metrics.extend(m)

    sf, sm = run_service_checks(feed, config, flex_route_ids=flex_route_ids)
    findings.extend(sf)
    metrics.extend(sm)

    return findings, metrics
