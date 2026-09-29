"""Audit configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


class ServiceBandConfig(BaseModel):
    name: str = "peak"
    start_time: str = "07:00:00"
    end_time: str = "09:00:00"
    reference_stop_id: str | None = None


class EquityGroupConfig(BaseModel):
    name: str
    attribute: str
    value: str | int | float | bool
    reference: bool = False


class ZipLimitsConfig(BaseModel):
    max_members: int = 256
    max_uncompressed_bytes: int = 256 * 1024 * 1024
    max_member_bytes: int = 64 * 1024 * 1024
    max_compression_ratio: float = 100.0


class AuditConfig(BaseModel):
    proximity_thresholds_m: list[int] = Field(default_factory=lambda: [400, 500, 800])
    default_proximity_m: int = 500
    enabled_checks: list[str] = Field(default_factory=list)
    service_bands: list[ServiceBandConfig] = Field(
        default_factory=lambda: [ServiceBandConfig()]
    )
    service_date: str = "2024-06-03"
    reference_stop_aggregation: Literal["median", "mean", "min", "max"] = "median"
    equity_groups: list[EquityGroupConfig] = Field(default_factory=list)
    flex_exclude_from_fixed_route: bool = True
    severity_fail_threshold: str = "error"
    census_crs: str | None = None
    population_method: Literal["areal_weight", "population_points"] = "areal_weight"
    population_points_path: Path | None = None
    zip_limits: ZipLimitsConfig = Field(default_factory=ZipLimitsConfig)
    validator_timeout_seconds: int = 300
    validator_max_output_bytes: int = 1_048_576
    data_attributions: list[dict[str, str]] = Field(default_factory=list)

    @field_validator("proximity_thresholds_m")
    @classmethod
    def validate_thresholds(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("proximity_thresholds_m must not be empty")
        for threshold in value:
            if threshold <= 0:
                raise ValueError("proximity thresholds must be positive")
        return value

    @field_validator("validator_timeout_seconds")
    @classmethod
    def validate_timeout(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("validator_timeout_seconds must be positive")
        return value

    def is_check_enabled(self, check_id: str) -> bool:
        if not self.enabled_checks:
            return True
        prefix = check_id.split(".", 1)[0]
        return check_id in self.enabled_checks or f"{prefix}.*" in self.enabled_checks


def load_config(path: Path | None) -> AuditConfig:
    if path is None:
        return AuditConfig()
    try:
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in config file: {exc}") from exc
    try:
        return AuditConfig.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid config: {exc}") from exc


def default_enabled_checks() -> list[str]:
    return [
        "GTFS.*",
        "ACCESS.*",
        "SERVICE.*",
        "PROXIMITY.*",
        "EQUITY.*",
        "FLEX.*",
    ]
