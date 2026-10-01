# Amendment 2026-10-01 02: walking

Repair-round label: 2026-10-01, requested by the maintainer.

Results had already been seen before this amendment. No independent freeze chronology is claimed. The preregistration body and its separate hash file remain unchanged.

## Change and reason

Replace degree-grid walking search with a three-dimensional metric chord grid and exact haversine filtering. Walking closure occurs before each boarding round and consumes no transit legs. A maximum of k transfers permits k+1 transit legs. Transfer slack is charged once before a later boarding, in addition to walking time. Walking-only origins, intermediate stops and destinations must pass the stop policy. Retain the existing conservative rule requiring every stop on a transit trip to pass the policy, including pass-through stops; these are bounds for this declared rule, not all feasible on-street journeys.

Reason: independent verification Finding 2; see [repair report](../milestones/FIX_REPORT_2026-09-30.md) and regression evidence in `docs/repair_logs/`.

## Public method sources

- [GTFS schedule reference](https://gtfs.org/documentation/schedule/reference/), for wheelchair fields and parent station semantics.
