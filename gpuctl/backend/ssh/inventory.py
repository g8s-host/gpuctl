"""Node inventory for the SSH backend.

The inventory file (``$GPUCTL_STATE_DIR/inventory.yaml``, default
``~/.gpuctl/inventory.yaml``) declares the SSH-reachable GPU nodes and the
pools they belong to:

    version: v1
    nodes:
      - name: gpu-01
        host: 10.0.0.11
        port: 22
        user: ubuntu
        key_path: ~/.ssh/gpu_cluster
        pool: training-pool
        gpu_count: 8
        gpu_type: a100-80g
        labels:
          runwhere.ai/zone: cn-north-1a

The declared ``gpu_count`` / ``gpu_type`` are trusted (no probing on every
schedule). Reconciliation logic refreshes the runtime view of these values
in the state store.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from gpuctl.backend.errors import BackendNotConfiguredError
from gpuctl.constants import DEFAULT_POOL


@dataclass(frozen=True)
class Node:
    name: str
    host: str
    user: str
    port: int = 22
    key_path: str | None = None
    pool: str = DEFAULT_POOL
    gpu_count: int = 0
    gpu_type: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    allow_privileged: bool = False

    @property
    def address(self) -> str:
        return f"{self.user}@{self.host}:{self.port}"


@dataclass(frozen=True)
class Inventory:
    nodes: tuple[Node, ...]

    def by_name(self, name: str) -> Node:
        for n in self.nodes:
            if n.name == name:
                return n
        raise KeyError(f"node {name!r} not in inventory")

    def in_pool(self, pool: str | None) -> tuple[Node, ...]:
        target = pool or DEFAULT_POOL
        return tuple(n for n in self.nodes if n.pool == target)


def default_state_dir() -> Path:
    return Path(os.environ.get("GPUCTL_STATE_DIR", "~/.gpuctl")).expanduser()


def default_inventory_path() -> Path:
    return default_state_dir() / "inventory.yaml"


def load_inventory(path: Path | str | None = None) -> Inventory:
    """Read and validate the inventory file.

    Raises ``BackendNotConfiguredError`` if the file is missing or malformed
    so that the SSH backend fails fast at startup rather than at first use.
    """
    p = Path(path).expanduser() if path else default_inventory_path()
    if not p.is_file():
        raise BackendNotConfiguredError(
            f"SSH inventory not found at {p}. Create it (see "
            f"docs/design/ssh-backend.md §5.1) or set GPUCTL_STATE_DIR."
        )
    try:
        raw = yaml.safe_load(p.read_text()) or {}
    except yaml.YAMLError as exc:
        raise BackendNotConfiguredError(f"invalid inventory YAML at {p}: {exc}") from exc

    if not isinstance(raw, dict) or "nodes" not in raw:
        raise BackendNotConfiguredError(
            f"inventory at {p} must contain a top-level 'nodes' list"
        )
    nodes_raw = raw.get("nodes") or []
    if not isinstance(nodes_raw, list):
        raise BackendNotConfiguredError(f"'nodes' must be a list, got {type(nodes_raw).__name__}")
    nodes: list[Node] = []
    seen: set[str] = set()
    for idx, item in enumerate(nodes_raw):
        node = _parse_node(item, idx, source=p)
        if node.name in seen:
            raise BackendNotConfiguredError(f"duplicate node name {node.name!r} in {p}")
        seen.add(node.name)
        nodes.append(node)
    if not nodes:
        raise BackendNotConfiguredError(f"inventory at {p} declares no nodes")
    return Inventory(nodes=tuple(nodes))


def _parse_node(item: object, idx: int, *, source: Path) -> Node:
    if not isinstance(item, dict):
        raise BackendNotConfiguredError(
            f"inventory[{idx}] in {source} must be a mapping, got {type(item).__name__}"
        )
    try:
        name = str(item["name"])
        host = str(item["host"])
        user = str(item["user"])
    except KeyError as exc:
        raise BackendNotConfiguredError(
            f"inventory[{idx}] in {source} missing required field: {exc.args[0]}"
        ) from exc
    port = int(item.get("port", 22))
    if not (0 < port < 65536):
        raise BackendNotConfiguredError(
            f"inventory[{idx}] in {source}: port out of range: {port}"
        )
    key_path = item.get("key_path")
    if key_path is not None:
        key_path = str(Path(str(key_path)).expanduser())
    pool = str(item.get("pool", DEFAULT_POOL))
    gpu_count = int(item.get("gpu_count", 0))
    gpu_type = item.get("gpu_type")
    if gpu_type is not None:
        gpu_type = str(gpu_type)
    labels_raw = item.get("labels") or {}
    if not isinstance(labels_raw, dict):
        raise BackendNotConfiguredError(
            f"inventory[{idx}].labels must be a mapping, got {type(labels_raw).__name__}"
        )
    labels = {str(k): str(v) for k, v in labels_raw.items()}
    allow_privileged = bool(item.get("allow_privileged", False))
    return Node(
        name=name,
        host=host,
        user=user,
        port=port,
        key_path=key_path,
        pool=pool,
        gpu_count=gpu_count,
        gpu_type=gpu_type,
        labels=labels,
        allow_privileged=allow_privileged,
    )
