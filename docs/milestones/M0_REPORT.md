# M0 report: novelty and data check

Date: 2026-09-30  
Project: F8 accessibility-unknown routing bounds  
Gate: **PASS (proceed)**

## Research question

When GTFS wheelchair fields are missing, planners and riders should not silently treat unknown stops or trips as either accessible or inaccessible. Can we compute optimistic and pessimistic schedule-based reachability bounds and rank missing fields by their effect on reachable destinations?

## Closest prior art (verified)

| Prior art | What it does | Gap relative to this project |
|-----------|--------------|------------------------------|
| [MobilityData GTFS Validator](https://github.com/MobilityData/gtfs-validator) | Schema and best-practice validation | Reports missing fields; does not quantify routing impact or bounds |
| [OpenTripPlanner accessibility](https://docs.opentripplanner.org/en/dev-2.x/Accessibility/) | Configurable `unknownCost` and `onlyConsiderAccessible` | Single-scenario routing, not explicit optimistic/pessimistic bounds or verification ranking |
| [r5py](https://github.com/r5py/r5py) | Multimodal routing on GTFS plus OSM | No built-in unknown-field bound analysis or value-of-verification ranking |
| [GTFS accessibility guidance](https://gtfs.org/getting-started/features/accessibility/) | Documents unknown semantics for `wheelchair_boarding` and `wheelchair_accessible` | Standards only; no decision-impact evaluation |
| [Wessel et al. 2019, JTLU](https://doi.org/10.5198/jtlu.2019.1502) | Schedule-based accessibility accuracy vs observed operations | Timetable fidelity, not unknown-field policy bounds |
| Oh et al. 2017 ([rosap.ntl.bts.gov/view/dot/34806](https://rosap.ntl.bts.gov/view/dot/34806/dot_34806_DS1.pdf)) | GTFS wheelchair analysis | Treats unknown/default cases ad hoc; no verification prioritization method found |

Direct repository and documentation searches (MobilityData, OpenTripPlanner, r5py, GTFS.org, JTLU DOI resolver) found no published open-source tool that combines:

1. explicit optimistic and pessimistic bounds for unknown GTFS wheelchair metadata,
2. bounded OD reachability intervals under schedule-based routing, and
3. ranking of missing fields by recomputed interval-width change.

OpenTripPlanner exposes sensitivity knobs, but not a reproducible bound pair plus verification ranking workflow aimed at agency data QA.

## Proposed contribution (verified in M3)

1. **Policy pair:** optimistic (unknown treated as accessible) vs pessimistic (unknown treated as inaccessible) on the same OD sample.
2. **Reachability interval width:** per OD pair, width = optimistic reachable minus pessimistic reachable.
3. **Value of verification:** rank unknown stops and trips by interval-width change when each field is verified.
4. **Baselines:** completeness counts, schedule-only connectivity, optimistic/pessimistic-only counts, and MobilityData GTFS Validator notices.

## Public data check

| Dataset | Verified source | Licence | Size | Usable |
|---------|-------------------|---------|------|--------|
| Calgary Transit GTFS | [City of Calgary Open Data](https://data.calgary.ca/Transportation-Transit/Calgary-Transit-Scheduling-Data/npk7-z3bj) | [Open Data terms](https://data.calgary.ca/stories/s/u45n-7awa/) | ~17 MB compressed (2026-09-30) | Yes (primary; missing wheelchair columns) |
| Edmonton Transit GTFS | `https://gtfs.edmonton.ca/TMGTFSRealTimeWebService/GTFS/gtfs.zip` | [Open Government Licence - Edmonton](https://data.edmonton.ca/stories/s/Open-Government-Licence-Edmonton/msh8-if28/) | 19,065,635 bytes compressed (2026-09-30) | Yes (partial unknown stops) |
| TTC merged GTFS | [Open Toronto CKAN API](https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=merged-gtfs-ttc-routes-and-schedules) | [Open Government Licence - Toronto](https://open.toronto.ca/open-data-licence/) | 84,337,545 bytes compressed (API, 2026-09-30) | Yes (null check; fully coded trips) |
| Synthetic fixtures | `tests/fixtures/bounds_route.zip` | Apache-2.0 | < 2 KB | Yes (tests and smoke evaluation) |

Schedule-based bounds are explicitly **not** observed journey accessibility.

## Novelty verdict

The combination of bound pair, interval width, and verification ranking on Canadian GTFS feeds is **defensible and not duplicated** by the nearest open tools checked above. Individual ingredients (GTFS wheelchair fields, schedule routing, completeness QA) are known; the integrated evaluation method is the contribution.

## Stop condition

Not triggered. Real public data exists under usable licences, and a distinct method is available.

## Evidence files

- This report
- `DATA_LICENSES.md`
- `scripts/fetch_gtfs.py`
