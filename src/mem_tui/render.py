"""Pure per-cell styling for treemap blocks.

Each block is drawn with a 3D bevel — a lighter top/left edge and a darker
bottom/right edge — so adjacent blocks read as distinct tiles, the way
GrandPerspective renders them. The selected block gets a bright white frame.
"""

from __future__ import annotations

from dataclasses import dataclass

from mem_tui.layout import Block

_SELECT_COLOR = "#ffffff"
_BEVEL_DELTA = 45


@dataclass(frozen=True, slots=True)
class Cell:
    """Resolved styling for one terminal cell."""

    char: str
    bg: str
    fg: str
    bold: bool


def block_cell(
    block: Block,
    x: int,
    y: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    selected: bool,
) -> Cell:
    """Return the styling for cell ``(x, y)`` within ``block``'s rectangle.

    ``right`` and ``bottom`` are exclusive bounds. Blocks smaller than 2x2 are
    drawn as a solid tile (no bevel) so they never disappear into border shades.
    """
    base = block.color
    width = right - left
    height = bottom - top

    on_left = x == left
    on_top = y == top
    on_right = x == right - 1
    on_bottom = y == bottom - 1
    is_edge = on_left or on_top or on_right or on_bottom

    if selected and is_edge:
        bg = _SELECT_COLOR
    elif width < 2 or height < 2:
        bg = base
    elif on_bottom or on_right:
        bg = _shift(base, -_BEVEL_DELTA)
    elif on_top or on_left:
        bg = _shift(base, +_BEVEL_DELTA)
    else:
        bg = base

    return Cell(char=" ", bg=bg, fg=_contrast(bg), bold=selected)


def _shift(hex_color: str, delta: int) -> str:
    r = _clamp(int(hex_color[1:3], 16) + delta)
    g = _clamp(int(hex_color[3:5], 16) + delta)
    b = _clamp(int(hex_color[5:7], 16) + delta)
    return f"#{r:02x}{g:02x}{b:02x}"


def _clamp(value: int) -> int:
    return max(0, min(255, value))


def _contrast(hex_color: str) -> str:
    """Black or white text, whichever is readable on ``hex_color``."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.6 else "#ffffff"
