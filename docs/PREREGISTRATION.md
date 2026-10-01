# Preregistration phase 2: accessibility-unknown routing bounds

Frozen before phase 2 evaluation. Phase 1 hash archived in `docs/PREREGISTRATION.sha256`.

## Research question

For fixed Canadian GTFS feeds and a service day, how wide are schedule-based reachability intervals when unknown wheelchair metadata is treated optimistically versus pessimistically, and which missing fields most reduce that interval when verified?

## Hypotheses

1. **H1:** At least one primary evaluation feed will show non-zero mean interval width on the preregistered OD sample when unknown wheelchair fields are present under correct GTFS semantics.
2. **H2:** The schedule-only baseline (no wheelchair filtering) will reach strictly more OD pairs than the pessimistic policy on feeds with unknown or missing wheelchair columns.
3. **H3:** Verification ranking by recomputed interval-width change will rank high-impact unknown fields above zero-change fields on the synthetic bounds fixture (exact test).

## Primary datasets

| Feed | Role | Licence | Service date |
|------|------|---------|--------------|
| Calgary Transit GTFS | Primary (missing wheelchair columns) | [City of Calgary Open Data](https://data.calgary.ca/pages/open-data-licence) | First Tuesday in feed calendar after download |
| Edmonton Transit GTFS | Primary (partial unknown stop coding) | [City of Edmonton Open Data](https://www.edmonton.ca/city_government/open_data) | First Tuesday in feed calendar after download |
| TTC merged GTFS | Null check (trips fully coded) | [Open Government Licence – Toronto](https://open.toronto.ca/open-data-licence/) | 2026-10-07 (Tuesday within feed calendar) |

No raw feeds committed to git. Local cache under `.cache/gtfs/`.

## Sample design

| Parameter | Value |
|-----------|-------|
| Origins sampled | 20 |
| Destinations sampled | 40 |
| OD pairs | All origin-destination combinations excluding identical stop (800 pairs when full grid) |
| Origin sampling | Stratified preference for stops with unknown `wheelchair_boarding` after parent inheritance |
| Departure time | 08:30:00 local |
| Random seed | 42 |
| Walking transfers | 1.4 m/s, 300 m radius (GTFS stop coordinates) |

## Routing model

Schedule-based reachability on GTFS stop times:

- Active trips filtered by `calendar.txt` / `calendar_dates.txt` for the service date.
- Trip allowed under a policy only if trip `wheelchair_accessible` and all served stops `wheelchair_boarding` resolve as accessible under that policy.
- GTFS semantics: empty or `0` = no information; `1` = accessible; `2` = not accessible ([spec](https://gtfs.org/documentation/schedule/reference/#stopstxt-wheelchair_boarding)).
- Child stops coded `0` or empty inherit parent station `wheelchair_boarding`.
- Walking transfers between stops within 300 m at 1.4 m/s, applied each transfer round.
- Transfers allowed up to 2, minimum 5 minutes.
- Maximum in-vehicle plus wait travel time 60 minutes from departure.

## Policies

| Policy | Unknown GTFS fields |
|--------|---------------------|
| Optimistic | Accessible |
| Pessimistic | Not accessible |
| Schedule-only baseline | Wheelchair fields ignored (connectivity upper bound) |

The former exclude-unknown baseline is removed because it duplicated pessimistic routing once GTFS codes were corrected.

## Metrics

| Metric | Definition |
|--------|------------|
| Interval width (OD pair) | 1 if optimistic reachable and pessimistic not; else 0 |
| Mean interval width | Mean over sampled OD pairs |
| 95% CI for mean width | Bootstrap with 1,000 resamples, seed 42 |
| Verification change | Base mean width minus min(mean width if field set to 1, mean width if set to 2) |
| Affected OD pairs | Count of sampled pairs with interval width 1 before verification |

## Sensitivity analysis (secondary)

- Transfer grid: `min_transfer_minutes` in {3, 5, 10} and `max_travel_minutes` in {45, 60, 90}.
- Walking grid: speed in {1.0, 1.4, 1.8} m/s and radius in {200, 300, 500} m.

## Baselines

1. Completeness audit counts (unknown stop and trip counts).
2. Optimistic-only and pessimistic-only reachable counts.
3. Schedule-only reachable count (no wheelchair filtering).
4. MobilityData GTFS Validator notices per feed (schema baseline).

## Stop rules

- Abort if any feed download fails or exceeds 500 MB compressed.
- Abort if peak process memory exceeds 12 GB on the evaluation slice.
- Do not tune sample sizes after viewing interval widths.
- Report timetable-based limits plainly.

## SHA-256 of this document

Hash computed over this file excluding this section:

```text
b9b793b753bffcf761232632f85a910ee2af444a8db6018aaf9ffc1dc262bde2
```

## Deviations log

None at preregistration time.
