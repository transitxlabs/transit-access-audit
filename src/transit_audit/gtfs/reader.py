"""Read GTFS data from ZIP archives."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from transit_audit.gtfs.zip_limits import ZipLimitExceededError, ZipLimits, validate_zip_member

DEFAULT_ZIP_LIMITS = ZipLimits()


@dataclass
class GtfsFeed:
    path: Path
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)

    def has_table(self, name: str) -> bool:
        return name in self.tables

    def table(self, name: str) -> pd.DataFrame:
        return self.tables.get(name, pd.DataFrame())

    def flex_present(self) -> bool:
        return any(
            self.has_table(name)
            for name in ("locations", "location_groups", "booking_rules", "timetables")
        ) or self.has_table("locations_geojson")

    def flex_service_ids(self) -> list[str]:
        if not self.flex_present():
            return []
        trips = self.table("trips")
        if trips.empty:
            return []
        return sorted(trips["route_id"].astype(str).unique().tolist())


def _read_csv_from_zip(archive: zipfile.ZipFile, member: str) -> pd.DataFrame:
    with archive.open(member) as handle:
        return pd.read_csv(handle, dtype=str, keep_default_na=False)


def read_gtfs_zip(
    path: Path,
    limits: ZipLimits | None = None,
    *,
    only_tables: set[str] | None = None,
) -> GtfsFeed:
    if not path.exists():
        raise FileNotFoundError(f"GTFS feed not found: {path}")
    if not zipfile.is_zipfile(path):
        raise ValueError(f"Not a valid ZIP archive: {path}")

    zip_limits = limits or DEFAULT_ZIP_LIMITS
    loaded: dict[str, pd.DataFrame] = {}
    with zipfile.ZipFile(path) as archive:
        all_members = [
            m for m in archive.namelist() if not m.endswith("/") and not m.startswith("__MACOSX")
        ]
        if len(all_members) > zip_limits.max_members:
            raise ZipLimitExceededError(
                f"ZIP member count {len(all_members)} exceeds limit {zip_limits.max_members}"
            )

        total_uncompressed = 0
        for member in all_members:
            info = archive.getinfo(member)
            total_uncompressed = validate_zip_member(info, zip_limits, total_uncompressed)

        members = [
            m for m in all_members if m.lower().endswith(".txt") or m.lower().endswith(".geojson")
        ]

        for member in members:
            if not member.lower().endswith(".txt"):
                continue
            table_name = Path(member).name.replace(".txt", "")
            if only_tables is not None and table_name not in only_tables:
                continue
            try:
                loaded[table_name] = _read_csv_from_zip(archive, member)
            except Exception as exc:
                raise ValueError(f"Failed to read {member}: {exc}") from exc

        if only_tables is None and "locations.geojson" in archive.namelist():
            with archive.open("locations.geojson") as handle:
                loaded["locations_geojson"] = pd.DataFrame(
                    [{"raw": handle.read().decode("utf-8", errors="replace")}]
                )

    return GtfsFeed(path=path, tables=loaded)


def parse_hhmmss(value: str) -> int:
    parts = value.strip().split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid time: {value}")
    hours, minutes, seconds = (int(p) for p in parts)
    if hours < 0:
        raise ValueError(f"Invalid time (negative hours): {value}")
    if not (0 <= minutes <= 59):
        raise ValueError(f"Invalid time (minutes out of range): {value}")
    if not (0 <= seconds <= 59):
        raise ValueError(f"Invalid time (seconds out of range): {value}")
    return hours * 3600 + minutes * 60 + seconds


def seconds_to_hhmmss(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
