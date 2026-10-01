# Routing bounds

## Problem

Missing GTFS wheelchair fields force a policy choice. Reporting only completeness hides routing consequences.

## Commands

```bash
# Synthetic demo
transit-audit bounds tests/fixtures/bounds_route.zip \
  --service-date 2024-06-03 \
  --departure-time 07:00:00 \
  --origin-count 5 \
  --destination-count 5

# TTC evaluation (after fetch)
python scripts/fetch_gtfs.py ttc
transit-audit bounds .cache/gtfs/ttc_completegtfs.zip \
  --service-date 2026-10-07 --departure-time 08:30:00 --output bounds-results.json
```

## Policies

| Policy | Unknown wheelchair fields |
|--------|---------------------------|
| Optimistic | Treated as accessible |
| Pessimistic | Treated as inaccessible |
| Schedule-only baseline | Wheelchair fields ignored (connectivity upper bound) |

## Metrics

- **Interval width:** optimistic reachable minus pessimistic reachable (per OD pair)
- **Verification targets:** exact counterfactual recomputation for a time-selected subset of unknown fields. Rank only among evaluated fields; skipped impact is unknown. Report accessible and inaccessible outcomes separately. The 600 s Calgary and 1,800 s Edmonton limits are soft candidate-start budgets; a running candidate can exceed them. See [ranking implementation](https://github.com/transitxlabs/transit-access-audit/blob/main/src/transit_audit/routing/bounds.py) and [post-result correction](amendments/AMENDMENT_2026-10-01_06_publication.md).

## Limitations

Schedule-based reachability only. See [results](results.md) and [technical report](technical-report.md).

Walking closure uses no transit-leg rounds. A maximum of k transfers allows k+1 transit legs. The origin walk precedes the first boarding; later boardings charge transfer slack once, plus walking time. Walking-only stops must satisfy the policy. The conservative trip rule requires all trip stops to satisfy the policy.

Uncertainty resamples origins within resolved accessibility strata and destinations independently, carrying each draw across its crossed OD cells. See [the post-result amendment](amendments/AMENDMENT_2026-10-01_05_uncertainty.md) and [Owen](https://arxiv.org/abs/0712.1111). Field semantics follow the [GTFS reference](https://gtfs.org/documentation/schedule/reference/).
