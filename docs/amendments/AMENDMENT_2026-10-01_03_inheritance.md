# Amendment 2026-10-01 03: inheritance

Repair-round label: 2026-10-01, requested by the maintainer.

Results had already been seen before this amendment. No independent freeze chronology is claimed. The preregistration body and its separate hash file remain unchanged.

## Change and reason

Apply raw field overrides before stop resolution, inherit from the nearest coded ancestor, terminate cycles or missing parents as unknown, and honour trip and stop overrides when accessibility columns are absent.

Reason: independent verification Finding 3; see [repair report](../milestones/FIX_REPORT_2026-09-30.md) and regression evidence in `docs/repair_logs/`.

## Public method sources

- [GTFS schedule reference](https://gtfs.org/documentation/schedule/reference/), for wheelchair fields and parent station semantics.
