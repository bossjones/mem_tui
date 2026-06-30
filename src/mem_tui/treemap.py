"""Squarified treemap layout (Bruls, Huizing & van Wijk, 2000).

Pure geometry: turn weighted items into non-overlapping rectangles that fill a
container while keeping each block as close to square as possible.
"""

from __future__ import annotations

from collections.abc import Hashable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rect:
    """An axis-aligned rectangle in cell coordinates."""

    x: float
    y: float
    w: float
    h: float

    @property
    def area(self) -> float:
        return self.w * self.h

    @property
    def shorter_side(self) -> float:
        return min(self.w, self.h)


@dataclass(frozen=True, slots=True)
class Placed:
    """An item placed at a rectangle."""

    item_id: Hashable
    rect: Rect


def squarify(items: Sequence[tuple[Hashable, float]], rect: Rect) -> list[Placed]:
    """Lay out ``items`` (id, weight) inside ``rect`` as a squarified treemap.

    Items with non-positive weight are dropped. Output is ordered with the
    largest-weight item first and is deterministic for a given input.
    """
    positive = [(item_id, weight) for item_id, weight in items if weight > 0]
    if not positive or rect.area <= 0:
        return []

    positive.sort(key=lambda pair: pair[1], reverse=True)

    total_weight = sum(weight for _, weight in positive)
    scale = rect.area / total_weight
    scaled = [(item_id, weight * scale) for item_id, weight in positive]

    placed: list[Placed] = []
    _squarify(scaled, rect, placed)
    return placed


def _squarify(
    items: list[tuple[Hashable, float]],
    rect: Rect,
    out: list[Placed],
) -> None:
    """Recursively place area-scaled items into ``rect``."""
    if not items:
        return

    row: list[tuple[Hashable, float]] = []
    side = rect.shorter_side
    index = 0
    while index < len(items):
        candidate = [*row, items[index]]
        if row and _worst_ratio(candidate, side) > _worst_ratio(row, side):
            break
        row = candidate
        index += 1

    remaining = items[index:]
    rect = _place_row(row, rect, out)
    _squarify(remaining, rect, out)


def _worst_ratio(row: list[tuple[Hashable, float]], side: float) -> float:
    """Worst (largest) aspect ratio if ``row`` is laid along ``side``."""
    areas = [area for _, area in row]
    row_sum = sum(areas)
    if row_sum <= 0 or side <= 0:
        return float("inf")
    side_sq = side * side
    sum_sq = row_sum * row_sum
    return max(max(side_sq * area / sum_sq, sum_sq / (side_sq * area)) for area in areas)


def _place_row(
    row: list[tuple[Hashable, float]],
    rect: Rect,
    out: list[Placed],
) -> Rect:
    """Place ``row`` along the shorter side and return the leftover rectangle."""
    row_area = sum(area for _, area in row)
    if rect.w <= rect.h:
        # Lay the row horizontally across the top; consume height.
        row_height = row_area / rect.w if rect.w > 0 else 0.0
        offset = rect.x
        for item_id, area in row:
            width = area / row_height if row_height > 0 else 0.0
            out.append(Placed(item_id, Rect(offset, rect.y, width, row_height)))
            offset += width
        return Rect(rect.x, rect.y + row_height, rect.w, rect.h - row_height)

    # Lay the row vertically down the left; consume width.
    row_width = row_area / rect.h if rect.h > 0 else 0.0
    offset = rect.y
    for item_id, area in row:
        height = area / row_width if row_width > 0 else 0.0
        out.append(Placed(item_id, Rect(rect.x, offset, row_width, height)))
        offset += height
    return Rect(rect.x + row_width, rect.y, rect.w - row_width, rect.h)
