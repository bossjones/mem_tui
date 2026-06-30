"""Tests for turning a process tree + collapsed set into drawable blocks."""

from __future__ import annotations

from mem_tui.layout import Block, compute_blocks
from mem_tui.models import ProcessInfo
from mem_tui.tree import build_tree
from mem_tui.treemap import Rect

MB = 1024 * 1024


def p(pid: int, ppid: int, name: str, rss_mb: int) -> ProcessInfo:
    return ProcessInfo(pid=pid, ppid=ppid, name=name, rss=rss_mb * MB, cmdline=name)


def pids(blocks: list[Block]) -> set[int]:
    return {b.pid for b in blocks}


def test_single_leaf_process_is_one_block() -> None:
    root = build_tree([p(10, 0, "solo", 5)])

    blocks = compute_blocks(root, collapsed=set(), rect=Rect(0, 0, 20, 10))

    assert len(blocks) == 1
    assert blocks[0].pid == 10
    assert blocks[0].kind == "leaf"


def test_collapsed_parent_hides_children() -> None:
    procs = [p(1, 0, "app", 10), p(2, 1, "child", 20), p(3, 1, "child2", 30)]
    root = build_tree(procs)

    blocks = compute_blocks(root, collapsed={1}, rect=Rect(0, 0, 40, 20))

    assert pids(blocks) == {1}
    assert blocks[0].subtree_rss == (10 + 20 + 30) * MB


def test_expanded_parent_shows_children_and_self_slice() -> None:
    procs = [p(1, 0, "app", 10), p(2, 1, "child", 20), p(3, 1, "child2", 30)]
    root = build_tree(procs)

    blocks = compute_blocks(root, collapsed=set(), rect=Rect(0, 0, 60, 30))

    # children present plus a "self" slice for the parent's own RSS
    assert {2, 3}.issubset(pids(blocks))
    self_blocks = [b for b in blocks if b.kind == "self"]
    assert len(self_blocks) == 1
    assert self_blocks[0].pid == 1


def test_expanded_parent_without_own_memory_has_no_self_slice() -> None:
    procs = [p(1, 0, "app", 0), p(2, 1, "child", 20)]
    root = build_tree(procs)

    blocks = compute_blocks(root, collapsed=set(), rect=Rect(0, 0, 40, 20))

    assert all(b.kind != "self" for b in blocks)
    assert pids(blocks) == {2}


def test_blocks_for_same_ancestor_share_color() -> None:
    procs = [
        p(100, 0, "Chrome", 10),
        p(101, 100, "Helper", 20),
        p(102, 101, "Renderer", 30),
    ]
    root = build_tree(procs)

    blocks = compute_blocks(root, collapsed=set(), rect=Rect(0, 0, 60, 30))

    assert len({b.color for b in blocks}) == 1


def test_all_block_rects_stay_within_bounds() -> None:
    procs = [p(1, 0, "a", 10), p(2, 1, "b", 20), p(3, 0, "c", 15)]
    root = build_tree(procs)

    for b in compute_blocks(root, collapsed=set(), rect=Rect(0, 0, 80, 24)):
        assert b.rect.x >= -1e-9
        assert b.rect.y >= -1e-9
        assert b.rect.x + b.rect.w <= 80 + 1e-9
        assert b.rect.y + b.rect.h <= 24 + 1e-9


def test_each_pid_appears_at_most_once() -> None:
    procs = [p(1, 0, "a", 10), p(2, 1, "b", 20), p(3, 1, "c", 30)]
    root = build_tree(procs)

    blocks = compute_blocks(root, collapsed=set(), rect=Rect(0, 0, 60, 30))
    block_pids = [b.pid for b in blocks]

    assert len(block_pids) == len(set(block_pids))
