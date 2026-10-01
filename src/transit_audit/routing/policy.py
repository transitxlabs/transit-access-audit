"""Wheelchair accessibility assumptions for unknown GTFS fields."""

from __future__ import annotations

from enum import StrEnum

GTFS_ACCESSIBILITY_SPEC = (
    "https://gtfs.org/documentation/schedule/reference/#stopstxt-wheelchair_boarding"
)


class UnknownPolicy(StrEnum):
    """How to treat GTFS wheelchair fields when building a schedule index."""

    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"
    SCHEDULE_ONLY = "schedule_only"


def wheelchair_category(raw: str) -> str:
    """Return accessible, not_accessible, or unknown for a GTFS wheelchair field.

    GTFS semantics (``wheelchair_boarding``, ``wheelchair_accessible``):
    empty or ``0`` = no information; ``1`` = accessible; ``2`` = not accessible.
    See ``GTFS_ACCESSIBILITY_SPEC``.
    """
    value = str(raw).strip()
    if value == "1":
        return "accessible"
    if value == "2":
        return "not_accessible"
    return "unknown"


def is_accessible(raw: str, policy: UnknownPolicy) -> bool:
    """Resolve a GTFS wheelchair field under the chosen unknown policy."""
    category = wheelchair_category(raw)
    if category == "accessible":
        return True
    if category == "not_accessible":
        return False
    return policy == UnknownPolicy.OPTIMISTIC
