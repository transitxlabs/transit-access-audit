# Methodology

## Proximity coverage

Population within configurable buffer distances (default 400, 500, 800 m) of stops using a projected CRS (default EPSG:3347, Statistics Canada Lambert).

**Population weighting (default: areal weight):** for each census polygon intersecting a stop buffer, the counted population is `population × (intersection area ÷ polygon area)`, assuming uniform population density within the polygon. This avoids counting an entire polygon when only a sliver touches the buffer.

**Alternative:** set `population_method: population_points` in the audit config to count whole polygons on binary intersection (legacy behaviour).

Layers without a CRS are rejected unless `census_crs` is set in the config. Source and target CRS are recorded in metric metadata and provenance.

Label: **proximity coverage** (informed by [StatCan SDG table 23-10-0314](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2310031401)). Not walk accessibility.

## Service metrics

Frequency and span metrics use a configured `service_date` (default: first Monday in June 2024). Active `service_id`s are computed from `calendar.txt` and `calendar_dates.txt` (additions and removals). `frequencies.txt` rows expand into departure times (including past-midnight end times).

- `SERVICE.BAND_SPAN`: first-to-last departure within a configured time band at a reference stop (or aggregated across stops per `reference_stop_aggregation`).
- `SERVICE.DAILY_SPAN`: first-to-last departure across the full active service day.
- `SERVICE.DEPARTURES_PER_HOUR`, `SERVICE.MAX_GAP`, `SERVICE.MEDIAN_HEADWAY`: band-limited headway metrics.

Informed by [TCQSM 3rd edition](https://nap.nationalacademies.org/catalog/24766/transit-capacity-and-quality-of-service-manual-third-edition). Scheduled headways are **scheduled regularity**, not operational reliability.

## Equity diagnostics

`EQUITY.COVERAGE_GAP` compares group vs reference **proximity coverage shares** within a threshold. Results are **descriptive associations** only: not causal, not legal compliance, not statutory limits. Requires exactly one reference group; undefined when a group has zero population.

Informed by [StatCan spatial access](https://www150.statcan.gc.ca/n1/pub/18-001-x/18-001-x2024005-eng.htm).

## Accessibility data coverage

Wheelchair checks resolve `wheelchair_boarding` with `parent_station` inheritance (empty or unknown child values inherit the parent station). Pathway checks validate `pathway_mode`, `traversal_time`, `is_bidirectional`, and stop references; connectivity uses a **directed** graph for reachability from entrances to platforms.

These checks reflect GTFS field completeness and pathway graph structure; they do not assess physical compliance.
