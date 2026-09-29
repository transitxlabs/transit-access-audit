# Demonstration data licences

Verified 2026-09-28 against official publisher pages.

## BC Transit GTFS

- Source: [BC Transit Open Data](https://www.bctransit.com/open-data/)
- Terms: [BC Transit Open Data Terms of Use](https://www.bctransit.com/open-data/terms-of-use/)
- Licence summary: use, reproduce, and redistribute permitted with attribution; BC Transit retains intellectual property; no trademark use without permission.
- Attribution text: *Data provided by BC Transit. Used under the BC Transit Open Data Terms of Use.*
- Repository policy: do not commit raw feeds; use synthetic fixtures or maintainer-verified samples only.

## City of Toronto (TTC) GTFS

- Source: [Merged GTFS TTC Routes and Schedules](https://open.toronto.ca/dataset/merged-gtfs-ttc-routes-and-schedules/)
- Terms: [Open Government Licence – Toronto](https://open.toronto.ca/open-data-licence/)
- Licence summary: worldwide, royalty-free, perpetual licence to copy, modify, publish, and distribute with attribution; no endorsement implied.
- Attribution text: *Contains information licensed under the Open Government Licence – Toronto.*
- Repository policy: derived aggregated results preferred for demos; no raw feed committed without maintainer verification.

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
