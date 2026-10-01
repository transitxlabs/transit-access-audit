"""Models for routing bounds analysis."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from transit_audit.routing.policy import UnknownPolicy

__all__ = [
    "BoundsConfig",
    "BoundsResult",
    "OdPairResult",
    "PolicyReachabilitySummary",
    "UnknownPolicy",
    "VerificationTarget",
]


class BoundsConfig(BaseModel):
    service_date: date
    departure_time: str = "08:00:00"
    max_travel_minutes: int = Field(default=60, ge=1, le=240)
    max_transfers: int = Field(default=2, ge=0, le=6)
    min_transfer_minutes: int = Field(default=5, ge=0, le=60)
    origin_count: int = Field(default=25, ge=1, le=500)
    destination_count: int = Field(default=50, ge=1, le=2000)
    random_seed: int = 42
    verification_rank_limit: int = Field(default=25, ge=1, le=500)
    walk_speed_mps: float = Field(default=1.4, gt=0.0, le=3.0)
    walk_radius_m: float = Field(default=300.0, gt=0.0, le=2000.0)
    rank_verification: bool = True


class OdPairResult(BaseModel):
    origin_stop_id: str
    destination_stop_id: str
    optimistic_reachable: bool
    pessimistic_reachable: bool
    interval_width: int
    optimistic_travel_seconds: int | None = None
    pessimistic_travel_seconds: int | None = None


class VerificationTarget(BaseModel):
    entity_type: str
    entity_id: str
    field: str
    interval_width_change: float
    affected_od_pairs: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyReachabilitySummary(BaseModel):
    policy: UnknownPolicy
    reachable_destination_count: int
    mean_travel_seconds: float | None = None


class BoundsResult(BaseModel):
    schema_version: str = "1.1"
    feed_path: str
    config: BoundsConfig
    origin_stop_ids: list[str]
    destination_stop_ids: list[str]
    od_pairs: list[OdPairResult]
    optimistic_summary: PolicyReachabilitySummary
    pessimistic_summary: PolicyReachabilitySummary
    schedule_only_summary: PolicyReachabilitySummary | None = None
    mean_interval_width: float
    median_interval_width: float
    verification_targets: list[VerificationTarget]
    unknown_stop_count: int
    unknown_trip_count: int
    runtime_seconds: float
    metadata: dict[str, Any] = Field(default_factory=dict)
