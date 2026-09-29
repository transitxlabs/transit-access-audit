"""Accessible HTML report renderer."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from transit_audit.models import AuditResult
from transit_audit.security import escape_text, validate_url

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _safe_url_or_empty(url: str | None) -> str:
    if url is None:
        return ""
    try:
        return validate_url(url) or ""
    except ValueError:
        return ""


def render_html_report(result: AuditResult, output_path: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["escape_text"] = escape_text
    env.filters["safe_url"] = _safe_url_or_empty
    template = env.get_template("report.html.j2")
    html = template.render(result=result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
