"""Tests for the squarified treemap layout."""

from __future__ import annotations

from mem_tui.treemap import Placed, Rect, squarify


def total_area(placed: list[Placed]) -> float:
    return sum(p.rect.w * p.rect.h for p in placed)


def test_empty_items_returns_empty() -> None:
    assert squarify([], Rect(0, 0, 10, 10)) == []


def test_single_item_fills_rect() -> None:
    placed = squarify([("a", 5.0)], Rect(0, 0, 10, 8))

    assert len(placed) == 1
    assert placed[0].item_id == "a"
    assert placed[0].rect.x == 0
    assert placed[0].rect.y == 0
    assert placed[0].rect.w == 10
    assert placed[0].rect.h == 8


def test_zero_and_negative_weights_filtered() -> None:
    placed = squarify([("a", 5.0), ("b", 0.0), ("c", -3.0)], Rect(0, 0, 10, 10))

    assert {p.item_id for p in placed} == {"a"}


def test_area_is_conserved() -> None:
    items = [("a", 6.0), ("b", 6.0), ("c", 4.0), ("d", 3.0), ("e", 2.0)]
    rect = Rect(0, 0, 6, 4)

    placed = squarify(items, rect)

    assert abs(total_area(placed) - 24.0) < 1e-6


def test_all_rects_within_bounds() -> None:
    items = [("a", 6.0), ("b", 3.0), ("c", 2.0), ("d", 1.0)]
    rect = Rect(0, 0, 6, 4)

    for pl in squarify(items, rect):
        assert pl.rect.x >= -1e-9
        assert pl.rect.y >= -1e-9
        assert pl.rect.x + pl.rect.w <= 6 + 1e-9
        assert pl.rect.y + pl.rect.h <= 4 + 1e-9


def test_areas_proportional_to_weights() -> None:
    items = [("a", 3.0), ("b", 1.0)]
    rect = Rect(0, 0, 4, 1)  # total area 4 == total weight 4

    placed = {p.item_id: p.rect for p in squarify(items, rect)}

    assert abs(placed["a"].w * placed["a"].h - 3.0) < 1e-6
    assert abs(placed["b"].w * placed["b"].h - 1.0) < 1e-6


def test_layout_is_deterministic() -> None:
    items = [("a", 6.0), ("b", 6.0), ("c", 4.0), ("d", 3.0), ("e", 2.0), ("f", 1.0)]
    rect = Rect(0, 0, 6, 4)

    first = squarify(items, rect)
    second = squarify(items, rect)

    assert first == second


def test_aspect_ratios_are_reasonable() -> None:
    # Classic squarified example should keep blocks close to square.
    items = [
        ("a", 6.0),
        ("b", 6.0),
        ("c", 4.0),
        ("d", 3.0),
        ("e", 2.0),
        ("f", 2.0),
        ("g", 1.0),
    ]
    placed = squarify(items, Rect(0, 0, 6, 4))

    worst = max(max(p.rect.w, p.rect.h) / min(p.rect.w, p.rect.h) for p in placed)
    assert worst < 4.0
