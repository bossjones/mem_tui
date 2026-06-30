"""Bridge tree + collapse state + a rectangle into drawable treemap blocks.

A *block* is a single rectangle to paint. Internal (expanded) nodes are not
painted directly; instead their rectangle is subdivided among their children
plus a "self" slice representing the parent process's own resident memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mem_tui.colors import color_for
from mem_tui.tree import ProcessNode, top_level_ancestor
from mem_tui.treemap import Placed, Rect, squarify

BlockKind = Literal["leaf", "self"]


@dataclass(frozen=True, slots=True)
class Block:
    """A drawable rectangle tied to a process.

    Attributes:
        pid: The process this block represents.
        name: Process name for the label/status bar.
        color: Hex fill color (by top-level ancestor).
        own_rss: The process's own resident memory (bytes).
        subtree_rss: own RSS plus all descendants (bytes).
        child_count: Number of direct children.
        kind: "leaf" (whole subtree / childless process) or "self" (the own-RSS
            slice of an expanded parent).
        rect: Placement in cell coordinates.
    """

    pid: int
    name: str
    color: str
    own_rss: int
    subtree_rss: int
    child_count: int
    kind: BlockKind
    rect: Rect


def compute_blocks(root: ProcessNode, collapsed: set[int], rect: Rect) -> list[Block]:
    """Lay out the visible blocks for ``root`` given the collapsed set."""
    blocks: list[Block] = []
    _place_nodes(root.children, rect, root, collapsed, blocks)
    return blocks


def _place_nodes(
    nodes: list[ProcessNode],
    rect: Rect,
    root: ProcessNode,
    collapsed: set[int],
    out: list[Block],
) -> None:
    items: list[tuple[int, float]] = [(node.info.pid, float(node.subtree_rss)) for node in nodes]
    by_pid = {node.info.pid: node for node in nodes}

    for placed in squarify(items, rect):
        node = by_pid[_as_int(placed.item_id)]
        _emit(node, placed, root, collapsed, out)


def _emit(
    node: ProcessNode,
    placed: Placed,
    root: ProcessNode,
    collapsed: set[int],
    out: list[Block],
) -> None:
    is_collapsed = node.info.pid in collapsed
    if is_collapsed or not node.children:
        out.append(_make_block(node, root, "leaf", placed.rect))
        return

    # Expanded internal node: subdivide its rect among children + a self slice.
    children = list(node.children)
    items: list[tuple[int, float]] = [
        (child.info.pid, float(child.subtree_rss)) for child in children
    ]
    by_pid = {child.info.pid: child for child in children}

    self_key = -node.info.pid - 1  # negative sentinel id for the self slice
    if node.info.rss > 0:
        items.append((self_key, float(node.info.rss)))

    for sub in squarify(items, placed.rect):
        key = _as_int(sub.item_id)
        if key == self_key:
            out.append(_make_block(node, root, "self", sub.rect))
        else:
            _emit(by_pid[key], sub, root, collapsed, out)


def _make_block(node: ProcessNode, root: ProcessNode, kind: BlockKind, rect: Rect) -> Block:
    ancestor = top_level_ancestor(node, root)
    return Block(
        pid=node.info.pid,
        name=node.info.name,
        color=color_for(ancestor.info.pid),
        own_rss=node.info.rss,
        subtree_rss=node.subtree_rss,
        child_count=len(node.children),
        kind=kind,
        rect=rect,
    )


def _as_int(value: object) -> int:
    assert isinstance(value, int)
    return value


def block_at(blocks: list[Block], x: float, y: float) -> int | None:
    """Return the pid of the topmost block containing cell ``(x, y)``.

    Later blocks in the list are considered drawn on top, so they win ties.
    """
    for block in reversed(blocks):
        r = block.rect
        if r.x <= x < r.x + r.w and r.y <= y < r.y + r.h:
            return block.pid
    return None
