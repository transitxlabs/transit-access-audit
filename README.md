# transit-access-audit

Open-source toolkit by **TransitX Labs Inc.** for auditing Canadian GTFS feeds: accessibility data coverage, service metrics, proximity coverage, and equity diagnostics. The tool reports **data and standards conformance**; it does **not** determine legal accessibility compliance.

## Open by design

**We build in the open.** TransitX Labs Inc. publishes its tools, methods and learning materials under open licences, so public-interest teams can use them, check how they work and adapt them freely. Open work is easier to trust, because anyone can see exactly how a result is produced. Code is licensed under Apache-2.0.

**Our own work, and only ours.** Everything in this repository was created by TransitX Labs Inc. from public data and synthetic examples. It contains no client data, no client projects, and no one else's confidential information or intellectual property.

## Quick start

```bash
python -m pip install -e ".[geo,dev]"
transit-audit --help
transit-audit audit tests/fixtures/minimal_valid.zip \
  --census tests/fixtures/census_tiny.gpkg \
  --config examples/audit.yml \
  --output-dir audit-output
```

Outputs in `audit-output/`:

- `results.json`: schema version 1.0 machine-readable audit
- `report.html`: standalone accessible HTML report
- `backlog.json` / `backlog.csv`: prioritized remediation backlog

## CLI reference

| Command | Description |
|---------|-------------|
| `transit-audit audit <feed.zip>` | Run full audit (optional `--config`, `--census`, `--validator-report`) |
| `transit-audit validate <feed.zip>` | Run MobilityData validator when Java is available, or ingest `--report` |
| `transit-audit checks list` | List check/metric IDs and source URLs |
| `transit-audit report <results.json> -o report.html` | Render HTML from saved JSON |

Exit codes: `0` pass, `1` thresholds exceeded, `2` invalid args/config, `3` processing error.

## Metric and check catalogue

Checks are **informed by** GTFS, TCQSM, Statistics Canada spatial access guidance, and GTFS-Flex specifications. See `research/03_standards.md` and `transit-audit checks list`.

| Prefix | Examples |
|--------|----------|
| `GTFS.*` | Required files, FK integrity, calendar coverage |
| `ACCESS.*` | Wheelchair field completeness, pathway presence |
| `SERVICE.*` | Departures/hour, span, max gap |
| `PROXIMITY.*` | Population within 400/500/800 m (**proximity coverage**, not walk access) |
| `EQUITY.*` | Coverage gap vs reference group (configurable thresholds) |
| `FLEX.*` | Flexible service inventory and zone geometry |

## Limitations

- Proximity metrics use geodesic buffers, not pedestrian network routing.
- Equity metrics require analyst-supplied census attributes and configurable groups; they are not statutory compliance tests.
- MobilityData validator integration is optional and requires Java plus a pinned JAR in `vendor/`.
- Core checks run offline with no network dependency.

## Development

```bash
ruff check src tests
mypy src
pyright
pytest
python -m build
```

## Licence

Apache-2.0. See [LICENSE](LICENSE). Demonstration data licences in [DATA_LICENSES.md](DATA_LICENSES.md).
