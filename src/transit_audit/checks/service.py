"""Service frequency and span metrics."""

from __future__ import annotations

from statistics import mean, median

from transit_audit.config import AuditConfig
from transit_audit.gtfs.reader import GtfsFeed, parse_hhmmss, seconds_to_hhmmss
from transit_audit.gtfs.service_calendar import all_departures_at_stop, parse_service_date
from transit_audit.models import Finding, Metric

TCQSM_URL = (
    "https://nap.nationalacademies.org/catalog/24766/"
    "transit-capacity-and-quality-of-service-manual-third-edition"
)
GTFS_URL = "https://gtfs.org/documentation/schedule/reference/"


def _aggregate(values: list[float], method: str) -> float | None:
    if not values:
        return None
    if method == "mean":
        return float(mean(values))
    if method == "min":
        return float(min(values))
    if method == "max":
        return float(max(values))
    return float(median(values))


def _reference_stop_ids(feed: GtfsFeed, config: AuditConfig) -> list[str]:
    explicit = [b.reference_stop_id for b in config.service_bands if b.reference_stop_id]
    if explicit:
        return list(dict.fromkeys(str(s) for s in explicit))
    stop_times = feed.table("stop_times")
    if stop_times.empty:
        return []
    return sorted(stop_times["stop_id"].astype(str).unique().tolist())


