"""Tests for the process-tree builder and subtree RSS rollup."""

from __future__ import annotations

from mem_tui.models import ProcessInfo
from mem_tui.tree import (
    ProcessNode,
    build_tree,
    find,
    flatten,
    top_level_ancestor,
)

MB = 1024 * 1024


def p(pid: int, ppid: int, name: str, rss_mb: int) -> ProcessInfo:
    return ProcessInfo(pid=pid, ppid=ppid, name=name, rss=rss_mb * MB, cmdline=name)


def test_single_process_becomes_child_of_root() -> None:
    root = build_tree([p(10, 0, "solo", 5)])

    assert isinstance(root, ProcessNode)
    assert len(root.children) == 1
    assert root.children[0].info.pid == 10
    assert root.children[0].subtree_rss == 5 * MB


def test_subtree_rss_rolls_children_into_parent() -> None:
    # parent 100 (10MB) with two children 200 (20MB) and 300 (30MB)
    procs = [
        p(100, 1, "parent", 10),
        p(200, 100, "child-a", 20),
        p(300, 100, "child-b", 30),
    ]
    root = build_tree(procs)
    parent = find(root, 100)

    assert parent is not None
    assert parent.info.rss == 10 * MB
    assert parent.subtree_rss == (10 + 20 + 30) * MB


def test_deep_rollup_is_recursive() -> None:
    # 1 -> 2 -> 3, each 10MB; node 1 subtree should be 30MB
    procs = [
        p(1, 0, "a", 10),
        p(2, 1, "b", 10),
        p(3, 2, "c", 10),
    ]
    root = build_tree(procs)
    a = find(root, 1)

    assert a is not None
    assert a.subtree_rss == 30 * MB


def test_orphan_attaches_to_root() -> None:
    # process whose parent pid is not in the sample
    root = build_tree([p(500, 999, "orphan", 7)])

    assert len(root.children) == 1
    assert root.children[0].info.pid == 500
    assert root.subtree_rss == 7 * MB


def test_cycle_does_not_infinite_loop() -> None:
    # malformed: 1's parent is 2 and 2's parent is 1
    procs = [p(1, 2, "a", 10), p(2, 1, "b", 10)]

    root = build_tree(procs)  # must return, not hang

    assert root.subtree_rss == 20 * MB
    assert len(flatten(root)) == 2


def test_top_level_ancestor_of_deep_child() -> None:
    procs = [
        p(100, 0, "Chrome", 5),
        p(101, 100, "Chrome Helper", 5),
        p(102, 101, "Chrome Helper (Renderer)", 5),
    ]
    root = build_tree(procs)
    deep = find(root, 102)

    assert deep is not None
    ancestor = top_level_ancestor(deep, root)
    assert ancestor.info.pid == 100


def test_top_level_ancestor_of_top_node_is_itself() -> None:
    root = build_tree([p(1, 0, "app", 5)])
    node = find(root, 1)

    assert node is not None
    assert top_level_ancestor(node, root).info.pid == 1


def test_color_group_breaks_at_launchd() -> None:
    # root(0) -> launchd(1) -> AppA(10) -> helper(11);  launchd -> AppB(20)
    procs = [
        p(1, 0, "launchd", 1),
        p(10, 1, "AppA", 5),
        p(11, 10, "AppA Helper", 5),
        p(20, 1, "AppB", 5),
    ]
    root = build_tree(procs)

    helper = find(root, 11)
    app_b = find(root, 20)
    assert helper is not None and app_b is not None
    # The color group is the app, not the shared launchd ancestor.
    assert top_level_ancestor(helper, root).info.pid == 10
    assert top_level_ancestor(app_b, root).info.pid == 20


def test_flatten_excludes_synthetic_root() -> None:
    procs = [p(1, 0, "a", 1), p(2, 1, "b", 1)]
    root = build_tree(procs)

    pids = {n.info.pid for n in flatten(root)}
    assert pids == {1, 2}
