> **Superseded in part 2026-10-01.** Historical ranking-disabled, exhaustive-production, zero-RSS and hard-memory-stop statements are not current guarantees. See [publication correction](AMENDMENT_2026-10-01_06_publication.md). The dated record below is retained; this notice does not establish a freeze chronology.

# Amendment 2026-10-01 04: ranking

Repair-round label: 2026-10-01.

Results had already been seen before this amendment. No independent freeze chronology is claimed. The preregistration body and its separate hash file remain unchanged.

## Change and reason

Consider every unknown stop and trip field on the sampled OD pairs through exhaustive single-field recomputation. Remove usage cutoffs. Keep the same walking graph in both counterfactual outcomes. Enable time-budgeted ranking in each production primary run (Calgary 600 s, Edmonton 1800 s), prioritising sampled origins, destinations and their trip neighbours before remaining unknown fields. Rank by best-case mean width reduction, the larger of the accessible and inaccessible outcome reductions; report both outcomes separately. This quantity is not expected value without outcome probabilities. The output limit restricts presentation only. Serialise candidates total, evaluated, skipped, positive targets and measured runtime; never convert skipped evaluation into zero impact.

Reason: internal review finding 4.

## Public method sources

- [GTFS schedule reference](https://gtfs.org/documentation/schedule/reference/), for wheelchair fields and parent station semantics.
