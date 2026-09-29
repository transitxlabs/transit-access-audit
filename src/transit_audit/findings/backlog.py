"""Prioritized remediation backlog."""

from __future__ import annotations

from transit_audit.models import BacklogItem, Finding, Severity


def priority_score(severity: Severity, impact: int, effort: int) -> float:
    severity_weight = {"error": 3.0, "warning": 2.0, "info": 1.0}[severity.value]
    return round((severity_weight * impact) / effort, 4)


def _impact_for_finding(finding: Finding) -> int:
    affected = finding.evidence.get("trip_ids") or finding.evidence.get("stop_ids") or []
    if isinstance(affected, list) and len(affected) >= 5:
        return 5
    if isinstance(affected, list) and len(affected) >= 2:
        return 3
    return 2


def _effort_for_finding(finding: Finding) -> int:
    if finding.check_id.startswith("GTFS."):
        return 4
    if finding.check_id.startswith("ACCESS."):
        return 3
    return 2


def build_backlog(findings: list[Finding]) -> list[BacklogItem]:
    items: list[BacklogItem] = []
    for finding in findings:
        if finding.severity == Severity.INFO:
            continue
        impact = _impact_for_finding(finding)
        effort = _effort_for_finding(finding)
        affected: list[str] = []
        for key in ("trip_ids", "stop_ids", "station_ids", "route_ids"):
            value = finding.evidence.get(key)
            if isinstance(value, list):
                affected.extend(str(v) for v in value)
        category = finding.check_id.split(".", 1)[0]
        items.append(
            BacklogItem(
                check_id=finding.check_id,
                title=finding.message,
                description=finding.suggested_action or finding.message,
                severity=finding.severity,
                impact=impact,
                effort=effort,
                priority=priority_score(finding.severity, impact, effort),
                affected_records=sorted(set(affected)),
                category=category,
            )
        )
    items.sort(key=lambda item: item.priority, reverse=True)
    return items
