"""Tests for the async process sampler (psutil mocked)."""

from __future__ import annotations

from collections.abc import Callable

import psutil
import pytest
from pytest_mock import MockerFixture

from mem_tui.models import ProcessInfo
from mem_tui.sampler import sample


class FakeProc:
    """Minimal stand-in for psutil.Process."""

    def __init__(
        self,
        pid: int,
        ppid: int,
        name: str,
        rss: int,
        cmdline: list[str] | None = None,
        raises: Exception | None = None,
    ) -> None:
        self.pid = pid
        self._ppid = ppid
        self._name = name
        self._rss = rss
        self._cmdline = cmdline if cmdline is not None else [name]
        self._raises = raises

    def ppid(self) -> int:
        return self._ppid

    def name(self) -> str:
        return self._name

    def memory_info(self) -> object:
        if self._raises is not None:
            raise self._raises
        return type("MemInfo", (), {"rss": self._rss})()

    def cmdline(self) -> list[str]:
        return self._cmdline


PatchIter = Callable[[list[FakeProc]], None]


@pytest.fixture
def patch_iter(mocker: MockerFixture) -> PatchIter:
    def _patch(procs: list[FakeProc]) -> None:
        mocker.patch("mem_tui.sampler.psutil.process_iter", return_value=iter(procs))

    return _patch


async def test_sample_returns_process_info_records(patch_iter: PatchIter) -> None:
    patch_iter([FakeProc(10, 1, "node", 2048, ["node", "server.js"])])

    result = await sample()

    assert result == [ProcessInfo(pid=10, ppid=1, name="node", rss=2048, cmdline="node server.js")]


async def test_vanished_process_is_skipped(patch_iter: PatchIter) -> None:
    procs = [
        FakeProc(1, 0, "good", 100),
        FakeProc(2, 0, "gone", 0, raises=psutil.NoSuchProcess(2)),
        FakeProc(3, 0, "denied", 0, raises=psutil.AccessDenied(3)),
    ]
    patch_iter(procs)

    result = await sample()

    assert [r.pid for r in result] == [1]


async def test_empty_cmdline_becomes_empty_string(patch_iter: PatchIter) -> None:
    patch_iter([FakeProc(5, 0, "kernel_task", 500, cmdline=[])])

    result = await sample()

    assert result[0].cmdline == ""


async def test_sample_returns_a_list(patch_iter: PatchIter) -> None:
    patch_iter([])

    result = await sample()

    assert result == []
