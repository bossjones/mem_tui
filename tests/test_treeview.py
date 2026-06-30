"""Tests for the ps-style indented tree row builder."""

from __future__ import annotations

from mem_tui.models import ProcessInfo
from mem_tui.tree import build_tree
from mem_tui.treeview import TreeRow, build_rows, format_tree_line

MB = 1024 * 1024


def p(pid: int, ppid: int, name: str, rss_mb: int) -> ProcessInfo:
    return ProcessInfo(pid=pid, ppid=ppid, name=name, rss=rss_mb * MB, cmdline=name)


def by_pid(rows: list[TreeRow], pid: int) -> TreeRow:
    return next(r for r in rows if r.pid == pid)


def test_rows_exclude_synthetic_root() -> None:
    root = build_tree([p(10, 0, "solo", 5)])

    rows = build_rows(root, collapsed=set())

    assert [r.pid for r in rows] == [10]
    assert isinstance(rows[0], TreeRow)


def test_children_sorted_by_subtree_rss_desc() -> None:
    procs = [
        p(1, 0, "parent", 1),
        p(2, 1, "small", 10),
        p(3, 1, "big", 90),
        p(4, 1, "medium", 50),
    ]
    root = build_tree(procs)

    rows = build_rows(root, collapsed=set())
    child_pids = [r.pid for r in rows if r.depth == 1]

    assert child_pids == [3, 4, 2]  # 90, 50, 10


def test_depth_increases_for_descendants() -> None:
    procs = [p(1, 0, "a", 10), p(2, 1, "b", 10), p(3, 2, "c", 10)]
    root = build_tree(procs)

    rows = build_rows(root, collapsed=set())

    assert by_pid(rows, 1).depth == 0
    assert by_pid(rows, 2).depth == 1
    assert by_pid(rows, 3).depth == 2


def test_collapsed_node_hides_descendants() -> None:
    procs = [p(1, 0, "a", 10), p(2, 1, "b", 10), p(3, 2, "c", 10)]
    root = build_tree(procs)

    rows = build_rows(root, collapsed={1})

    assert {r.pid for r in rows} == {1}
    assert by_pid(rows, 1).collapsed is True
    assert by_pid(rows, 1).child_count == 1


def test_branch_glyphs_mark_last_sibling() -> None:
    procs = [p(1, 0, "parent", 1), p(2, 1, "first", 50), p(3, 1, "last", 10)]
    root = build_tree(procs)

    rows = build_rows(root, collapsed=set())

    assert by_pid(rows, 2).prefix.endswith("├── ")
    assert by_pid(rows, 3).prefix.endswith("└── ")


def test_row_reports_memory_and_child_count() -> None:
    procs = [p(1, 0, "parent", 10), p(2, 1, "child", 20)]
    root = build_tree(procs)

    parent = by_pid(build_rows(root, collapsed=set()), 1)

    assert parent.own_rss == 10 * MB
    assert parent.subtree_rss == 30 * MB
    assert parent.child_count == 1


def test_format_tree_line_includes_name_and_memory() -> None:
    procs = [p(1, 0, "Chrome", 10), p(2, 1, "Helper", 20)]
    root = build_tree(procs)
    parent = by_pid(build_rows(root, collapsed=set()), 1)

    line = format_tree_line(parent, total_rss=30 * MB)

    assert "Chrome" in line
    assert "30.0 MB" in line  # subtree
    assert "10.0 MB" in line  # own


def test_format_tree_line_marks_collapsed_vs_expanded() -> None:
    procs = [p(1, 0, "a", 10), p(2, 1, "b", 10)]
    root = build_tree(procs)

    expanded = by_pid(build_rows(root, collapsed=set()), 1)
    collapsed = by_pid(build_rows(root, collapsed={1}), 1)

    assert format_tree_line(expanded, 20 * MB) != format_tree_line(collapsed, 20 * MB)


def test_build_rows_is_deterministic() -> None:
    procs = [p(1, 0, "a", 5), p(2, 0, "b", 5), p(3, 1, "c", 3), p(4, 1, "d", 3)]
    root = build_tree(procs)

    first = build_rows(root, collapsed=set())
    second = build_rows(root, collapsed=set())

    assert [r.pid for r in first] == [r.pid for r in second]
