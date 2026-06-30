"""Async process sampler built on psutil.

The blocking psutil enumeration runs in a worker thread so the Textual event
loop never stalls during a refresh.
"""

from __future__ import annotations

import asyncio

import psutil

from mem_tui.models import ProcessInfo


async def sample() -> list[ProcessInfo]:
    """Snapshot all visible processes as ``ProcessInfo`` records.

    psutil work is offloaded to a thread; processes that vanish or deny access
    mid-enumeration are skipped rather than raising.
    """
    return await asyncio.to_thread(_collect)


def _collect() -> list[ProcessInfo]:
    records: list[ProcessInfo] = []
    for proc in psutil.process_iter():
        info = _extract(proc)
        if info is not None:
            records.append(info)
    return records


def _extract(proc: psutil.Process) -> ProcessInfo | None:
    """Pull a single process's fields, returning None if it is inaccessible."""
    try:
        return ProcessInfo(
            pid=proc.pid,
            ppid=proc.ppid(),
            name=proc.name(),
            rss=proc.memory_info().rss,
            cmdline=" ".join(proc.cmdline()),
        )
    except psutil.Error:
        return None
