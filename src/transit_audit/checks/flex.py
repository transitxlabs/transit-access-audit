"""GTFS-Flex awareness checks."""

from __future__ import annotations

import json

from transit_audit.config import AuditConfig
from transit_audit.gtfs.reader import GtfsFeed
from transit_audit.models import Finding, Metric, Severity


def run_flex_checks(feed: GtfsFeed, config: AuditConfig) -> tuple[list[Finding], list[Metric]]:
    findings: list[Finding] = []
    metrics: list[Metric] = []

    if not config.is_check_enabled("FLEX.PRESENCE"):
        return findings, metrics

    flex_ids = feed.flex_service_ids()
    if flex_ids:
        metrics.append(
            Metric(
                metric_id="FLEX.PRESENCE",
                label="Flexible service routes detected",
                value=len(flex_ids),
                metadata={"route_ids": flex_ids},
                source_url="https://gtfs.org/getting-started/features/flexible-services/",
            )
        )
        findings.append(
            Finding(
                check_id="FLEX.PRESENCE",
                severity=Severity.INFO,
                message="Flexible GTFS services detected; fixed-route metrics exclude these trips.",
                evidence={"route_ids": flex_ids},
            )
        )

    if config.is_check_enabled("FLEX.BOOKING_RULES"):
        booking = feed.table("booking_rules")
        if feed.flex_present() and booking.empty:
            findings.append(
                Finding(
                    check_id="FLEX.BOOKING_RULES",
                    severity=Severity.WARNING,
                    message="Flex feed present but booking_rules.txt is missing.",
                    suggested_action="Publish booking_rules.txt for flexible services.",
                )
            )

    if config.is_check_enabled("FLEX.ZONE.GEOMETRY") and feed.has_table("locations_geojson"):
        raw = feed.table("locations_geojson").iloc[0]["raw"]
        try:
            payload = json.loads(raw)
            if payload.get("type") != "FeatureCollection":
                raise ValueError("Expected FeatureCollection")
        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as exc:
            findings.append(
                Finding(
                    check_id="FLEX.ZONE.GEOMETRY",
                    severity=Severity.ERROR,
                    message=f"Invalid locations.geojson: {exc}",
                    suggested_action="Repair Flex zone geometry.",
                )
            )

    return findings, metrics
