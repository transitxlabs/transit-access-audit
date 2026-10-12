> **Superseded in part 2026-10-01.** Historical ranking-disabled, exhaustive-production, zero-RSS and hard-memory-stop statements are not current guarantees. See [publication correction](amendments/AMENDMENT_2026-10-01_06_publication.md). The dated record below is retained; this notice does not establish a freeze chronology.

# Preregistration amendment (2026-09-30)

Results for phase 2 had already been computed before this amendment. The frozen prefix of `docs/PREREGISTRATION.md` and `docs/PREREGISTRATION.sha256` are unchanged.

## Changes after results were seen

| Item | Original preregistration text | Amendment |
|------|------------------------------|-----------|
| Service dates | "First Tuesday in feed calendar after download" | Fixed dates: Calgary and Edmonton 2026-09-30 (Wednesday); TTC 2026-10-07 (Wednesday). Tuesday wording was incorrect for these snapshots. |
| OD sample size | 800 pairs implied | Confirmed 800 pairs (20 origins x 40 destinations). Phase 2 report previously noted a 400-pair exploratory run; that run is historical only. |
| Uncertainty | Pairwise bootstrap over 800 OD rows | Crossed origin/destination bootstrap preserving unknown/known origin strata (see `transit_audit.routing.uncertainty`). |
| Verification ranking | Exact ranking language | Batch evaluation keeps `rank_verification=False` on large feeds; exhaustive ranking remains on fixtures and in library API. |
| Hypotheses H1-H3 | Stated before repair | Withdrawn pending regeneration after the routing repairs recorded in amendments 01 to 05 in `docs/amendments/`. |

## Chronology note

The phase 1 preregistration body is not present in this repository; only its SHA-256 is archived in `docs/PREREGISTRATION.sha256`. Phase 2 hash is self-recorded in `docs/PREREGISTRATION.md` and enforced at evaluation time by `scripts/run_bounds_evaluation.py`.
