# mem_tui

Async-first terminal UI that renders a **squarified treemap of process memory
usage on macOS** — a GrandPerspective-style segmented view, but for RAM.

Memory is rolled up the process tree, so a parent (e.g. `Google Chrome`, `node`,
a supervisor) shows the total of itself plus all descendants. Answer "which
process is eating all my memory?" at a glance.

Two views, toggled with **t**:

- **Treemap** — squarified, beveled tiles sized by subtree memory and colored by
  application. Hover any tile to read its process in the status bar.
- **Tree** — a scrollable ps-style hierarchy showing each process indented under
  its parent, with own RSS, subtree total + percent of all memory, and child
  counts. Both views share the same live samples, selection, and collapse state.

## Run

```bash
uv run mem_tui.py
```

## Keys

- **t** — toggle Treemap / Tree view
- **Click / Enter** — collapse/expand a subtree (roll children into the parent)
- **Arrows / Tab** — move selection
- **Hover** (treemap) — show the process under the cursor in the status bar
- **m** — toggle mouse on/off
- **r** — force refresh
- **space** — pause/resume auto-refresh
- **q** — quit

## Develop

```bash
uv sync
uv run pytest
uv run ruff check .
uv run pyright
```
