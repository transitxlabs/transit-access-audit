> **Resource assertion superseded 2026-10-01.** Missing peak observations do not establish that a run stayed below a memory limit. Use [current timing and availability](../results.md) and [the publication correction](../amendments/AMENDMENT_2026-10-01_06_publication.md).

> Withdrawn historical evidence (2026-09-30). Retained for traceability; see [FIX_REPORT_2026-09-30.md](FIX_REPORT_2026-09-30.md) and regenerated [results](../results.md).

# Phase 2 report: independent verification fixes

Date: 2026-09-30  
Project: F8 accessibility-unknown routing bounds

## Summary

Phase 2 corrected GTFS wheelchair semantics, replaced the duplicate exclude baseline, implemented walking transfers and exact verification ranking on fixtures, re-ran evaluation on Calgary (primary), Edmonton, and TTC (null), restored preregistration integrity, and regenerated `RESULTS.md` from code.

Headline after fixes: **Calgary mean interval width 0.00625** (95% CI 0.001 to 0.013) on **800** sampled OD pairs; **TTC width 0.0** (fully coded).

## Item checklist

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | GTFS code mapping (`0`/empty unknown, `1` accessible, `2` not) | Done | `src/transit_audit/routing/policy.py`, `src/transit_audit/checks/access.py`, `tests/test_routing_bounds.py` (`test_wheelchair_category_matches_gtfs_spec`) |
| 2 | Real feeds with unknown fields; TTC null | Done | Calgary/Edmonton in `scripts/fetch_gtfs.py`; `RESULTS.md` headline and null section |
| 3 | Verification ranking by recomputed interval change | Done | `src/transit_audit/routing/bounds.py` `rank_verification_targets`; `tests/test_routing_bounds.py` fixture exact test |
| 4 | Exclude baseline replaced | Done | `UnknownPolicy.SCHEDULE_ONLY` in `src/transit_audit/routing/models.py`; removed duplicate exclude |
| 5 | Walking transfers + sensitivity | Done | `src/transit_audit/routing/walking.py`; `RESULTS.md` walk sensitivity table |
| 6 | MobilityData GTFS Validator baseline | Done | `vendor/gtfs-validator-6.0.0-cli.jar`; `docs/bounds_eval/evaluation.json` validator blocks |
| 7 | Preregistration integrity | Done | Phase 1 hash `docs/PREREGISTRATION.sha256`; phase 2 `docs/PREREGISTRATION.md` SHA `b9b793b7...` |
| 8 | Citation fixes | Done | `docs/technical-report.md`, `RESULTS.md`, `docs/milestones/M0_REPORT.md` (Wessel 2019 DOI; Oh et al. 2017) |
| 9 | M0 prior art without unverified synthesis | Done | `docs/milestones/M0_REPORT.md` |
| 10 | Correct wrong numbers | Done | 800 OD pairs, schedule-only baseline counts, fixture `--departure-time 07:00:00`, H1-H3 in technical report |
| 11 | Hygiene (ruff, mypy, pyright, mkdocs, coverage, LICENSE, versions) | Done | Commands below |

## Commands (evidence)

```bash
cd transit-access-audit
python -m pip install -e ".[geo,dev]"
.venv/bin/ruff check src tests
.venv/bin/mypy src
.venv/bin/pyright
.venv/bin/pytest -q
MPLCONFIGDIR=/tmp/mpl .venv/bin/mkdocs build --strict
python scripts/run_bounds_evaluation.py --include-ttc --feeds calgary edmonton --sensitivity --walk-sensitivity
```

## Measured results (from `docs/bounds_eval/evaluation.json`)

| Feed | Mean width | 95% CI | OD pairs | Opt / Pess / Schedule-only reachable |
|------|----------:|--------|--------:|-------------------------------------:|
| Calgary (primary) | 0.00625 | [0.001, 0.013] | 800 | 5 / 0 / 74 |
| TTC (null) | 0.0 | [0, 0] | 800 | 4 / 4 / 196 |
| Edmonton | 0.0 | [0, 0] | 800 | 3 / 3 / 97 |

Verification fixture (`bounds_route.zip`): stop S1 `wheelchair_boarding` interval-width change **0.200**, 4 affected OD pairs.

## GTFS Validator (does / does not catch)

| Feed | Notices | Errors | Catches wheelchair gaps? |
|------|--------:|-------:|--------------------------|
| TTC | 13 | 1 | No |
| Calgary | 12 | 0 | No |
| Edmonton | 6 | 0 | No |

Validator reports schema, geometry, and referential issues (sample codes in JSON). It does **not** quantify optimistic/pessimistic routing impact.

## Runtime and memory

| Step | Duration |
|------|----------|
| Full evaluation (3 feeds, sensitivities, validators) | ~425 s |
| Calgary primary bounds | ~13 s |
| TTC null check | ~79 s |
| Edmonton bounds | ~34 s |

Peak RSS was not captured reliably in the evaluation script (`peak_memory_mb` null). Calgary primary slice stayed well under the 12 GB watchdog limit during development.

## Test and lint outcomes

| Check | Result |
|-------|--------|
| pytest | 118 passed, 1 deselected (network) |
| Coverage | 90.20% |
| ruff | clean |
| mypy | clean |
| pyright | clean |
| mkdocs `--strict` | clean |

## Deviations

| Item | Note |
|------|------|
| Calgary OD sample | Phase 2 initial run sampled 400 pairs due to origin stratification bug when all stops are unknown; fixed in `sample.py` and re-run |
| Verification ranking on Calgary | Batch eval keeps `rank_verification=False` for runtime; exact ranking on fixture only |
| Validator JAR | Not committed (39 MB); download via `vendor/README.md` |
| Phase 1 preregistration | Archived hash only in `docs/PREREGISTRATION.sha256`; body was edited post-hoc in phase 1 (logged in `RESULTS.md`) |

## Files touched (principal)

- Routing: `src/transit_audit/routing/{policy,accessibility,bounds,sample,walking,index,reachability,models}.py`
- Checks: `src/transit_audit/checks/access.py`
- Validator: `src/transit_audit/validator/mobilitydata.py`
- Evaluation: `scripts/run_bounds_evaluation.py`, `scripts/fetch_gtfs.py`
- Results: `RESULTS.md`, `docs/results.md`, `docs/bounds_eval/evaluation.json`, `docs/figures/interval_width_hist.png`
- Docs: `docs/PREREGISTRATION.md`, `docs/technical-report.md`, `README.md`, `CHANGELOG.md`, `DATA_LICENSES.md`, `LICENSE`
