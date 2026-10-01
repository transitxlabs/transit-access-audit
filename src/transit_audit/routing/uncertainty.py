"""Uncertainty intervals for crossed origin-destination sampling."""

from __future__ import annotations

import random
import statistics


def crossed_bootstrap_interval(
    pairs: list[tuple[str, str, float]],
    strata: dict[str, str],
    *,
    samples: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap mean width by resampling origin and destination lists independently."""
    if not pairs:
        return 0.0, 0.0

    widths: dict[tuple[str, str], float] = {}
    for origin, destination, width in pairs:
        key = (origin, destination)
        if key in widths:
            raise ValueError(f"duplicate OD key: {key}")
        widths[key] = width

    origins = sorted({origin for origin, _, _ in pairs})
    destinations = sorted({destination for _, destination, _ in pairs})
    unknown_origins = [origin for origin in origins if strata.get(origin) == "unknown"]
    known_origins = [origin for origin in origins if strata.get(origin) != "unknown"]
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(samples):
        sampled_origins = (
            [rng.choice(unknown_origins) for _ in unknown_origins]
            + [rng.choice(known_origins) for _ in known_origins]
        )
        sampled_destinations = [rng.choice(destinations) for _ in destinations]
        values = [
            widths[(origin, destination)]
            for origin in sampled_origins
            for destination in sampled_destinations
            if origin != destination
        ]
        means.append(statistics.mean(values) if values else 0.0)

    means.sort()
    lower_idx = int((alpha / 2) * samples)
    upper_idx = int((1 - alpha / 2) * samples) - 1
    return means[lower_idx], means[upper_idx]
