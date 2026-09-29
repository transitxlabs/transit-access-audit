from pathlib import Path

from transit_audit.checks.gtfs import run_gtfs_checks
from transit_audit.config import AuditConfig
from transit_audit.gtfs.reader import read_gtfs_zip

FIXTURES = Path(__file__).parent / "fixtures"


def test_broken_references_finding() -> None:
    feed = read_gtfs_zip(FIXTURES / "broken_references.zip")
    findings, _ = run_gtfs_checks(feed, AuditConfig())
    assert any(f.check_id == "GTFS.FK.INTEGRITY" for f in findings)


def test_feed_url_warning_on_minimal() -> None:
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    findings, metrics = run_gtfs_checks(feed, AuditConfig())
    assert any(m.metric_id == "GTFS.CALENDAR.COVERAGE" for m in metrics)
    assert not any(f.check_id == "GTFS.FEED.URL" for f in findings)
