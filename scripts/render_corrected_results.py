"""Render result tables and destination-relative evidence links from saved data."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def _settings_text(config: dict[str, Any]) -> str:
    """Base routing settings in plain words; empty when the stored record lacks them."""
    keys = ("departure_time", "max_travel_minutes", "max_transfers", "min_transfer_minutes",
            "walk_speed_mps", "walk_radius_m", "origin_count", "destination_count", "random_seed")
    if not all(key in config for key in keys):
        return ""
    return (
        f"departures at {config['departure_time']}, trips of at most "
        f"{config['max_travel_minutes']} minutes with at most {config['max_transfers']} transfers "
        f"({config['min_transfer_minutes']}-minute minimum), walking at {config['walk_speed_mps']} m/s "
        f"within {config['walk_radius_m']:.0f} m, {config['origin_count']} origins by "
        f"{config['destination_count']} destinations (seed {config['random_seed']})"
    )


def _summary_conditions(payload: dict[str, Any]) -> str:
    feeds = payload["feeds"]
    dates = ", ".join(f"{name} {feed.get('service_date', 'unknown')}" for name, feed in feeds.items())
    configs = [{k: v for k, v in feed.get("config", {}).items() if k != "service_date"}
               for feed in feeds.values()]
    shared = configs[0] if configs and all(c == configs[0] for c in configs) else {}
    settings = _settings_text(shared)
    settings_part = f"; {settings}" if settings else ""
    return (
        "Conditions: schedule-based reachability on the retained GTFS snapshots "
        f"(service dates: {dates}){settings_part}. Counts are origin-destination pairs reachable "
        "under each policy. Timetable data only; not checked against real trips."
    )


def _feed_conditions(feed: dict[str, Any], varied: str = "") -> str:
    settings = _settings_text(feed.get("config", {}))
    base = f"service date {feed.get('service_date', 'unknown')}"
    if settings:
        base += f"; base settings: {settings}"
    note = f" Each row changes only {varied}; every other setting stays at its base value." if varied else ""
    return f"Conditions: {base}.{note}"


def _ranking_section(feed: dict[str, Any]) -> list[str]:
    metadata = feed["metadata"]
    snapshot = feed["feed_snapshot"]
    ran = metadata.get("ranking_ran", False)
    lines = ["### Verification ranking", ""]
    if ran:
        lines += [
            "Exact single-field counterfactual recomputation on a time-selected subset of unknown "
            "fields, using the sampled OD pairs. Ranking is only among evaluated fields; "
            "skipped impact is unknown. Both outcomes share the same walking graph. "
            "Best-case reduction is the larger outcome reduction, not expected value. "
            "Budgets are soft candidate-start budgets: a running candidate can exceed them.", "",
        ]
    else:
        lines += [f"Ranking not run ({metadata.get('ranking_skipped_reason', 'disabled')}).", ""]
    lines += [
        _feed_conditions(feed) + " Widths are mean interval widths over the sampled pairs.", "",
        "| Field | Best-case reduction | Accessible outcome width | Inaccessible outcome width | Affected pairs |",
        "|-------|--------------------:|-------------------------:|---------------------------:|---------------:|",
    ]
    for target in feed["verification_targets"]:
        meta = target["metadata"]
        lines.append(
            f"| {target['entity_type']} {target['entity_id']} | {target['interval_width_change']:.5f} | "
            f"{meta['mean_width_if_accessible']:.5f} | {meta['mean_width_if_not_accessible']:.5f} | "
            f"{target['affected_od_pairs']} |"
        )
    if not feed["verification_targets"]:
        description = "No positive reduction among evaluated fields" if ran else "Ranking not run"
        lines.append(f"| {description} | n/a | n/a | n/a | n/a |")
    budget = metadata.get("ranking_time_budget_seconds")
    budget_note = f" Soft candidate-start budget {budget:.0f} s." if budget else ""
    lines += [
        "",
        f"Candidates total {metadata.get('ranking_candidates_total', 0)}; "
        f"evaluated {metadata.get('ranking_candidates_evaluated', 0)}; "
        f"skipped {metadata.get('ranking_candidates_skipped', 0)}; "
        f"positive targets {metadata.get('ranking_positive_target_count', 0)}; "
        f"ranking runtime {metadata.get('ranking_runtime_seconds', 0):.3f} s.{budget_note}",
        f"Publisher acknowledgement: {snapshot.get('attribution', 'unavailable')}", "",
    ]
    return lines


def _summary_table(payload: dict[str, Any]) -> list[str]:
    lines = [
        _summary_conditions(payload), "",
        "| Feed | Mean width | Nominal 95% crossed interval | n | Optimistic | Pessimistic | Schedule-only |",
        "|------|-----------:|:----------------------------|--:|-----------:|------------:|--------------:|",
    ]
    for name, feed in payload["feeds"].items():
        ci = feed["mean_interval_width_ci95"]
        lines.append(
            f"| {name} | {feed['mean_interval_width']:.5f} | [{ci['lower']:.5f}, {ci['upper']:.5f}] | "
            f"{feed['od_pair_count']} | {feed['optimistic_reachable_od_pairs']} | "
            f"{feed['pessimistic_reachable_od_pairs']} | {feed['schedule_only_reachable_od_pairs']} |"
        )
    return lines


def _relative_link(destination: Path, target: Path) -> str:
    return quote(Path(os.path.relpath(target.resolve(), destination.parent.resolve())).as_posix(),
                 safe="/.")


def _body(payload: dict[str, Any], json_path: Path, destination: Path) -> str:
    def link(label: str, target: str | Path) -> str:
        if (isinstance(target, str) and destination.parent != ROOT
                and not target.startswith("docs/")):
            return f"[{label}](https://github.com/transitxlabs/transit-access-audit/blob/main/{target})"
        path = target if isinstance(target, Path) else ROOT / target
        return f"[{label}]({_relative_link(destination, path)})"

    table = _summary_table(payload)
    text = [
        "# Corrected accessibility routing results", "",
        "Post-result repair round 2026-10-01. Previous routing results and H1/H2/H3 support "
        "claims are withdrawn. Results below are generated from the retained public feed snapshots.",
        f"Hardware/platform record: {payload.get('hardware_note') or 'unavailable'}.", "",
        f"Preregistration SHA-256 (phase 2 prefix): `{payload.get('preregistration_sha256')}`.", "",
        *table, "",
        "Intervals use 1,000 seeded crossed origin/destination bootstrap replicates, resampling "
        "origins within resolved accessibility strata. They are nominal intervals, not certified coverage. "
        + link("Post-result uncertainty amendment", "docs/amendments/AMENDMENT_2026-10-01_05_uncertainty.md")
        + "; [Owen](https://arxiv.org/abs/0712.1111).", "",
    ]
    for name, feed in payload["feeds"].items():
        metadata, snapshot = feed["metadata"], feed["feed_snapshot"]
        text += [
            f"## {name}", "",
            f"Service date: {feed['service_date']}. Unknown stops / trips: "
            f"{feed['unknown_stop_count']} / {feed['unknown_trip_count']}. Retained optimistic / "
            f"pessimistic / schedule-only trips: {metadata['active_trip_count_optimistic']} / "
            f"{metadata['active_trip_count_pessimistic']} / {metadata['active_trip_count_schedule_only']}.", "",
            f"Source: [{name} feed]({snapshot['manifest_url']}). Licence record: "
            + link("data licences", "DATA_LICENSES.md")
            + f". Snapshot SHA-256: `{snapshot['sha256']}`.", "",
            *_ranking_section(feed),
            f"Validator status: {feed['validator']['status']}; notice categories "
            f"{feed['validator'].get('notice_count', 'unavailable')}; error categories "
            f"{feed['validator'].get('error_count', 'unavailable')}.", "",
        ]
        for key in ["transfer_sensitivity", "walk_sensitivity"]:
            if not feed[key]:
                continue
            varied = {"transfer_sensitivity": "the minimum transfer time and the maximum trip time",
                      "walk_sensitivity": "the walking speed and the walking radius"}[key]
            text += [f"### {key.replace('_', ' ').title()}", "",
                     _feed_conditions(feed, varied), "",
                     "| Settings | Mean width | Optimistic | Schedule-only |",
                     "|----------|-----------:|-----------:|--------------:|"]
            for row in feed[key]:
                settings = {k: v for k, v in row.items() if k in {
                    "min_transfer_minutes", "max_travel_minutes", "walk_speed_mps", "walk_radius_m",
                }}
                text.append(f"| {settings} | {row['mean_interval_width']:.5f} | "
                            f"{row['optimistic_reachable']} | {row['schedule_only_reachable']} |")
            text.append("")
    text += [
        "## Synthetic regression fixture", "",
        "The fixture is for correctness tests only, not real-data evidence. Source: "
        + link("fixture builder", "scripts/build_fixtures.py") + "; licence: "
        + link("Apache-2.0", "LICENSE") + ".", "",
        "| Entity | Width reduction | Affected pairs |",
        "|--------|----------------:|---------------:|",
    ]
    for row in payload["fixture_verification"]:
        text.append(f"| {row['entity_type']} {row['entity_id']} | "
                    f"{row['interval_width_change']:.5f} | {row['affected_od_pairs']} |")
    timing = payload["timing"]
    peak = timing.get("peak_memory_mb")
    peak_text = f"{peak:.0f} MB" if peak is not None else "unavailable"
    text += [
        "", "## Interpretation and limitations", "",
        "Positive width measures sensitivity to missing metadata under the declared routing policy. "
        "It does not establish on-street accessibility or practical benefit from field verification. "
        "Zero width is a null policy-difference result, not universal accessibility.", "",
        "All stops on retained trips must pass the policy, including pass-through stops. "
        "Walking-only journeys require permitted endpoints and intermediate stops. Walks consume "
        "no boarding rounds; transfer slack is charged once before later boardings plus walking time. "
        "Geodesic walking omits street barriers. Frequency, pathway, transfer-rule and pickup/drop-off "
        "modelling remain outside this evaluation. "
        "[GTFS field semantics](https://gtfs.org/documentation/schedule/reference/).", "",
        "## Reproduce", "", "```bash", "python scripts/regenerate_publication.py", "```", "",
        f"Numerical evaluation wall time including reading, ranking, sensitivities, validators and plotting: "
        f"{timing['wall_seconds']:.3f} s.", "",
        f"Largest observed complete-tree sample: {peak_text} "
        f"({timing.get('memory_measurement_status', 'unavailable')}). "
        f"Stop enforcement: {timing.get('memory_stop_enforcement', 'unavailable')}. "
        "This is not a certified process-tree peak or hard memory cap. Samples are non-atomic; "
        "transient peaks can be missed. RSS excludes compressed/swapped memory. "
        "An unavailable sample means the stop could not be enforced for that interval. "
        + link("Memory/resource correction", "docs/amendments/AMENDMENT_2026-10-01_06_publication.md")
        + "; [Python subprocess semantics](https://docs.python.org/3/library/subprocess.html).", "",
        f"![Interval widths]({_relative_link(destination, ROOT / 'docs/figures/interval_width_hist.png')})", "",
        link("Machine-readable output, sampled keys and per-pair results", json_path) + ".", "",
    ]
    return "\n".join(text)


def render_results(payload: dict[str, Any], *, json_path: Path | None = None) -> None:
    json_path = json_path or ROOT / "docs/bounds_eval/evaluation.json"
    for name in ["RESULTS.md", "docs/results.md"]:
        destination = ROOT / name
        destination.write_text(_body(payload, json_path, destination), encoding="utf-8")
    block = "<!-- GENERATED RESULTS START -->\n" + "\n".join(_summary_table(payload))
    block += "\n<!-- GENERATED RESULTS END -->"
    for name in ["README.md", "docs/technical-report.md", "docs/index.md"]:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        start, end = "<!-- GENERATED RESULTS START -->", "<!-- GENERATED RESULTS END -->"
        if start in text:
            first, last = text.index(start), text.index(end) + len(end)
            text = text[:first] + block + text[last:]
        else:
            text += "\n" + block + "\n"
        path.write_text(text, encoding="utf-8")
