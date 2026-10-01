"""Regenerate the complete demo and real-feed publication artifacts in one command."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Keep cache, temporary files and input paths inside this checkout.
for variable, relative in [("MPLCONFIGDIR", ".cache/matplotlib"), ("TMPDIR", ".cache/tmp"),
                           ("XDG_CACHE_HOME", ".cache")]:
    path = ROOT / relative
    path.mkdir(parents=True, exist_ok=True)
    os.environ[variable] = str(path)
os.environ["MPLBACKEND"] = "Agg"

from fetch_gtfs import DEFAULT_CACHE, fetch_feed  # noqa: E402
from run_bounds_evaluation import RESULTS_DIR, run_evaluation  # noqa: E402

from transit_audit.engine import run_audit  # noqa: E402
from transit_audit.reporting.backlog_export import (  # noqa: E402
    write_backlog_csv,
    write_backlog_json,
)
from transit_audit.reporting.html import render_html_report  # noqa: E402
from transit_audit.reporting.json_output import write_results_json  # noqa: E402
from transit_audit.validator.mobilitydata import java_available  # noqa: E402

VALIDATOR_DIGEST = "4f78d08a0b72a9ad1833a7cd979f701d1590590ff73f4224fb960dc8cc4014fd"


def regenerate_demo() -> None:
    os.chdir(ROOT)
    result = run_audit(Path("tests/fixtures/minimal_valid.zip"),
                       config_path=Path("examples/audit.yml"),
                       census_path=Path("tests/fixtures/census_tiny.gpkg"))
    output = ROOT / "examples/demo"
    output.mkdir(parents=True, exist_ok=True)
    write_results_json(result, output / "results.json")
    # Render from saved JSON, so the persisted evidence is the rendering input.
    saved = type(result).model_validate_json((output / "results.json").read_text())
    render_html_report(saved, output / "report.html")
    write_backlog_json(saved, output / "backlog.json")
    write_backlog_csv(saved, output / "backlog.csv")
    manifest = {
        "source": "https://github.com/transitxlabs/transit-access-audit/blob/main/scripts/build_fixtures.py",
        "licence": "Apache-2.0",
        "licence_url": "https://github.com/transitxlabs/transit-access-audit/blob/main/LICENSE",
        "provenance": saved.provenance.model_dump(mode="json"),
        "artifact_sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                            for name in ["results.json", "report.html", "backlog.json", "backlog.csv"]},
    }
    (output / "bundle_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-only", action="store_true", help="Regenerate only the fast synthetic bundle")
    args = parser.parse_args()
    os.chdir(ROOT)
    if not args.demo_only:
        jar = ROOT / "vendor/gtfs-validator-6.0.0-cli.jar"
        if not java_available() or not jar.is_file():
            raise RuntimeError("Java and the pinned validator JAR are required; see vendor/README.md")
        if hashlib.sha256(jar.read_bytes()).hexdigest() != VALIDATOR_DIGEST:
            raise RuntimeError("Validator JAR digest mismatch")
        for name in ["calgary", "edmonton", "ttc"]:
            fetch_feed(name, DEFAULT_CACHE)
    regenerate_demo()
    if not args.demo_only:
        payload = run_evaluation(DEFAULT_CACHE, output_dir=RESULTS_DIR,
                                 feeds=["ttc", "calgary", "edmonton"],
                                 sensitivity=True, walk_sensitivity=True)
        print(json.dumps({"headline": payload["headline"], "timing": payload["timing"]}))
    else:
        print("Synthetic demo bundle regenerated from one saved JSON result")
    return 0


if __name__ == "__main__":
    sys.exit(main())
