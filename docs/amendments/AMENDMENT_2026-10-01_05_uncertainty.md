# Amendment 2026-10-01 05: uncertainty

Repair-round label: 2026-10-01, requested by the maintainer.

Results had already been seen before this amendment. No independent freeze chronology is claimed. The preregistration body and its separate hash file remain unchanged.

## Change and reason

Resolve accessibility using all parent rows before restricting sampling candidates. Sample origins within known/unknown strata with the existing quota allocation and destinations uniformly without replacement. Fill a depleted stratum from the other pool. The estimand is the quota-mixture mean policy width over independently sampled origins and destinations, conditional on this feed snapshot, service date and routing configuration, excluding self pairs. It is not a population-weighted whole-agency mean. The reported ratio of total width to non-self crossed pairs estimates this design-specific mean. Replace independent OD-row resampling with a crossed bootstrap: resample origins with replacement within each observed stratum, preserving its sample size, and independently resample destinations with replacement; share multiplicities across all their OD cells, exclude self pairs, and recompute the ratio. Report 1,000 seeded percentile replicates as nominal 95% empirical intervals, without finite-population correction or a certified finite-sample coverage claim. Shared network structure is conditioned on, not a resampled independent unit. Service dates and seed remain unchanged.

Reason: independent verification Finding 5; see [repair report](../milestones/FIX_REPORT_2026-09-30.md) and regression evidence in `docs/repair_logs/`.

## Public method sources

- [GTFS schedule reference](https://gtfs.org/documentation/schedule/reference/), for wheelchair fields and parent station semantics.
- [Owen, The pigeonhole bootstrap](https://arxiv.org/abs/0712.1111), for crossed row and column resampling. This repair adds origin-stratum quota preservation; it does not claim a theorem for this finite transit sampling design.
