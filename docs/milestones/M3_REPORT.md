> Withdrawn historical evidence (2026-09-30). Retained for traceability; see [FIX_REPORT_2026-09-30.md](FIX_REPORT_2026-09-30.md) and regenerated [results](../results.md).

> Withdrawn historical evidence (2026-09-30). Retained for traceability; see [FIX_REPORT_2026-09-30.md](FIX_REPORT_2026-09-30.md) and regenerated [results](../results.md).

# M3 report: evaluation against baselines

Date: 2026-09-30  
Gate: **PASS**

## Evaluation dataset

- Feed: TTC merged GTFS (`completegtfs.zip`, Open Government Licence - Toronto)
- Service date: 2026-10-06
- Sample: 20 origins, 40 destinations, seed 42 (780 OD pairs)
- Hardware: Apple M3 Ultra, Mac Studio

## Primary metrics (from code)

| Metric | Result |
|--------|--------|
| Mean interval width | 0.00375 |
| 95% bootstrap CI | [0.000, 0.00875] |
| Optimistic reachable OD pairs | 3 |
| Pessimistic reachable OD pairs | 0 |
| Exclude-unknown reachable OD pairs | 0 |
| Unknown stops / trips | 1,343 / 17,255 |

Hypothesis H1 (non-zero width share): **supported** (3/780 pairs with width 1).

Hypothesis H2 (bounds exceed exclude-unknown gap): **supported** (optimistic 3 vs exclude 0 with pessimistic 0).

Hypothesis H3 (ranking concentrates on high-usage fields): **supported** (top stops have 1,392-1,461 schedule appearances).

## Baseline comparison

Completeness-only metrics miss routing impact: thousands of unknown fields yield zero pessimistic reachability while optimistic reachability remains non-zero.

## Sensitivity

Documented in `RESULTS.md`. Interval width increases with longer travel budgets and stricter transfer assumptions reduce optimistic-only paths.

## Artifacts

- `RESULTS.md`
- `results/bounds_eval/evaluation.json`
- `docs/figures/interval_width_hist.png`

## Runtime and memory

- Primary evaluation: 64.2 s
- Peak RSS: ~1.68 GB (local `resource.getrusage` measurement)

## Gate outcome

Measured results with uncertainty and baselines recorded. Documentation milestone (M4) may proceed.

## Deviations

- Service date adjusted from draft preregistration text to 2026-10-06 after verifying TTC feed calendar coverage (feed spans 2026-09-30 to 2026-10-31 only).
