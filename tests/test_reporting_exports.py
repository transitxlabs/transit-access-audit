import json
from pathlib import Path

from transit_audit.engine import run_audit
from transit_audit.models import Severity
from transit_audit.reporting.backlog_export import write_backlog_csv, write_backlog_json
from transit_audit.reporting.html import render_html_report
from transit_audit.reporting.json_output import write_results_json

FIXTURES = Path(__file__).parent / "fixtures"


def test_json_and_backlog_exports(tmp_path: Path) -> None:
    result = run_audit(
        FIXTURES / "trip_stop_conflict.zip",
        validator_report_path=FIXTURES / "validator_broken_references_report.json",
    )
    write_results_json(result, tmp_path / "results.json")
    write_backlog_json(result, tmp_path / "backlog.json", severity=Severity.WARNING)
    write_backlog_csv(result, tmp_path / "backlog.csv", category="ACCESS")
    render_html_report(result, tmp_path / "report.html")
    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert (tmp_path / "backlog.csv").read_text(encoding="utf-8").startswith("check_id")
