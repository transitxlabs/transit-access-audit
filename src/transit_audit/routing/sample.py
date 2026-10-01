"""Sample origin and destination stops for bounded routing evaluation."""

from __future__ import annotations

import random

import pandas as pd

from transit_audit.gtfs.reader import GtfsFeed
from transit_audit.routing.accessibility import unknown_entities


def _candidate_stops(feed: GtfsFeed) -> pd.DataFrame:
    stops = feed.table("stops")
    stop_times = feed.table("stop_times")
    if stops.empty or stop_times.empty:
        return pd.DataFrame()

    active = set(stop_times["stop_id"].astype(str))
    candidates = stops[stops["stop_id"].astype(str).isin(active)].copy()
    if "location_type" in candidates.columns:
        candidates = candidates[candidates["location_type"].astype(str).isin(["0", "4", ""])]
    return candidates


def sample_stop_ids(
    feed: GtfsFeed,
    count: int,
    random_seed: int,
    *,
    prefer_unknown: bool = False,
) -> list[str]:
    candidates = _candidate_stops(feed)
    if candidates.empty:
        return []

    unknown_stops, _ = unknown_entities(feed.table("stops"), feed.table("trips"))
    unknown_set = set(unknown_stops)
    pool = candidates["stop_id"].astype(str).tolist()

    rng = random.Random(random_seed)
    if prefer_unknown and unknown_set:
        unknown_pool = [stop_id for stop_id in pool if stop_id in unknown_set]
        known_pool = [stop_id for stop_id in pool if stop_id not in unknown_set]
        half = max(1, count // 2)
        chosen = rng.sample(unknown_pool, k=min(half, len(unknown_pool)))
        remaining = count - len(chosen)
        if remaining > 0 and known_pool:
            chosen.extend(rng.sample(known_pool, k=min(remaining, len(known_pool))))
        remaining = count - len(chosen)
        if remaining > 0:
            extra_unknown = [stop_id for stop_id in unknown_pool if stop_id not in chosen]
            if extra_unknown:
                chosen.extend(rng.sample(extra_unknown, k=min(remaining, len(extra_unknown))))
        rng.shuffle(chosen)
        return chosen[:count]

    if len(pool) <= count:
        return pool
    return rng.sample(pool, k=count)


def sample_od_pairs(
    origin_ids: list[str],
    destination_ids: list[str],
    random_seed: int,
    *,
    max_pairs: int | None = None,
) -> list[tuple[str, str]]:
    pairs = [(origin, dest) for origin in origin_ids for dest in destination_ids if origin != dest]
    if max_pairs is not None and len(pairs) > max_pairs:
        rng = random.Random(random_seed)
        pairs = rng.sample(pairs, k=max_pairs)
    return pairs
