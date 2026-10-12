# Technical report: accessibility-unknown routing bounds

TransitX Labs Inc.  
Version 0.3.0  
Date: 2026-09-30

## Abstract

General Transit Feed Specification (GTFS) wheelchair fields are often missing or coded as no information. Treating those values as either accessible or inaccessible silently changes schedule-based reachability conclusions. We implement optimistic and pessimistic routing bounds with walking transfers, report reachability interval widths on a bounded origin-destination sample, and rank unknown fields by recomputed interval-width change. Evaluation on Calgary Transit (missing wheelchair columns) shows non-zero interval widths; Toronto Transit Commission merged GTFS is a null check (fully coded after corrected semantics).

## 1. Introduction

Transit agencies publish `wheelchair_boarding` (stops) and `wheelchair_accessible` (trips) with three-valued semantics: empty or `0` = no information, `1` = accessible, `2` = not accessible ([GTFS accessibility](https://gtfs.org/documentation/schedule/reference/#stopstxt-wheelchair_boarding)). Child stops coded `0` or empty inherit parent station values. Journey planners must decide how unknown values affect routing. OpenTripPlanner exposes costs and filtering switches ([OTP accessibility docs](https://docs.opentripplanner.org/en/dev-2.x/Accessibility/)), but agencies lack a reproducible workflow to quantify decision impact or prioritize field verification.

This work adds schedule-based bound analysis to the transit-access-audit toolkit.

## 2. Related work

| Work | Contribution | Gap |
|------|--------------|-----|
| MobilityData GTFS Validator | Feed validation | No routing bounds or policy intervals |
| OpenTripPlanner | Accessibility-aware routing | Single scenario, no verification ranking |
| r5py / R5 | Multimodal routing | No unknown-field bound workflow |
| Wessel and Farber 2019 ([doi:10.5198/jtlu.2019.1502](https://doi.org/10.5198/jtlu.2019.1502)) | Schedule vs observed accessibility | Timetable fidelity, not unknown semantics |
| Oh et al. 2017 ([rosap.ntl.bts.gov/view/dot/34806](https://rosap.ntl.bts.gov/view/dot/34806/dot_34806_DS1.pdf)) | GTFS wheelchair analysis | No bound pair or verification ranking |

## 3. Method

### 3.1 Policies

| Policy | Unknown fields |
|--------|----------------|
| Optimistic | Accessible |
| Pessimistic | Not accessible |
| Schedule-only baseline | Ignored (connectivity upper bound) |

Both stop and trip must pass under a policy for a trip to remain in the schedule index. The former exclude-unknown baseline duplicated pessimistic routing once GTFS codes were corrected and was removed.

### 3.2 Schedule index and walking transfers

For service date `d`, filter trips by active `service_id`, build boarding lists per stop from `stop_times`, and drop trips failing accessibility resolution including parent-station inheritance. Walking transfers connect stops within a configurable geodesic radius at a fixed speed (default 1.4 m/s, 300 m).

### 3.3 Reachability and interval width

From origin stop at departure time `t0`, run round-based boarding with minimum transfer time, walking edges, and maximum travel budget. Destination `d` is reachable under policy `p` if earliest arrival within budget exists.

For OD pair `(o, d)`: `width(o,d) = reachable_optimistic(o,d) - reachable_pessimistic(o,d)` in {0, 1}.

### 3.4 Verification ranking

For each candidate unknown field on the sampled OD pairs, re-run routing with that field set to accessible and to not accessible. Rank by reduction in mean interval width (exact counterfactual recomputation for a time-selected subset; rank only among evaluated fields and leave skipped impact unknown; soft candidate-start budgets permit an in-progress candidate to exceed the budget; see `docs/amendments/AMENDMENT_2026-10-01_04_ranking.md`).

## 4. Data

| Source | Licence | Role |
|--------|---------|------|
| Calgary Transit GTFS | [Open Government Licence - City of Calgary](https://data.calgary.ca/stories/s/u45n-7awa/) | Primary (missing wheelchair columns) |
| Edmonton Transit GTFS | [Open Government Licence - City of Edmonton](https://data.edmonton.ca/stories/s/Open-Government-Licence-Edmonton/msh8-if28/) | Secondary (partial unknown stops) |
| TTC merged GTFS | [Open Government Licence - Toronto](https://open.toronto.ca/open-data-licence/) | Null check (fully coded trips) |
| Synthetic `bounds_route.zip` | Apache-2.0 | Unit tests |

Feeds downloaded 2026-09-30; service dates in `docs/PREREGISTRATION.md`.

## 5. Experiments

Phase 2 preregistration: `docs/PREREGISTRATION.md` (SHA-256 recorded at evaluation time in `RESULTS.md` and `docs/bounds_eval/evaluation.json`). Archived phase 1 hash: `docs/PREREGISTRATION.sha256`.

Baselines: completeness counts, optimistic-only, pessimistic-only, schedule-only, MobilityData GTFS Validator notices.

Sensitivity: transfer times {3, 5, 10} minutes; travel budgets {45, 60, 90} minutes; walking speed {1.0, 1.4, 1.8} m/s and radius {200, 300, 500} m.

Previous H1/H2/H3 support claims are withdrawn because accessibility routing discarded all trips. This post-result repair is exploratory under the separate dated amendments in `docs/amendments/`; no retrospective freeze is claimed.

## 6. Corrected results

Generated results appear below and in [results](results.md). Positive widths describe policy sensitivity. A null width does not establish universal accessibility. Production ranking reports evaluated candidate counts, both counterfactual outcomes for positive targets, and skips when the time budget is exceeded.

## 7. Limitations

- Schedule-based, not observed operations.
- Walking transfers use geodesic distance, not a pedestrian network.
- Bounded sample, not exhaustive OD matrix.
- Does not establish legal accessibility compliance.

## 8. Reproducibility

```bash
python -m pip install -e ".[geo,dev]"
python scripts/fetch_gtfs.py calgary
python scripts/fetch_gtfs.py edmonton
python scripts/fetch_gtfs.py ttc
python scripts/run_bounds_evaluation.py --include-ttc --feeds calgary edmonton --sensitivity --walk-sensitivity
pytest -m "not network"
transit-audit bounds tests/fixtures/bounds_route.zip \
  --service-date 2024-06-03 --departure-time 07:00:00 --origin-count 5 --destination-count 5
```

Place `gtfs-validator-6.0.0-cli.jar` in `vendor/` for validator baselines.

## References

1. GTFS accessibility reference. https://gtfs.org/documentation/schedule/reference/#stopstxt-wheelchair_boarding
2. OpenTripPlanner accessibility configuration. https://docs.opentripplanner.org/en/dev-2.x/Accessibility/
3. Wessel, N., Farber, S. (2019). On the accuracy of schedule-based GTFS for measuring accessibility. *Journal of Transport and Land Use*. https://doi.org/10.5198/jtlu.2019.1502
4. Oh, J., et al. (2017). Estimating and Enhancing Public Transit Accessibility for People with Mobility Limitations. U.S. DOT. https://rosap.ntl.bts.gov/view/dot/34806/dot_34806_DS1.pdf

<!-- GENERATED RESULTS START -->
Conditions: schedule-based reachability on the retained GTFS snapshots (service dates: ttc 2026-10-07, calgary 2026-09-30, edmonton 2026-09-30); departures at 08:30:00, trips of at most 60 minutes with at most 2 transfers (5-minute minimum), walking at 1.4 m/s within 300 m, 20 origins by 40 destinations (seed 42). Counts are origin-destination pairs reachable under each policy. Timetable data only; not checked against real trips.

| Feed | Mean width | Nominal 95% crossed interval | n | Optimistic | Pessimistic | Schedule-only |
|------|-----------:|:----------------------------|--:|-----------:|------------:|--------------:|
| ttc | 0.00000 | [0.00000, 0.00000] | 800 | 50 | 50 | 330 |
| calgary | 0.28500 | [0.19500, 0.40000] | 800 | 228 | 0 | 228 |
| edmonton | 0.13625 | [0.08375, 0.20000] | 800 | 190 | 81 | 190 |
<!-- GENERATED RESULTS END -->
