"""Tests for phase-4 independent re-verification fixes."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path

import pytest

from transit_audit.gtfs.reader import read_gtfs_zip
from transit_audit.gtfs.zip_limits import EVALUATION_ZIP_LIMITS
from transit_audit.routing.bounds import (
    _pair_widths_for_overrides,
    _verification_change,
    compute_bounds,
)
from transit_audit.routing.models import BoundsConfig
from transit_audit.routing.walking import build_walk_edges

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "bounds_route.zip"
FROZEN_MANIFESTS = ROOT / "docs" / "bounds_eval" / "frozen_feed_manifests.json"
EDMONTON = ROOT / ".cache" / "gtfs" / "edmonton_transit_gtfs.zip"
HOME_PATH_PATTERN = re.compile(r"/Users/|/home/")


def _load_eval_script():
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    path = ROOT / "scripts" / "run_bounds_evaluation.py"
    spec = importlib.util.spec_from_file_location("run_bounds_evaluation", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_fetch_script():
    path = ROOT / "scripts" / "fetch_gtfs.py"
    spec = importlib.util.spec_from_file_location("fetch_gtfs", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_preregistration_missing_digest_rejected(tmp_path: Path) -> None:
    module = _load_eval_script()
    docs = tmp_path / "docs"
    docs.mkdir()
    prereg = docs / "PREREGISTRATION.md"
    prereg.write_text("# Plan\n\n## SHA-256 of this document\n\nNo hash here.\n", encoding="utf-8")
    sha = docs / "PREREGISTRATION.sha256"
    sha.write_text("abc" * 21 + "a", encoding="utf-8")
    original_root = module.ROOT
    module.ROOT = tmp_path
    try:
        with pytest.raises(RuntimeError, match="missing a recorded SHA-256"):
            module._enforce_preregistration_hash()
    finally:
        module.ROOT = original_root


def test_missing_manifest_rejected(tmp_path: Path) -> None:
    module = _load_eval_script()
    feed = tmp_path / "feed.zip"
    feed.write_bytes(b"not a real zip")
    with pytest.raises(RuntimeError, match="Missing frozen manifest"):
        module._verify_feed_snapshot(feed, "calgary", tmp_path)


@pytest.mark.slow
def test_edmonton_stop_4790_positive_reduction() -> None:
    if not EDMONTON.exists():
        pytest.skip("Cached Edmonton snapshot unavailable")
    feed = read_gtfs_zip(
        EDMONTON,
        EVALUATION_ZIP_LIMITS,
        only_tables={"stops", "trips", "stop_times", "calendar", "calendar_dates"},
    )
    config = BoundsConfig(
        service_date=date(2026, 9, 30),
        departure_time="08:30:00",
        max_travel_minutes=60,
        max_transfers=2,
        min_transfer_minutes=5,
        origin_count=20,
        destination_count=40,
        random_seed=42,
        rank_verification=False,
    )
    base = compute_bounds(feed, config)
    pairs = [(pair.origin_stop_id, pair.destination_stop_id) for pair in base.od_pairs]
    walk = build_walk_edges(
        feed.table("stops"),
        speed_mps=config.walk_speed_mps,
        radius_m=config.walk_radius_m,
        active_stop_ids=set(feed.table("stop_times")["stop_id"].astype(str)),
    )
    base_widths = _pair_widths_for_overrides(feed, config, pairs, walk_edges=walk)
    accessible = _pair_widths_for_overrides(
        feed, config, pairs, stop_overrides={"4790": "1"}, walk_edges=walk
    )
    inaccessible = _pair_widths_for_overrides(
        feed, config, pairs, stop_overrides={"4790": "2"}, walk_edges=walk
    )
    change, affected = _verification_change(
        base_widths,
        accessible,
        inaccessible,
        total_pairs=len(base_widths),
    )
    assert change == pytest.approx(0.02125, abs=1e-5)
    assert affected == 17


def test_edmonton_ranking_headline_from_evaluation_json() -> None:
    payload_path = ROOT / "docs" / "bounds_eval" / "evaluation.json"
    if not payload_path.exists():
        pytest.skip("evaluation.json not regenerated yet")
    edmonton = json.loads(payload_path.read_text(encoding="utf-8"))["feeds"]["edmonton"]
    assert edmonton["verification_targets"]
    top = edmonton["verification_targets"][0]
    assert top["entity_id"] == "4790"
    assert top["interval_width_change"] == pytest.approx(0.02125, abs=1e-5)


def test_evaluation_payload_reports_ranking_not_zero_by_default() -> None:
    payload_path = ROOT / "docs" / "bounds_eval" / "evaluation.json"
    if not payload_path.exists():
        pytest.skip("evaluation.json not regenerated yet")
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    edmonton = payload["feeds"]["edmonton"]
    metadata = edmonton["metadata"]
    if "ranking_ran" not in metadata:
        pytest.skip("evaluation.json predates phase-4 ranking metadata")
    assert metadata["ranking_candidates_evaluated"] > 0
    if metadata["ranking_positive_target_count"] > 0:
        assert edmonton["verification_targets"]
        assert edmonton["verification_targets"][0]["interval_width_change"] > 0


def test_timing_peak_memory_null_not_zero_when_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from render_corrected_results import render_results

    monkeypatch.setattr("render_corrected_results.ROOT", tmp_path)
    (tmp_path / "docs").mkdir()
    for name in ["README.md", "docs/index.md", "docs/technical-report.md"]:
        (tmp_path / name).write_text("", encoding="utf-8")

    payload = {
        "feeds": {
            "calgary": {
                "peak_memory_mb": None,
                "memory_measurement_status": "unavailable",
                "metadata": {
                    "ranking_ran": False,
                    "ranking_skipped_reason": "disabled",
                    "active_trip_count_optimistic": 0,
                    "active_trip_count_pessimistic": 0,
                    "active_trip_count_schedule_only": 0,
                },
                "feed_snapshot": {"manifest_url": "https://example.com", "sha256": "abc", "attribution": "test"},
                "service_date": "2026-09-30",
                "unknown_stop_count": 0,
                "unknown_trip_count": 0,
                "verification_targets": [],
                "validator": {"status": "skipped"},
                "transfer_sensitivity": [],
                "walk_sensitivity": [],
                "mean_interval_width": 0.0,
                "mean_interval_width_ci95": {"lower": 0.0, "upper": 0.0},
                "od_pair_count": 0,
                "optimistic_reachable_od_pairs": 0,
                "pessimistic_reachable_od_pairs": 0,
                "schedule_only_reachable_od_pairs": 0,
            }
        },
        "timing": {
            "wall_seconds": 1.0,
            "peak_memory_mb": None,
            "memory_measurement_status": "unavailable",
        },
        "headline": {},
        "fixture_verification": [],
        "preregistration_sha256": "abc",
    }
    render_results(payload)
    text = (tmp_path / "RESULTS.md").read_text(encoding="utf-8")
    assert "Largest observed complete-tree sample: unavailable" in text


def test_frozen_manifests_and_data_licences() -> None:
    frozen = json.loads(FROZEN_MANIFESTS.read_text(encoding="utf-8"))
    licences = (ROOT / "DATA_LICENSES.md").read_text(encoding="utf-8")
    assert "Open Government Licence \u2013 City of Calgary" in frozen["calgary"]["attribution"]
    assert "Open Government Licence \u2013 City of Edmonton" in frozen["edmonton"]["attribution"]
    assert "npk7-z3bj" in frozen["calgary"]["url"]
    assert "Open Government Licence \u2013 City of Calgary" in licences
    assert "Open Government Licence \u2013 City of Edmonton" in licences
    fetch = _load_fetch_script()
    assert fetch.FEEDS["calgary"]["sha256"] == frozen["calgary"]["sha256"]


def test_wessel_and_farber_authors_in_technical_report() -> None:
    report = (ROOT / "docs" / "technical-report.md").read_text(encoding="utf-8")
    assert re.search(r"Wessel, N\., Farber, S\. \(2019\)", report)
    assert "Wessel et al." not in report


def test_public_release_surface_hygiene() -> None:
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from release_hygiene import scan_release

    assert not scan_release(ROOT), "\n".join(scan_release(ROOT))


def test_demo_report_regenerated_without_em_dash() -> None:
    report = ROOT / "examples" / "demo" / "report.html"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "\u2014" not in text
    assert "0.3.0" in text
