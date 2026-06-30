# mem_tui — Design Spec

**Date:** 2026-06-30
**Status:** Approved (design phase)

## Summary

`mem_tui` is an async-first terminal UI that renders a **squarified treemap of
process memory usage on macOS** — a GrandPerspective-style "segmented" view, but
for RAM instead of disk. Memory is rolled **up the process tree** so a parent
(e.g. `Google Chrome`, `node`, a launchd/supervisor process) is shown as the
total of itself plus all descendants. The goal: answer "which process or
supervisor is using all my memory?" at a glance, interactively.

It is launched with `uv run mem_tui.py` (PEP 723 inline metadata) and built on
**Textual** for native mouse + keyboard handling and a real async event loop.

## Goals

- Show total resident memory per process **tree** (rollup of children into parents).
- Render a squarified treemap where block **size = resident memory**, block
  **color = top-level ancestor process**.
- Interactively collapse/expand subtrees, scan with keyboard, inspect a block.
- Live auto-refresh without blocking the UI (async sampling off the UI thread).
- Prioritize speed and responsiveness.

## Non-Goals (YAGNI)

- Cross-platform support beyond macOS in v1 (psutil is portable, but only macOS
  is targeted/tested now).
- Killing processes or any mutation of system state (read-only tool).
- Historical graphs / time-series storage. The view is a live snapshot.
- Per-thread or virtual/compressed memory breakdowns. v1 uses **RSS** only.

## Definitions

- **RSS (Resident Set Size):** physical RAM a process currently holds. This is
  the memory metric used throughout.
- **Own RSS:** a single process's RSS.
- **Subtree RSS:** a process's own RSS plus the subtree RSS of all its children
  (recursive). This is the value that drives treemap block size.
- **Top-level ancestor:** the highest non-root process in a node's ancestor
  chain; used to assign a stable color so all of one app's helpers share a hue.

## Architecture

Small, independently testable units. Pure data/logic modules are separated from
the Textual UI so the bulk of behavior is unit-testable without a terminal.

```
mem_tui.py        # PEP 723 entry point — `uv run mem_tui.py`
src/mem_tui/
  __init__.py
  sampler.py      # async snapshot of processes via psutil -> list[ProcessInfo]
  tree.py         # build process tree, compute subtree RSS rollups
  treemap.py      # squarified treemap layout: (items, rect) -> placed rects
  colors.py       # stable color per top-level ancestor
  app.py          # Textual App: render, hit-test, keyboard/mouse, refresh, status bar
  widgets.py      # TreemapWidget (custom render + click hit-testing) + status bar
tests/
  test_sampler.py
  test_tree.py
  test_treemap.py
  test_colors.py
  test_app.py
```

### 1. `sampler.py`

- `ProcessInfo` dataclass: `pid: int`, `ppid: int`, `name: str`, `rss: int`,
  `cmdline: str`.
- `async def sample() -> list[ProcessInfo]`: enumerates processes with `psutil`
  (`pid`, `ppid`, `name`, `memory_info().rss`, `cmdline`). The blocking psutil
  work runs in a thread via `asyncio.to_thread` so the UI loop never stalls.
- Processes that vanish mid-sample (`NoSuchProcess`, `AccessDenied`,
  `ZombieProcess`) are skipped, not fatal.
- **Pure data out.** Tests mock psutil via pytest-mock and assert the records.

### 2. `tree.py`

- `ProcessNode`: `info: ProcessInfo`, `children: list[ProcessNode]`,
  `subtree_rss: int`.
- `build_tree(procs: list[ProcessInfo]) -> ProcessNode`: links children to
  parents by ppid, attaches orphans (parent missing) to a synthetic root,
  returns a single synthetic root node. Computes `subtree_rss` bottom-up.
- `top_level_ancestor(node, root) -> ProcessNode`: the child-of-root on a node's
  path; used by coloring.
- Helper to flatten/iterate visible nodes given a set of collapsed node ids.
- **Pure functions.** Heavily unit-tested: rollup math, orphan handling, cycles
  (defensive — a ppid loop must not infinite-loop), single process, empty input.

### 3. `treemap.py`

