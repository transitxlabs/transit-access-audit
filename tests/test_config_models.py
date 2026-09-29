from pathlib import Path

import pytest

from transit_audit.config import AuditConfig, default_enabled_checks, load_config
from transit_audit.models import AuditResult, Severity


def test_load_invalid_yaml(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yml"
    bad.write_text(":\n- oops\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config(bad)


def test_config_check_enabled_wildcards() -> None:
    config = AuditConfig(enabled_checks=["ACCESS.*"])
    assert config.is_check_enabled("ACCESS.STOP.WHEELCHAIR.KNOWN")
    assert not config.is_check_enabled("GTFS.FILES.REQUIRED")


def test_audit_result_schema_version() -> None:
    with pytest.raises(ValueError):
        AuditResult.model_validate(
            {
                "schema_version": "9.9",
                "tool": {"name": "x", "version": "0"},
                "input": {"feed_path": "a.zip"},
                "provenance": {
                    "tool_name": "x",
                    "tool_version": "0",
                    "executed_at": "2024-01-01T00:00:00Z",
                },
            }
        )


def test_severity_enum() -> None:
    assert Severity.ERROR.value == "error"


def test_default_enabled_checks() -> None:
    checks = default_enabled_checks()
    assert "GTFS.*" in checks
    assert "SERVICE.*" in checks


def test_validator_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError):
        AuditConfig(validator_timeout_seconds=0)
