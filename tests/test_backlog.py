from transit_audit.findings.backlog import build_backlog, priority_score
from transit_audit.models import Finding, Severity


def test_priority_score_ordering() -> None:
    assert priority_score(Severity.ERROR, 5, 1) > priority_score(Severity.WARNING, 3, 2)


def test_backlog_sorted_desc() -> None:
    findings = [
        Finding(check_id="ACCESS.X", severity=Severity.WARNING, message="warn"),
        Finding(
            check_id="GTFS.X",
            severity=Severity.ERROR,
            message="err",
            evidence={"trip_ids": ["a", "b", "c", "d", "e"]},
        ),
    ]
    backlog = build_backlog(findings)
    assert backlog[0].priority >= backlog[-1].priority
    assert backlog[0].severity == Severity.ERROR
