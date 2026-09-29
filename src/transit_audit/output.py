"""Safe audit output directory management."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

EXPORTER_MARKER = ".transit-audit-output"


def is_exporter_owned(path: Path) -> bool:
    return (path / EXPORTER_MARKER).is_file()


def write_exporter_marker(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    marker = path / EXPORTER_MARKER
    marker.write_text(
        "This directory was created by transit-access-audit.\n",
        encoding="utf-8",
    )


def prepare_output_dir(
    output_dir: Path,
    force_clean: bool = False,
    use_run_subdir: bool = True,
) -> Path:
    """Prepare a safe output directory, never deleting arbitrary user data."""
    if use_run_subdir:
        run_dir = output_dir / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        run_dir.mkdir(parents=True, exist_ok=False)
        write_exporter_marker(run_dir)
        return run_dir

    if output_dir.exists():
        if not output_dir.is_dir():
            raise ValueError(f"Output path exists and is not a directory: {output_dir}")
        contents = list(output_dir.iterdir())
        if contents:
            if not force_clean:
                raise ValueError(
                    f"Output directory {output_dir} is not empty. "
                    "Use a new path, omit --no-run-subdir for timestamped runs, "
                    "or pass --force-clean on an exporter-owned directory."
                )
            if not is_exporter_owned(output_dir):
                raise ValueError(
                    f"Output directory {output_dir} is not exporter-owned "
                    f"(missing {EXPORTER_MARKER} marker). Refusing to delete."
                )
            shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_exporter_marker(output_dir)
    return output_dir
