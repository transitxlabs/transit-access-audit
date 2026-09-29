"""Backlog export helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from transit_audit.models import AuditResult, BacklogItem, Severity


def filter_backlog(
    items: list[BacklogItem],
    severity: Severity | None = None,
    category: str | None = None,
) -> list[BacklogItem]:
    filtered = items
    if severity is not None:
        filtered = [item for item in filtered if item.severity == severity]
    if category is not None:
        filtered = [item for item in filtered if item.category == category]
    return filtered


def write_backlog_json(
    result: AuditResult,
    output_path: Path,
    severity: Severity | None = None,
    category: str | None = None,
) -> None:
    items = filter_backlog(result.backlog, severity=severity, category=category)
    payload = [item.model_dump(mode="json") for item in items]
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_backlog_csv(
    result: AuditResult,
    output_path: Path,
    severity: Severity | None = None,
    category: str | None = None,
) -> None:
    items = filter_backlog(result.backlog, severity=severity, category=category)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "check_id",
                "title",
                "severity",
                "impact",
                "effort",
                "priority",
                "category",
                "affected_records",
            ],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(
                {
                    "check_id": item.check_id,
                    "title": item.title,
                    "severity": item.severity.value,
                    "impact": item.impact,
                    "effort": item.effort,
                    "priority": item.priority,
                    "category": item.category,
                    "affected_records": ";".join(item.affected_records),
                }
            )
