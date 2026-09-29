"""Equity diagnostic metrics."""

from __future__ import annotations

from transit_audit.config import AuditConfig
from transit_audit.geo.census import CensusLayer, population_within_distance, stops_to_gdf
from transit_audit.gtfs.reader import GtfsFeed
from transit_audit.models import Metric


def run_equity_metrics(
    feed: GtfsFeed,
    census: CensusLayer,
    config: AuditConfig,
) -> list[Metric]:
    metrics: list[Metric] = []
    if not config.equity_groups:
        return metrics

    stops = feed.table("stops")
    if stops.empty:
        return metrics

    reference_groups = [g for g in config.equity_groups if g.reference]
    comparison_groups = [g for g in config.equity_groups if not g.reference]

    if len(reference_groups) != 1:
        metrics.append(
            Metric(
                metric_id="EQUITY.COVERAGE_GAP",
                label="Equity coverage gap",
                value=None,
                unit="percentage_points",
                metadata={
                    "reason": "exactly_one_reference_group_required",
                    "reference_group_count": len(reference_groups),
                    "policy_note": (
                        "Descriptive association between group proximity coverage shares; "
                        "not causal, not legal compliance, not a statutory limit."
                    ),
                },
                source_url="https://www150.statcan.gc.ca/n1/pub/18-001-x/18-001-x2024005-eng.htm",
            )
        )
        return metrics

    if not comparison_groups:
        return metrics

    for group in config.equity_groups:
        if group.attribute not in census.gdf.columns:
            metrics.append(
                Metric(
                    metric_id="EQUITY.COVERAGE_GAP",
                    label=f"Equity coverage gap for {group.name}",
                    value=None,
                    unit="percentage_points",
                    metadata={
                        "reason": "missing_attribute",
                        "attribute": group.attribute,
                        "group": group.name,
                    },
                    source_url="https://www150.statcan.gc.ca/n1/pub/18-001-x/18-001-x2024005-eng.htm",
                )
            )
            return metrics

    stops_gdf = stops_to_gdf(stops, census.epsg)
    threshold = float(config.default_proximity_m)
    ref_group = reference_groups[0]

    ref_mask = census.gdf[ref_group.attribute].astype(str) == str(ref_group.value)
    ref_pop = float(census.gdf.loc[ref_mask, "population"].astype(float).sum())
    if ref_pop <= 0:
        metrics.append(
            Metric(
                metric_id="EQUITY.COVERAGE_GAP",
                label=f"Coverage gap vs {ref_group.name}",
                value=None,
                unit="percentage_points",
                metadata={
                    "reason": "reference_group_zero_population",
                    "reference": ref_group.name,
                    "policy_note": (
                        "Descriptive association only; undefined when reference population is zero."
                    ),
                },
                source_url="https://www150.statcan.gc.ca/n1/pub/18-001-x/18-001-x2024005-eng.htm",
            )
        )
        return metrics

    ref_covered, _, _ref_meta = population_within_distance(
        CensusLayer(
            gdf=census.gdf.loc[ref_mask],
            epsg=census.epsg,
            source_crs=census.source_crs,
            population_method=census.population_method,
        ),
        stops_gdf,
        threshold,
    )
    ref_pct = ref_covered / ref_pop * 100.0

    for group in comparison_groups:
        if not config.is_check_enabled("EQUITY.COVERAGE_GAP"):
            continue
        mask = census.gdf[group.attribute].astype(str) == str(group.value)
        group_pop = float(census.gdf.loc[mask, "population"].astype(float).sum())
        if group_pop <= 0:
            metrics.append(
                Metric(
                    metric_id="EQUITY.COVERAGE_GAP",
                    label=f"Descriptive coverage association for {group.name} vs {ref_group.name}",
                    value=None,
                    unit="percentage_points",
                    metadata={
                        "group": group.name,
                        "reference": ref_group.name,
                        "threshold_m": threshold,
                        "reason": "comparison_group_zero_population",
                        "population_method": census.population_method,
                        "policy_note": (
                            "Descriptive association between group proximity coverage shares; "
                            "not causal, not legal compliance, not a statutory limit."
                        ),
                    },
                    source_url="https://www150.statcan.gc.ca/n1/pub/18-001-x/18-001-x2024005-eng.htm",
                )
            )
            continue

        covered, _, group_meta = population_within_distance(
            CensusLayer(
                gdf=census.gdf.loc[mask],
                epsg=census.epsg,
                source_crs=census.source_crs,
                population_method=census.population_method,
            ),
            stops_gdf,
            threshold,
        )
        group_pct = covered / group_pop * 100.0
        gap = group_pct - ref_pct
        metrics.append(
            Metric(
                metric_id="EQUITY.COVERAGE_GAP",
                label=f"Descriptive coverage association for {group.name} vs {ref_group.name}",
                value=round(gap, 4),
                numerator=round(group_pct, 4),
                denominator=round(ref_pct, 4),
                unit="percentage_points",
                metadata={
                    "group": group.name,
                    "reference": ref_group.name,
                    "threshold_m": threshold,
                    "group_coverage_pct": round(group_pct, 4),
                    "reference_coverage_pct": round(ref_pct, 4),
                    "population_method": census.population_method,
                    "weighting": group_meta.get("weighting"),
                    "assumption": group_meta.get("assumption"),
                    "policy_note": (
                        "Descriptive association between group proximity coverage shares; "
                        "not causal, not legal compliance, not a statutory limit."
                    ),
                },
                source_url="https://www150.statcan.gc.ca/n1/pub/18-001-x/18-001-x2024005-eng.htm",
            )
        )

    return metrics
