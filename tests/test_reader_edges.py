import zipfile
from pathlib import Path

import pytest

from transit_audit.gtfs.reader import GtfsFeed, parse_hhmmss, read_gtfs_zip

FIXTURES = Path(__file__).parent / "fixtures"


def test_missing_feed_file() -> None:
    with pytest.raises(FileNotFoundError):
        read_gtfs_zip(FIXTURES / "does_not_exist.zip")


def test_flex_not_present() -> None:
    feed = read_gtfs_zip(FIXTURES / "minimal_valid.zip")
    assert feed.flex_present() is False
    assert feed.flex_service_ids() == []


def test_parse_hhmmss_invalid() -> None:
    with pytest.raises(ValueError):
        parse_hhmmss("bad")


def test_macosx_entries_skipped(tmp_path: Path) -> None:
    path = tmp_path / "mac.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("__MACOSX/._stops.txt", "junk")
        archive.writestr(
            "stops.txt",
            "stop_id,stop_name,stop_lat,stop_lon\nS1,One,48.4,-123.3\n",
        )
    feed = read_gtfs_zip(path)
    assert len(feed.table("stops")) == 1


def test_table_default_empty() -> None:
    feed = GtfsFeed(path=FIXTURES / "minimal_valid.zip")
    assert feed.table("missing").empty
