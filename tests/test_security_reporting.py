from pathlib import Path

import pytest

from transit_audit.engine import run_audit
from transit_audit.reporting.html import render_html_report
from transit_audit.security import escape_text, validate_url

FIXTURES = Path(__file__).parent / "fixtures"


def test_escape_text() -> None:
    assert escape_text("<script>") == "&lt;script&gt;"


def test_validate_url_rejects_javascript() -> None:
    with pytest.raises(ValueError):
        validate_url("javascript:alert(1)")


def test_validate_url_rejects_protocol_relative() -> None:
    with pytest.raises(ValueError):
        validate_url("//evil.example")


def test_html_report_structure(tmp_path: Path) -> None:
    result = run_audit(FIXTURES / "minimal_valid.zip")
    output = tmp_path / "report.html"
    render_html_report(result, output)
    html = output.read_text(encoding="utf-8")
    assert '<html lang="en">' in html
    assert html.count("<h1>") == 1
    assert 'id="main"' in html
    assert "Skip to main content" in html
    assert "<th" in html
    assert "proximity coverage" in html.lower()
