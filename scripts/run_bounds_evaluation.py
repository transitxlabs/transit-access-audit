#!/usr/bin/env python3
"""Run preregistered routing bounds evaluation and write RESULTS artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

from transit_audit.gtfs.reader import read_gtfs_zip
from transit_audit.gtfs.zip_limits import EVALUATION_ZIP_LIMITS
from transit_audit.routing.accessibility import resolve_stop_boarding
from transit_audit.routing.bounds import compute_bounds, rank_verification_targets
from transit_audit.routing.models import BoundsConfig
from transit_audit.routing.policy import wheelchair_category
from transit_audit.routing.uncertainty import crossed_bootstrap_interval
from transit_audit.routing.walking import build_walk_edges
from transit_audit.validator.mobilitydata import (
    ingest_validator_report,
    java_available,
    run_mobilitydata_validator,
)

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from memory_monitor import ProcessMemoryMonitor  # noqa: E402
from render_corrected_results import render_results  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = ROOT / ".cache" / "gtfs"
RESULTS_DIR = ROOT / "docs" / "bounds_eval"
FIGURES_DIR = ROOT / "docs" / "figures"
FROZEN_MANIFESTS = RESULTS_DIR / "frozen_feed_manifests.json"
MEMORY_LIMIT_MB = 12_288
FIXTURE_ZIP = ROOT / "tests" / "fixtures" / "bounds_route.zip"
RANKING_BUDGET_SECONDS = {
    "calgary": 600.0,
    "edmonton": 1800.0,
}


def _preregistration_hashes() -> tuple[str, str]:
    archived = (ROOT / "docs" / "PREREGISTRATION.sha256").read_text(encoding="utf-8").strip()
    prereg_text = (ROOT / "docs" / "PREREGISTRATION.md").read_text(encoding="utf-8")
    marker = "## SHA-256 of this document"
    if marker in prereg_text:
        prereg_text = prereg_text.split(marker)[0].rstrip() + "\n"
    phase2 = hashlib.sha256(prereg_text.encode()).hexdigest()
    return archived, phase2


def _enforce_preregistration_hash() -> tuple[str, str]:
    archived, phase2 = _preregistration_hashes()
    recorded: str | None = None
    marker = "## SHA-256 of this document"
    prereg_text = (ROOT / "docs" / "PREREGISTRATION.md").read_text(encoding="utf-8")
    if marker in prereg_text:
        for line in prereg_text.split(marker, 1)[1].splitlines():
            candidate = line.strip().strip("`")
            if len(candidate) == 64:
                recorded = candidate
                break
    if recorded is None:
        raise RuntimeError(
            "PREREGISTRATION.md is missing a recorded SHA-256 digest; "
            "record the frozen hash before evaluation."
        )
    if recorded != phase2:
        raise RuntimeError(
            "PREREGISTRATION.md body changed after freeze; record a dated AMENDMENT instead."
        )
    return archived, phase2


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return path.name


def _load_frozen_manifests() -> dict[str, dict[str, Any]]:
    return json.loads(FROZEN_MANIFESTS.read_text(encoding="utf-8"))


def _read_manifest_digest(cache_dir: Path, feed_name: str) -> dict[str, str | int]:
    manifest = cache_dir / f"{feed_name}_manifest.txt"
    if not manifest.exists():
        raise RuntimeError(
            f"Missing frozen manifest for {feed_name}: {manifest}. "
            "Run scripts/fetch_gtfs.py with the pinned snapshot first."
        )
    values: dict[str, str | int] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = int(value) if key == "bytes" and value.isdigit() else value
    if not values.get("sha256"):
        raise RuntimeError(f"Manifest for {feed_name} is missing sha256")
    return values


def _verify_feed_snapshot(feed_path: Path, feed_name: str, cache_dir: Path) -> dict[str, Any]:
    manifest = _read_manifest_digest(cache_dir, feed_name)
    frozen = _load_frozen_manifests()[feed_name]
    digest = hashlib.sha256()
    with feed_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    observed = digest.hexdigest()
    expected = str(frozen["sha256"])
    if observed != expected:
        raise RuntimeError(f"{feed_name} SHA-256 mismatch: expected {expected}, got {observed}")
    if feed_path.stat().st_size != int(frozen["bytes"]):
        raise RuntimeError(
            f"{feed_name} byte count mismatch: expected {frozen['bytes']}, "
            f"got {feed_path.stat().st_size}"
        )
    if str(manifest.get("sha256", "")) != expected:
        raise RuntimeError(f"{feed_name} manifest SHA-256 does not match frozen snapshot record")
    return {
        "relative_path": _relative_path(feed_path),
        "sha256": observed,
        "bytes": feed_path.stat().st_size,
        "manifest_url": frozen["url"],
        "licence_url": frozen["licence_url"],
        "attribution": frozen["attribution"],
        "snapshot_path": frozen["snapshot_path"],
        "dataset_url": frozen["dataset_url"],
        "licence_version": frozen["licence_version"],
    }


def _sanitize_validator_report(report_path: Path) -> None:
    text = report_path.read_text(encoding="utf-8")
    sanitized = text.replace(str(ROOT), ".")
    sanitized = re.sub(r"file://[^\"']+", lambda match: _relative_feed_uri(match.group(0)), sanitized)
    if sanitized != text:
        report_path.write_text(sanitized, encoding="utf-8")
    html_path = report_path.with_suffix(".html")
    if html_path.exists():
        html = html_path.read_text(encoding="utf-8")
        sanitized_html = html.replace(str(ROOT), ".")
        sanitized_html = re.sub(
            r"file://[^<\"']+",
            lambda match: _relative_feed_uri(match.group(0)),
            sanitized_html,
        )
        if sanitized_html != html:
            html_path.write_text(sanitized_html, encoding="utf-8")


def _relative_feed_uri(uri: str) -> str:
    marker = ".cache/gtfs/"
    if marker in uri:
        return uri[uri.index(marker) :]
    return uri.replace(str(ROOT), ".")


def _fixture_verification_table() -> list[dict[str, Any]]:
    feed = read_gtfs_zip(FIXTURE_ZIP, EVALUATION_ZIP_LIMITS)
    config = BoundsConfig(
        service_date=date(2024, 6, 3),
        departure_time="07:00:00",
        max_travel_minutes=60,
        max_transfers=1,
        min_transfer_minutes=0,
        origin_count=5,
        destination_count=5,
        random_seed=0,
        rank_verification=True,
    )
    result = compute_bounds(feed, config)
    pairs = [(pair.origin_stop_id, pair.destination_stop_id) for pair in result.od_pairs]
    targets = rank_verification_targets(
        feed,
        config,
        pairs,
        od_results=result.od_pairs,
        base_mean_width=result.mean_interval_width,
    )
    return [
        {
            "rank": index + 1,
            "entity_type": target.entity_type,
            "entity_id": target.entity_id,
            "field": target.field,
            "interval_width_change": target.interval_width_change,
            "affected_od_pairs": target.affected_od_pairs,
        }
        for index, target in enumerate(targets[:5])
    ]


def _write_results_markdown(payload: dict[str, Any], *, json_path: Path) -> None:
    render_results(payload, json_path=json_path)


FEED_SPECS: dict[str, dict[str, str]] = {
    "ttc": {
        "path": "ttc_completegtfs.zip",
        "service_date": "2026-10-07",
        "role": "null_fully_coded",
    },
    "calgary": {
        "path": "calgary_transit_gtfs.zip",
        "service_date": "2026-09-30",
        "role": "primary_missing_columns",
    },
    "edmonton": {
        "path": "edmonton_transit_gtfs.zip",
        "service_date": "2026-09-30",
        "role": "primary_partial_unknown_stops",
    },
}


def _bootstrap_interval(
    od_pairs: list[tuple[str, str, float]],
    origin_strata: dict[str, str],
    *,
    samples: int = 1000,
    alpha: float = 0.05,
) -> tuple[float, float]:
    if not od_pairs:
        return 0.0, 0.0
    return crossed_bootstrap_interval(
        od_pairs,
        origin_strata,
        samples=samples,
        alpha=alpha,
    )


def _validator_summary(
    feed: Path,
    output_dir: Path,
    monitor: ProcessMemoryMonitor,
) -> dict[str, Any]:
    if not java_available():
        return {"status": "skipped", "reason": "java_not_available"}
    validator_dir = output_dir / "validator" / feed.stem
    try:
        report_path = monitor.run(
            f"{feed.stem} validator",
            lambda: run_mobilitydata_validator(
                feed,
                validator_dir,
                timeout_seconds=600,
                memory_limit_mb=MEMORY_LIMIT_MB,
                parent_memory_mb=monitor.peak_mb,
            ),
        )
        findings, provenance = ingest_validator_report(report_path)
        _sanitize_validator_report(report_path)
    except (TimeoutError, RuntimeError, FileNotFoundError) as exc:
        return {"status": "failed", "reason": str(exc)}

    codes = sorted({finding.check_id for finding in findings})
    errors = sum(1 for finding in findings if finding.severity.value == "error")
    warnings = sum(1 for finding in findings if finding.severity.value == "warning")
    return {
        "status": "completed",
        "validator_version": provenance.get("validator_version"),
        "notice_count": len(findings),
        "error_count": errors,
        "warning_count": warnings,
        "sample_codes": codes[:15],
        "catches_accessibility_gaps": any(
            "wheelchair" in finding.message.lower() for finding in findings
        ),
        "report_path": _relative_path(report_path),
    }


def _run_production_ranking(
    gtfs: Any,
    base_config: BoundsConfig,
    base_result: Any,
    *,
    feed_name: str,
    monitor: ProcessMemoryMonitor,
) -> tuple[list[Any], dict[str, Any]]:
    if feed_name not in RANKING_BUDGET_SECONDS:
        return [], {
            "ran": False,
            "candidates_total": 0,
            "candidates_evaluated": 0,
            "candidates_skipped": 0,
            "positive_target_count": 0,
            "runtime_seconds": 0.0,
            "skipped_reason": "not_primary_feed",
        }
    pairs = [(pair.origin_stop_id, pair.destination_stop_id) for pair in base_result.od_pairs]
    walk_edges = build_walk_edges(
        gtfs.table("stops"),
        speed_mps=base_config.walk_speed_mps,
        radius_m=base_config.walk_radius_m,
        active_stop_ids=set(gtfs.table("stop_times")["stop_id"].astype(str)),
    )
    ranking_stats: dict[str, Any] = {}
    monitor.enforce(f"{feed_name} pre-ranking")
    targets = rank_verification_targets(
        gtfs,
        base_config,
        pairs,
        od_results=base_result.od_pairs,
        base_mean_width=base_result.mean_interval_width,
        walk_edges=walk_edges,
        time_budget_seconds=RANKING_BUDGET_SECONDS[feed_name],
        stats=ranking_stats,
    )
    monitor.enforce(f"{feed_name} post-ranking")
    return targets, ranking_stats


def _evaluate_feed(
    feed: Path,
    *,
    feed_name: str,
    service_date: date,
    cache_dir: Path,
    output_dir: Path,
    sensitivity: bool,
    walk_sensitivity: bool,
    monitor: ProcessMemoryMonitor,
) -> dict[str, Any]:
    print(f"{feed_name}: reading verified snapshot", flush=True)
    monitor.enforce(f"{feed_name} pre-read")
    snapshot = _verify_feed_snapshot(feed, feed_name, cache_dir)
    gtfs = read_gtfs_zip(
        feed,
        EVALUATION_ZIP_LIMITS,
        only_tables={"stops", "trips", "stop_times", "calendar", "calendar_dates"},
    )
    monitor.enforce(f"{feed_name} post-read")
    base_config = BoundsConfig(
        service_date=service_date,
        departure_time="08:30:00",
        max_travel_minutes=60,
        max_transfers=2,
        min_transfer_minutes=5,
        origin_count=20,
        destination_count=40,
        random_seed=42,
        verification_rank_limit=15,
        walk_speed_mps=1.4,
        walk_radius_m=300.0,
        rank_verification=False,
    )

    print(f"{feed_name}: routing base OD sample", flush=True)
    started = time.perf_counter()
    monitor.enforce(f"{feed_name} pre-bounds")
    base_result = compute_bounds(gtfs, base_config)
    monitor.enforce(f"{feed_name} post-bounds")
    print(f"{feed_name}: verification subset ranking", flush=True)
    ranking_targets, ranking_metadata = _run_production_ranking(
        gtfs,
        base_config,
        base_result,
        feed_name=feed_name,
        monitor=monitor,
    )
    runtime = time.perf_counter() - started
    print(f"{feed_name}: ranking metadata {json.dumps(ranking_metadata)}", flush=True)

    resolved_stops = resolve_stop_boarding(gtfs.table("stops"))
    origin_strata = {
        stop_id: "unknown" if wheelchair_category(raw) == "unknown" else "known"
        for stop_id, raw in resolved_stops.items()
    }
    bootstrap_pairs = [
        (pair.origin_stop_id, pair.destination_stop_id, float(pair.interval_width))
        for pair in base_result.od_pairs
    ]
    width_ci = _bootstrap_interval(bootstrap_pairs, origin_strata)

    transfer_sensitivity: list[dict[str, Any]] = []
    if sensitivity:
        print(f"{feed_name}: transfer sensitivity grid", flush=True)
        for transfer_minutes in (3, 5, 10):
            for travel_minutes in (45, 60, 90):
                cfg = base_config.model_copy(
                    update={
                        "min_transfer_minutes": transfer_minutes,
                        "max_travel_minutes": travel_minutes,
                        "rank_verification": False,
                    }
                )
                result = compute_bounds(gtfs, cfg)
                monitor.enforce(f"{feed_name} transfer sensitivity")
                transfer_sensitivity.append(
                    {
                        "min_transfer_minutes": transfer_minutes,
                        "max_travel_minutes": travel_minutes,
                        "mean_interval_width": result.mean_interval_width,
                        "optimistic_reachable": result.optimistic_summary.reachable_destination_count,
                        "pessimistic_reachable": result.pessimistic_summary.reachable_destination_count,
                        "schedule_only_reachable": (
                            result.schedule_only_summary.reachable_destination_count
                            if result.schedule_only_summary
                            else None
                        ),
                        "runtime_seconds": result.runtime_seconds,
                    }
                )

    walk_sensitivity_rows: list[dict[str, Any]] = []
    if walk_sensitivity:
        print(f"{feed_name}: walking sensitivity grid", flush=True)
        for speed in (1.0, 1.4, 1.8):
            for radius in (200.0, 300.0, 500.0):
                cfg = base_config.model_copy(
                    update={
                        "walk_speed_mps": speed,
                        "walk_radius_m": radius,
                        "rank_verification": False,
                    }
                )
                result = compute_bounds(gtfs, cfg)
                monitor.enforce(f"{feed_name} walk sensitivity")
                walk_sensitivity_rows.append(
                    {
                        "walk_speed_mps": speed,
                        "walk_radius_m": radius,
                        "mean_interval_width": result.mean_interval_width,
                        "optimistic_reachable": result.optimistic_summary.reachable_destination_count,
                        "schedule_only_reachable": (
                            result.schedule_only_summary.reachable_destination_count
                            if result.schedule_only_summary
                            else None
                        ),
                    }
                )

    print(f"{feed_name}: validator baseline", flush=True)
    validator = _validator_summary(feed, output_dir, monitor)
    print(f"{feed_name}: completed; validator {validator['status']}", flush=True)
    metadata = dict(base_result.metadata)
    metadata.update(
        {
            "ranking_runtime_seconds": ranking_metadata.get("runtime_seconds", 0.0),
            "ranking_positive_target_count": ranking_metadata.get("positive_target_count", 0),
            "ranking_candidates_total": ranking_metadata.get("candidates_total", 0),
            "ranking_candidates_evaluated": ranking_metadata.get("candidates_evaluated", 0),
            "ranking_candidates_skipped": ranking_metadata.get("candidates_skipped", 0),
            "ranking_ran": ranking_metadata.get("ran", False),
            "ranking_skipped_reason": ranking_metadata.get("skipped_reason"),
            "ranking_time_budget_seconds": ranking_metadata.get("time_budget_seconds"),
        }
    )

    return {
        "feed_name": feed_name,
        "feed_snapshot": snapshot,
        "service_date": service_date.isoformat(),
        "runtime_seconds": runtime,
        **monitor.record(),
        "mean_interval_width": base_result.mean_interval_width,
        "median_interval_width": base_result.median_interval_width,
        "mean_interval_width_ci95": {"lower": width_ci[0], "upper": width_ci[1]},
        "optimistic_reachable_od_pairs": base_result.optimistic_summary.reachable_destination_count,
        "pessimistic_reachable_od_pairs": base_result.pessimistic_summary.reachable_destination_count,
        "schedule_only_reachable_od_pairs": (
            base_result.schedule_only_summary.reachable_destination_count
            if base_result.schedule_only_summary
            else None
        ),
        "unknown_stop_count": base_result.unknown_stop_count,
        "unknown_trip_count": base_result.unknown_trip_count,
        "od_pair_count": len(base_result.od_pairs),
        "origin_stop_ids": base_result.origin_stop_ids,
        "destination_stop_ids": base_result.destination_stop_ids,
        "origin_strata": {o: origin_strata[o] for o in base_result.origin_stop_ids},
        "od_pairs": [pair.model_dump(mode="json") for pair in base_result.od_pairs],
        "verification_targets": [
            target.model_dump(mode="json")
            for target in ranking_targets[: base_config.verification_rank_limit]
        ],
        "transfer_sensitivity": transfer_sensitivity,
        "walk_sensitivity": walk_sensitivity_rows,
        "validator": validator,
        "config": base_config.model_dump(mode="json"),
        "metadata": metadata,
    }


def _run_evaluation(
    cache_dir: Path,
    *,
    output_dir: Path,
    feeds: list[str],
    sensitivity: bool,
    walk_sensitivity: bool,
    monitor: ProcessMemoryMonitor,
    hardware_label: str | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    wall_started = time.perf_counter()
    archived_sha, phase2_sha = _enforce_preregistration_hash()

    feed_results: dict[str, Any] = {}
    primary_name = next(name for name, spec in FEED_SPECS.items() if spec["role"].startswith("primary"))
    for feed_name in feeds:
        spec = FEED_SPECS[feed_name]
        feed_path = cache_dir / spec["path"]
        if not feed_path.exists():
            raise FileNotFoundError(f"Feed not found: {feed_path}. Run scripts/fetch_gtfs.py {feed_name}")
        feed_results[feed_name] = _evaluate_feed(
            feed_path,
            feed_name=feed_name,
            service_date=date.fromisoformat(spec["service_date"]),
            cache_dir=cache_dir,
            output_dir=output_dir,
            sensitivity=sensitivity and feed_name == primary_name,
            walk_sensitivity=walk_sensitivity and feed_name == primary_name,
            monitor=monitor,
        )

    primary = feed_results[primary_name]
    fixture_verification = _fixture_verification_table()
    figure_path: str | None = None
    try:
        import matplotlib.pyplot as plt

        primary_widths = [pair["interval_width"] for pair in primary["od_pairs"]]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(primary_widths, bins=[-0.5, 0.5, 1.5], color="#1f77b4", edgecolor="white")
        ax.set_xlabel("Reachability interval width (optimistic minus pessimistic)")
        ax.set_ylabel("OD pair count")
        ax.set_title(f"{primary_name} bounds evaluation: interval width distribution")
        ax.set_xticks([0, 1])
        saved = FIGURES_DIR / "interval_width_hist.png"
        fig.tight_layout()
        fig.savefig(saved, dpi=150)
        plt.close(fig)
        figure_path = _relative_path(saved)
    except ImportError:
        figure_path = None

    wall_seconds = time.perf_counter() - wall_started
    monitor.sample()
    payload: dict[str, Any] = {
        "hardware_note": hardware_label or f"{platform.system()} {platform.release()} ({platform.machine()})",
        "hardware_provenance": _hardware_provenance(hardware_label),
        "preregistration_sha256_archived": archived_sha,
        "preregistration_sha256": phase2_sha,
        "feeds": feed_results,
        "primary_feed": primary_name,
        "fixture_verification": fixture_verification,
        "figure_path": figure_path,
        "timing": {
            "wall_seconds": wall_seconds,
            **monitor.record(),
        },
        "headline": {
            "feed": primary_name,
            "mean_interval_width": primary["mean_interval_width"],
            "mean_interval_width_ci95": primary["mean_interval_width_ci95"],
            "optimistic_reachable_od_pairs": primary["optimistic_reachable_od_pairs"],
            "pessimistic_reachable_od_pairs": primary["pessimistic_reachable_od_pairs"],
        },
    }

    json_path = output_dir / "evaluation.json"
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    _write_results_markdown(payload, json_path=json_path)
    return payload


def _hardware_provenance(label: str | None) -> dict[str, Any]:
    info: dict[str, Any] = {
        "label": label, "label_source": "explicitly_supplied" if label else "platform",
        "system": platform.system(), "release": platform.release(),
        "machine": platform.machine(), "processor": platform.processor() or None,
        "physical_memory_bytes": None, "model": None,
    }
    if platform.system() == "Darwin":
        for key, query in [("physical_memory_bytes", "hw.memsize"), ("model", "hw.model")]:
            try:
                value = subprocess.check_output(["sysctl", "-n", query], text=True, timeout=5, stderr=subprocess.DEVNULL).strip()
                info[key] = int(value) if key == "physical_memory_bytes" else value or None
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
    return info


def run_evaluation(cache_dir: Path, *, output_dir: Path, feeds: list[str],
                   sensitivity: bool, walk_sensitivity: bool,
                   hardware_label: str | None = None) -> dict[str, Any]:
    monitor = ProcessMemoryMonitor(MEMORY_LIMIT_MB)
    return monitor.run("full evaluation", lambda: _run_evaluation(
        cache_dir, output_dir=output_dir, feeds=feeds, sensitivity=sensitivity,
        walk_sensitivity=walk_sensitivity, monitor=monitor, hardware_label=hardware_label,
    ))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hardware-label", help="Optional operator-supplied label; recorded as supplied")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument(
        "--feeds",
        nargs="+",
        choices=sorted(FEED_SPECS),
        default=["calgary", "edmonton"],
    )
    parser.add_argument("--include-ttc", action="store_true")
    parser.add_argument("--sensitivity", action="store_true")
    parser.add_argument("--walk-sensitivity", action="store_true")
    args = parser.parse_args()

    feeds = list(args.feeds)
    if args.include_ttc and "ttc" not in feeds:
        feeds.insert(0, "ttc")

    try:
        payload = run_evaluation(
            args.cache_dir,
            output_dir=args.output_dir,
            feeds=feeds,
            sensitivity=args.sensitivity,
            walk_sensitivity=args.walk_sensitivity,
            hardware_label=args.hardware_label,
        )
    except (FileNotFoundError, MemoryError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    headline = payload["headline"]
    print(
        json.dumps(
            {
                "primary_feed": headline["feed"],
                "mean_interval_width": headline["mean_interval_width"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
