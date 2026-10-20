# transit-access-audit

How much does missing wheelchair-accessibility data change where a rider can get to by transit? For 800 sampled origin and destination pairs (08:30 departures, trips of up to 60 minutes with up to 2 transfers), Calgary's feed, with 6,220 stops and 62,862 trips whose wheelchair fields are unknown, gives 228 reachable pairs if every unknown counts as accessible and none if none does. Edmonton's gives 190 against 81. Toronto's TTC feed has no unknown fields, so both policies give 50. The full corrected results are in [RESULTS.md](RESULTS.md).

transit-access-audit is an open-source toolkit by **TransitX Labs Inc.** for auditing Canadian GTFS feeds and measuring these bounds. It is a research prototype: it has not been checked against real trips, no transit agency uses it, and its results describe timetable data under stated assumptions, not whether a stop or trip is accessible in practice.

## How it relates to other tools

| Compared to | They provide | This project offers |
|-------------|--------------|-------------------|
| [MobilityData GTFS Validator](https://github.com/MobilityData/gtfs-validator) | Schema and best-practice validation | Optimistic/pessimistic routing bounds and verification ranking ([RESULTS.md](RESULTS.md)) |
| [OpenTripPlanner accessibility](https://docs.opentripplanner.org/en/dev-2.x/Accessibility/) | Single-scenario unknown-cost routing | Explicit bound pair plus interval width metrics on a sampled OD set |
| [r5py](https://github.com/r5py/r5py) | Street-network multimodal routing | Accessibility-unknown policy analysis on GTFS schedules without treating unknowns silently |
| [Wessel and Farber 2019](https://doi.org/10.5198/jtlu.2019.1502) | Schedule vs observed accessibility accuracy | Unknown-field policy bounds rather than timetable fidelity alone |
| Existing audit checks (v0.1) | Coverage and equity diagnostics | Decision-impact bounds linked to missing `wheelchair_*` fields |

## Open by design

**Open for inspection and reuse.** The code, method documentation and synthetic examples are under [Apache-2.0](LICENSE), and the results carry the parameters, sampled pairs and provenance needed to check them. The retained public GTFS snapshots remain their publishers' information under the terms in [DATA_LICENSES.md](DATA_LICENSES.md), with source records beside the [snapshots](data/snapshots/README.md); no publisher endorsement is implied.

## Quick start

```bash
python -m pip install -e ".[geo,dev]"
transit-audit --help

# Feed audit
transit-audit audit tests/fixtures/minimal_valid.zip \
  --census tests/fixtures/census_tiny.gpkg \
  --config examples/audit.yml \
  --output-dir audit-output

# Accessibility routing bounds
transit-audit bounds tests/fixtures/bounds_route.zip \
  --service-date 2024-06-03 --departure-time 07:00:00 --output bounds-results.json
```

## Routing bounds

Unknown GTFS wheelchair fields should not silently become accessible or inaccessible. The `bounds` command computes:

- optimistic reachability (unknown = accessible)
- pessimistic reachability (unknown = not accessible)
- interval width per origin-destination pair
- ranked verification targets for missing fields

Reproduce evaluation (Calgary primary, TTC null check):

```bash
python scripts/regenerate_publication.py
```

Install dependencies with `python -m pip install -e ".[geo,dev,docs]"` and prepare Java plus the digest-pinned JAR as described in [vendor/README.md](vendor/README.md). The regeneration command uses the [retained, licensed snapshots](data/snapshots/README.md); it does not depend on mutable feed URLs. It regenerates the demo JSON, HTML, backlog exports and digest manifest, then the real-feed evaluation, tables and figure. Production ranking covers a time-selected subset; skipped impact is unknown. Memory stops apply only to complete sampled observations, not certified peaks. See [publication correction](docs/amendments/AMENDMENT_2026-10-01_06_publication.md).

Corrected results below supersede the previous routing headline.

See [RESULTS.md](RESULTS.md) and [docs/routing-bounds.md](docs/routing-bounds.md).

## CLI reference

| Command | Description |
|---------|-------------|
| `transit-audit audit <feed.zip>` | Full accessibility and service audit |
| `transit-audit bounds <feed.zip>` | Optimistic/pessimistic routing bounds |
| `transit-audit validate <feed.zip>` | MobilityData validator bridge |
| `transit-audit checks list` | Check and metric catalogue |
| `transit-audit report <results.json>` | Render HTML from saved JSON |

## Limitations

- Bounds use schedule connectivity, not observed vehicle operations or street walking paths.
- Results report data and timetable assumptions; they do not determine legal accessibility compliance.
- Proximity metrics use geodesic buffers, not pedestrian network routing.
- MobilityData validator integration requires Java plus a pinned JAR in `vendor/`.

## Development

```bash
ruff check src tests scripts
mypy src
pyright
pytest -m "not network"
python -m build
```

## Licence

Apache-2.0. See [LICENSE](LICENSE). Demonstration data licences in [DATA_LICENSES.md](DATA_LICENSES.md).

<!-- GENERATED RESULTS START -->
Conditions: schedule-based reachability on the retained GTFS snapshots (service dates: ttc 2026-10-07, calgary 2026-09-30, edmonton 2026-09-30); departures at 08:30:00, trips of at most 60 minutes with at most 2 transfers (5-minute minimum), walking at 1.4 m/s within 300 m, 20 origins by 40 destinations (seed 42). Counts are origin-destination pairs reachable under each policy. Timetable data only; not checked against real trips.

| Feed | Mean width | Nominal 95% crossed interval | n | Optimistic | Pessimistic | Schedule-only |
|------|-----------:|:----------------------------|--:|-----------:|------------:|--------------:|
| ttc | 0.00000 | [0.00000, 0.00000] | 800 | 50 | 50 | 330 |
| calgary | 0.28500 | [0.19500, 0.40000] | 800 | 228 | 0 | 228 |
| edmonton | 0.13625 | [0.08375, 0.20000] | 800 | 190 | 81 | 190 |
<!-- GENERATED RESULTS END -->
