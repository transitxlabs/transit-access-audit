"""Core data models for audit results."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Finding(BaseModel):
    check_id: str
    severity: Severity
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    suggested_action: str | None = None


class Metric(BaseModel):
    metric_id: str
    label: str
    value: float | int | str | None
    numerator: float | int | None = None
    denominator: float | int | None = None
    unit: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_url: str | None = None


class BacklogItem(BaseModel):
    check_id: str
    title: str
    description: str
    severity: Severity
    impact: int = Field(ge=1, le=5)
    effort: int = Field(ge=1, le=5)
    priority: float
    affected_records: list[str] = Field(default_factory=list)
    category: str = "general"


class Provenance(BaseModel):
    tool_name: str
    tool_version: str
    executed_at: datetime
    feed_sha256: str | None = None
    config_sha256: str | None = None
    census_sha256: str | None = None
    validator_name: str | None = None
    validator_version: str | None = None
    crs_epsg: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class AuditInput(BaseModel):
    feed_path: str
    config_path: str | None = None
    census_path: str | None = None


class AuditSummary(BaseModel):
    finding_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    metric_count: int = 0
    backlog_count: int = 0


class AuditResult(BaseModel):
    schema_version: str = "1.0"
    tool: dict[str, str]
    input: AuditInput
    provenance: Provenance
    summary: AuditSummary = Field(default_factory=AuditSummary)
    findings: list[Finding] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    backlog: list[BacklogItem] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        if value != "1.0":
            raise ValueError(f"Unsupported schema version: {value}")
        return value

    def recompute_summary(self) -> None:
        self.summary = AuditSummary(
            finding_count=len(self.findings),
            error_count=sum(1 for f in self.findings if f.severity == Severity.ERROR),
            warning_count=sum(1 for f in self.findings if f.severity == Severity.WARNING),
            metric_count=len(self.metrics),
            backlog_count=len(self.backlog),
        )
