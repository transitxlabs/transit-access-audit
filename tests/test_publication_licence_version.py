"""Check publisher licence versions and the declared scope of retained inputs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_f4_toronto_licence_version_matches_publisher_and_saved_result():
    # https://open.toronto.ca/open-data-licence/ declares version 1.0.
    manifests = json.loads((ROOT / "docs/bounds_eval/frozen_feed_manifests.json").read_text())
    snapshot = manifests["ttc"]
    record = json.loads((ROOT / snapshot["snapshot_path"]).with_suffix(".json").read_text())
    evaluation = json.loads((ROOT / "docs/bounds_eval/evaluation.json").read_text())
    for item in [snapshot, record, evaluation["feeds"]["ttc"]["feed_snapshot"]]:
        assert item["licence_version"] == "1.0"


def test_f5_retention_policy_does_not_invent_a_translink_snapshot():
    text = (ROOT / "DATA_LICENSES.md").read_text()
    section = text.split("## TransLink GTFS\n", 1)[1].split("\n## ", 1)[0]
    assert "evaluated input retained" not in section
    assert "no raw feed committed without maintainer verification" in section
