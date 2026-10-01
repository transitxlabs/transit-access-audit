# Documentation

Transit-access-audit measures GTFS accessibility data quality and routing uncertainty.

## Guides

- [Routing bounds](routing-bounds.md)
- [Methodology](methodology.md)
- [CLI reference](cli.md)
- [Results](results.md)
- [Technical report](technical-report.md)

## Quick start

```bash
pip install -e ".[geo,dev]"
transit-audit bounds tests/fixtures/bounds_route.zip --service-date 2024-06-03
transit-audit audit tests/fixtures/minimal_valid.zip --output-dir audit-output
```

## Concepts

**Interval width:** difference between optimistic and pessimistic reachability for an OD pair.

**Verification target:** unknown wheelchair field that changes policy-filtered trips, ranked by exact best-case mean interval-width reduction, with both verification outcomes reported.

See the repository README for licence and limitation notes.

<!-- GENERATED RESULTS START -->
| Feed | Mean width | Nominal 95% crossed interval | n | Optimistic | Pessimistic | Schedule-only |
|------|-----------:|:----------------------------|--:|-----------:|------------:|--------------:|
| ttc | 0.00000 | [0.00000, 0.00000] | 800 | 50 | 50 | 330 |
| calgary | 0.28500 | [0.19500, 0.40000] | 800 | 228 | 0 | 228 |
| edmonton | 0.13625 | [0.08375, 0.20000] | 800 | 190 | 81 | 190 |
<!-- GENERATED RESULTS END -->
