# Python API

Install the package in editable mode:

```bash
python -m pip install -e ".[geo,dev]"
```

## Audit engine

```python
from pathlib import Path
from transit_audit.config import AuditConfig
from transit_audit.engine import run_audit

result = run_audit(
    feed_path=Path("tests/fixtures/minimal_valid.zip"),
    config_path=Path("examples/audit.yml"),
    census_path=Path("tests/fixtures/census_tiny.gpkg"),
)
print(result.summary.error_count)
```

## Routing bounds

```python
from datetime import date
from pathlib import Path
from transit_audit.routing.bounds import compute_bounds
from transit_audit.routing.models import BoundsConfig

config = BoundsConfig(
    service_date=date(2024, 6, 3),
    departure_time="07:00:00",
    origin_count=5,
    destination_count=5,
)
result = compute_bounds(Path("tests/fixtures/bounds_route.zip"), config)
print(result.mean_interval_width)
print(result.verification_targets[0].interval_width_change)
```

## GTFS reader

```python
from transit_audit.gtfs.reader import read_gtfs_zip

feed = read_gtfs_zip("tests/fixtures/minimal_valid.zip")
stops = feed.table("stops")
```

## MobilityData validator bridge

```python
from pathlib import Path
from transit_audit.validator.mobilitydata import run_mobilitydata_validator, ingest_validator_report

report = run_mobilitydata_validator(Path("tests/fixtures/minimal_valid.zip"), Path(".validator-out"))
findings, provenance = ingest_validator_report(report)
```
