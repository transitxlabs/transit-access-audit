# transit-access-audit

Open-source toolkit by **TransitX Labs Inc.** for auditing Canadian GTFS feeds and quantifying how unknown wheelchair-accessibility metadata affects schedule-based reachability bounds.

## What is new

| Compared to | They provide | This project adds |
|-------------|--------------|-------------------|
| [MobilityData GTFS Validator](https://github.com/MobilityData/gtfs-validator) | Schema and best-practice validation | Optimistic/pessimistic routing bounds and verification ranking ([RESULTS.md](RESULTS.md)) |
| [OpenTripPlanner accessibility](https://docs.opentripplanner.org/en/dev-2.x/Accessibility/) | Single-scenario unknown-cost routing | Explicit bound pair plus interval width metrics on a sampled OD set |
| [r5py](https://github.com/r5py/r5py) | Street-network multimodal routing | Accessibility-unknown policy analysis on GTFS schedules without treating unknowns silently |
| [Wessel and Farber 2019](https://doi.org/10.5198/jtlu.2019.1502) | Schedule vs observed accessibility accuracy | Unknown-field policy bounds rather than timetable fidelity alone |
| Existing audit checks (v0.1) | Coverage and equity diagnostics | Decision-impact bounds linked to missing `wheelchair_*` fields |

## Open by design

**Materials for inspection and reuse.** Project source, method documentation and synthetic examples are supplied under [Apache-2.0](LICENSE). Retained public inputs use the publisher terms recorded in [DATA_LICENSES.md](DATA_LICENSES.md). The results include the parameters, sampled pairs and recorded provenance needed to inspect this implementation.

**Project code and licensed inputs.** Project code and synthetic fixtures are provided under [Apache-2.0](LICENSE). Retained public GTFS snapshots remain the publishers' information and use their respective [licences and acknowledgements](DATA_LICENSES.md). The demo uses synthetic inputs; source and licence records accompany the [retained evaluation snapshots](data/snapshots/README.md). No publisher endorsement is implied.

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

## Routing bounds (flagship)

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
| Feed | Mean width | Nominal 95% crossed interval | n | Optimistic | Pessimistic | Schedule-only |
|------|-----------:|:----------------------------|--:|-----------:|------------:|--------------:|
| ttc | 0.00000 | [0.00000, 0.00000] | 800 | 50 | 50 | 330 |
| calgary | 0.28500 | [0.19500, 0.40000] | 800 | 228 | 0 | 228 |
| edmonton | 0.13625 | [0.08375, 0.20000] | 800 | 190 | 81 | 190 |
<!-- GENERATED RESULTS END -->
