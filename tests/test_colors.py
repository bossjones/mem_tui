"""Tests for stable per-ancestor color assignment."""

from __future__ import annotations

import re

from mem_tui.colors import PALETTE, color_for

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def test_palette_is_non_empty_and_valid_hex() -> None:
    assert PALETTE
    assert all(HEX.match(c) for c in PALETTE)


def test_color_is_stable_for_same_id() -> None:
    assert color_for(4321) == color_for(4321)


def test_color_is_from_palette() -> None:
    for pid in range(0, 50):
        assert color_for(pid) in PALETTE


def test_different_ids_use_more_than_one_color() -> None:
    colors = {color_for(pid) for pid in range(0, 100)}
    assert len(colors) > 1
