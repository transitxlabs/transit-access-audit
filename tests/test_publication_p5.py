"""Publication regression checks indexed by required finding number."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from transit_audit.models import AuditResult
from transit_audit.reporting.html import render_html_report
from transit_audit.validator.mobilitydata import run_mobilitydata_validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_f1_transient_memory_violation_interrupts_callable(monkeypatch):
    module = load_script("memory_monitor")
    high = threading.Event()
    monitor = module.ProcessMemoryMonitor(100)
    monitor.interval_seconds = 0.01
    monkeypatch.setattr(monitor, "sample", lambda: 200.0 if high.is_set() else 1.0)

    def operation():
        high.set()
        try:
            time.sleep(0.15)
        finally:
            high.clear()

    with pytest.raises(MemoryError, match="100 MB"):
        monitor.run("transient", operation)


def test_f1_pid_parser_requires_process_row():
    module = load_script("memory_monitor")
    output = "PhysMem: 2048M used, 10G unused\nPID MEM\n2048 20M\n"
    assert module._parse_top_memory_mb(output, 2048) == 20


def test_f1_complete_descendant_tree(monkeypatch):
    module = load_script("memory_monitor")

    def output(cmd, **kwargs):
        if cmd[0] == "pgrep":
            pid = int(cmd[-1])
            return str(pid + 1) if pid < 4 else ""
        if cmd[0] == "top":
            pid = int(cmd[cmd.index("-pid") + 1])
            return f"PID MEM\n{pid} 10M\n"
        raise AssertionError(cmd)

    monkeypatch.setattr(module.subprocess, "check_output", output)
    assert module.sample_process_tree_mb(1) == 40


def test_f1_partial_measurement_is_unavailable(monkeypatch):
    module = load_script("memory_monitor")

    def output(cmd, **kwargs):
        if cmd[0] == "pgrep":
            return "2" if cmd[-1] == "1" else ""
        if cmd[0] == "top" and cmd[cmd.index("-pid") + 1] == "1":
            return "1 10M\n"
        raise OSError("measurement denied")

    monkeypatch.setattr(module.subprocess, "check_output", output)
    assert module.sample_process_tree_mb(1) is None


def test_f1_validator_memory_error_propagates(monkeypatch, tmp_path):
    module = load_script("run_bounds_evaluation")
    monkeypatch.setattr(module, "java_available", lambda: True)
    monitor = MagicMock()
    monitor.run.side_effect = MemoryError("resource stop")
    with pytest.raises(MemoryError, match="resource stop"):
        module._validator_summary(tmp_path / "feed.zip", tmp_path, monitor)


def test_f1_java_heap_reserves_parent_and_native_budget(monkeypatch, tmp_path):
    import transit_audit.validator.mobilitydata as module

    monkeypatch.setattr(module, "java_available", lambda: True)
    monkeypatch.setattr(module.Path, "exists", lambda self: True)
    completed = MagicMock(returncode=0, stdout=b"", stderr=b"")
    run = MagicMock(return_value=completed)
    monkeypatch.setattr(module.subprocess, "run", run)
    run_mobilitydata_validator(ROOT / "tests/fixtures/minimal_valid.zip", tmp_path,
                              memory_limit_mb=12288)
    heap = next(arg for arg in run.call_args.args[0] if arg.startswith("-Xmx"))
    assert int(heap[4:-1]) <= 8192


def test_f2_ranking_scope_and_soft_budget():
    module = load_script("render_corrected_results")
    payload = json.loads((ROOT / "docs/bounds_eval/evaluation.json").read_text())
    lines = "\n".join(module._ranking_section(payload["feeds"]["calgary"]))
    assert "time-selected subset" in lines
    assert "skipped impact is unknown" in lines.lower()
    assert "soft candidate-start" in lines
    assert "Exhaustive single-field" not in lines
    not_run = "\n".join(module._ranking_section(payload["feeds"]["ttc"]))
    assert "recomputation on" not in not_run
    method = (ROOT / "docs/routing-bounds.md").read_text()
    assert "proven zero" not in method
    assert "time-selected subset" in method
    assert "Wednesday" in (ROOT / "docs/milestones/M1_REPORT.md").read_text()
    for name in ["docs/PREREGISTRATION_AMENDMENT_2026-09-30.md",
                 "docs/milestones/FIX_REPORT_2026-09-30.md"]:
        assert "Superseded" in (ROOT / name).read_text()


def test_f3_tracked_logs_are_part_of_release_scan():
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    offenders = []
    for name in names:
        if not name or name.startswith("tests/"):
            continue
        try:
            content = (ROOT / name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, IsADirectoryError):
            continue
        if re.search(r"/(?:Users|home|var/folders)/", content):
            offenders.append(name)
    assert not offenders, offenders


def test_f4_exact_publisher_acknowledgements_and_dataset_links():
    manifests = json.loads((ROOT / "docs/bounds_eval/frozen_feed_manifests.json").read_text())
    for name, publisher in [("calgary", "City of Calgary"), ("edmonton", "City of Edmonton"),
                            ("ttc", "Toronto")]:
        assert manifests[name]["attribution"] == (
            f"Contains information licensed under the Open Government Licence \u2013 {publisher}."
        )
    for name in ["DATA_LICENSES.md", "docs/milestones/M0_REPORT.md"]:
        text = (ROOT / name).read_text()
        assert "gtfs-schedule-data)" not in text
        assert "npk7-z3bj" in text


@pytest.mark.parametrize("replacement", [b"bad replacement", OSError("interrupted stream")])
def test_f5_failed_force_refresh_preserves_snapshot_and_manifest(monkeypatch, tmp_path, replacement):
    module = load_script("fetch_gtfs")
    old = b"verified previous snapshot"
    spec = {"filename": "feed.zip", "sha256": hashlib.sha256(old).hexdigest(), "bytes": len(old),
            "url": "https://example.org/feed.zip", "licence_url": "https://example.org/licence",
            "attribution": "test"}
    monkeypatch.setattr(module, "FEEDS", {"test": spec})
    dest = tmp_path / "feed.zip"
    dest.write_bytes(old)
    manifest = tmp_path / "test_manifest.txt"
    manifest.write_text("original manifest\n")
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.side_effect = [replacement, b""] if isinstance(replacement, bytes) else replacement
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *args, **kwargs: response)
    with pytest.raises((ValueError, OSError)):
        module.fetch_feed("test", tmp_path, force=True)
    assert dest.read_bytes() == old
    assert manifest.read_text() == "original manifest\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["feed.zip", "test_manifest.txt"]


def test_f5_immutable_snapshot_bytes_and_acquisition_records():
    manifests = json.loads((ROOT / "docs/bounds_eval/frozen_feed_manifests.json").read_text())
    for spec in manifests.values():
        path = ROOT / spec["snapshot_path"]
        assert spec["sha256"] in path.name
        assert path.stat().st_size == spec["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == spec["sha256"]
        record = json.loads(path.with_suffix(".json").read_text())
        for key in ["sha256", "bytes", "url", "licence_url", "attribution"]:
            assert record[key] == spec[key]
        assert record["acquisition_date"] == "2026-09-30"


def test_f6_renderer_uses_stored_hardware(monkeypatch, tmp_path):
    module = load_script("render_corrected_results")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    (tmp_path / "docs").mkdir()
    for name in ["README.md", "docs/technical-report.md", "docs/index.md"]:
        (tmp_path / name).write_text("")
    payload = json.loads((ROOT / "docs/bounds_eval/evaluation.json").read_text())
    payload["hardware_note"] = "Test platform label"
    module.render_results(payload)
    text = (tmp_path / "RESULTS.md").read_text()
    assert "Test platform label" in text
    assert "Apple M3 Ultra" not in text


def test_f7_demo_json_reproduces_report_and_backlog(tmp_path):
    from transit_audit.reporting.backlog_export import write_backlog_csv, write_backlog_json

    folder = ROOT / "examples/demo"
    result = AuditResult.model_validate_json((folder / "results.json").read_text())
    report = tmp_path / "report.html"
    render_html_report(result, report)
    assert report.read_text() == (folder / "report.html").read_text()
    assert result.provenance.tool_version == "0.3.0"
    assert result.summary.metric_count == len(result.metrics) == 14
    write_backlog_json(result, tmp_path / "backlog.json")
    write_backlog_csv(result, tmp_path / "backlog.csv")
    for name in ["backlog.json", "backlog.csv"]:
        assert (tmp_path / name).read_text() == (folder / name).read_text()


@pytest.mark.parametrize("directory", ["docs/bounds_eval", "alternate"])
def test_f8_reports_link_actual_json_relative_to_destination(monkeypatch, tmp_path, directory):
    module = load_script("run_bounds_evaluation")
    monkeypatch.setattr("render_corrected_results.ROOT", tmp_path)
    (tmp_path / "docs").mkdir()
    for name in ["README.md", "docs/technical-report.md", "docs/index.md"]:
        (tmp_path / name).write_text("")
    payload = json.loads((ROOT / "docs/bounds_eval/evaluation.json").read_text())
    json_path = tmp_path / directory / "evaluation.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload))
    module._write_results_markdown(payload, json_path=json_path)
    for name in ["RESULTS.md", "docs/results.md"]:
        report = tmp_path / name
        text = report.read_text()
        match = re.search(r"\[Machine-readable output[^]]*\]\(([^)]+)\)", text)
        assert match
        assert (report.parent / match[1]).resolve() == json_path.resolve()


def test_f1_rss_fallback_has_explicit_type_and_discovery_failure_is_unavailable(monkeypatch):
    module = load_script("memory_monitor")

    def output(cmd, **kwargs):
        if cmd[0] == "pgrep":
            return ""
        if cmd[0] == "top":
            raise OSError("top denied")
        return "2048"

    monkeypatch.setattr(module.subprocess, "check_output", output)
    monitor = module.ProcessMemoryMonitor(100, root_pid=1)
    assert monitor.enforce("rss") == 2
    record = monitor.record()
    assert record["memory_measurement_type"] == "rss"
    assert record["memory_sample_complete"] is True
    assert record["certified_peak"] is False
    monkeypatch.setattr(module, "_child_pids", lambda pid: None)
    assert monitor.sample() is None
    record = monitor.record()
    assert record["memory_stop_enforcement"] == "could_not_be_enforced"
    assert record["memory_measurement_status"] == "unavailable"
    assert record["peak_memory_mb"] is None


def test_f1_java_insufficient_budget_fails(monkeypatch, tmp_path):
    import transit_audit.validator.mobilitydata as module

    monkeypatch.setattr(module, "java_available", lambda: True)
    monkeypatch.setattr(module.Path, "exists", lambda self: True)
    with pytest.raises(MemoryError, match="Insufficient process-tree budget"):
        run_mobilitydata_validator(ROOT / "tests/fixtures/minimal_valid.zip", tmp_path,
                                  memory_limit_mb=1024)


def test_f3_deliberate_private_prefixes_and_extensionless_text(monkeypatch, tmp_path):
    module = load_script("release_hygiene")
    assert not module.is_release_path(".review/anything.log")
    assert not module.is_release_path("state/p5/anything.log")
    assert module.is_release_path("docs/repair_logs/check.log")
    (tmp_path / "NOTICE").write_text("leaked " + "/" + "home" + "/private/file\n")
    monkeypatch.setattr(module.subprocess, "check_output", lambda *args, **kwargs: b"NOTICE\0")
    assert module.scan_release(tmp_path) == ["NOTICE:1: absolute/home path"]


def test_f6_platform_provenance_has_no_fabricated_mac_label(monkeypatch):
    module = load_script("run_bounds_evaluation")
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(module.platform, "processor", lambda: "")
    record = module._hardware_provenance(None)
    assert record["system"] == "Linux"
    assert record["machine"] == "x86_64"
    assert record["model"] is None
    assert record["physical_memory_bytes"] is None
    assert record["label_source"] == "platform"


def test_f7_bundle_manifest_records_artifact_digests():
    folder = ROOT / "examples/demo"
    manifest = json.loads((folder / "bundle_manifest.json").read_text())
    result = AuditResult.model_validate_json((folder / "results.json").read_text())
    assert manifest["provenance"] == result.provenance.model_dump(mode="json")
    for name, digest in manifest["artifact_sha256"].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest


def test_f1_resource_stop_terminates_descendants_deepest_first(monkeypatch):
    module = load_script("memory_monitor")
    monkeypatch.setattr(module, "_child_pids", lambda pid: [pid + 1] if pid < 4 else [])
    killed = []
    monkeypatch.setattr(module.os, "kill", lambda pid, sig: killed.append(pid))
    module._terminate_descendants(1)
    assert killed == [4, 3, 2]
