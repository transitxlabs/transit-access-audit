> Withdrawn historical evidence (2026-09-30). Retained for traceability; see [FIX_REPORT_2026-09-30.md](FIX_REPORT_2026-09-30.md) and regenerated [results](../results.md).

> Withdrawn historical evidence (2026-09-30). Retained for traceability; see [FIX_REPORT_2026-09-30.md](FIX_REPORT_2026-09-30.md) and regenerated [results](../results.md).

# M2 report: implementation on real public data

Date: 2026-09-30  
Gate: **PASS**

## Implementation summary

Added `transit_audit.routing` package:

| Module | Role |
|--------|------|
| `policy.py` | Unknown field policies |
| `accessibility.py` | Stop/trip wheelchair resolution |
| `index.py` | Accessibility-filtered schedule index |
| `reachability.py` | Transfer-aware reachability search |
| `bounds.py` | Bound computation and verification ranking |
| `sample.py` | Bounded OD sampling |

CLI command: `transit-audit bounds <feed.zip>`

Scripts:

- `scripts/fetch_gtfs.py ttc` downloads Open Toronto feed to `.cache/gtfs/`
- `scripts/run_bounds_evaluation.py` runs preregistered evaluation

## Real data smoke test

Synthetic fixture `tests/fixtures/bounds_route.zip` produces mean interval width 0.15 (seed 0, 5x5 sample).

TTC feed loads with evaluation ZIP limits and selective table reads (`stops`, `trips`, `stop_times`, `calendar`, `calendar_dates`).

## Engineering evidence

- 101 tests passing (network test opt-in)
- Library coverage 90.12%
- ruff, mypy, pyright clean on `src/`

## Gate outcome

Core method runs on real public data path. M3 evaluation permitted.
