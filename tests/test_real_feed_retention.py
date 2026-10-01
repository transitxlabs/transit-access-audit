"""Independent CSV inventory checks for cached public feed trip retention.

Sources and licences are recorded beside each ZIP in .cache/gtfs/*_manifest.txt.
No network acquisition is performed by these tests.
"""
from __future__ import annotations

import csv
import io
import zipfile
from datetime import date
from pathlib import Path

import pytest

from transit_audit.gtfs.reader import read_gtfs_zip
from transit_audit.gtfs.zip_limits import EVALUATION_ZIP_LIMITS
from transit_audit.routing.index import build_schedule_index
from transit_audit.routing.models import UnknownPolicy


@pytest.mark.parametrize(('name', 'day'), [('calgary', date(2026, 9, 30)),
    ('edmonton', date(2026, 9, 30)), ('ttc', date(2026, 10, 7))])
def test_f1_cached_feeds_retain_independently_permitted_trips(name, day):
    filenames = {'calgary': 'calgary_transit_gtfs.zip', 'edmonton': 'edmonton_transit_gtfs.zip', 'ttc': 'ttc_completegtfs.zip'}
    path = Path('.cache/gtfs') / filenames[name]
    if not path.exists():
        pytest.skip('Cached public snapshot is unavailable')
    with zipfile.ZipFile(path) as archive:
        def rows(table):
            if table + '.txt' not in archive.namelist():
                return
            with archive.open(table + '.txt') as stream:
                yield from csv.DictReader(io.TextIOWrapper(stream, encoding='utf-8-sig'))

        stops = {r['stop_id']: r for r in rows('stops')}
        def resolve(stop):
            seen = set()
            while stop in stops and stop not in seen:
                seen.add(stop)
                raw = stops[stop].get('wheelchair_boarding', '').strip()
                if raw in ['1', '2']:
                    return raw
                stop = stops[stop].get('parent_station', '').strip()
            return '0'

        categories = {s: resolve(s) for s in stops}
        service_day = day.strftime('%Y%m%d')
        weekday = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][day.weekday()]
        services = {r['service_id'] for r in rows('calendar')
            if r['start_date'] <= service_day <= r['end_date'] and r[weekday] == '1'}
        for row in rows('calendar_dates'):
            if row['date'] == service_day:
                if row['exception_type'] == '1':
                    services.add(row['service_id'])
                elif row['exception_type'] == '2':
                    services.discard(row['service_id'])
        trips = {r['trip_id']: r for r in rows('trips') if r['service_id'] in services}
        blocked = {policy: set() for policy in [UnknownPolicy.OPTIMISTIC, UnknownPolicy.PESSIMISTIC]}
        has_times = set()
        for row in rows('stop_times'):
            trip, stop = row['trip_id'], row['stop_id']
            has_times.add(trip)
            for policy in blocked:
                raw = categories.get(stop, '0')
                if raw == '2' or (policy == UnknownPolicy.PESSIMISTIC and raw != '1'):
                    blocked[policy].add(trip)
    feed = read_gtfs_zip(path, EVALUATION_ZIP_LIMITS,
        only_tables={'stops', 'trips', 'stop_times', 'calendar', 'calendar_dates'})
    for policy in blocked:
        expected = {t for t, row in trips.items() if t in has_times and t not in blocked[policy]
            and (row.get('wheelchair_accessible', '').strip() == '1'
                 or (policy == UnknownPolicy.OPTIMISTIC and row.get('wheelchair_accessible', '').strip() != '2'))}
        actual = build_schedule_index(feed, day, policy)
        assert set(actual.trips) == expected
        if expected:
            assert len(actual.trips) > 0
