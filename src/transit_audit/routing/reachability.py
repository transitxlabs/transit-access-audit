"""Earliest arrivals by transit-leg count with walking closure in each round."""
from __future__ import annotations

import heapq

from transit_audit.routing.index import ScheduleIndex
from transit_audit.routing.policy import UnknownPolicy


def reachable_arrivals(
    origin_stop_id: str,
    departure_seconds: int,
    max_travel_seconds: int,
    max_transfers: int,
    min_transfer_seconds: int,
    index: ScheduleIndex,
    *,
    witnesses: dict[str, set[tuple[str, str]]] | None = None,
) -> dict[str, int]:
    """Walks use no boarding rounds; transfer slack is charged once per later boarding.

    Both ends of walking edges must pass the stop policy, including walking-only
    journeys. All stops of retained transit trips pass the same policy.
    """
    unrestricted = index.policy == UnknownPolicy.SCHEDULE_ONLY
    if not unrestricted and origin_stop_id not in index.accessible_stop_ids:
        return {}
    deadline = departure_seconds + max_travel_seconds
    layer = {origin_stop_id: departure_seconds}
    paths = {origin_stop_id: {('stop', origin_stop_id)}}
    best: dict[str, int] = {}
    for legs in range(max_transfers + 2):
        queue = [(arrival, stop) for stop, arrival in layer.items()]
        heapq.heapify(queue)
        while queue:
            arrival, stop = heapq.heappop(queue)
            if arrival != layer[stop]:
                continue
            for neighbour, seconds in index.walk_edges.get(stop, []):
                if not unrestricted and neighbour not in index.accessible_stop_ids:
                    continue
                candidate = arrival + seconds
                if candidate <= deadline and candidate < layer.get(neighbour, deadline + 1):
                    layer[neighbour] = candidate
                    paths[neighbour] = paths[stop] | {('stop', neighbour)}
                    heapq.heappush(queue, (candidate, neighbour))
        for stop, arrival in layer.items():
            if arrival < best.get(stop, deadline + 1):
                best[stop] = arrival
                if witnesses is not None:
                    witnesses[stop] = paths[stop]
        if legs == max_transfers + 1:
            break
        next_layer: dict[str, int] = {}
        next_paths: dict[str, set[tuple[str, str]]] = {}
        scanned: dict[str, int] = {}
        for stop, arrival in layer.items():
            min_board = arrival + (min_transfer_seconds if legs else 0)
            for trip_id, position, departure in index.boardings.get(stop, []):
                if departure < min_board or departure > deadline:
                    continue
                if index.permitted_trip_ids is not None and trip_id not in index.permitted_trip_ids:
                    continue
                trip = index.trips.get(trip_id)
                if trip is None or scanned.get(trip_id, len(trip.stops)) <= position:
                    continue
                scanned[trip_id] = position
                path = paths[stop] | {('trip', trip_id)} | {('stop', s.stop_id) for s in trip.stops}
                for target in trip.stops[position + 1:]:
                    if target.arrival_s > deadline:
                        break
                    if target.arrival_s < next_layer.get(target.stop_id, deadline + 1):
                        next_layer[target.stop_id] = target.arrival_s
                        next_paths[target.stop_id] = path
        layer, paths = next_layer, next_paths
        if not layer:
            break
    return best


def is_destination_reachable(
    origin_stop_id: str,
    destination_stop_id: str,
    departure_seconds: int,
    max_travel_seconds: int,
    max_transfers: int,
    min_transfer_seconds: int,
    index: ScheduleIndex,
) -> tuple[bool, int | None]:
    arrivals = reachable_arrivals(origin_stop_id, departure_seconds, max_travel_seconds,
                                  max_transfers, min_transfer_seconds, index)
    arrival = arrivals.get(destination_stop_id)
    return (False, None) if arrival is None else (True, arrival - departure_seconds)
