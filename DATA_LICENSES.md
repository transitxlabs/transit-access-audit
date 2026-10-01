# Demonstration data licences

Verified 2026-09-28 against official publisher pages.

## BC Transit GTFS

- Source: [BC Transit Open Data](https://www.bctransit.com/open-data/)
- Terms: [BC Transit Open Data Terms of Use](https://www.bctransit.com/open-data/terms-of-use/)
- Licence summary: use, reproduce, and redistribute permitted with attribution; BC Transit retains intellectual property; no trademark use without permission.
- Attribution text: *Data provided by BC Transit. Used under the BC Transit Open Data Terms of Use.*
- Repository policy: do not commit raw feeds; use synthetic fixtures or maintainer-verified samples only.

## City of Calgary (Calgary Transit GTFS)

- Source: [Calgary Transit GTFS Schedule Data](https://data.calgary.ca/Transportation-Transit/Calgary-Transit-Scheduling-Data/npk7-z3bj) (download endpoint: `https://data.calgary.ca/download/npk7-z3bj/application/zip`)
- Terms: [Open Government Licence - City of Calgary](https://data.calgary.ca/stories/s/u45n-7awa/)
- Licence summary: use and redistribution permitted with attribution; derivation allowed subject to acknowledgement.
- Attribution text: *Contains information licensed under the Open Government Licence – City of Calgary.*
- Repository policy: derived aggregated results in `docs/bounds_eval/`; verified frozen input retained under `data/snapshots/sha256/`; working copy in `.cache/gtfs/`. Frozen snapshot SHA-256 recorded in `docs/bounds_eval/frozen_feed_manifests.json`.

## City of Edmonton (Edmonton Transit GTFS)

- Source: `https://gtfs.edmonton.ca/TMGTFSRealTimeWebService/GTFS/gtfs.zip` (via `scripts/fetch_gtfs.py edmonton`; dataset metadata: [Edmonton GTFS dataset](https://data.edmonton.ca/api/views/4fvt-p2se.json))
- Terms: [Open Government Licence - Edmonton](https://data.edmonton.ca/stories/s/Open-Government-Licence-Edmonton/msh8-if28/)
- Licence summary: use permitted under Edmonton Open Government Licence v1.0 (July 2022) with attribution.
- Attribution text: *Contains information licensed under the Open Government Licence – City of Edmonton.*
- Repository policy: derived aggregated results in `docs/bounds_eval/`; verified frozen input retained under `data/snapshots/sha256/`; working copy in `.cache/gtfs/`. Frozen snapshot SHA-256 recorded in `docs/bounds_eval/frozen_feed_manifests.json`.

## City of Toronto (TTC) GTFS

- Source: [Merged GTFS TTC Routes and Schedules](https://open.toronto.ca/dataset/merged-gtfs-ttc-routes-and-schedules/)
- Direct download (verified 2026-09-30): CKAN resource `completegtfs.zip` (~84 MB compressed)
- Terms: [Open Government Licence – Toronto](https://open.toronto.ca/open-data-licence/)
- Licence summary: worldwide, royalty-free, perpetual licence to copy, modify, publish, and distribute with attribution; no endorsement implied.
- Attribution text: *Contains information licensed under the Open Government Licence – Toronto.*
- Repository policy: derived aggregated results preferred for demos; digest-verified evaluated input retained under `data/snapshots/sha256/` with publisher licence and acknowledgement. Local evaluation cache: `.cache/gtfs/` (gitignored).

## TransLink GTFS

- Source: [TransLink GTFS data](https://www.translink.ca/about-us/doing-business-with-translink/app-developer-resources/gtfs/gtfs-data)
- Terms: same page (GTFS-specific terms)
- Licence summary: limited, revocable, non-exclusive licence to use, reproduce, and redistribute with required legend; commercial use may require additional terms.
- Attribution text: *Route and arrival data used in this product or service is provided by permission of TransLink. TransLink assumes no responsibility for the accuracy or currency of the Data used in this product or service.*
- Repository policy: no raw feed committed without maintainer verification.

## Statistics Canada 2021 Census boundary files

- Source: [2021 Census Boundary Files guide (92-160-G)](https://www150.statcan.gc.ca/n1/pub/92-160-g/92-160-g2021001-eng.htm)
- Terms: [Statistics Canada Open Licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence)
- Licence summary: reproduce, publish, freely distribute, or sell with attribution.
- Attribution text: *Source: Statistics Canada, 2021 Census Boundary Files, 2021. Reproduced and distributed on an "as is" basis with the permission of Statistics Canada.*
- Derived products require adaptation notice (see licence FAQ).

## Synthetic fixtures in this repository

- `tests/fixtures/*.zip` and `tests/fixtures/census_tiny.gpkg` are synthetic and may be redistributed under the project Apache-2.0 licence.
- `examples/demo/` contains derived audit outputs from synthetic fixtures only.

## Report attribution fields

Configure publisher attributions in audit YAML under `data_attributions` (list of `publisher` and `text` keys). Generated HTML reports render these in the metrics section.

## Retained evaluation snapshots

Phase 5 retains only the three digest-verified evaluated GTFS snapshots under `data/snapshots/sha256/`. Each file has an adjacent acquisition and licence record, and its digest is required by `docs/bounds_eval/frozen_feed_manifests.json`. See [snapshot retrieval](data/snapshots/README.md). These bytes are distributable under the respective [Calgary terms (v2.1)](https://data.calgary.ca/stories/s/u45n-7awa/), [Edmonton terms (v1.0, July 2022)](https://data.edmonton.ca/stories/s/Open-Government-Licence-Edmonton/msh8-if28/) and [Toronto terms](https://open.toronto.ca/open-data-licence/) with the acknowledgements above. No publisher endorsement is claimed. Dataset-to-endpoint associations cite [Calgary metadata](https://data.calgary.ca/api/views/npk7-z3bj.json) and [Edmonton metadata](https://data.edmonton.ca/api/views/4fvt-p2se.json); these were verified in the independent review but could not be freshly fetched in this sandbox. Exact original acquisition timestamps are unavailable.
