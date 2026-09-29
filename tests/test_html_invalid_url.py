from datetime import UTC, datetime
from pathlib import Path

from transit_audit.models import AuditInput, AuditResult, Metric, Provenance
from transit_audit.reporting.html import render_html_report


def test_html_escapes_invalid_metric_url(tmp_path: Path) -> None:
    result = AuditResult(
        tool={"name": "transit-access-audit", "version": "0.1.0"},
        input=AuditInput(feed_path="feed.zip"),
        provenance=Provenance(
            tool_name="transit-access-audit",
            tool_version="0.1.0",
            executed_at=datetime.now(UTC),
        ),
        metrics=[
            Metric(
                metric_id="TEST",
                label="Test",
                value=1,
                source_url="javascript:alert(1)",
            )
        ],
    )
    output = tmp_path / "report.html"
    render_html_report(result, output)
    assert "javascript:" not in output.read_text(encoding="utf-8")
