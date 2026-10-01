> **Memory guarantee superseded 2026-10-01.** The monitor supports sampled observations with explicit availability, not a certified peak or hard cap. See [publication correction](../amendments/AMENDMENT_2026-10-01_06_publication.md). This historical report is retained.

# Fix report: independent re-verification 2026-10-01

Date: 2026-10-01. Scope: seven required fixes from the 2026-09-30 re-verification verdict.

## Regenerated headline numbers (Calgary primary, 800 OD pairs)

| Metric | Value | Nominal 95% crossed bootstrap CI |
|--------|------:|----------------------------------|
| Mean interval width | 0.28500 | [0.19500, 0.40000] |
| Optimistic reachable OD pairs | 228 | n/a |
| Pessimistic reachable OD pairs | 0 | n/a |
| Schedule-only reachable OD pairs | 228 | n/a |

Edmonton mean width 0.13625 (190 optimistic / 81 pessimistic). Top evaluated verification target: stop 4790, best-case reduction 0.02125. TTC null width 0.0 (50 / 50 optimistic/pessimistic; 330 schedule-only). Full wall time 2787.2 s. Peak process-tree memory unavailable (`top` denied; recorded as null, not zero).

Reproduce:

```bash
MPLBACKEND=Agg .venv/bin/python scripts/run_bounds_evaluation.py --include-ttc --feeds calgary edmonton --sensitivity --walk-sensitivity
```

## Fix disposition

| # | Fix | Evidence |
|---|-----|----------|
| 1 | Production ranking runs on Calgary and Edmonton with time budgets; outputs report evaluated/skipped counts and positive targets. Edmonton stop 4790 shows 0.02125 reduction. | `scripts/run_bounds_evaluation.py` `_run_production_ranking`; `docs/bounds_eval/evaluation.json` feeds.edmonton.verification_targets[0]; `test_edmonton_stop_4790_positive_reduction`; `test_edmonton_ranking_headline_from_evaluation_json` |
| 2 | Missing preregistration digest fails closed. Phase-2 hash enforced; phase-1 hash retained separately. | `scripts/run_bounds_evaluation.py:69-76`; `test_preregistration_missing_digest_rejected`; `test_preregistration_hash_enforced` |
| 3 | Frozen feed manifests required before evaluation; byte counts and SHA-256 enforced. | `docs/bounds_eval/frozen_feed_manifests.json`; `scripts/run_bounds_evaluation.py:89-118`; `test_missing_manifest_rejected`; `test_frozen_manifests_and_data_licences` |
| 4 | Process-tree memory monitor enforces 12 GB limit when measurable; unavailable measurements stay null. Java validator receives `-Xmx` cap. | `scripts/memory_monitor.py`; `scripts/run_bounds_evaluation.py`; `src/transit_audit/validator/mobilitydata.py`; `test_timing_peak_memory_null_not_zero_when_unavailable` |
| 5 | Calgary and Edmonton licence URLs, attributions and frozen snapshot records corrected. Wessel and Farber author names fixed. | `DATA_LICENSES.md`; `scripts/fetch_gtfs.py`; `docs/technical-report.md`; `test_frozen_manifests_and_data_licences`; `test_wessel_and_farber_authors_in_technical_report`; `test_wessel_citation_has_two_authors` |
| 6 | Ranking amendment, technical report, and M1 gate reconciled; superseded PASS records retained with dated notes. | `docs/amendments/AMENDMENT_2026-10-01_04_ranking.md`; `docs/milestones/M1_REPORT.md`; `docs/technical-report.md` sections 3.4, 5 and 6 |
| 7 | Demo HTML regenerated at version 0.3.0; release-surface hygiene scan covers tracked text files. Repair logs use repository-relative paths. | `examples/demo/report.html`; `tests/test_public_release_surface_hygiene`; `test_demo_report_regenerated_without_em_dash`; `docs/repair_logs/` path cleanup |

## Verification commands

```bash
.venv/bin/pytest -m "not network" --cov=transit_audit --cov-fail-under=90
.venv/bin/ruff check src tests scripts
.venv/bin/mypy src
.venv/bin/pyright
.venv/bin/mkdocs build --strict
```

Results at fix time: 158 passed (159 with optional slow real-feed check), 91.67% coverage; all linters clean; strict MkDocs clean.

## Deviations

- Production ranking is time-budgeted (Calgary 600 s, Edmonton 1800 s) rather than exhaustive over all unknown fields; skipped candidates are reported explicitly and never treated as zero impact.
- Peak compressed/swapped process-tree memory remained unavailable in this environment; JSON records null plus measurement status.
- H1/H2/H3 support claims remain withdrawn; regenerated numbers are exploratory under dated amendments.
