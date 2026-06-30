#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "textual>=0.60.0",
#     "psutil>=5.9.0",
# ]
# ///
"""Standalone entry point: `uv run mem_tui.py`.

Adds the local ``src`` directory to ``sys.path`` so the script runs without an
editable install, then launches the Textual application.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mem_tui.app import main

if __name__ == "__main__":
    main()
