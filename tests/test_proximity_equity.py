from pathlib import Path

from transit_audit.config import AuditConfig, EquityGroupConfig
from transit_audit.engine import run_audit
from transit_audit.geo.census import load_census_geopackage
from transit_audit.gtfs.reader import read_gtfs_zip
from transit_audit.metrics.equity import run_equity_metrics
from transit_audit.metrics.proximity import run_proximity_metrics

FIXTURES = Path(__file__).parent / "fixtures"


def test_proximity_empty_stops() -> None:
    from pathlib import Path

    import pandas as pd

    from transit_audit.gtfs.reader import GtfsFeed

    census = load_census_geopackage(FIXTURES / "census_tiny.gpkg")
    empty_feed = GtfsFeed(path=Path("empty.zip"), tables={"stops": pd.DataFrame()})
    metrics = run_proximity_metrics(empty_feed, census, AuditConfig())
    assert metrics == []


def test_proximity_exact_percentage() -> None:
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    census = load_census_geopackage(FIXTURES / "census_tiny.gpkg")
    config = AuditConfig(default_proximity_m=500, proximity_thresholds_m=[500])
    metrics = run_proximity_metrics(feed, census, config)
    metric = next(m for m in metrics if m.metric_id == "PROXIMITY.POPULATION_WITHIN_500M")
    assert metric.value is not None
    assert 0 < float(metric.value) < 100
    assert metric.metadata["metric_type"] == "proximity_coverage"
    assert metric.metadata["population_method"] == "areal_weight"


def test_equity_coverage_gap() -> None:
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    census = load_census_geopackage(FIXTURES / "census_tiny.gpkg")
    config = AuditConfig(
        default_proximity_m=500,
        equity_groups=[
            EquityGroupConfig(name="ref", attribute="group_code", value="ref", reference=True),
            EquityGroupConfig(name="low", attribute="group_code", value="low"),
        ],
    )
    metrics = run_equity_metrics(feed, census, config)
    assert any(m.metric_id == "EQUITY.COVERAGE_GAP" for m in metrics)


def test_full_audit_with_attributions(tmp_path: Path) -> None:
    config = tmp_path / "audit.yml"
    config.write_text(
        "proximity_thresholds_m: [500]\n"
        "data_attributions:\n"
        "  - publisher: Test Agency\n"
        "    text: Sample attribution\n",
        encoding="utf-8",
    )
    result = run_audit(
        feed_path=FIXTURES / "minimal_valid.zip",
        config_path=config,
        census_path=FIXTURES / "census_tiny.gpkg",
    )
    assert result.provenance.extra.get("data_attributions")


def test_full_audit_with_census(tmp_path: Path) -> None:
    config = tmp_path / "audit.yml"
    config.write_text(
        "proximity_thresholds_m: [500]\n"
        "default_proximity_m: 500\n"
        "equity_groups:\n"
        "  - {name: reference, attribute: group_code, value: ref, reference: true}\n"
        "  - {name: low, attribute: group_code, value: low}\n",
        encoding="utf-8",
    )
    result = run_audit(
        feed_path=FIXTURES / "minimal_valid.zip",
        config_path=config,
        census_path=FIXTURES / "census_tiny.gpkg",
    )
    assert result.provenance.crs_epsg == 3347
    assert result.summary.metric_count > 0
