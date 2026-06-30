"""Tests for human-readable byte formatting."""

from __future__ import annotations

from mem_tui.format import human_bytes


def test_bytes_under_a_kilobyte() -> None:
    assert human_bytes(0) == "0 B"
    assert human_bytes(512) == "512 B"


def test_kilobytes_megabytes_gigabytes() -> None:
    assert human_bytes(1024) == "1.0 KB"
    assert human_bytes(1024**2) == "1.0 MB"
    assert human_bytes(1024**3) == "1.0 GB"


def test_fractional_values() -> None:
    assert human_bytes(int(1.5 * 1024**2)) == "1.5 MB"
