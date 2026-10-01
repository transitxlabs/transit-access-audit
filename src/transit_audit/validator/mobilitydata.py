"""Optional MobilityData GTFS Validator bridge."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from transit_audit.models import Finding, Severity

VALIDATOR_VERSION = "6.0.0"
VALIDATOR_JAR_NAMES = (
    f"gtfs-validator-{VALIDATOR_VERSION}-all.jar",
    f"gtfs-validator-{VALIDATOR_VERSION}-cli.jar",
)
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MAX_OUTPUT_BYTES = 1_048_576


def java_available() -> bool:
    return shutil.which("java") is not None


def _bounded_output(stdout: bytes, stderr: bytes, max_bytes: int) -> tuple[str, str]:
    return (
        stdout[:max_bytes].decode("utf-8", errors="replace"),
        stderr[:max_bytes].decode("utf-8", errors="replace"),
    )


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    return here.parents[3]


def run_mobilitydata_validator(
    feed_path: Path,
    output_dir: Path | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    memory_limit_mb: float | None = None,
    parent_memory_mb: float | None = None,
) -> Path:
    if not java_available():
        raise RuntimeError("Java runtime not available for MobilityData validator")

    feed_path = feed_path.resolve()
    if not feed_path.is_file():
        raise FileNotFoundError(f"GTFS feed not found: {feed_path}")

    jar_path: Path | None = None
    vendor_dir = _project_root() / "vendor"
    for jar_name in VALIDATOR_JAR_NAMES:
        candidate = vendor_dir / jar_name
        if candidate.exists():
            jar_path = candidate
            break
    if jar_path is None:
        raise FileNotFoundError(
            f"Pinned validator JAR not found in {vendor_dir} "
            f"(expected one of: {', '.join(VALIDATOR_JAR_NAMES)}). "
            "Place the MobilityData validator JAR in vendor/ or ingest report.json directly."
        )

    temp_output: tempfile.TemporaryDirectory[str] | None = None
    if output_dir is None:
        temp_output = tempfile.TemporaryDirectory(prefix="transit-audit-validator-")
        resolved_output = Path(temp_output.name)
    else:
        resolved_output = output_dir.resolve()
        resolved_output.mkdir(parents=True, exist_ok=True)

    report_path = resolved_output / "report.json"
    java_cmd = ["java"]
    if memory_limit_mb is not None:
        # Reserve observed parent memory (or a conservative allocation) and native JVM space.
        parent_reserve = max(2048.0, parent_memory_mb or 0.0)
        native_reserve = max(1024.0, memory_limit_mb * 0.25)
        heap_mb = int(memory_limit_mb - parent_reserve - native_reserve)
        if heap_mb < 256:
            raise MemoryError("Insufficient process-tree budget for parent, native JVM and Java heap")
        java_cmd.extend([f"-Xmx{heap_mb}m"])
    java_cmd.extend(
        [
            "-jar",
            str(jar_path.resolve()),
            "-i",
            str(feed_path),
            "-o",
            str(resolved_output),
        ]
    )
    cmd = java_cmd

    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = _bounded_output(
            exc.stdout or b"",
            exc.stderr or b"",
            max_output_bytes,
        )
        raise TimeoutError(
            f"MobilityData validator timed out after {timeout_seconds}s. stderr: {stderr[:500]}"
        ) from exc

    stdout, stderr = _bounded_output(completed.stdout, completed.stderr, max_output_bytes)
    if completed.returncode != 0:
        raise RuntimeError(
            f"MobilityData validator failed (exit {completed.returncode}). stderr: {stderr[:500]}"
        )

    if not report_path.exists():
        raise FileNotFoundError(
            f"Validator did not produce report.json. stdout: {stdout[:200]} stderr: {stderr[:200]}"
        )

    return report_path


def ingest_validator_report(report_path: Path) -> tuple[list[Finding], dict[str, Any]]:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    findings: list[Finding] = []
    notices = payload.get("notices", [])
    for notice in notices:
        code = str(notice.get("code", "UNKNOWN"))
        severity_raw = str(notice.get("severity", "INFO")).lower()
        severity = Severity.ERROR if severity_raw == "error" else Severity.WARNING
        findings.append(
            Finding(
                check_id=f"GTFS.MD.{code}",
                severity=severity,
                message=str(notice.get("summary", code)),
                evidence={"notice": notice},
                suggested_action="Resolve MobilityData validator notice in source GTFS.",
            )
        )
    provenance = {
        "validator_name": "MobilityData GTFS Validator",
        "validator_version": str(payload.get("version", VALIDATOR_VERSION)),
        "executed_at": datetime.now(UTC).isoformat(),
    }
    return findings, provenance
