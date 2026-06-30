"""Human-readable formatting helpers."""

from __future__ import annotations

_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def human_bytes(n: int) -> str:
    """Format a byte count as a short human-readable string.

    Bytes are shown as a whole number; larger units use one decimal place
    (e.g. ``1536`` -> ``"1.5 KB"``).
    """
    value = float(n)
    for unit in _UNITS:
        if value < 1024 or unit == _UNITS[-1]:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"
