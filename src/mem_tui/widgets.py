"""Textual widgets: the treemap canvas and the status bar."""

from __future__ import annotations

from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.geometry import Size
from textual.message import Message
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widget import Widget

from mem_tui.format import human_bytes
from mem_tui.layout import Block, block_at
from mem_tui.render import block_cell
from mem_tui.treeview import TreeRow, format_tree_line


class TreemapWidget(Widget):
    """Renders treemap blocks as filled colored cells and reports clicks."""

    can_focus = True

    class BlockClicked(Message):
        """Posted when a block is clicked."""

        def __init__(self, pid: int) -> None:
            self.pid = pid
            super().__init__()

    class BlockHovered(Message):
        """Posted as the mouse moves; pid is None when over no block."""

        def __init__(self, pid: int | None) -> None:
            self.pid = pid
            super().__init__()

    class Resized(Message):
        """Posted when the widget's size changes, so the app can re-layout."""

    def __init__(self) -> None:
        super().__init__()
        self._blocks: list[Block] = []
        self._selected: int | None = None

    def set_blocks(self, blocks: list[Block], selected: int | None) -> None:
        self._blocks = blocks
        self._selected = selected
        self.refresh()

    def render_line(self, y: int) -> Strip:
        width = self.size.width
        if width <= 0 or not self._blocks:
            return Strip.blank(width)

        cells = self._row_cells(y, width)
        segments = [Segment(char, style) for char, style in cells]
        return Strip(segments, width)

    def _row_cells(self, y: int, width: int) -> list[tuple[str, Style]]:
        blank = Style()
        row: list[tuple[str, Style]] = [(" ", blank)] * width

        for block in self._blocks:
            r = block.rect
            top = round(r.y)
            bottom = round(r.y + r.h)
            if not (top <= y < bottom):
                continue
            left = max(0, round(r.x))
            right = min(width, round(r.x + r.w))
            if right <= left:
                continue

            selected = block.pid == self._selected
            label = self._label(block, right - left, bottom - top)
            for x in range(left, right):
                cell = block_cell(block, x, y, left, top, right, bottom, selected)
                char = cell.char
                idx = x - left
                # Draw the label on the second row, inset by one, over the fill.
                if label and y == top + 1 and 1 <= idx <= len(label):
                    char = label[idx - 1]
                row[x] = (char, Style(bgcolor=cell.bg, color=cell.fg, bold=cell.bold))
        return row

    def _label(self, block: Block, avail_w: int, avail_h: int) -> str:
        if avail_w < 8 or avail_h < 3:
            return ""
        text = f"{block.name} {human_bytes(block.subtree_rss)}"
        return text[: avail_w - 2]

    def on_resize(self, event: events.Resize) -> None:
        self.post_message(self.Resized())

    def on_mouse_move(self, event: events.MouseMove) -> None:
        pid = block_at(self._blocks, event.x, event.y)
        self.post_message(self.BlockHovered(pid))

    def on_click(self, event: object) -> None:  # pragma: no cover - UI plumbing
        x = getattr(event, "x", None)
        y = getattr(event, "y", None)
        if x is None or y is None:
            return
        pid = block_at(self._blocks, x, y)
        if pid is not None:
            self.post_message(self.BlockClicked(pid))

    def get_content_width(self, container: Size, viewport: Size) -> int:
        return container.width

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return container.height


class ProcessTreeWidget(ScrollView):
    """Scrollable ps-style indented tree of processes and their memory."""

    can_focus = True

    def __init__(self, *, classes: str | None = None) -> None:
        super().__init__(classes=classes)
        self._rows: list[TreeRow] = []
        self._selected: int | None = None
        self._total_rss: int = 0

    def set_rows(self, rows: list[TreeRow], selected: int | None, total_rss: int) -> None:
        self._rows = rows
        self._selected = selected
        self._total_rss = total_rss
        width = max((len(self._line(r)) for r in rows), default=0)
        self.virtual_size = Size(max(width, self.size.width), len(rows))
        self._scroll_selected_into_view()
        self.refresh()

    def _line(self, row: TreeRow) -> str:
        return format_tree_line(row, self._total_rss)

    def _scroll_selected_into_view(self) -> None:
        if self._selected is None:
            return
        for index, row in enumerate(self._rows):
            if row.pid == self._selected:
                _, scroll_y = self.scroll_offset
                height = self.size.height or 1
                if index < scroll_y or index >= scroll_y + height:
                    self.scroll_to(y=max(0, index - height // 2), animate=False)
                return

    def render_line(self, y: int) -> Strip:
        scroll_x, scroll_y = self.scroll_offset
        index = y + scroll_y
        width = self.size.width
        if index < 0 or index >= len(self._rows):
            return Strip.blank(width)

        row = self._rows[index]
        selected = row.pid == self._selected
        style = Style(reverse=True, bold=True) if selected else Style()
        text = self._line(row).ljust(width)
        strip = Strip([Segment(text, style)], len(text))
        return strip.crop(scroll_x, scroll_x + width)


class StatusBar(Widget):
    """One-line bar showing the selected block's details."""

    DEFAULT_CSS = """
    StatusBar { height: 1; background: $panel; color: $text; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._text = "Loading…"

    @property
    def text(self) -> str:
        return self._text

    def set_block(self, block: Block | None, total_rss: int) -> None:
        if block is None:
            self._text = "No selection"
        else:
            self._text = (
                f" {block.name}  PID {block.pid}  "
                f"own {human_bytes(block.own_rss)}  "
                f"subtree {human_bytes(block.subtree_rss)} "
                f"({block.child_count} children)  •  total {human_bytes(total_rss)}"
            )
        self.refresh()

    def render(self) -> str:
        return self._text
