"""Typer CLI for transit-access-audit."""

from __future__ import annotations

import json
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from transit_audit.checks.registry import CHECK_SOURCES
from transit_audit.config import load_config
from transit_audit.engine import run_audit
from transit_audit.models import AuditResult, Severity
from transit_audit.output import prepare_output_dir
from transit_audit.reporting.backlog_export import write_backlog_csv, write_backlog_json
from transit_audit.reporting.html import render_html_report
from transit_audit.reporting.json_output import write_results_json
from transit_audit.routing.bounds import bounds_to_dict, compute_bounds
from transit_audit.routing.models import BoundsConfig
from transit_audit.validator.mobilitydata import (
    ingest_validator_report,
    java_available,
    run_mobilitydata_validator,
)
from transit_audit.version import __version__

app = typer.Typer(
    name="transit-audit",
    help="Audit Canadian GTFS feeds for accessibility data coverage and service access metrics.",
    no_args_is_help=True,
)


class ExitCode(int, Enum):
    OK = 0
    THRESHOLD_EXCEEDED = 1
    INVALID_ARGS = 2
    PROCESSING_ERROR = 3


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(code=ExitCode.OK.value)


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """Transit access audit CLI."""


checks_app = typer.Typer(help="Inspect available checks.")
app.add_typer(checks_app, name="checks")


@checks_app.command("list")
def checks_list() -> None:
    """List known check and metric IDs with sources."""
    for check_id, source in sorted(CHECK_SOURCES.items()):
        typer.echo(f"{check_id}\t{source}")


@app.command()
def validate(
    feed: Annotated[Path, typer.Argument(help="GTFS ZIP feed path")],
    report: Annotated[Path | None, typer.Option(help="Existing validator report.json")] = None,
    output_dir: Annotated[Path, typer.Option(help="Validator output directory")] = Path(
        ".transit-audit-validator"
    ),
    timeout_seconds: Annotated[int, typer.Option(help="Validator subprocess timeout")] = 300,
) -> None:
    """Run or ingest MobilityData GTFS Validator output."""
    try:
        if report is not None:
            findings, _ = ingest_validator_report(report)
        elif java_available():
            report_path = run_mobilitydata_validator(
                feed,
                output_dir,
                timeout_seconds=timeout_seconds,
            )
            findings, _ = ingest_validator_report(report_path)
        else:
            typer.echo(
                "Java not available; provide --report with an existing report.json",
                err=True,
            )
            raise typer.Exit(code=ExitCode.INVALID_ARGS.value)
        errors = [f for f in findings if f.severity == Severity.ERROR]
        raise typer.Exit(code=ExitCode.THRESHOLD_EXCEEDED.value if errors else ExitCode.OK.value)
    except typer.Exit:
        raise
    except Exception as exc:
        typer.echo(f"Validation failed: {exc}", err=True)
        raise typer.Exit(code=ExitCode.PROCESSING_ERROR.value) from exc


@app.command()
def audit(
    feed: Annotated[Path, typer.Argument(help="GTFS ZIP feed path")],
    config: Annotated[Path | None, typer.Option("--config", help="YAML audit config")] = None,
    census: Annotated[Path | None, typer.Option("--census", help="Census GeoPackage")] = None,
    validator_report: Annotated[
        Path | None, typer.Option("--validator-report", help="MobilityData report.json")
    ] = None,
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Output directory")] = Path(
        "audit-output"
    ),
    force_clean: Annotated[
        bool, typer.Option("--force-clean", help="Clean exporter-owned output directory")
    ] = False,
    no_run_subdir: Annotated[
        bool,
        typer.Option(
            "--no-run-subdir",
            help="Write directly to output-dir instead of a timestamped run subdirectory",
        ),
    ] = False,
    severity: Annotated[
        str | None, typer.Option(help="Filter backlog severity")
    ] = None,
    category: Annotated[str | None, typer.Option(help="Filter backlog category")] = None,
) -> None:
    """Run a full transit access audit."""
    try:
        cfg = load_config(config)
        result = run_audit(
            feed_path=feed,
            config_path=config,
            census_path=census,
            validator_report_path=validator_report,
        )
        resolved_output = prepare_output_dir(
            output_dir,
            force_clean=force_clean,
            use_run_subdir=not no_run_subdir,
        )
        _write_outputs(result, resolved_output, severity=severity, category=category)
        typer.echo(f"Wrote outputs to {resolved_output}")
        exit_code = _exit_code_for_result(result, cfg)
        raise typer.Exit(code=exit_code)
    except ValueError as exc:
        typer.echo(f"Invalid configuration: {exc}", err=True)
        raise typer.Exit(code=ExitCode.INVALID_ARGS.value) from exc
    except typer.Exit:
        raise
    except Exception as exc:
        typer.echo(f"Audit failed: {exc}", err=True)
        raise typer.Exit(code=ExitCode.PROCESSING_ERROR.value) from exc


