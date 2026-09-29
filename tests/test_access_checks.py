from pathlib import Path

from transit_audit.checks.access import run_access_checks
from transit_audit.config import AuditConfig
from transit_audit.gtfs.reader import read_gtfs_zip

FIXTURES = Path(__file__).parent / "fixtures"


def test_missing_wheelchair_unknown_count() -> None:
    feed = read_gtfs_zip(FIXTURES / "missing_wheelchair.zip")
    findings, metrics = run_access_checks(feed, AuditConfig())
    metric = next(m for m in metrics if m.metric_id == "ACCESS.STOP.WHEELCHAIR.KNOWN")
    assert metric.numerator == 0
    assert metric.denominator == len(feed.table("stops"))
    assert any(f.check_id == "ACCESS.STOP.WHEELCHAIR.KNOWN" for f in findings)


def test_trip_stop_conflict() -> None:
    feed = read_gtfs_zip(FIXTURES / "trip_stop_conflict.zip")
    findings, _ = run_access_checks(feed, AuditConfig())
    conflict = next(f for f in findings if f.check_id == "ACCESS.TRIP_STOP.CONFLICT")
    assert "T1" in conflict.evidence["trip_ids"]
    assert "S1" in conflict.evidence["stop_ids"]


def test_pathway_checks() -> None:
    feed = read_gtfs_zip(FIXTURES / "pathways.zip")
    findings, metrics = run_access_checks(feed, AuditConfig())
    assert any(m.metric_id == "ACCESS.PATHWAY.PRESENCE" for m in metrics)
    assert isinstance(findings, list)
