"""ZIP archive resource limits for GTFS ingestion."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass


@dataclass(frozen=True)
class ZipLimits:
    max_members: int = 256
    max_uncompressed_bytes: int = 256 * 1024 * 1024
    max_member_bytes: int = 64 * 1024 * 1024
    max_compression_ratio: float = 100.0


EVALUATION_ZIP_LIMITS = ZipLimits(
    max_members=512,
    max_uncompressed_bytes=1024 * 1024 * 1024,
    max_member_bytes=512 * 1024 * 1024,
    max_compression_ratio=200.0,
)


class ZipLimitExceededError(ValueError):
    """Raised when a ZIP archive exceeds configured safety limits."""


def validate_zip_member(
    info: zipfile.ZipInfo,
    limits: ZipLimits,
    total_uncompressed: int,
) -> int:
    if info.flag_bits & 0x1:
        raise ZipLimitExceededError(f"Encrypted ZIP member not allowed: {info.filename}")

    uncompressed = info.file_size
    if uncompressed > limits.max_member_bytes:
        raise ZipLimitExceededError(
            f"ZIP member {info.filename} exceeds per-member size limit "
            f"({uncompressed} > {limits.max_member_bytes})"
        )

    new_total = total_uncompressed + uncompressed
    if new_total > limits.max_uncompressed_bytes:
        raise ZipLimitExceededError(
            "ZIP total uncompressed size exceeds limit "
            f"({new_total} > {limits.max_uncompressed_bytes})"
        )

    if info.compress_size > 0 and uncompressed > 0:
        ratio = uncompressed / info.compress_size
        if ratio > limits.max_compression_ratio:
            raise ZipLimitExceededError(
                f"ZIP member {info.filename} compression ratio {ratio:.1f} exceeds limit "
                f"({limits.max_compression_ratio})"
            )

    return new_total
