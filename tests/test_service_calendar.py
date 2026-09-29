from datetime import date
from pathlib import Path

from transit_audit.checks.service import run_service_checks
from transit_audit.config import AuditConfig, ServiceBandConfig
from transit_audit.gtfs.reader import read_gtfs_zip
from transit_audit.gtfs.service_calendar import (
    active_service_ids,
    all_departures_at_stop,
    departures_for_trip_on_date,
    expand_frequency_departures,
    parse_service_date,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_service_date_formats() -> None:
    assert parse_service_date("2024-06-03") == date(2024, 6, 3)
    assert parse_service_date("20240603") == date(2024, 6, 3)


def test_calendar_exception_switches_service() -> None:
    feed = read_gtfs_zip(FIXTURES / "calendar_exception.zip")
    monday = date(2024, 6, 3)
    active = active_service_ids(feed, monday)
    assert active == {"SATURDAY"}


def test_calendar_exception_metrics_use_active_service() -> None:
    feed = read_gtfs_zip(FIXTURES / "calendar_exception.zip")
    config = AuditConfig(
        service_date="2024-06-03",
        service_bands=[
            ServiceBandConfig(
                name="morning",
                start_time="10:00:00",
                end_time="11:00:00",
                reference_stop_id="S1",
            )
        ],
    )
    _, metrics = run_service_checks(feed, config, flex_route_ids=set())
    departures = next(m for m in metrics if m.metric_id == "SERVICE.DEPARTURES_PER_HOUR")
    assert departures.value == 1
    assert departures.metadata["service_date"] == "2024-06-03"


def test_frequencies_expansion() -> None:
    departures = expand_frequency_departures("07:00:00", "08:00:00", 900, exact_times="0")
    assert departures == [7 * 3600, 7 * 3600 + 900, 7 * 3600 + 1800, 7 * 3600 + 2700]


def test_frequencies_feed_departures() -> None:
    feed = read_gtfs_zip(FIXTURES / "frequencies.zip")
    config = AuditConfig(
        service_date="2024-06-03",
        service_bands=[
            ServiceBandConfig(
                name="peak",
                start_time="07:00:00",
                end_time="08:00:00",
                reference_stop_id="S1",
            )
        ],
    )
    _, metrics = run_service_checks(feed, config, flex_route_ids=set())
    departures = next(m for m in metrics if m.metric_id == "SERVICE.DEPARTURES_PER_HOUR")
    assert departures.value == 4
    band_span = next(m for m in metrics if m.metric_id == "SERVICE.BAND_SPAN")
    assert band_span.metadata["time_band"] == "peak"


def test_departures_for_inactive_trip_returns_empty() -> None:
    feed = read_gtfs_zip(FIXTURES / "calendar_exception.zip")
    monday = date(2024, 6, 3)
    assert departures_for_trip_on_date(feed, "T1", monday, "S1") == []
    assert departures_for_trip_on_date(feed, "T3", monday, "S1") == [10 * 3600]


def test_all_departures_at_stop_includes_frequencies() -> None:
    feed = read_gtfs_zip(FIXTURES / "frequencies.zip")
    deps = all_departures_at_stop(feed, "S1", date(2024, 6, 3), set())
    assert len(deps) == 4


def test_expand_frequency_zero_headway() -> None:
    assert expand_frequency_departures("07:00:00", "08:00:00", 0) == []


def test_expand_frequency_exact_times() -> None:
    deps = expand_frequency_departures("07:00:00", "07:30:00", 600, exact_times="1")
    assert deps == [7 * 3600, 7 * 3600 + 600, 7 * 3600 + 1200, 7 * 3600 + 1800]


def test_active_service_calendar_only() -> None:
    feed = read_gtfs_zip(FIXTURES / "missing_calendar.zip")
    feed.tables["calendar_dates"] = __import__("pandas").read_csv(
        __import__("io").StringIO(
            "service_id,date,exception_type\nONLY,20240603,1\n"
        ),
        dtype=str,
        keep_default_na=False,
    )
    active = active_service_ids(feed, date(2024, 6, 3))
    assert active == {"ONLY"}


def test_service_aggregation_without_reference_stop() -> None:
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    config = AuditConfig(
        service_date="2024-06-03",
        reference_stop_aggregation="median",
        service_bands=[ServiceBandConfig(name="peak", start_time="07:00:00", end_time="09:00:00")],
    )
    _, metrics = run_service_checks(feed, config, flex_route_ids=set())
    departures = next(m for m in metrics if m.metric_id == "SERVICE.DEPARTURES_PER_HOUR")
    assert departures.metadata["aggregation"] == "median"
    assert departures.metadata["stop_id"] == "aggregated"


def test_departures_per_hour_and_band_span() -> None:
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    config = AuditConfig(
        service_date="2024-06-03",
        service_bands=[
            ServiceBandConfig(
                name="peak",
                start_time="07:00:00",
                end_time="09:00:00",
                reference_stop_id="S1",
            )
        ],
    )
    _, metrics = run_service_checks(feed, config, flex_route_ids=set())
    departures = next(m for m in metrics if m.metric_id == "SERVICE.DEPARTURES_PER_HOUR")
    assert departures.value == 2
    span = next(m for m in metrics if m.metric_id == "SERVICE.BAND_SPAN")
    assert span.metadata["band_start"] == "07:00:00"
    gap = next(m for m in metrics if m.metric_id == "SERVICE.MAX_GAP")
    assert gap.value == 40
    daily = next(m for m in metrics if m.metric_id == "SERVICE.DAILY_SPAN")
    assert daily.metadata["method"] == "active_service_day_first_to_last"
