"""Tests for mapping a clicked cell back to a block."""

from __future__ import annotations

from mem_tui.layout import Block, block_at
from mem_tui.treemap import Rect


def b(pid: int, x: float, y: float, w: float, h: float) -> Block:
    return Block(
        pid=pid,
        name=f"p{pid}",
        color="#4e79a7",
        own_rss=0,
        subtree_rss=0,
        child_count=0,
        kind="leaf",
        rect=Rect(x, y, w, h),
    )


def test_click_inside_block_returns_its_pid() -> None:
    blocks = [b(1, 0, 0, 10, 5), b(2, 10, 0, 10, 5)]

    assert block_at(blocks, 3, 2) == 1
    assert block_at(blocks, 15, 4) == 2


def test_click_outside_all_blocks_returns_none() -> None:
    blocks = [b(1, 0, 0, 5, 5)]

    assert block_at(blocks, 99, 99) is None


def test_topmost_block_wins_on_overlap() -> None:
    # later block drawn on top should win
    blocks = [b(1, 0, 0, 10, 10), b(2, 0, 0, 4, 4)]

    assert block_at(blocks, 1, 1) == 2
