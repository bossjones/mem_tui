"""Shared data models with no external dependencies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    """A single process snapshot.

    Attributes:
        pid: Process id.
        ppid: Parent process id (0 for the kernel/root on macOS).
        name: Process name.
        rss: Resident set size in bytes (physical RAM held).
        cmdline: Full command line, joined with spaces.
    """

    pid: int
    ppid: int
    name: str
    rss: int
    cmdline: str
