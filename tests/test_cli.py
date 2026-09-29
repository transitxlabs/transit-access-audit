from pathlib import Path

from typer.testing import CliRunner

from transit_audit.cli.app import app

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures"


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "audit" in result.stdout
    assert "validate" in result.stdout
    assert "report" in result.stdout


def test_checks_list() -> None:
    result = runner.invoke(app, ["checks", "list"])
    assert result.exit_code == 0
    assert "ACCESS.STOP.WHEELCHAIR.KNOWN" in result.stdout


def test_audit_command(tmp_path: Path) -> None:
    config = tmp_path / "audit.yml"
    config.write_text(
        "proximity_thresholds_m: [500]\n"
        "default_proximity_m: 500\n"
        "service_bands:\n"
        "  - name: peak\n"
        "    start_time: '07:00:00'\n"
        "    end_time: '09:00:00'\n"
        "    reference_stop_id: S1\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "audit",
            str(FIXTURES / "minimal_valid.zip"),
            "--config",
            str(config),
            "--census",
            str(FIXTURES / "census_tiny.gpkg"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )
    assert result.exit_code in (0, 1)
    out_dir = tmp_path / "out"
    run_dirs = [p for p in out_dir.iterdir() if p.is_dir()]
    assert run_dirs
    latest = sorted(run_dirs)[-1]
    assert (latest / "results.json").exists()
    assert (latest / "report.html").exists()


def test_validate_with_report() -> None:
    result = runner.invoke(
        app,
        [
            "validate",
            str(FIXTURES / "broken_references.zip"),
            "--report",
            str(FIXTURES / "validator_broken_references_report.json"),
        ],
    )
    assert result.exit_code == 1


def test_invalid_config_exit_code(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yml"
    bad.write_text("proximity_thresholds_m: []\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["audit", str(FIXTURES / "minimal_valid.zip"), "--config", str(bad)],
    )
    assert result.exit_code == 2
