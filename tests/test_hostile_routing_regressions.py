"""Independent timetable and spatial counterexamples from verification findings 1-5."""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from transit_audit.gtfs.reader import GtfsFeed
from transit_audit.routing.accessibility import accessible_trips, resolve_stop_boarding
from transit_audit.routing.bounds import _pair_widths_for_overrides, rank_verification_targets
from transit_audit.routing.index import (
    ScheduleIndex,
    TripSchedule,
    TripStopTime,
    build_schedule_index,
)
from transit_audit.routing.models import BoundsConfig, UnknownPolicy
from transit_audit.routing.reachability import is_destination_reachable
from transit_audit.routing.sample import sample_stop_ids
from transit_audit.routing.walking import build_walk_edges, haversine_m


def independent_feed(stops, trips, times):
    calendar = pd.DataFrame([{'service_id': 's', **{d: '1' for d in
        ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']},
        'start_date': '20240101', 'end_date': '20261231'}])
    return GtfsFeed(Path('synthetic'), {'stops': pd.DataFrame(stops), 'trips': pd.DataFrame(trips),
        'stop_times': pd.DataFrame(times), 'calendar': calendar})


def trip_rows(trip_id, ids, minutes):
    return [{'trip_id': trip_id, 'stop_id': s, 'stop_sequence': str(i + 1),
        'arrival_time': f'08:{m:02}:00', 'departure_time': f'08:{m:02}:00'}
        for i, (s, m) in enumerate(zip(ids, minutes, strict=True))]


@pytest.mark.parametrize('policy', list(UnknownPolicy))
def test_f1_transit_only_independent_oracle(policy):
    feed = independent_feed([{'stop_id': s, 'wheelchair_boarding': '1'} for s in ['A', 'B']],
        [{'trip_id': 'T', 'service_id': 's', 'wheelchair_accessible': '1'}],
        trip_rows('T', ['A', 'B'], [30, 40]))
    index = build_schedule_index(feed, date(2026, 9, 30), policy)
    assert set(index.trips) == {'T'}
    assert not index.walk_edges
    assert is_destination_reachable('A', 'B', 30600, 3600, 0, 0, index) == (True, 600)


@pytest.mark.parametrize('lat', [43.7, 51.0, 53.5, 60.0, 70.0, 89.9])
def test_f2_metric_radius_matches_brute_force(lat):
    rows = [{'stop_id': str(i), 'stop_lat': lat + (i % 3) * .001,
        'stop_lon': -114 + (i // 3) * .002} for i in range(18)]
    edges = build_walk_edges(pd.DataFrame(rows), speed_mps=1.4, radius_m=300)
    expected = {(a['stop_id'], b['stop_id']) for a in rows for b in rows
        if a != b and haversine_m(a['stop_lat'], a['stop_lon'], b['stop_lat'], b['stop_lon']) <= 300}
    assert {(s, t) for s, links in edges.items() for t, _ in links} == expected


def test_f2_inaccessible_walk_target():
    index = ScheduleIndex(UnknownPolicy.PESSIMISTIC, accessible_stop_ids={'A'}, walk_edges={'A': [('B', 60)]})
    assert not is_destination_reachable('A', 'B', 30600, 3600, 0, 0, index)[0]


def test_f2_access_walk_then_bus_zero_transfers():
    index = ScheduleIndex(UnknownPolicy.SCHEDULE_ONLY,
        trips={'T': TripSchedule('T', [TripStopTime('B', 30720, 30720, 1), TripStopTime('C', 31320, 31320, 2)])},
        boardings={'B': [('T', 0, 30720)]}, walk_edges={'A': [('B', 60)]})
    assert is_destination_reachable('A', 'C', 30600, 3600, 0, 300, index) == (True, 720)


@pytest.mark.parametrize('cross_stop', [False, True])
def test_f2_transfer_rounds_and_minimum(cross_stop):
    middle = 'X' if cross_stop else 'B'
    index = ScheduleIndex(UnknownPolicy.SCHEDULE_ONLY,
        trips={'T': TripSchedule('T', [TripStopTime('A', 30600, 30600, 1), TripStopTime('B', 30720, 30720, 2)]),
               'U': TripSchedule('U', [TripStopTime(middle, 31020, 31020, 1), TripStopTime('C', 31320, 31320, 2)])},
        boardings={'A': [('T', 0, 30600)], middle: [('U', 0, 31020)]},
        walk_edges={'B': [('X', 60)]} if cross_stop else {})
    assert not is_destination_reachable('A', 'C', 30600, 3600, 0, 180, index)[0]
    assert is_destination_reachable('A', 'C', 30600, 3600, 1, 180, index) == (True, 720)
    assert not is_destination_reachable('A', 'C', 30600, 3600, 1, 360, index)[0]


def test_f3_nearest_parent_and_override():
    stops = pd.DataFrame([{'stop_id': 'P', 'wheelchair_boarding': '2', 'parent_station': ''},
        {'stop_id': 'M', 'wheelchair_boarding': '1', 'parent_station': 'P'},
        {'stop_id': 'C', 'wheelchair_boarding': '0', 'parent_station': 'M'}])
    assert resolve_stop_boarding(stops)['C'] == '1'
    assert resolve_stop_boarding(stops, stop_overrides={'M': '2'})['C'] == '2'
    assert resolve_stop_boarding(stops.drop(columns='wheelchair_boarding'), stop_overrides={'P': '1'})['C'] == '1'
    trips = pd.DataFrame([{'trip_id': 'T'}])
    assert accessible_trips(trips, UnknownPolicy.PESSIMISTIC, trip_overrides={'T': '1'}) == {'T'}


def test_f4_no_candidate_cutoff_and_exhaustive_equivalence():
    rows = [{'stop_id': f'D{i:02}', 'wheelchair_boarding': '0'} for i in range(26)]
    rows += [{'stop_id': 'Z', 'wheelchair_boarding': '0'}, {'stop_id': 'B', 'wheelchair_boarding': '1'}]
    feed = independent_feed(rows, [{'trip_id': 'dummy', 'service_id': 's', 'wheelchair_accessible': '2'}],
        trip_rows('dummy', [f'D{i:02}' for i in range(26)], [30] * 26))
    config = BoundsConfig(service_date=date(2026, 9, 30), departure_time='08:30:00', min_transfer_minutes=0)
    pairs = [('Z', 'B')]
    walk = {'Z': [('B', 60)]}
    targets = rank_verification_targets(feed, config, pairs, walk_edges=walk)
    exhaustive = {}
    base = _pair_widths_for_overrides(feed, config, pairs, walk_edges=walk)
    for row in rows[:-1]:
        outcomes = [_pair_widths_for_overrides(feed, config, pairs,
            stop_overrides={row['stop_id']: value}, walk_edges=walk) for value in ['1', '2']]
        change = sum(base) - min(map(sum, outcomes))
        if change:
            exhaustive[row['stop_id']] = change
    assert {t.entity_id: t.interval_width_change for t in targets} == exhaustive == {'Z': 1.0}


def test_f5_sampling_resolves_full_feed_parents():
    rows = [{'stop_id': 'P', 'wheelchair_boarding': '1', 'location_type': '1'}]
    rows += [{'stop_id': f'C{i}', 'wheelchair_boarding': '0', 'parent_station': 'P', 'location_type': '0'} for i in range(8)]
    rows += [{'stop_id': f'U{i}', 'wheelchair_boarding': '0', 'location_type': '0'} for i in range(8)]
    feed = independent_feed(rows, [{'trip_id': 'T', 'service_id': 's'}], trip_rows('T', [r['stop_id'] for r in rows[1:]], [30] * 16))
    chosen = sample_stop_ids(feed, 8, 42, prefer_unknown=True)
    assert sum(s.startswith('C') for s in chosen) == 4
    assert sum(s.startswith('U') for s in chosen) == 4


def test_f4_intermediate_trip_and_exhaustive_outcomes():
    feed = independent_feed([{'stop_id': s, 'wheelchair_boarding': '1'} for s in 'ABCD'],
        [{'trip_id': t, 'service_id': 's', 'wheelchair_accessible': '0' if t == 'U' else '1'} for t in 'TUV'],
        trip_rows('T', ['A', 'B'], [30, 32]) + trip_rows('U', ['B', 'C'], [34, 36]) + trip_rows('V', ['C', 'D'], [38, 40]))
    config = BoundsConfig(service_date=date(2026, 9, 30), departure_time='08:30:00', min_transfer_minutes=0)
    targets = rank_verification_targets(feed, config, [('A', 'D')], walk_edges={})
    assert [(t.entity_id, t.interval_width_change) for t in targets] == [('U', 1.0)]
    assert targets[0].metadata['mean_width_if_accessible'] == 0.0
    assert targets[0].metadata['mean_width_if_not_accessible'] == 0.0


def test_f5_crossed_bootstrap_preserves_strata_and_clusters():
    from transit_audit.routing.uncertainty import crossed_bootstrap_interval
    pairs = [(o, d, float(o == 'U1')) for o in ['U1', 'U2', 'K1', 'K2'] for d in ['D1', 'D2', 'D3']]
    strata = {'U1': 'unknown', 'U2': 'unknown', 'K1': 'known', 'K2': 'known'}
    lo, hi = crossed_bootstrap_interval(pairs, strata, samples=1000)
    assert (lo, hi) == (0.0, 0.5)
    assert crossed_bootstrap_interval([(o, d, 1.0) for o, d, _ in pairs], strata) == (1.0, 1.0)
    assert crossed_bootstrap_interval([(o, d, 0.0) for o, d, _ in pairs], strata) == (0.0, 0.0)
    assert crossed_bootstrap_interval([], {}) == (0.0, 0.0)
    with pytest.raises(ValueError, match='duplicate'):
        crossed_bootstrap_interval([('U1', 'D1', 0.0)] * 2, strata)


def test_scorer_perfect_resolution_and_empty():
    from transit_audit.routing.bounds import _verification_change
    assert _verification_change([1, 1], [0, 0], [0, 0]) == (1.0, 2)
    assert _verification_change([], [], []) == (0.0, 0)
    assert _verification_change([0, 0], [0, 0], [0, 0]) == (0.0, 0)


def test_f2_preserves_later_arrival_with_fewer_transit_legs():
    # A two-leg arrival at X is earlier, but only the later one-leg state can
    # board the final bus within a one-transfer budget.
    trips = {'T': TripSchedule('T', [TripStopTime('A', 30600, 30600, 1), TripStopTime('B', 30660, 30660, 2)]),
        'U': TripSchedule('U', [TripStopTime('B', 30660, 30660, 1), TripStopTime('X', 30720, 30720, 2)]),
        'V': TripSchedule('V', [TripStopTime('A', 30600, 30600, 1), TripStopTime('X', 30780, 30780, 2)]),
        'W': TripSchedule('W', [TripStopTime('X', 30840, 30840, 1), TripStopTime('D', 30900, 30900, 2)])}
    index = ScheduleIndex(UnknownPolicy.SCHEDULE_ONLY, trips=trips,
        boardings={'A': [('T', 0, 30600), ('V', 0, 30600)], 'B': [('U', 0, 30660)], 'X': [('W', 0, 30840)]})
    assert is_destination_reachable('A', 'D', 30600, 3600, 1, 0, index) == (True, 300)


def test_f4_exact_ranking_against_all_fields_on_adversarial_small_feeds():
    import random

    from transit_audit.routing.accessibility import unknown_entities

    rng = random.Random(19)
    for _ in range(15):
        rows = [{'stop_id': 'P', 'wheelchair_boarding': '0', 'parent_station': ''}]
        rows += [{'stop_id': s, 'wheelchair_boarding': rng.choice(['0', '1', '2']),
            'parent_station': 'P' if s == 'B' else ''} for s in 'ABCD']
        trip_ids = ['T', 'U', 'V']
        feed = independent_feed(rows,
            [{'trip_id': t, 'service_id': 's', 'wheelchair_accessible': rng.choice(['0', '1'])} for t in trip_ids],
            trip_rows('T', ['A', 'B'], [30, 32]) + trip_rows('U', ['B', 'C'], [34, 36]) + trip_rows('V', ['C', 'D'], [38, 40]))
        config = BoundsConfig(service_date=date(2026, 9, 30), departure_time='08:30:00', min_transfer_minutes=0)
        pairs = [('A', 'D'), ('A', 'C'), ('B', 'D')]
        walk = {'A': [('B', 60)], 'C': [('D', 60)]}
        base = _pair_widths_for_overrides(feed, config, pairs, walk_edges=walk)
        unknown_stops, unknown_trips = unknown_entities(feed.table('stops'), feed.table('trips'))
        exhaustive = {}
        for kind, ids in [('stop', unknown_stops), ('trip', unknown_trips)]:
            for entity in ids:
                outcomes = [_pair_widths_for_overrides(feed, config, pairs, walk_edges=walk,
                    **{f'{kind}_overrides': {entity: value}}) for value in ['1', '2']]
                reduction = (sum(base) - min(map(sum, outcomes))) / len(pairs)
                if reduction > 0:
                    exhaustive[kind, entity] = (reduction, sum(outcomes[0]) / len(pairs), sum(outcomes[1]) / len(pairs))
        actual = {(t.entity_type, t.entity_id): (t.interval_width_change,
            t.metadata['mean_width_if_accessible'], t.metadata['mean_width_if_not_accessible'])
            for t in rank_verification_targets(feed, config, pairs, walk_edges=walk)}
        assert actual == exhaustive


def test_reachability_scorer_perfect_and_empty():
    from transit_audit.routing.bounds import _policy_summary
    from transit_audit.routing.models import OdPairResult

    pairs = [OdPairResult(origin_stop_id='A', destination_stop_id=d,
        optimistic_reachable=True, pessimistic_reachable=True, interval_width=0,
        optimistic_travel_seconds=60, pessimistic_travel_seconds=60) for d in ['B', 'C']]
    summary = _policy_summary(pairs, UnknownPolicy.OPTIMISTIC, optimistic=True)
    assert summary.reachable_destination_count / len(pairs) == 1.0
    for p in pairs:
        p.optimistic_reachable = False
        p.pessimistic_reachable = False
    assert _policy_summary(pairs, UnknownPolicy.OPTIMISTIC, optimistic=True).reachable_destination_count == 0
    assert _policy_summary([], UnknownPolicy.PESSIMISTIC, optimistic=False).reachable_destination_count == 0
