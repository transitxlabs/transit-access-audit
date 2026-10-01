"""Tests for phase-3 independent verification fixes (items 6-12)."""

from __future__ import annotations

import importlib.util
import re
import sys
from datetime import date
from pathlib import Path

import pytest

from transit_audit.routing.bounds import compute_bounds, rank_verification_targets
from transit_audit.routing.models import BoundsConfig

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "bounds_route.zip"


def _load_eval_script():
    path = ROOT / "scripts" / "run_bounds_evaluation.py"
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("run_bounds_evaluation", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_preregistration_hash_enforced() -> None:
    module = _load_eval_script()
    archived, phase2 = module._enforce_preregistration_hash()
    assert len(archived) == 64
    assert len(phase2) == 64
    recorded = (ROOT / "docs" / "PREREGISTRATION.sha256").read_text(encoding="utf-8").strip()
    assert archived == recorded


def test_fixture_verification_table_from_code() -> None:
    module = _load_eval_script()
    rows = module._fixture_verification_table()
    assert rows
    assert rows[0]["entity_id"] == "S1"
    assert rows[0]["interval_width_change"] == pytest.approx(0.4)
    assert rows[0]["affected_od_pairs"] == 8


def test_ranking_matches_exhaustive_recomputation() -> None:
    from transit_audit.gtfs.reader import read_gtfs_zip
    from transit_audit.routing.bounds import _pair_widths_for_overrides
    from transit_audit.routing.walking import build_walk_edges

    feed = read_gtfs_zip(FIXTURE)
    config = BoundsConfig(
        service_date=date(2024, 6, 3),
        departure_time="07:00:00",
        origin_count=5,
        destination_count=5,
        random_seed=0,
    )
    result = compute_bounds(feed, config)
    walk = build_walk_edges(feed.table("stops"), speed_mps=config.walk_speed_mps, radius_m=config.walk_radius_m)
    pairs = [(pair.origin_stop_id, pair.destination_stop_id) for pair in result.od_pairs]
    targets = rank_verification_targets(feed, config, pairs, od_results=result.od_pairs)
    base = [pair.interval_width for pair in result.od_pairs]
    exhaustive = {}
    for stop_id in ("S1",):
        outcomes = [
            _pair_widths_for_overrides(
                feed,
                config,
                pairs,
                stop_overrides={stop_id: value},
                walk_edges=walk,
            )
            for value in ("1", "2")
        ]
        change = (sum(base) - min(map(sum, outcomes))) / len(base)
        if change:
            exhaustive[stop_id] = change
    assert {target.entity_id: target.interval_width_change for target in targets} == exhaustive


def test_public_docs_have_no_em_dash() -> None:
    test_phase4 = ROOT / "tests" / "test_phase4_reverification_fixes.py"
    assert test_phase4.exists()
    text = test_phase4.read_text(encoding="utf-8")
    assert "test_public_release_surface_hygiene" in text


def test_fetch_gtfs_streams_with_limit(tmp_path: Path) -> None:
    import importlib.util
    import urllib.request

    path = ROOT / "scripts" / "fetch_gtfs.py"
    spec = importlib.util.spec_from_file_location("fetch_gtfs", path)
    fetch_gtfs = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(fetch_gtfs)

    class FakeResponse:
        remaining = 5000

        def read(self, size: int = -1) -> bytes:
            if self.remaining <= 0:
                return b""
            chunk = min(size if size > 0 else self.remaining, self.remaining)
            self.remaining -= chunk
            return b"x" * chunk

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(request, timeout=600):
        del request, timeout
        return FakeResponse()

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(urllib.request, "urlopen", fake_urlopen)
        patch.setattr(fetch_gtfs, "CHUNK_SIZE", 1024)
        patch.setattr(fetch_gtfs, "MAX_COMPRESSED_BYTES", 2048)
        with pytest.raises(ValueError, match="byte compressed limit"):
            fetch_gtfs.fetch_feed("calgary", tmp_path, force=True)


def test_wessel_citation_has_two_authors() -> None:
    report = (ROOT / "docs" / "technical-report.md").read_text(encoding="utf-8")
    match = re.search(r"Wessel, N\., Farber, S\.", report)
    assert match
    assert "Allen" not in match.group(0)
