"""Tests for per-cell block styling (bevel borders + selection)."""

from __future__ import annotations

from mem_tui.layout import Block
from mem_tui.render import Cell, block_cell
from mem_tui.treemap import Rect

BASE = "#4e79a7"


def block(x: float, y: float, w: float, h: float) -> Block:
    return Block(
        pid=1,
        name="p",
        color=BASE,
        own_rss=0,
        subtree_rss=0,
        child_count=0,
        kind="leaf",
        rect=Rect(x, y, w, h),
    )


def test_interior_cell_uses_base_color() -> None:
    b = block(0, 0, 10, 6)
    cell = block_cell(b, x=5, y=3, left=0, top=0, right=10, bottom=6, selected=False)

    assert isinstance(cell, Cell)
    assert cell.bg == BASE


def test_top_left_edge_is_lighter_than_base() -> None:
    b = block(0, 0, 10, 6)
    top = block_cell(b, x=5, y=0, left=0, top=0, right=10, bottom=6, selected=False)
    left = block_cell(b, x=0, y=3, left=0, top=0, right=10, bottom=6, selected=False)

    assert top.bg != BASE
    assert left.bg != BASE
    assert top.bg == left.bg  # both highlight shade


def test_bottom_right_edge_is_darker_than_base() -> None:
    b = block(0, 0, 10, 6)
    bottom = block_cell(b, x=5, y=5, left=0, top=0, right=10, bottom=6, selected=False)
    right = block_cell(b, x=9, y=3, left=0, top=0, right=10, bottom=6, selected=False)

    assert bottom.bg != BASE
    assert right.bg == bottom.bg


def test_highlight_and_shadow_differ() -> None:
    b = block(0, 0, 10, 6)
    hi = block_cell(b, x=0, y=0, left=0, top=0, right=10, bottom=6, selected=False)
    sh = block_cell(b, x=9, y=5, left=0, top=0, right=10, bottom=6, selected=False)

    assert hi.bg != sh.bg


def test_selected_edge_is_white() -> None:
    b = block(0, 0, 10, 6)
    edge = block_cell(b, x=0, y=0, left=0, top=0, right=10, bottom=6, selected=True)

    assert edge.bg == "#ffffff"


def test_tiny_block_stays_solid_base() -> None:
    # a 1x1 block must remain its own color (not collapse to a border shade)
    b = block(0, 0, 1, 1)
    cell = block_cell(b, x=0, y=0, left=0, top=0, right=1, bottom=1, selected=False)

    assert cell.bg == BASE
