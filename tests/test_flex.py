from pathlib import Path

from transit_audit.checks.flex import run_flex_checks
from transit_audit.config import AuditConfig
from transit_audit.gtfs.reader import read_gtfs_zip

FIXTURES = Path(__file__).parent / "fixtures"


def test_flex_presence() -> None:
    feed = read_gtfs_zip(FIXTURES / "flex_service.zip")
    _findings, metrics = run_flex_checks(feed, AuditConfig())
    assert any(m.metric_id == "FLEX.PRESENCE" for m in metrics)
    assert feed.flex_service_ids()


def test_invalid_flex_geometry() -> None:
    feed = read_gtfs_zip(FIXTURES / "flex_invalid_geometry.zip")
    findings, _ = run_flex_checks(feed, AuditConfig())
    assert any(f.check_id == "FLEX.ZONE.GEOMETRY" for f in findings)
