"""Single-node scheduler for the SSH backend.

Decision policy (v1, intentionally simple):

1. Filter nodes by ``spec.pool`` (defaulting to "default").
2. If ``spec.gpu_type`` is set, require the node to declare it.
3. Require ``free_gpus >= spec.gpu_count``.
4. Among survivors, pick the node with the most free GPUs (or, if no GPUs
   are needed, the least-loaded node by used-GPU count — keeps GPU-heavy
   workloads from crowding onto a single 0-GPU job's host).

Bin-packing, anti-affinity, preemption: out of scope for v1.
"""

from __future__ import annotations

from dataclasses import dataclass

from gpuctl.backend.base import JobSpec
from gpuctl.backend.errors import NoCapacityError
from gpuctl.backend.ssh.inventory import Inventory, Node
from gpuctl.constants import DEFAULT_POOL


@dataclass(frozen=True)
class Decision:
    node: Node
    free_gpus: int


def select_node(
    spec: JobSpec, inventory: Inventory, used_gpus: dict[str, int]
) -> Decision:
    """Pick a node for ``spec`` or raise ``NoCapacityError``.

    ``used_gpus`` maps node name → currently-allocated GPU count, sourced
    from ``StateStore.used_gpus_per_node()``.
    """
    pool = spec.pool or DEFAULT_POOL
    candidates = inventory.in_pool(pool)
    if not candidates:
        raise NoCapacityError(
            f"no nodes registered in pool {pool!r} "
            f"(inventory has {len(inventory.nodes)} nodes total)"
        )

    matched = list(candidates)
    if spec.gpu_type:
        matched = [n for n in matched if n.gpu_type == spec.gpu_type]
        if not matched:
            raise NoCapacityError(
                f"no node in pool {pool!r} matches gpu_type={spec.gpu_type!r}"
            )

    fit: list[Decision] = []
    for n in matched:
        free = n.gpu_count - used_gpus.get(n.name, 0)
        if free < spec.gpu_count:
            continue
        fit.append(Decision(node=n, free_gpus=free))

    if not fit:
        # Most useful error: tell the user which nodes were close.
        details = ", ".join(
            f"{n.name}=({n.gpu_count - used_gpus.get(n.name, 0)}/{n.gpu_count} free)"
            for n in matched
        )
        raise NoCapacityError(
            f"pool {pool!r} has no node with {spec.gpu_count} free GPU(s). "
            f"current: {details}"
        )

    if spec.gpu_count > 0:
        # Spread across nodes: pick the one with the most headroom.
        fit.sort(key=lambda d: d.free_gpus, reverse=True)
    else:
        # CPU-only job: prefer least-busy host (free_gpus = unused capacity).
        fit.sort(key=lambda d: d.free_gpus, reverse=True)
    return fit[0]
