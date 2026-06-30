"""Stable color assignment: one hue per top-level ancestor process."""

from __future__ import annotations

# A curated, visually distinct palette (no near-duplicates, readable on a dark
# terminal background). Colors are assigned deterministically by ancestor pid.
PALETTE: tuple[str, ...] = (
    "#4e79a7",  # blue
    "#f28e2b",  # orange
    "#59a14f",  # green
    "#e15759",  # red
    "#b07aa1",  # purple
    "#76b7b2",  # teal
    "#edc948",  # yellow
    "#ff9da7",  # pink
    "#9c755f",  # brown
    "#bab0ac",  # grey
    "#86bcb6",  # light teal
    "#d37295",  # rose
)


def color_for(ancestor_id: int) -> str:
    """Return a stable hex color for a top-level ancestor pid.

    The same id always maps to the same palette entry within and across runs.
    """
    return PALETTE[ancestor_id % len(PALETTE)]
