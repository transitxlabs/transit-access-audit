"""Tests for walking transfer edges."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from transit_audit.routing.walking import build_walk_edges, haversine_m

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_haversine_short_distance() -> None:
    distance = haversine_m(48.4284, -123.3656, 48.4290, -123.3640)
    assert 50.0 < distance < 200.0


def test_build_walk_edges_empty_without_coordinates() -> None:
    stops = pd.DataFrame({"stop_id": ["S1"], "stop_name": ["One"]})
    assert build_walk_edges(stops, speed_mps=1.4, radius_m=300.0) == {}


def test_build_walk_edges_links_nearby_stops() -> None:
    stops = pd.DataFrame(
        {
            "stop_id": ["S1", "S2", "S3"],
            "stop_lat": [48.4284, 48.4290, 50.0],
            "stop_lon": [-123.3656, -123.3640, -123.0],
        }
    )
    edges = build_walk_edges(stops, speed_mps=1.4, radius_m=300.0)
    assert "S1" in edges
    assert "S2" in edges["S1"][0][0] or any(neighbor == "S2" for neighbor, _ in edges["S1"])
    assert all(neighbor != "S3" for neighbor, _ in edges.get("S1", []))
