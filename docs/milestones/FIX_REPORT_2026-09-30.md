> **Superseded in part 2026-10-01.** Historical ranking-disabled, exhaustive-production, zero-RSS and hard-memory-stop statements are not current guarantees. See [publication correction](../amendments/AMENDMENT_2026-10-01_06_publication.md). The dated record below is retained; this notice does not establish a freeze chronology.

# Fix report: independent verification 2026-09-30

Date: 2026-09-30. Scope: all twelve numbered findings from the local independent verification brief.

## Regenerated headline numbers (Calgary primary, 800 OD pairs)

| Metric | Value | 95% crossed bootstrap CI |
|--------|------:|--------------------------|
| Mean interval width | 0.2850 | [0.195, 0.400] |
| Optimistic reachable OD pairs | 228 | n/a |
| Pessimistic reachable OD pairs | 0 | n/a |
| Schedule-only reachable OD pairs | 228 | n/a |

Edmonton mean width 0.13625 (190 optimistic / 81 pessimistic). TTC null width 0.0 (50 / 50 optimistic/pessimistic; 330 schedule-only). Full wall time 388.9 s. Peak memory not captured (`top` unavailable in sandbox; RSS fallback returned 0).

Reproduce: `MPLBACKEND=Agg .venv/bin/python scripts/run_bounds_evaluation.py --include-ttc --feeds calgary edmonton --sensitivity --walk-sensitivity`

## Finding disposition

| # | Fix | Evidence |
|---|-----|----------|
| 1 | Restored transit trip retention (`index.py:96` starts trips allowed; all-stop policy check). | `test_f1_transit_only_independent_oracle`; regenerated Calgary optimistic trips > 0 in `docs/bounds_eval/evaluation.json` metadata. |
| 2 | Metric 3D chord grid walking (`walking.py:58`); reachability walking closure with policy checks and access-walk transfer accounting (`reachability.py`). | `test_f2_*` in `tests/test_hostile_routing_regressions.py`. |
| 3 | Overrides before parent resolution (`accessibility.py`); missing-column trip overrides. | `test_f3_nearest_parent_and_override`. |
| 4 | Exhaustive per-field ranking without usage cutoff (`bounds.py:323`); batch eval keeps `rank_verification=False` on large feeds. | `test_f4_*`; `test_ranking_matches_exhaustive_recomputation`. |
| 5 | Crossed origin/destination bootstrap with origin strata (`uncertainty.py`). | `test_f5_crossed_bootstrap_preserves_strata_and_clusters`; Calgary CI in `evaluation.json`. |
| 6 | Frozen preregistration hash enforced; post-result changes in `docs/PREREGISTRATION_AMENDMENT_2026-09-30.md`. | `test_preregistration_hash_enforced`; `_enforce_preregistration_hash()` in `scripts/run_bounds_evaluation.py:52`. |
| 7 | All tables from code via `render_corrected_results.py`; fixture row from `_fixture_verification_table()`. | `test_fixture_verification_table_from_code`; `RESULTS.md` regenerated. |
| 8 | Feed snapshots hashed; relative paths and OD keys in `docs/bounds_eval/evaluation.json`. | `feed_snapshot` and `od_pairs` keys per feed. |
| 9 | Streaming fetch with 500 MB cap (`fetch_gtfs.py`); memory stop at 12 GB via `_enforce_memory_limit`. | `test_fetch_gtfs_streams_with_limit`; timing block in `evaluation.json`. |
| 10 | Calgary/Edmonton licence URLs corrected in `DATA_LICENSES.md` and fetch manifests. | Publisher URLs in `DATA_LICENSES.md:16-24`. |
| 11 | Wessel citation corrected to two authors in `docs/technical-report.md`. | `test_wessel_citation_has_two_authors`. |
| 12 | Em dashes removed from public template; doc scan test. | `test_public_docs_have_no_em_dash`; `report.html.j2:25`. |

## Verification commands

```bash
.venv/bin/pytest -m "not network" --cov=transit_audit --cov-fail-under=90
.venv/bin/ruff check src tests scripts
.venv/bin/mypy src
.venv/bin/pyright
.venv/bin/mkdocs build --strict
```

Results at fix time: 149 passed, 91.9% coverage; all linters clean.

## Deviations

- H1/H2 support claims withdrawn until independently reviewed against regenerated numbers.
- Production verification ranking not run on Calgary/Edmonton batch (runtime budget); library API and fixture remain exhaustive.
- Peak compressed/swapped memory not measured when `top` is denied.
