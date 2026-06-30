# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An async Textual TUI that renders a **squarified treemap of process memory** (GrandPerspective for RAM), targeting macOS via `psutil`. Memory is rolled up the process tree so a parent shows its own RSS plus all descendants. Two views (toggled with `t`): a treemap canvas and a scrollable ps-style indented tree. See `README.md` for the user-facing keymap and screenshots.

## Commands

```bash
uv sync                                       # install deps (incl. dev group)
uv run mem_tui.py                             # run the app (standalone PEP-723 script)
uv run pytest                                 # full test suite
uv run pytest tests/test_treemap.py           # one file
uv run pytest tests/test_treemap.py::test_name -v   # one test
uv run pytest --cov=mem_tui --cov-report=term-missing   # with coverage (as CI runs it)
uv run ruff check .                           # lint
uv run ruff format --check .                  # format check (CI fails if not formatted)
uv run pyright                                # type check (strict mode)
```

Requires Python >=3.13. CI (`.github/workflows/ci.yml`) runs ruff check, `ruff format --check`, pyright strict, then pytest with coverage — match all four locally before pushing.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the diagram, module
table, and data-model reference.

A strict one-directional pipeline. Each stage is a separate module with a single dataclass output; everything up to the widgets is **pure and Textual-free**, which is what makes it testable in isolation. Never import `textual` into the lower layers.

```
sampler ──► tree ──┬──► layout (+ treemap) ──► render ──► widgets ──► app
  │          │     └──► treeview ───────────────────────┘
ProcessInfo  ProcessNode    Block / Placed      Cell      (TreemapWidget,
(models.py)  (subtree_rss)  TreeRow                        ProcessTreeWidget,
                                                           StatusBar)
```

- **`models.ProcessInfo`** — frozen snapshot of one process (pid, ppid, name, rss, cmdline). No dependencies; the shared currency between sampler and tree.
- **`sampler.sample()`** — async; offloads the blocking `psutil.process_iter()` to `asyncio.to_thread` so the event loop never stalls. Processes that vanish or deny access mid-scan are silently skipped.
- **`tree.build_tree()`** — turns the flat list into a `ProcessNode` tree under a **synthetic root at pid 0**. Orphans (missing parent) and **cycles** both attach to the root, so it never hangs. `_compute_subtree_rss` does the rollup. `top_level_ancestor` walks up to the color-group root — the first ancestor whose parent is a **boundary ppid** (`{0, 1}`: synthetic root and launchd/init), so each app under launchd gets its own color instead of all sharing launchd's.
- **`treemap.squarify()`** — pure squarified-treemap geometry (Bruls/Huizing/van Wijk). Takes `(id, weight)` pairs + a `Rect`, returns `Placed` rects. Drops non-positive weights; deterministic, largest-first.
- **`layout.compute_blocks()`** — bridges tree + collapse-state + rect into drawable `Block`s. Key idea: an **expanded** internal node is not drawn directly — its rect is subdivided among its children plus a **"self" slice** (`kind="self"`, negative sentinel id) representing the parent's own RSS. A **collapsed** or childless node becomes one `kind="leaf"` block. `block_at()` does hit-testing (later blocks win, i.e. drawn-on-top).
- **`treeview.build_rows()`** — the alternate view: depth-first `TreeRow` list, children sorted by subtree RSS desc, with branch-glyph prefixes (`├──`/`└──`/`│`).
- **`render.block_cell()`** — pure per-cell styling: 3D bevel (lighter top/left, darker bottom/right) so tiles read as distinct; white frame on selection; auto black/white text by luminance contrast.
- **`colors.color_for()`** — stable hex from a curated palette, keyed by ancestor pid (`pid % len(PALETTE)`).
- **`widgets.py`** — the only Textual layer below the app. `TreemapWidget` renders blocks via `render_line` and posts `BlockClicked`/`BlockHovered`/`Resized` messages. `ProcessTreeWidget` is a `ScrollView` of formatted rows.
- **`app.MemTuiApp`** — owns all mutable UI state (`collapsed` set, `selected_pid`, `hovered_pid`, `view_mode`, `paused`). The central method is `_recompute()`: re-run layout + treeview from the current tree/collapse-state and re-render. `refresh_data()` re-samples on a timer; **on an empty sample it keeps the previous frame** rather than blanking.

### Conventions

- **Dependency injection for testing**: `MemTuiApp(sample_fn=..., auto_refresh=False)` injects a fake sampler — `tests/test_app.py` drives the real app through Textual's `run_test()` pilot with no live processes. Follow this pattern; don't reach for live `psutil` in tests.
- All data classes are `@dataclass(frozen=True, slots=True)` (mutable `ProcessNode` is the exception). Keep new ones the same.
- `from __future__ import annotations` at the top of every module; strict pyright, so annotate fully.
- The synthetic-root pid `0` is filtered out by `tree.flatten()` and `_ROOT_PID` checks — real processes are never pid 0 here.
- Tests mirror modules one-to-one (`test_<module>.py`). Add tests at the lowest pure layer a change touches, not only through the app.
