"""Walking transfer edges between nearby GTFS stops."""

from __future__ import annotations

import math
from collections import defaultdict

import pandas as pd

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def build_walk_edges(
    stops: pd.DataFrame,
    *,
    speed_mps: float,
    radius_m: float,
    active_stop_ids: set[str] | None = None,
) -> dict[str, list[tuple[str, int]]]:
    """Return directed walk edges between stop pairs within ``radius_m``."""
    if stops.empty or speed_mps <= 0 or radius_m <= 0:
        return {}
    if "stop_lat" not in stops.columns or "stop_lon" not in stops.columns:
        return {}

    coords: list[tuple[str, float, float]] = []
    for _, row in stops.iterrows():
        lat_raw = str(row.get("stop_lat", "")).strip()
        lon_raw = str(row.get("stop_lon", "")).strip()
        if not lat_raw or not lon_raw:
            continue
        try:
            lat = float(lat_raw)
            lon = float(lon_raw)
        except ValueError:
            continue
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            continue
        stop_id = str(row["stop_id"])
        if active_stop_ids is not None and stop_id not in active_stop_ids:
            continue
        coords.append((stop_id, lat, lon))

    if len(coords) < 2:
        return {}

    # Chord distance never exceeds arc distance, so a metric cube grid cannot
    # omit a pair within the haversine radius, including at poles or the dateline.
    grid: dict[tuple[int, int, int], list[tuple[str, float, float]]] = defaultdict(list)
    for stop_id, lat, lon in coords:
        phi, lam = math.radians(lat), math.radians(lon)
        xyz = (EARTH_RADIUS_M * math.cos(phi) * math.cos(lam),
               EARTH_RADIUS_M * math.cos(phi) * math.sin(lam), EARTH_RADIUS_M * math.sin(phi))
        key = tuple(math.floor(value / radius_m) for value in xyz)
        grid[(key[0], key[1], key[2])].append((stop_id, lat, lon))

    seen: set[tuple[str, str]] = set()
    edges: dict[str, list[tuple[str, int]]] = {}
    for (x, y, z), bucket in grid.items():
        candidates = [item for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
                      for item in grid.get((x + dx, y + dy, z + dz), [])]
        for stop_a, lat_a, lon_a in bucket:
            for stop_b, lat_b, lon_b in candidates:
                if stop_a == stop_b:
                    continue
                pair = (stop_a, stop_b) if stop_a < stop_b else (stop_b, stop_a)
                if pair in seen:
                    continue
                seen.add(pair)
                distance = haversine_m(lat_a, lon_a, lat_b, lon_b)
                if distance > radius_m:
                    continue
                walk_seconds = max(1, round(distance / speed_mps))
                edges.setdefault(stop_a, []).append((stop_b, walk_seconds))
                edges.setdefault(stop_b, []).append((stop_a, walk_seconds))
    return edges
