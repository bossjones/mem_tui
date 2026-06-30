"""The Textual application: live treemap of process memory."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import BindingType

from mem_tui.layout import Block, compute_blocks
from mem_tui.models import ProcessInfo
from mem_tui.sampler import sample as default_sample
from mem_tui.tree import ProcessNode, build_tree
from mem_tui.treemap import Rect
from mem_tui.treeview import TreeRow, build_rows
from mem_tui.widgets import ProcessTreeWidget, StatusBar, TreemapWidget

SampleFn = Callable[[], Awaitable[list[ProcessInfo]]]

DEFAULT_REFRESH_SECONDS = 2.0


class MemTuiApp(App[None]):
    """Async TUI showing a squarified treemap of process memory."""

    CSS = """
    Screen { layout: vertical; }
    TreemapWidget { width: 1fr; height: 1fr; }
    ProcessTreeWidget { width: 1fr; height: 1fr; }
    ProcessTreeWidget.hidden { display: none; }
    TreemapWidget.hidden { display: none; }
    StatusBar { dock: bottom; height: 1; }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("enter", "toggle_collapse", "Collapse/Expand"),
        ("tab", "next", "Next"),
        ("right", "next", "Next"),
        ("down", "next", "Next"),
        ("shift+tab", "prev", "Prev"),
        ("left", "prev", "Prev"),
        ("up", "prev", "Prev"),
        ("t", "toggle_view", "Map/Tree"),
        ("m", "toggle_mouse", "Mouse on/off"),
        ("r", "refresh_now", "Refresh"),
        ("space", "toggle_pause", "Pause"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        sample_fn: SampleFn | None = None,
        auto_refresh: bool = True,
        refresh_interval: float = DEFAULT_REFRESH_SECONDS,
    ) -> None:
        super().__init__()
        self._sample_fn: SampleFn = sample_fn or default_sample
        self._auto_refresh = auto_refresh
        self._interval = refresh_interval

        self.root: ProcessNode | None = None
        self.blocks: list[Block] = []
        self.rows: list[TreeRow] = []
        self.collapsed: set[int] = set()
        self.selected_pid: int | None = None
        self.hovered_pid: int | None = None
        self.mouse_enabled: bool = True
        self.paused: bool = False
        self.view_mode: str = "map"  # "map" | "tree"

    def compose(self) -> ComposeResult:
        yield TreemapWidget()
        yield ProcessTreeWidget(classes="hidden")
        yield StatusBar()

    async def on_mount(self) -> None:
        await self.refresh_data()
        if self._auto_refresh:
            self.set_interval(self._interval, self._tick)

    async def _tick(self) -> None:
        if not self.paused:
            await self.refresh_data()

    def on_treemap_widget_resized(self, message: TreemapWidget.Resized) -> None:
        """Re-lay out the treemap when its widget changes size."""
        self._recompute()

    def on_treemap_widget_block_hovered(self, message: TreemapWidget.BlockHovered) -> None:
        """Show the hovered process in the status bar without selecting it."""
        self.hovered_pid = message.pid
        self._update_status()

    async def refresh_data(self) -> None:
        """Sample processes, rebuild the tree, and re-render."""
        procs = await self._sample_fn()
        if not procs and self.root is not None:
            return  # keep the previous frame rather than blanking
        self.root = build_tree(procs)
        self._recompute()

    def _layout_rect(self) -> Rect:
        try:
            size = self.query_one(TreemapWidget).size
            if size.width > 0 and size.height > 0:
                return Rect(0, 0, float(size.width), float(size.height))
        except Exception:
            pass
        width, height = self.size
        return Rect(0, 0, float(width), float(max(1, height - 1)))

    def _recompute(self) -> None:
        if self.root is None:
            return
        self.blocks = compute_blocks(self.root, self.collapsed, self._layout_rect())
        self.rows = build_rows(self.root, self.collapsed)

        pids = self._ordered_pids()
        if self.selected_pid not in pids:
            self.selected_pid = pids[0] if pids else None

        self._render_state()

    def _ordered_pids(self) -> list[int]:
        if self.view_mode == "tree":
            return [r.pid for r in self.rows]
        return [b.pid for b in self.blocks]

    def _render_state(self) -> None:
        try:
            treemap = self.query_one(TreemapWidget)
            tree = self.query_one(ProcessTreeWidget)
        except Exception:  # not yet mounted
            return
        treemap.set_blocks(self.blocks, self.selected_pid)
        tree.set_rows(self.rows, self.selected_pid, self._total_rss())
        treemap.set_class(self.view_mode != "map", "hidden")
        tree.set_class(self.view_mode != "tree", "hidden")
        self._update_status()

    def _update_status(self) -> None:
        try:
            status = self.query_one(StatusBar)
        except Exception:  # not yet mounted
            return
        # Prefer the hovered block (live readout) over the selection.
        pid = self.hovered_pid if self.hovered_pid is not None else self.selected_pid
        status.set_block(self._block_by_pid(pid), self._total_rss())

    def _block_by_pid(self, pid: int | None) -> Block | None:
        for block in self.blocks:
            if block.pid == pid:
                return block
        return None

    def _selected_block(self) -> Block | None:
        return self._block_by_pid(self.selected_pid)

    def _total_rss(self) -> int:
        return self.root.subtree_rss if self.root else 0

    # --- actions -----------------------------------------------------------

    def action_toggle_collapse(self) -> None:
        if self.selected_pid is None:
            return
        if self.selected_pid in self.collapsed:
            self.collapsed.discard(self.selected_pid)
        else:
            self.collapsed.add(self.selected_pid)
        self._recompute()

    def action_next(self) -> None:
        self._move(1)

    def action_prev(self) -> None:
        self._move(-1)

    def _move(self, delta: int) -> None:
        pids = self._ordered_pids()
        if not pids:
            return
        if self.selected_pid in pids:
            index = (pids.index(self.selected_pid) + delta) % len(pids)
        else:
            index = 0
        self.selected_pid = pids[index]
        self._render_state()

    def action_toggle_view(self) -> None:
        self.view_mode = "tree" if self.view_mode == "map" else "map"
        self._render_state()

    def action_toggle_mouse(self) -> None:
        self.mouse_enabled = not self.mouse_enabled

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused

    async def action_refresh_now(self) -> None:
        await self.refresh_data()

    # --- events ------------------------------------------------------------

    def on_treemap_widget_block_clicked(
        self, message: TreemapWidget.BlockClicked
    ) -> None:  # pragma: no cover - exercised via UI
        if not self.mouse_enabled:
            return
        self.selected_pid = message.pid
        self.action_toggle_collapse()


def main() -> None:
    """Entry point for `uv run mem_tui.py` / the `mem-tui` script."""
    MemTuiApp().run()


if __name__ == "__main__":
    main()
