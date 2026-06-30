"""Flatten the process tree into indented ps-style rows for the tree view."""

from __future__ import annotations

from dataclasses import dataclass

from mem_tui.format import human_bytes
from mem_tui.tree import ProcessNode

_ROOT_PID = 0


@dataclass(frozen=True, slots=True)
class TreeRow:
    """One rendered line of the ps-tree view.

    Attributes:
        pid: Process id.
        depth: Indentation depth (top-level processes are depth 0).
        name: Process name.
        own_rss: The process's own resident memory (bytes).
        subtree_rss: own RSS plus all descendants (bytes).
        child_count: Number of direct children.
        collapsed: True if this node's children are hidden.
        prefix: The branch-glyph prefix (e.g. ``"│   ├── "``).
    """

    pid: int
    depth: int
    name: str
    own_rss: int
    subtree_rss: int
    child_count: int
    collapsed: bool
    prefix: str


def build_rows(root: ProcessNode, collapsed: set[int]) -> list[TreeRow]:
    """Depth-first list of rows, children ordered by subtree RSS (desc)."""
    rows: list[TreeRow] = []
    _visit(root.children, collapsed, depth=0, ancestor_last=[], out=rows)
    return rows


def _visit(
    nodes: list[ProcessNode],
    collapsed: set[int],
    depth: int,
    ancestor_last: list[bool],
    out: list[TreeRow],
) -> None:
    ordered = sorted(nodes, key=lambda n: (-n.subtree_rss, n.info.pid))
    for index, node in enumerate(ordered):
        is_last = index == len(ordered) - 1
        is_collapsed = node.info.pid in collapsed and bool(node.children)
        out.append(
            TreeRow(
                pid=node.info.pid,
                depth=depth,
                name=node.info.name,
                own_rss=node.info.rss,
                subtree_rss=node.subtree_rss,
                child_count=len(node.children),
                collapsed=is_collapsed,
                prefix=_prefix(ancestor_last, depth, is_last),
            )
        )
        if node.children and not is_collapsed:
            _visit(node.children, collapsed, depth + 1, [*ancestor_last, is_last], out)


def format_tree_line(row: TreeRow, total_rss: int) -> str:
    """Render a single tree row as plain text (marker, name, memory, share)."""
    if row.collapsed:
        marker = "▶"
    elif row.child_count > 0:
        marker = "▼"
    else:
        marker = "·"
    pct = (row.subtree_rss / total_rss * 100) if total_rss else 0.0
    kids = f"{row.child_count} kids" if row.child_count else ""
    return (
        f"{marker} {row.prefix}{row.name}  "
        f"pid {row.pid}  own {human_bytes(row.own_rss)}  "
        f"Σ {human_bytes(row.subtree_rss)} ({pct:.1f}%)  {kids}".rstrip()
    )


def _prefix(ancestor_last: list[bool], depth: int, is_last: bool) -> str:
    if depth == 0:
        return "└── " if is_last else "├── "
    trunk = "".join("    " if last else "│   " for last in ancestor_last)
    connector = "└── " if is_last else "├── "
    return trunk + connector
