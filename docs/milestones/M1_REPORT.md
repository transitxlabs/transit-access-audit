> **Superseded 2026-10-01.** This gate record predates the phase-2 preregistration body now in `docs/PREREGISTRATION.md`. The archived phase-1 hash in `docs/PREREGISTRATION.sha256` does not match the current document. See [FIX_REPORT_2026-10-01.md](FIX_REPORT_2026-10-01.md) and dated amendments in `docs/amendments/`.

# M1 report: preregistration gate

Date: 2026-09-30  
Gate: **PASS (superseded)**

## Deliverable

- `docs/PREREGISTRATION.md` frozen with SHA-256 `c7d47f31f78f3d50c13f19324a845ed791b1392c18994fbed1cc41484fb400a0` (phase 1; body no longer present)

## Design decisions locked before implementation

| Decision | Choice |
|----------|--------|
| Router | Schedule-based GTFS reachability (accessibility-filtered trips and transfers) |
| Policy pair | Optimistic unknown=accessible vs pessimistic unknown=inaccessible |
| Baseline | Exclude-unknown policy (OTP-like default) |
| Primary feed | TTC merged GTFS via Open Toronto CKAN |
| Service date | 2026-10-07 ([Wednesday](https://www.timeanddate.com/calendar/monthly.html?year=2026&month=10&country=27); the earlier Tuesday label was incorrect) |
| Sample | 20 origins, 40 destinations, seed 42 |
| Metrics | Interval width, reachable OD counts, verification ranking, sensitivity grid |

## Review notes

Architecture review (local): bounds module separated from audit checks; evaluation uses raised ZIP limits only on explicit evaluation path; no raw GTFS committed.

## Gate outcome

Preregistration complete at the time of this report. Current evaluation uses the phase-2 preregistration body and separate dated amendments.
