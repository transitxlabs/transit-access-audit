"""Audit orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from transit_audit.checks.registry import run_all_checks
from transit_audit.config import load_config
from transit_audit.findings.backlog import build_backlog
from transit_audit.gtfs.reader import read_gtfs_zip
from transit_audit.gtfs.zip_limits import ZipLimits
from transit_audit.hashing import sha256_file
from transit_audit.models import AuditInput, AuditResult, Provenance
from transit_audit.validator.mobilitydata import ingest_validator_report
from transit_audit.version import __version__


def run_audit(
    feed_path: Path,
    config_path: Path | None = None,
    census_path: Path | None = None,
    validator_report_path: Path | None = None,
) -> AuditResult:
    config = load_config(config_path)
    zip_limits = ZipLimits(
        max_members=config.zip_limits.max_members,
        max_uncompressed_bytes=config.zip_limits.max_uncompressed_bytes,
        max_member_bytes=config.zip_limits.max_member_bytes,
        max_compression_ratio=config.zip_limits.max_compression_ratio,
    )
    feed = read_gtfs_zip(feed_path, limits=zip_limits)
    flex_route_ids = set(feed.flex_service_ids()) if config.flex_exclude_from_fixed_route else set()

    findings, metrics = run_all_checks(feed, config, flex_route_ids=flex_route_ids)

    if validator_report_path and validator_report_path.exists():
        validator_findings, validator_meta = ingest_validator_report(validator_report_path)
        findings.extend(validator_findings)
        validator_name = validator_meta.get("validator_name")
        validator_version = validator_meta.get("validator_version")
    else:
        validator_name = None
        validator_version = None

    crs_epsg = None
    census_source_crs = None
    if census_path:
        from transit_audit.geo.census import load_census_geopackage
        from transit_audit.metrics.equity import run_equity_metrics
        from transit_audit.metrics.proximity import run_proximity_metrics

        census = load_census_geopackage(
            census_path,
            census_crs=config.census_crs,
            population_method=config.population_method,
        )
        crs_epsg = census.epsg
        census_source_crs = census.source_crs
        metrics.extend(run_proximity_metrics(feed, census, config))
        metrics.extend(run_equity_metrics(feed, census, config))

    backlog = build_backlog(findings)
    provenance_extra: dict[str, object] = {}
    if census_source_crs:
        provenance_extra["census_source_crs"] = census_source_crs
    if census_path:
        provenance_extra["population_method"] = config.population_method
    if config.data_attributions:
        provenance_extra["data_attributions"] = config.data_attributions

    provenance = Provenance(
        tool_name="transit-access-audit",
        tool_version=__version__,
        executed_at=datetime.now(UTC),
        feed_sha256=sha256_file(feed_path),
        config_sha256=sha256_file(config_path) if config_path else None,
        census_sha256=sha256_file(census_path) if census_path else None,
        validator_name=validator_name,
        validator_version=validator_version,
        crs_epsg=crs_epsg,
        extra=provenance_extra,
    )
    result = AuditResult(
        tool={"name": "transit-access-audit", "version": __version__},
        input=AuditInput(
            feed_path=str(feed_path),
            config_path=str(config_path) if config_path else None,
            census_path=str(census_path) if census_path else None,
        ),
        provenance=provenance,
        findings=findings,
        metrics=metrics,
        backlog=backlog,
    )
    result.recompute_summary()
    return result
