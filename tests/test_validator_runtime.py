from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from transit_audit.validator.mobilitydata import (
    ingest_validator_report,
    java_available,
    run_mobilitydata_validator,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_java_available_bool() -> None:
    assert isinstance(java_available(), bool)


def test_run_validator_requires_java(tmp_path: Path) -> None:
    with (
        patch("transit_audit.validator.mobilitydata.java_available", return_value=False),
        pytest.raises(RuntimeError, match="Java runtime"),
    ):
        run_mobilitydata_validator(FIXTURES / "minimal_valid.zip", tmp_path)


def test_run_validator_missing_jar(tmp_path: Path) -> None:
    empty_vendor = tmp_path / "vendor"
    empty_vendor.mkdir()
    with (
        patch("transit_audit.validator.mobilitydata.java_available", return_value=True),
        patch("transit_audit.validator.mobilitydata._project_root", return_value=tmp_path),
        pytest.raises(FileNotFoundError, match="Pinned validator JAR"),
    ):
        run_mobilitydata_validator(FIXTURES / "minimal_valid.zip", tmp_path)


def test_run_validator_success(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text('{"version":"6.0.0","notices":[]}', encoding="utf-8")
    completed = MagicMock(returncode=0, stdout=b"ok", stderr=b"")
    with (
        patch("transit_audit.validator.mobilitydata.java_available", return_value=True),
        patch("transit_audit.validator.mobilitydata.Path.exists", return_value=True),
        patch("transit_audit.validator.mobilitydata.subprocess.run", return_value=completed),
    ):
        path = run_mobilitydata_validator(FIXTURES / "minimal_valid.zip", tmp_path)
    assert path == report
    findings, meta = ingest_validator_report(path)
    assert findings == []
    assert meta["validator_version"] == "6.0.0"


def test_run_validator_nonzero_exit(tmp_path: Path) -> None:
    completed = MagicMock(returncode=1, stdout=b"", stderr=b"failed")
    with (
        patch("transit_audit.validator.mobilitydata.java_available", return_value=True),
        patch("transit_audit.validator.mobilitydata.Path.exists", return_value=True),
        patch("transit_audit.validator.mobilitydata.subprocess.run", return_value=completed),
        pytest.raises(RuntimeError, match="failed"),
    ):
        run_mobilitydata_validator(FIXTURES / "minimal_valid.zip", tmp_path)


def test_run_validator_missing_report(tmp_path: Path) -> None:
    completed = MagicMock(returncode=0, stdout=b"", stderr=b"err")
    original_exists = Path.exists

    def exists_override(self: Path) -> bool:
        if self.name.endswith(".jar"):
            return True
        if self.name == "report.json":
            return False
        return original_exists(self)

    with (
        patch("transit_audit.validator.mobilitydata.java_available", return_value=True),
        patch.object(Path, "exists", exists_override),
        patch("transit_audit.validator.mobilitydata.subprocess.run", return_value=completed),
        pytest.raises(FileNotFoundError, match=r"report\.json"),
    ):
        run_mobilitydata_validator(FIXTURES / "minimal_valid.zip", tmp_path)