def run_service_checks(
    feed: GtfsFeed,
    config: AuditConfig,
    flex_route_ids: set[str],
) -> tuple[list[Finding], list[Metric]]:
    metrics: list[Metric] = []
    stop_times = feed.table("stop_times")
    trips = feed.table("trips")
    if stop_times.empty or trips.empty:
        return [], metrics

    service_date = parse_service_date(config.service_date)
    date_label = service_date.isoformat()
    reference_stops = _reference_stop_ids(feed, config)
    aggregation = config.reference_stop_aggregation

    for band in config.service_bands:
        stop_id = band.reference_stop_id
        stop_ids = reference_stops if stop_id is None else [str(stop_id)]

        band_spans: list[float] = []
        band_departures_per_hour: list[float] = []
        band_max_gaps: list[float] = []
        band_median_headways: list[float] = []

        for sid in stop_ids:
            departures = all_departures_at_stop(feed, sid, service_date, flex_route_ids)
            if not departures:
                continue

            start = parse_hhmmss(band.start_time)
            end = parse_hhmmss(band.end_time)
            in_band = [d for d in departures if start <= d <= end]
            if not in_band:
                continue

            if config.is_check_enabled("SERVICE.DEPARTURES_PER_HOUR"):
                hour = start // 3600
                hour_departures = [d for d in in_band if d // 3600 == hour]
                band_departures_per_hour.append(float(len(hour_departures)))

            if config.is_check_enabled("SERVICE.BAND_SPAN"):
                band_spans.append(float(in_band[-1] - in_band[0]))

            if config.is_check_enabled("SERVICE.MAX_GAP") and len(in_band) > 1:
                gaps = [in_band[i + 1] - in_band[i] for i in range(len(in_band) - 1)]
                band_max_gaps.append(float(max(gaps)))

            if config.is_check_enabled("SERVICE.MEDIAN_HEADWAY") and len(in_band) > 1:
                gaps = sorted(in_band[i + 1] - in_band[i] for i in range(len(in_band) - 1))
                band_median_headways.append(float(gaps[len(gaps) // 2]))

        stop_label = stop_id if stop_id else f"aggregated({aggregation})"

        if config.is_check_enabled("SERVICE.DEPARTURES_PER_HOUR") and band_departures_per_hour:
            value = _aggregate(band_departures_per_hour, aggregation)
            if value is not None:
                metrics.append(
                    Metric(
                        metric_id="SERVICE.DEPARTURES_PER_HOUR",
                        label=f"Departures per hour at {stop_label} ({band.name})",
                        value=int(value),
                        numerator=int(value),
                        denominator=1,
                        unit="departures/hour",
                        metadata={
                            "stop_id": stop_id or "aggregated",
                            "reference_stop_ids": stop_ids,
                            "aggregation": aggregation,
                            "time_band": band.name,
                            "service_date": date_label,
                            "method": "active_service_trips_and_frequencies",
                        },
                        source_url=TCQSM_URL,
                    )
                )

        if config.is_check_enabled("SERVICE.BAND_SPAN") and band_spans:
            span_secs = _aggregate(band_spans, aggregation)
            if span_secs is not None:
                metrics.append(
                    Metric(
                        metric_id="SERVICE.BAND_SPAN",
                        label=f"Band-limited service span at {stop_label} ({band.name})",
                        value=seconds_to_hhmmss(int(span_secs)),
                        metadata={
                            "time_band": band.name,
                            "band_start": band.start_time,
                            "band_end": band.end_time,
                            "stop_id": stop_id or "aggregated",
                            "reference_stop_ids": stop_ids,
                            "aggregation": aggregation,
                            "service_date": date_label,
                            "note": "First-to-last departure within the configured time band only.",
                        },
                        source_url=TCQSM_URL,
                    )
                )

        if config.is_check_enabled("SERVICE.MAX_GAP") and band_max_gaps:
            gap_val = _aggregate(band_max_gaps, aggregation)
            if gap_val is not None:
                metrics.append(
                    Metric(
                        metric_id="SERVICE.MAX_GAP",
                        label=f"Maximum headway at {stop_label}",
                        value=int(gap_val) // 60,
                        numerator=int(gap_val),
                        denominator=60,
                        unit="minutes",
                        metadata={
                            "stop_id": stop_id or "aggregated",
                            "time_band": band.name,
                            "service_date": date_label,
                        },
                        source_url=TCQSM_URL,
                    )
                )

        if config.is_check_enabled("SERVICE.MEDIAN_HEADWAY") and band_median_headways:
            med_val = _aggregate(band_median_headways, aggregation)
            if med_val is not None:
                metrics.append(
                    Metric(
                        metric_id="SERVICE.MEDIAN_HEADWAY",
                        label=f"Median headway at {stop_label}",
                        value=int(med_val) // 60,
                        unit="minutes",
                        metadata={
                            "stop_id": stop_id or "aggregated",
                            "service_date": date_label,
                        },
                        source_url=TCQSM_URL,
                    )
                )

    if config.is_check_enabled("SERVICE.DAILY_SPAN"):
        daily_spans: list[float] = []
        for sid in reference_stops:
            departures = all_departures_at_stop(feed, sid, service_date, flex_route_ids)
            if len(departures) >= 2:
                daily_spans.append(float(departures[-1] - departures[0]))
        if daily_spans:
            span_val = _aggregate(daily_spans, aggregation)
            if span_val is not None:
                metrics.append(
                    Metric(
                        metric_id="SERVICE.DAILY_SPAN",
                        label="Daily service span (first to last departure)",
                        value=seconds_to_hhmmss(int(span_val)),
                        metadata={
                            "reference_stop_ids": reference_stops,
                            "aggregation": aggregation,
                            "service_date": date_label,
                            "first_departure": seconds_to_hhmmss(
                                int(
                                    _aggregate(
                                        [
                                            float(
                                                all_departures_at_stop(
                                                    feed, s, service_date, flex_route_ids
                                                )[0]
                                            )
                                            for s in reference_stops
                                            if all_departures_at_stop(
                                                feed, s, service_date, flex_route_ids
                                            )
                                        ],
                                        aggregation,
                                    )
                                    or 0
                                )
                            ),
                            "method": "active_service_day_first_to_last",
                        },
                        source_url=TCQSM_URL,
                    )
                )

    if config.is_check_enabled("SERVICE.DAYS_PER_WEEK"):
        calendar = feed.table("calendar")
        if not calendar.empty:
            metrics.append(
                Metric(
                    metric_id="SERVICE.DAYS_PER_WEEK",
                    label="Distinct service patterns",
                    value=len(calendar),
                    unit="patterns",
                    metadata={"service_date": date_label},
                    source_url=GTFS_URL,
                )
            )

    return [], metrics
