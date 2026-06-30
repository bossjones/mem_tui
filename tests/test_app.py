"""Behavior tests for the Textual app via the run_test pilot."""

from __future__ import annotations

from mem_tui.app import MemTuiApp
from mem_tui.models import ProcessInfo
from mem_tui.widgets import StatusBar, TreemapWidget

MB = 1024 * 1024


def make_sampler(procs: list[ProcessInfo]):
    async def _sample() -> list[ProcessInfo]:
        return list(procs)

    return _sample


BASE = [
    ProcessInfo(1, 0, "Chrome", 50 * MB, "Chrome"),
    ProcessInfo(2, 1, "Chrome Helper", 200 * MB, "helper"),
    ProcessInfo(3, 1, "Chrome Helper", 150 * MB, "helper"),
    ProcessInfo(4, 0, "node", 300 * MB, "node"),
]


async def test_mount_samples_and_builds_blocks() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test():
        assert app.blocks
        assert app.selected_pid is not None


async def test_toggle_collapse_adds_then_removes() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test():
        app.selected_pid = 1
        app.action_toggle_collapse()
        assert 1 in app.collapsed
        app.action_toggle_collapse()
        assert 1 not in app.collapsed


async def test_navigation_changes_selection() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test():
        first = app.selected_pid
        app.action_next()
        assert app.selected_pid != first


async def test_toggle_mouse() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test():
        assert app.mouse_enabled is True
        app.action_toggle_mouse()
        assert app.mouse_enabled is False


async def test_toggle_pause() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test():
        assert app.paused is False
        app.action_toggle_pause()
        assert app.paused is True


async def test_refresh_now_repopulates_blocks() -> None:
    procs = list(BASE)
    app = MemTuiApp(sample_fn=make_sampler(procs), auto_refresh=False)
    async with app.run_test():
        assert all(b.pid != 99 for b in app.blocks)
        procs.append(ProcessInfo(99, 0, "newproc", 500 * MB, "new"))
        await app.action_refresh_now()
        assert any(b.pid == 99 for b in app.blocks)


async def test_layout_reacts_to_terminal_resize() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test(size=(120, 40)) as pilot:
        wide_extent = max(b.rect.x + b.rect.w for b in app.blocks)

        await pilot.resize_terminal(60, 20)
        await pilot.pause()

        narrow_extent = max(b.rect.x + b.rect.w for b in app.blocks)
        assert narrow_extent <= 60 + 1e-6
        assert wide_extent > 60  # had used the wider canvas before resizing


async def test_hover_updates_status_without_changing_selection() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test(size=(120, 40)) as pilot:
        selected_before = app.selected_pid

        await pilot.hover(TreemapWidget, offset=(5, 5))
        await pilot.pause()

        assert app.hovered_pid is not None
        assert any(b.pid == app.hovered_pid for b in app.blocks)
        assert app.selected_pid == selected_before  # hover never moves selection


async def test_hover_shows_hovered_block_name_in_status() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.hover(TreemapWidget, offset=(5, 5))
        await pilot.pause()

        hovered = next(b for b in app.blocks if b.pid == app.hovered_pid)
        status = app.query_one(StatusBar)
        assert hovered.name in status.text


async def test_toggle_view_switches_between_map_and_tree() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test():
        assert app.view_mode == "map"
        app.action_toggle_view()
        assert app.view_mode == "tree"
        app.action_toggle_view()
        assert app.view_mode == "map"


async def test_tree_view_has_rows() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test():
        app.action_toggle_view()
        pids = {r.pid for r in app.rows}
        assert {1, 2, 3, 4}.issubset(pids)


async def test_navigation_uses_tree_order_in_tree_mode() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test():
        app.action_toggle_view()
        row_pids = [r.pid for r in app.rows]
        app.selected_pid = row_pids[0]
        app.action_next()
        assert app.selected_pid == row_pids[1]


async def test_collapse_in_tree_mode_hides_children() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test():
        app.action_toggle_view()
        before = len(app.rows)
        app.selected_pid = 1  # Chrome, has two helpers
        app.action_toggle_collapse()
        assert len(app.rows) < before


async def test_collapsed_parent_reduces_block_count() -> None:
    app = MemTuiApp(sample_fn=make_sampler(BASE), auto_refresh=False)
    async with app.run_test():
        expanded = len(app.blocks)
        app.selected_pid = 1
        app.action_toggle_collapse()
        # collapsing Chrome hides its two helpers
        assert len(app.blocks) < expanded
