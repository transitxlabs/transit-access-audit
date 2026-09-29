"""Proximity coverage metrics."""

from __future__ import annotations

from transit_audit.config import AuditConfig
from transit_audit.geo.census import CensusLayer, population_within_distance, stops_to_gdf
from transit_audit.gtfs.reader import GtfsFeed
from transit_audit.models import Metric


def run_proximity_metrics(
    feed: GtfsFeed,
    census: CensusLayer,
    config: AuditConfig,
) -> list[Metric]:
    metrics: list[Metric] = []
    stops = feed.table("stops")
    if stops.empty:
        return metrics

    stops_gdf = stops_to_gdf(stops, census.epsg)
    for threshold in config.proximity_thresholds_m:
        check_id = f"PROXIMITY.POPULATION_WITHIN_{threshold}M"
        if not config.is_check_enabled(check_id):
            continue
        covered, total, pop_meta = population_within_distance(census, stops_gdf, float(threshold))
        pct = (covered / total * 100.0) if total else 0.0
        metrics.append(
            Metric(
                metric_id=check_id,
                label=f"Population within {threshold} m of stops (proximity coverage)",
                value=round(pct, 4),
                numerator=round(covered, 4),
                denominator=total,
                unit="percent",
                metadata={
                    "threshold_m": threshold,
                    "metric_type": "proximity_coverage",
                    **pop_meta,
                    "note": "Proximity coverage, not walk accessibility.",
                },
                source_url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2310031401",
            )
        )
    return metrics
