import zipfile
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from transit_audit.checks.access import run_access_checks
from transit_audit.checks.gtfs import run_gtfs_checks
from transit_audit.config import AuditConfig, EquityGroupConfig
from transit_audit.geo.census import (
    load_census_geopackage,
    population_within_distance,
    stops_to_gdf,
)
from transit_audit.gtfs.reader import parse_hhmmss, read_gtfs_zip
from transit_audit.gtfs.zip_limits import ZipLimitExceededError, ZipLimits
from transit_audit.metrics.equity import run_equity_metrics
from transit_audit.output import EXPORTER_MARKER, is_exporter_owned, prepare_output_dir
from transit_audit.validator.mobilitydata import run_mobilitydata_validator

FIXTURES = Path(__file__).parent / "fixtures"


def test_wheelchair_parent_inheritance() -> None:
    feed = read_gtfs_zip(FIXTURES / "wheelchair_inheritance.zip")
    _, metrics = run_access_checks(feed, AuditConfig())
    metric = next(m for m in metrics if m.metric_id == "ACCESS.STOP.WHEELCHAIR.KNOWN")
    assert metric.metadata["raw_unknown_count"] == 2
    assert metric.metadata["resolved_unknown_count"] == 0
    assert metric.numerator == 3


def test_no_location_type_column_does_not_raise() -> None:
    feed = read_gtfs_zip(FIXTURES / "no_location_type.zip")
    findings, metrics = run_access_checks(feed, AuditConfig())
    assert any(m.metric_id == "ACCESS.STOP.WHEELCHAIR.KNOWN" for m in metrics)
    assert isinstance(findings, list)


def test_directed_pathway_findings() -> None:
    feed = read_gtfs_zip(FIXTURES / "directed_pathways.zip")
    findings, _ = run_access_checks(feed, AuditConfig())
    messages = {f.message for f in findings}
    assert any("one-way dead ends" in m for m in messages)


def test_malformed_coordinates_filtered() -> None:
    feed = read_gtfs_zip(FIXTURES / "malformed_coords.zip")
    gdf = stops_to_gdf(feed.table("stops"), 3347)
    assert len(gdf) == 1
    assert gdf.iloc[0]["stop_id"] == "S3"


def test_missing_crs_rejected_without_config(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no CRS"):
        load_census_geopackage(FIXTURES / "census_no_crs.gpkg")


def test_missing_crs_accepted_with_config() -> None:
    census = load_census_geopackage(
        FIXTURES / "census_no_crs.gpkg",
        census_crs="EPSG:4326",
    )
    assert census.source_crs == "EPSG:4326"


def test_areal_weighting_partial_overlap() -> None:
    census = load_census_geopackage(FIXTURES / "census_tiny.gpkg")
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    stops_gdf = stops_to_gdf(feed.table("stops"), census.epsg)
    covered, total, meta = population_within_distance(census, stops_gdf, 500.0)
    assert meta["population_method"] == "areal_weight"
    assert meta["weighting"] == "intersection_area_over_polygon_area"
    assert 0 < covered < total


def test_parse_hhmmss_rejects_invalid_components() -> None:
    assert parse_hhmmss("24:00:00") == 24 * 3600
    assert parse_hhmmss("25:30:00") == 25 * 3600 + 30 * 60
    with pytest.raises(ValueError, match="minutes"):
        parse_hhmmss("07:99:99")
    with pytest.raises(ValueError, match="negative"):
        parse_hhmmss("-1:00:00")


def test_zip_member_limit(tmp_path: Path) -> None:
    path = tmp_path / "many.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for i in range(5):
            archive.writestr(f"file{i}.txt", "x" * 10)
    with pytest.raises(ZipLimitExceededError, match="member count"):
        read_gtfs_zip(path, limits=ZipLimits(max_members=3))


def test_zip_encrypted_member_rejected() -> None:
    info = zipfile.ZipInfo("secret.txt")
    info.flag_bits = 0x1
    info.file_size = 10
    info.compress_size = 10
    with pytest.raises(ZipLimitExceededError, match="Encrypted"):
        from transit_audit.gtfs.zip_limits import validate_zip_member

        validate_zip_member(info, ZipLimits(), 0)


def test_gtfs_missing_agency_and_calendar() -> None:
    feed = read_gtfs_zip(FIXTURES / "missing_agency.zip")
    findings, _ = run_gtfs_checks(feed, AuditConfig())
    assert any("agency.txt" in f.message for f in findings)

    feed2 = read_gtfs_zip(FIXTURES / "missing_calendar.zip")
    findings2, _ = run_gtfs_checks(feed2, AuditConfig())
    assert any("calendar" in f.message.lower() for f in findings2)


def test_equity_requires_single_reference_group() -> None:
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    census = load_census_geopackage(FIXTURES / "census_tiny.gpkg")
    config = AuditConfig(
        default_proximity_m=500,
        equity_groups=[
            EquityGroupConfig(name="r1", attribute="group_code", value="ref", reference=True),
            EquityGroupConfig(name="r2", attribute="group_code", value="ref", reference=True),
            EquityGroupConfig(name="low", attribute="group_code", value="low"),
        ],
    )
    metrics = run_equity_metrics(feed, census, config)
    assert metrics[0].value is None
    assert metrics[0].metadata["reason"] == "exactly_one_reference_group_required"


def test_equity_zero_population_group() -> None:
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    path = FIXTURES / "census_zero_group.gpkg"
    polygon = Polygon([(-123.37, 48.42), (-123.36, 48.42), (-123.36, 48.44), (-123.37, 48.44)])
    gdf = gpd.GeoDataFrame(
        {
            "DGUID": ["z1", "z2"],
            "population": [100, 0],
            "group_code": ["ref", "empty"],
        },
        geometry=[polygon, polygon],
        crs="EPSG:4326",
    )
    gdf.to_file(path, driver="GPKG")
    census = load_census_geopackage(path)
    config = AuditConfig(
        default_proximity_m=500,
        equity_groups=[
            EquityGroupConfig(name="ref", attribute="group_code", value="ref", reference=True),
            EquityGroupConfig(name="empty", attribute="group_code", value="empty"),
        ],
    )
    metrics = run_equity_metrics(feed, census, config)
    gap = next(m for m in metrics if m.metric_id == "EQUITY.COVERAGE_GAP")
    assert gap.value is None
    assert gap.metadata["reason"] == "comparison_group_zero_population"


def test_validator_timeout(tmp_path: Path) -> None:
    with (
        patch("transit_audit.validator.mobilitydata.java_available", return_value=True),
        patch("transit_audit.validator.mobilitydata.Path.exists", return_value=True),
        patch(
            "transit_audit.validator.mobilitydata.subprocess.run",
            side_effect=__import__("subprocess").TimeoutExpired(cmd="java", timeout=1),
        ),
        pytest.raises(TimeoutError, match="timed out"),
    ):
        run_mobilitydata_validator(FIXTURES / "minimal_valid.zip", tmp_path, timeout_seconds=1)


def test_prepare_output_run_subdir(tmp_path: Path) -> None:
    out = prepare_output_dir(tmp_path / "audit", use_run_subdir=True)
    assert out.parent == tmp_path / "audit"
    assert is_exporter_owned(out)
    assert (out / EXPORTER_MARKER).exists()


def test_prepare_output_refuses_foreign_clean(tmp_path: Path) -> None:
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "important.txt").write_text("data", encoding="utf-8")
    with pytest.raises(ValueError, match="not exporter-owned"):
        prepare_output_dir(foreign, force_clean=True, use_run_subdir=False)


