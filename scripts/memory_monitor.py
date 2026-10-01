"""Continuous sampled process-tree memory checks, not certified peak limits."""
from __future__ import annotations

import _thread
import os
import signal
import subprocess
import threading
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


def _child_pids(root_pid: int) -> list[int] | None:
    try:
        output = subprocess.check_output(["pgrep", "-P", str(root_pid)], text=True, timeout=5, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as exc:
        return [] if exc.returncode == 1 else None
    except (subprocess.SubprocessError, OSError):
        return None
    try:
        return [int(line) for line in output.splitlines() if line.strip()]
    except ValueError:
        return None


def _terminate_descendants(root_pid: int) -> None:
    pending = [root_pid]
    descendants: list[int] = []
    seen = {root_pid}
    while pending:
        children = _child_pids(pending.pop())
        for child in children or []:
            if child not in seen:
                seen.add(child)
                descendants.append(child)
                pending.append(child)
    for child in reversed(descendants):
        with suppress(OSError):
            os.kill(child, signal.SIGTERM)


def _parse_top_memory_mb(output: str, pid: int) -> float | None:
    for line in output.splitlines():
        parts = line.split()
        if len(parts) != 2 or parts[0] != str(pid):
            continue
        token = parts[1].rstrip("+-")
        factor = {"G": 1024.0, "M": 1.0, "K": 1 / 1024}.get(token[-1:])
        if factor is not None:
            try:
                return float(token[:-1]) * factor
            except ValueError:
                pass
    return None


@dataclass(frozen=True)
class MemorySample:
    mb: float | None
    measurement_type: str
    complete: bool
    reason: str | None = None


def sample_process_tree(root_pid: int | None = None) -> MemorySample:
    """Discover all generations; reject discovery failures and partial totals."""
    pid = root_pid or os.getpid()
    pending = [pid]
    seen: set[int] = set()
    while pending:
        candidate = pending.pop()
        if candidate in seen:
            continue
        seen.add(candidate)
        children = _child_pids(candidate)
        if children is None:
            return MemorySample(None, "unavailable", False, "descendant_discovery_failed")
        pending.extend(children)

    for measurement in ("top_mem", "rss"):
        total = 0.0
        complete = True
        for candidate in sorted(seen):
            try:
                if measurement == "top_mem":
                    output = subprocess.check_output(
                        ["top", "-l", "1", "-pid", str(candidate), "-stats", "pid,mem"],
                        text=True, timeout=5, stderr=subprocess.DEVNULL,
                    )
                    value = _parse_top_memory_mb(output, candidate)
                else:
                    output = subprocess.check_output(
                        ["ps", "-o", "rss=", "-p", str(candidate)], text=True, timeout=5, stderr=subprocess.DEVNULL,
                    )
                    value = int(output.strip()) / 1024.0
                if value is None or value <= 0:
                    complete = False
                    break
                total += value
            except (subprocess.SubprocessError, ValueError, OSError):
                complete = False
                break
        if complete:
            return MemorySample(total, measurement, True)
    return MemorySample(None, "unavailable", False, "complete_tree_measurement_unavailable")


def sample_process_tree_mb(root_pid: int | None = None) -> float | None:
    return sample_process_tree(root_pid).mb


class ProcessMemoryMonitor:
    """Interrupt on an observed excess; sampling can miss between-sample peaks."""

    def __init__(self, limit_mb: float, *, root_pid: int | None = None,
                 interval_seconds: float = 0.25) -> None:
        self.limit_mb = limit_mb
        self.root_pid = root_pid or os.getpid()
        self.interval_seconds = interval_seconds
        self.peak_mb: float | None = None
        self.measurement_status = "not_sampled"
        self.measurement_type = "unavailable"
        self.complete = False
        self.unavailable_samples = 0
        self.sample_count = 0
        self.peaks_by_type: dict[str, float] = {}
        self._stop = threading.Event()
        self._violation: MemoryError | None = None
        self._watcher: threading.Thread | None = None
        self._lock = threading.Lock()

    def sample(self) -> float | None:
        with self._lock:
            sample = sample_process_tree(self.root_pid)
            self.sample_count += 1
            self.complete = sample.complete
            self.measurement_type = sample.measurement_type
            if sample.mb is None:
                self.unavailable_samples += 1
                self.measurement_status = "unavailable"
                return None
            self.measurement_status = f"sampled_complete_{sample.measurement_type}"
            self.peaks_by_type[sample.measurement_type] = max(
                self.peaks_by_type.get(sample.measurement_type, 0), sample.mb,
            )
            # Do not merge RSS and top MEM into an unlabeled peak.
            self.peak_mb = self.peaks_by_type[sample.measurement_type]
            return sample.mb

    def enforce(self, label: str) -> float | None:
        if self._violation is not None:
            raise self._violation
        observed = self.sample()
        if observed is not None and observed > self.limit_mb:
            raise MemoryError(
                f"{label} exceeded {self.limit_mb:.0f} MB limit (observed {observed:.0f} MB)"
            )
        return observed

    def _watch(self, label: str) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self.enforce(label)
            except MemoryError as exc:
                self._violation = exc
                _terminate_descendants(self.root_pid)
                _thread.interrupt_main()
                return

    def record(self) -> dict[str, object]:
        return {
            "peak_memory_mb": self.peak_mb if self.complete else None,
            "memory_scope": "evaluation_process_tree_cumulative",
            "memory_measurement_status": self.measurement_status,
            "memory_measurement_type": self.measurement_type,
            "memory_sample_complete": self.complete,
            "sample_count": self.sample_count,
            "unavailable_samples": self.unavailable_samples,
            "sampled_peaks_mb_by_type": dict(self.peaks_by_type),
            "memory_limit_mb": self.limit_mb,
            "memory_stop_enforcement": (
                "could_not_be_enforced" if not self.sample_count or self.unavailable_samples
                else "sampled_observations_only"
            ),
            "certified_peak": False,
            "limitation": "Discovery and per-process samples are not atomic; transient peaks may be missed. "
                          "RSS excludes compressed/swapped memory. Interruption of native calls may be delayed.",
        }

    def run(self, label: str, func: Callable[[], T]) -> T:
        self.enforce(f"{label} pre")
        if self._watcher is not None:
            result = func()
            self.enforce(f"{label} post")
            return result
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("Continuous memory checks require the main thread")
        self._stop.clear()
        self._watcher = threading.Thread(target=self._watch, args=(label,), daemon=True)
        self._watcher.start()
        try:
            result = func()
        except KeyboardInterrupt:
            if self._violation is not None:
                raise self._violation from None
            raise
        finally:
            self._stop.set()
            self._watcher.join()
            self._watcher = None
        self.enforce(f"{label} post")
        return result
