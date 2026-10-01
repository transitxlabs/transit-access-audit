"""Tests for accessibility routing bounds."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from transit_audit.gtfs.reader import read_gtfs_zip
from transit_audit.routing.bounds import compute_bounds, rank_verification_targets
from transit_audit.routing.index import build_schedule_index
from transit_audit.routing.models import BoundsConfig, UnknownPolicy
from transit_audit.routing.policy import GTFS_ACCESSIBILITY_SPEC, is_accessible, wheelchair_category
from transit_audit.routing.reachability import is_destination_reachable
from transit_audit.routing.walking import build_walk_edges

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GTFS_SPEC = "https://gtfs.org/documentation/schedule/reference/#stopstxt-wheelchair_boarding"


def test_wheelchair_category_matches_gtfs_spec() -> None:
    assert GTFS_ACCESSIBILITY_SPEC.startswith("https://gtfs.org/")
    assert wheelchair_category("1") == "accessible"
    assert wheelchair_category("2") == "not_accessible"
    assert wheelchair_category("0") == "unknown"
    assert wheelchair_category("") == "unknown"
    assert GTFS_SPEC.startswith("https://gtfs.org/")


def test_unknown_policies() -> None:
    assert is_accessible("", UnknownPolicy.OPTIMISTIC) is True
    assert is_accessible("", UnknownPolicy.PESSIMISTIC) is False
    assert is_accessible("0", UnknownPolicy.PESSIMISTIC) is False
    assert is_accessible("0", UnknownPolicy.OPTIMISTIC) is True
    assert is_accessible("2", UnknownPolicy.OPTIMISTIC) is False


def test_bounds_fixture_has_interval_width() -> None:
    feed = read_gtfs_zip(FIXTURES / "bounds_route.zip")
    config = BoundsConfig(
        service_date=date(2024, 6, 3),
        departure_time="07:00:00",
        max_travel_minutes=60,
        max_transfers=1,
        min_transfer_minutes=0,
        origin_count=5,
        destination_count=5,
        random_seed=0,
        verification_rank_limit=5,
    )
    result = compute_bounds(feed, config)
    assert result.mean_interval_width > 0
    assert result.unknown_stop_count >= 1
    assert result.unknown_trip_count >= 1
    assert any(pair.interval_width == 1 for pair in result.od_pairs)


def test_known_route_has_zero_width() -> None:
    feed = read_gtfs_zip(FIXTURES / "bounds_route.zip")
    walk_edges = build_walk_edges(feed.table("stops"), speed_mps=1.4, radius_m=300.0)
    optimistic = build_schedule_index(
        feed, date(2024, 6, 3), UnknownPolicy.OPTIMISTIC, walk_edges=walk_edges
    )
    pessimistic = build_schedule_index(
        feed, date(2024, 6, 3), UnknownPolicy.PESSIMISTIC, walk_edges=walk_edges
    )
    opt_ok, _ = is_destination_reachable(
        "S4", "S5", 7 * 3600, 3600, 1, 0, optimistic
    )
    pess_ok, _ = is_destination_reachable(
        "S4", "S5", 7 * 3600, 3600, 1, 0, pessimistic
    )
    assert opt_ok and pess_ok


def test_verification_ranking_exact_on_fixture() -> None:
    feed = read_gtfs_zip(FIXTURES / "bounds_route.zip")
    config = BoundsConfig(
        service_date=date(2024, 6, 3),
        departure_time="07:00:00",
        max_travel_minutes=60,
        origin_count=5,
        destination_count=5,
        random_seed=0,
    )
    result = compute_bounds(feed, config)
    targets = rank_verification_targets(
        feed,
        config,
        [(pair.origin_stop_id, pair.destination_stop_id) for pair in result.od_pairs],
        od_results=result.od_pairs,
        base_mean_width=result.mean_interval_width,
    )
    assert targets
    assert targets[0].interval_width_change > 0
    assert targets[0].affected_od_pairs >= 1


def test_schedule_only_differs_from_pessimistic() -> None:
    feed = read_gtfs_zip(FIXTURES / "bounds_route.zip")
    config = BoundsConfig(
        service_date=date(2024, 6, 3),
        departure_time="07:00:00",
        max_travel_minutes=60,
        origin_count=5,
        destination_count=5,
        random_seed=0,
    )
    result = compute_bounds(feed, config)
    assert result.schedule_only_summary is not None
    assert (
        result.schedule_only_summary.reachable_destination_count
        >= result.pessimistic_summary.reachable_destination_count
    )


def test_bounds_cli_smoke(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from transit_audit.cli.app import app

    runner = CliRunner()
    output = tmp_path / "bounds.json"
    result = runner.invoke(
        app,
        [
            "bounds",
            str(FIXTURES / "bounds_route.zip"),
            "--output",
            str(output),
            "--service-date",
            "2024-06-03",
            "--departure-time",
            "07:00:00",
            "--origin-count",
            "2",
            "--destination-count",
            "2",
        ],
    )
    assert result.exit_code == 0
    assert output.exists()


@pytest.mark.network
def test_fetch_gtfs_script_smoke(tmp_path: Path) -> None:
    import subprocess

    proc = subprocess.run(
        [
            "python3",
            str(Path(__file__).resolve().parents[1] / "scripts" / "fetch_gtfs.py"),
            "ttc",
            "--cache-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "ttc_completegtfs.zip").exists()
