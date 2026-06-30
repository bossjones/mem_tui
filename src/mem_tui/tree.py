"""Build a process tree from flat snapshots and roll resident memory upward."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from mem_tui.models import ProcessInfo

# Synthetic root that owns every top-level process. Real pids are never 0 here.
_ROOT_PID = 0

# Parent pids that mark a color-group boundary: the synthetic root (0) and the
# OS init/supervisor process (launchd / init / systemd is always pid 1). A node
# whose parent is one of these starts its own color group, so each application
# under launchd gets a distinct color instead of all sharing launchd's.
_BOUNDARY_PPIDS = frozenset({0, 1})


def _no_children() -> list[ProcessNode]:
    return []


@dataclass(slots=True)
class ProcessNode:
    """A node in the process tree.

    Attributes:
        info: The process snapshot for this node.
        children: Direct child nodes.
        subtree_rss: This process's own RSS plus the subtree RSS of all
            descendants (bytes).
    """

    info: ProcessInfo
    children: list[ProcessNode] = field(default_factory=_no_children)
    subtree_rss: int = 0


def _synthetic_root() -> ProcessNode:
    return ProcessNode(
        info=ProcessInfo(pid=_ROOT_PID, ppid=-1, name="processes", rss=0, cmdline=""),
    )


def build_tree(procs: list[ProcessInfo]) -> ProcessNode:
    """Build the process tree and compute subtree RSS for every node.

    Processes whose parent is absent from ``procs`` (orphans) are attached to a
    synthetic root. Malformed parent chains that form a cycle are broken by
    attaching the offending node to the synthetic root, so this never hangs.
    """
    root = _synthetic_root()
    nodes: dict[int, ProcessNode] = {proc.pid: ProcessNode(info=proc) for proc in procs}

    for pid, node in nodes.items():
        parent_pid = node.info.ppid
        parent = nodes.get(parent_pid)
        if parent is None or parent_pid == pid or _creates_cycle(nodes, pid, parent_pid):
            root.children.append(node)
        else:
            parent.children.append(node)

    _compute_subtree_rss(root)
    return root


def _creates_cycle(nodes: dict[int, ProcessNode], pid: int, parent_pid: int) -> bool:
    """Return True if walking parents from ``parent_pid`` reaches ``pid``."""
    seen: set[int] = set()
    current = parent_pid
    while current in nodes:
        if current == pid:
            return True
        if current in seen:
            return True
        seen.add(current)
        current = nodes[current].info.ppid
    return False


def _compute_subtree_rss(node: ProcessNode) -> int:
    total = node.info.rss
    for child in node.children:
        total += _compute_subtree_rss(child)
    node.subtree_rss = total
    return total


def flatten(root: ProcessNode) -> list[ProcessNode]:
    """Return all real process nodes (excluding the synthetic root)."""
    return [node for node in _walk(root) if node.info.pid != _ROOT_PID]


def _walk(node: ProcessNode) -> Iterator[ProcessNode]:
    yield node
    for child in node.children:
        yield from _walk(child)


def find(root: ProcessNode, pid: int) -> ProcessNode | None:
    """Return the node with the given pid, or None."""
    for node in _walk(root):
        if node.info.pid == pid:
            return node
    return None


def top_level_ancestor(node: ProcessNode, root: ProcessNode) -> ProcessNode:
    """Return the color-group root on ``node``'s ancestor path.

    Walking up from ``node``, this is the first ancestor whose parent is a
    boundary process (the synthetic root or launchd/init at pid 1). For a deeply
    nested helper this is the owning application, so all of an app's helpers map
    to the same color while different apps stay distinct.
    """
    parents = _parent_map(root)
    current = node
    while True:
        if current.info.ppid in _BOUNDARY_PPIDS:
            return current
        parent = parents.get(current.info.pid)
        if parent is None or parent.info.pid == _ROOT_PID:
            return current
        current = parent


def _parent_map(root: ProcessNode) -> dict[int, ProcessNode]:
    parents: dict[int, ProcessNode] = {}
    for node in _walk(root):
        for child in node.children:
            parents[child.info.pid] = node
    return parents