@app.command()
def bounds(
    feed: Annotated[Path, typer.Argument(help="GTFS ZIP feed path")],
    output: Annotated[Path, typer.Option("--output", help="JSON bounds output path")] = Path(
        "bounds-results.json"
    ),
    service_date: Annotated[str, typer.Option(help="Service date YYYY-MM-DD")] = "2024-06-03",
    departure_time: Annotated[str, typer.Option(help="Departure time HH:MM:SS")] = "08:00:00",
    max_travel_minutes: Annotated[int, typer.Option(help="Maximum travel time in minutes")] = 60,
    max_transfers: Annotated[int, typer.Option(help="Maximum transfers allowed")] = 2,
    min_transfer_minutes: Annotated[int, typer.Option(help="Minimum transfer time")] = 5,
    origin_count: Annotated[int, typer.Option(help="Number of sampled origins")] = 25,
    destination_count: Annotated[int, typer.Option(help="Number of sampled destinations")] = 50,
    random_seed: Annotated[int, typer.Option(help="Random seed for sampling")] = 42,
) -> None:
    """Compute optimistic/pessimistic accessibility routing bounds."""
    try:
        parsed_date = date.fromisoformat(service_date)
        config = BoundsConfig(
            service_date=parsed_date,
            departure_time=departure_time,
            max_travel_minutes=max_travel_minutes,
            max_transfers=max_transfers,
            min_transfer_minutes=min_transfer_minutes,
            origin_count=origin_count,
            destination_count=destination_count,
            random_seed=random_seed,
        )
        result = compute_bounds(feed, config)
        output.write_text(
            json.dumps(bounds_to_dict(result), indent=2, default=str),
            encoding="utf-8",
        )
        typer.echo(
            f"Wrote {output} "
            f"(mean interval width={result.mean_interval_width:.3f}, "
            f"runtime={result.runtime_seconds:.2f}s)"
        )
    except ValueError as exc:
        typer.echo(f"Invalid arguments: {exc}", err=True)
        raise typer.Exit(code=ExitCode.INVALID_ARGS.value) from exc
    except Exception as exc:
        typer.echo(f"Bounds analysis failed: {exc}", err=True)
        raise typer.Exit(code=ExitCode.PROCESSING_ERROR.value) from exc


@app.command()
def report(
    results: Annotated[Path, typer.Argument(help="results.json path")],
    output: Annotated[Path, typer.Option("-o", "--output", help="HTML output path")] = Path(
        "report.html"
    ),
) -> None:
    """Render an HTML report from results.json."""
    try:
        payload = json.loads(results.read_text(encoding="utf-8"))
        audit_result = AuditResult.model_validate(payload)
        render_html_report(audit_result, output)
        typer.echo(f"Wrote {output}")
    except Exception as exc:
        typer.echo(f"Report rendering failed: {exc}", err=True)
        raise typer.Exit(code=ExitCode.PROCESSING_ERROR.value) from exc


def _write_outputs(
    result: AuditResult,
    output_dir: Path,
    severity: str | None,
    category: str | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_results_json(result, output_dir / "results.json")
    render_html_report(result, output_dir / "report.html")
    sev = Severity(severity) if severity else None
    write_backlog_json(result, output_dir / "backlog.json", severity=sev, category=category)
    write_backlog_csv(result, output_dir / "backlog.csv", severity=sev, category=category)


def _exit_code_for_result(result: AuditResult, config: object) -> int:
    threshold = getattr(config, "severity_fail_threshold", "error")
    if threshold == "error" and result.summary.error_count > 0:
        return ExitCode.THRESHOLD_EXCEEDED.value
    if threshold == "warning" and (result.summary.error_count + result.summary.warning_count) > 0:
        return ExitCode.THRESHOLD_EXCEEDED.value
    return ExitCode.OK.value


if __name__ == "__main__":
    app()
