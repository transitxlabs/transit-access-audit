# Changelog

## 0.1.0 — 2026-09-28

Initial public release.

### GTFS correctness

- Date-aware service selection via `calendar.txt` and `calendar_dates.txt` with configurable `service_date`
- `frequencies.txt` expansion for departure-based metrics
- `SERVICE.BAND_SPAN` (band-limited) and `SERVICE.DAILY_SPAN` (full active day) replace ambiguous span metric
- Documented reference-stop aggregation when `reference_stop_id` is omitted
- `wheelchair_boarding` parent-station inheritance with raw and resolved coverage reporting
- Directed pathway reachability from entrances to platforms with field validation
- Required-file checks include `agency.txt` and calendar/calendar_dates rule

### Census and equity

- Areal-weighted population in catchment buffers (uniform density assumption); optional `population_points` mode
- Reject census layers without CRS unless `census_crs` is configured; record CRS in provenance
- Equity metrics require exactly one reference group; zero-population groups return `value=None` with reason
- Equity outputs labeled as descriptive associations only

### Safety

- ZIP resource limits (member count, uncompressed size, per-member size, compression ratio)
- MobilityData validator subprocess timeout and bounded output
- Audit output writes to timestamped run subdirectories; `--force-clean` only on exporter-owned directories

### Tooling

- CLI `transit-audit` with `audit`, `validate`, `checks list`, and `report` commands
- Optional MobilityData validator report ingestion
- Versioned JSON results, accessible HTML report, prioritized backlog exports
- Synthetic test fixtures, ≥90% coverage, ruff/mypy/pyright clean
- `pytest-cov` in dev extras for `pytest -q` in fresh environments