- `Rect` dataclass: `x, y, w, h` (float cell coordinates).
- `Placed` dataclass: `item_id, rect`.
- `squarify(items: list[tuple[id, weight]], rect: Rect) -> list[Placed]`:
  classic squarified treemap (Bruls et al.) producing low-aspect-ratio blocks.
  Zero/negative weights filtered. Deterministic ordering (descending weight).
- For expanded subtrees the algorithm recurses: an expanded node's rect is
  subdivided among its children.
- **Pure function.** Tested against known inputs: total area conservation,
  ordering, single item fills rect, aspect-ratio sanity on a fixed example.

### 4. `colors.py`

- `color_for(ancestor_id: int) -> Color`: deterministic mapping from top-level
  ancestor to a stable, visually distinct color (hash into a curated palette).
- Same ancestor always yields the same color within a run.
- **Pure.** Tested for stability and palette membership.

### 5. `widgets.py`

- `TreemapWidget`: custom Textual widget that, given placed rects + colors,
  paints colored cell blocks (background-filled cells, label text where the
  block is large enough). Maintains the mapping from cell coordinates to node id
  for **hit-testing** mouse clicks. Emits a selection/toggle message on click.
- `StatusBar`: shows the selected node's name, PID, own RSS, subtree RSS, child
  count — formatted with human-readable byte sizes.

### 6. `app.py` — Textual `App`

State:
- `root: ProcessNode` (latest sample).
- `collapsed: set[int]` — node ids whose children are hidden (RAM rolled up).
- `selected: int | None` — currently highlighted node.
- `mouse_enabled: bool`, `paused: bool`.

Behavior:
- On mount: sample, build tree, layout, render. Start an interval timer
  (default **2s**) that re-samples asynchronously unless paused.
- Layout: run `squarify` over visible (non-collapsed) nodes sized by subtree_rss
  into the widget's rectangle; recurse into expanded subtrees.

Key/mouse bindings:
- **Click / Enter** on a block → toggle collapse/expand of that subtree.
- **Arrows / Tab / Shift+Tab** → move selection between blocks.
- **`m`** → toggle mouse capture on/off.
- **`r`** → force immediate refresh.
- **`space`** → pause/resume auto-refresh.
- **`q` / Ctrl+C** → quit.

### 7. `mem_tui.py` — entry point

PEP 723 inline metadata, `requires-python >= 3.13`, dependencies: `textual`,
`psutil`. Imports and runs `mem_tui.app.MemTuiApp`.

## Data Flow

```
psutil ──sample()──> list[ProcessInfo] ──build_tree()──> ProcessNode (with subtree_rss)
   │                                                            │
   │                                              visible nodes (minus collapsed)
   │                                                            │
   └────────── timer (2s, async) ◄──┐                    squarify() ──> list[Placed]
                                     │                          │
                              MemTuiApp state          colors.color_for()
                                     │                          │
                                     └────► TreemapWidget render + StatusBar
                                                    ▲
                                          mouse click / keys
```

## Error Handling

- Per-process psutil exceptions (`NoSuchProcess`, `AccessDenied`,
  `ZombieProcess`) are caught per-process and the process is skipped.
- A refresh that yields zero processes (shouldn't happen) keeps the prior frame
  and shows a status message rather than crashing.
- Defensive cycle guard in `build_tree` (malformed ppid chains).
- Terminal too small: widget renders a "resize" hint below a minimum size.

## Testing Strategy (TDD)

Stack: **pytest**, **pytest-mock** (mock psutil), **pytest-asyncio** (async
sampler + Textual pilots), **pytest-cov** (coverage).

- `tree.py`, `treemap.py`, `colors.py`: pure unit tests — the core logic.
- `sampler.py`: psutil mocked; assert record shaping and that vanished
  processes are skipped.
- `app.py` / `widgets.py`: Textual `App.run_test()` pilot — simulate clicks and
  keypresses, assert collapse/expand state, selection movement, mouse toggle,
  pause. Sampling is mocked so tests are deterministic.

Every production unit is written test-first (red → green → refactor).

## Tooling & Conventions

- Per project standards: `ruff format` + `ruff check` (`ruff.toml`), `pyright`
  strict (`pyrightconfig.json`). Both config files are created as part of setup.
- `pathlib.Path` over `os.path`; type hints throughout; docstrings on public
  functions; specific exception types.
- Run: `uv run mem_tui.py`. Tests: `uv run pytest`.

## Open Questions

None outstanding — all resolved during brainstorming.