def test_prepare_output_force_clean_owned(tmp_path: Path) -> None:
    owned = prepare_output_dir(tmp_path / "owned", use_run_subdir=False)
    (owned / "old.json").write_text("{}", encoding="utf-8")
    cleaned = prepare_output_dir(tmp_path / "owned", force_clean=True, use_run_subdir=False)
    assert cleaned == tmp_path / "owned"
    assert not (cleaned / "old.json").exists()


def test_zip_compression_ratio_limit(tmp_path: Path) -> None:
    path = tmp_path / "ratio.zip"
    payload = b"x" * 5000
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("stops.txt", payload)
    with pytest.raises(ZipLimitExceededError, match="compression ratio"):
        read_gtfs_zip(path, limits=ZipLimits(max_compression_ratio=2.0))


def test_equity_missing_attribute() -> None:
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    census = load_census_geopackage(FIXTURES / "census_tiny.gpkg")
    config = AuditConfig(
        default_proximity_m=500,
        equity_groups=[
            EquityGroupConfig(name="ref", attribute="group_code", value="ref", reference=True),
            EquityGroupConfig(name="x", attribute="missing_col", value="x"),
        ],
    )
    metrics = run_equity_metrics(feed, census, config)
    assert metrics[0].metadata["reason"] == "missing_attribute"


def test_population_points_method() -> None:
    census = load_census_geopackage(
        FIXTURES / "census_tiny.gpkg",
        population_method="population_points",
    )
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    stops_gdf = stops_to_gdf(feed.table("stops"), census.epsg)
    covered, total, meta = population_within_distance(census, stops_gdf, 500.0)
    assert meta["population_method"] == "population_points"
    assert meta["weighting"] == "binary_intersection_full_polygon_count"
    assert covered <= total


def test_directed_pathway_invalid_fields() -> None:
    feed = read_gtfs_zip(FIXTURES / "directed_pathways.zip")
    findings, _ = run_access_checks(feed, AuditConfig())
    assert any("invalid" in f.message.lower() for f in findings)


def test_equity_reference_zero_population() -> None:
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    path = FIXTURES / "census_ref_zero.gpkg"
    polygon = Polygon([(-123.37, 48.42), (-123.36, 48.42), (-123.36, 48.44), (-123.37, 48.44)])
    gdf = gpd.GeoDataFrame(
        {"DGUID": ["z1"], "population": [0], "group_code": ["ref"]},
        geometry=[polygon],
        crs="EPSG:4326",
    )
    gdf.to_file(path, driver="GPKG")
    census = load_census_geopackage(path)
    config = AuditConfig(
        default_proximity_m=500,
        equity_groups=[
            EquityGroupConfig(name="ref", attribute="group_code", value="ref", reference=True),
            EquityGroupConfig(name="low", attribute="group_code", value="low"),
        ],
    )
    metrics = run_equity_metrics(feed, census, config)
    assert metrics[0].metadata["reason"] == "reference_group_zero_population"


def test_unreachable_platform_station() -> None:
    feed = read_gtfs_zip(FIXTURES / "unreachable_platform.zip")
    findings, _ = run_access_checks(feed, AuditConfig())
    assert any("not reachable from entrances" in f.message for f in findings)


def test_zip_member_size_limit(tmp_path: Path) -> None:
    path = tmp_path / "big.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("stops.txt", "x" * 1000)
    with pytest.raises(ZipLimitExceededError, match="per-member"):
        read_gtfs_zip(path, limits=ZipLimits(max_member_bytes=100))
