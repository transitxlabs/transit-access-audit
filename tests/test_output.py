from pathlib import Path

import pytest

from transit_audit.output import prepare_output_dir


def test_prepare_output_nonempty_without_force(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "file.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="not empty"):
        prepare_output_dir(out, force_clean=False, use_run_subdir=False)


def test_prepare_output_not_directory(tmp_path: Path) -> None:
    path = tmp_path / "file"
    path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        prepare_output_dir(path, use_run_subdir=False)
