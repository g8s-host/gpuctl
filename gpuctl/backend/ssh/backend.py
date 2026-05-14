"""``SshBackend``: the ``Backend`` protocol implementation for SSH-deployed
docker workloads.

Composition: inventory + state + runtime + connection + scheduler. This file
contains no command-construction logic and no SQL — only orchestration.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from typing import Iterator

from gpuctl.backend.base import (
    Backend,
    JobHandle,
    JobSpec,
    JobState,
    JobStatus,
)
from gpuctl.backend.errors import (
    BackendError,
    JobNotFoundError,
    UnsupportedFeatureError,
)
from gpuctl.backend.ssh import runtime
from gpuctl.backend.ssh.connection import Executor, ExecResult, ParamikoExecutor
from gpuctl.backend.ssh.inventory import Inventory, Node, load_inventory
from gpuctl.backend.ssh.scheduler import select_node
from gpuctl.backend.ssh.state import JobRow, StateStore
from gpuctl.constants import Kind, Labels


def _default_timeout() -> int:
    return int(os.environ.get("GPUCTL_SSH_TIMEOUT", "30"))


class SshBackend:
    name = "ssh"

    def __init__(
        self,
        *,
        inventory: Inventory,
        state: StateStore,
        executor: Executor,
    ) -> None:
        self._inventory = inventory
        self._state = state
        self._executor = executor

    @classmethod
    def from_env(cls) -> "SshBackend":
        """Construct an SshBackend from environment + filesystem state."""
        inventory = load_inventory()
        state = StateStore()
        executor = ParamikoExecutor()
        return cls(inventory=inventory, state=state, executor=executor)

    # ----- create -----

    def create_job(self, spec: JobSpec) -> JobHandle:
        self._validate(spec)
        used = self._state.used_gpus_per_node()
        decision = select_node(spec, self._inventory, used)
        node = decision.node
        name = runtime.container_name(spec)
        spec_payload = _spec_to_json(spec)

        row = self._state.insert_job(
            name=spec.name,
            namespace=spec.namespace,
            kind=spec.kind.value,
            node=node.name,
            container_name=name,
            spec_json=spec_payload,
            labels=spec.labels_dict,
            status=JobState.PENDING.value,
        )

        cmd = runtime.build_run_command(spec, name=name)
        result = self._executor.exec(node, cmd, timeout=_default_timeout())
        if result.exit_code != 0:
            # The DB row is junk now; remove it so list_jobs doesn't show
            # ghosts.
            self._state.delete_job(spec.name, spec.namespace)
            raise BackendError(
                f"docker run failed on {node.name} (exit {result.exit_code}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        container_id = result.stdout.strip().splitlines()[-1] if result.stdout else ""
        if container_id:
            self._state.set_container_id(row.id, container_id)
        self._state.update_status(spec.name, spec.namespace, JobState.RUNNING.value)
        return JobHandle(
            name=spec.name,
            namespace=spec.namespace,
            kind=spec.kind,
            backend=self.name,
            backend_ref=container_id or name,
        )

    def _validate(self, spec: JobSpec) -> None:
        if spec.replicas > 1:
            raise UnsupportedFeatureError(
                "SshBackend (v1) does not support replicas > 1. Run multiple "
                "jobs explicitly, or use the kubernetes backend."
            )
        if spec.kind == Kind.NOTEBOOK and spec.port is None:
            # The k8s notebook builder defaults to 8888; the SSH backend
            # expects the spec to be explicit, so this only fires on
            # malformed specs.
            raise UnsupportedFeatureError(
                "notebook spec requires a service.port (default 8888)."
            )

    # ----- delete -----

    def delete_job(self, name: str, namespace: str) -> None:
        try:
            row = self._state.get_job(name, namespace)
        except JobNotFoundError:
            return
        node = self._inventory.by_name(row.node)
        cmd = runtime.build_rm_command(row.container_name)
        # docker rm -f on missing container is non-fatal; we don't escalate.
        self._executor.exec(node, cmd, timeout=_default_timeout())
        self._state.delete_job(name, namespace)

    # ----- get / list -----

    def get_job(self, name: str, namespace: str) -> JobStatus:
        row = self._state.get_job(name, namespace)
        node = self._inventory.by_name(row.node)
        return self._refresh_status(row, node)

    def list_jobs(
        self, namespace: str, labels: dict[str, str] | None = None
    ) -> list[JobStatus]:
        rows = self._state.list_jobs(namespace, labels=labels)
        out: list[JobStatus] = []
        # v1: sequential. List is cold path (CLI invocation); per-call latency
        # dominated by ssh round-trip not parallelism. Parallel fan-out can be
        # added later if list becomes painful with many nodes.
        for row in rows:
            try:
                node = self._inventory.by_name(row.node)
            except KeyError:
                out.append(_status_lost(row))
                continue
            out.append(self._refresh_status(row, node))
        return out

    def _refresh_status(self, row: JobRow, node: Node) -> JobStatus:
        cmd = runtime.build_inspect_command(row.container_name)
        result = self._executor.exec(node, cmd, timeout=_default_timeout())
        state = _state_from_inspect(result)
        # Persist if it changed.
        if state.state.value != row.status:
            self._state.update_status(row.name, row.namespace, state.state.value)
        return JobStatus(
            name=row.name,
            namespace=row.namespace,
            kind=Kind(row.kind),
            state=state.state,
            backend=self.name,
            node=node.name,
            container_id=row.container_id,
            started_at=state.started_at,
            finished_at=state.finished_at,
            exit_code=state.exit_code,
            message=state.message,
            raw={"row": asdict(row), "inspect": state.raw},
        )

    # ----- logs -----

    def stream_logs(
        self, name: str, namespace: str, tail: int = 100, follow: bool = False
    ) -> Iterator[str]:
        row = self._state.get_job(name, namespace)
        node = self._inventory.by_name(row.node)
        cmd = runtime.build_logs_command(row.container_name, tail=tail, follow=follow)
        # follow=True can run for a long time; bump timeout so paramiko doesn't
        # kill the channel mid-stream. The user terminates with Ctrl-C.
        timeout = 86400 if follow else _default_timeout()
        yield from self._executor.stream(node, cmd, timeout=timeout)

    # ----- health -----

    def health_check(self) -> None:
        # Cheap probe: ensure each node answers ``docker version``.
        for node in self._inventory.nodes:
            cmd = runtime.build_probe_command()
            result = self._executor.exec(node, cmd, timeout=_default_timeout())
            if result.exit_code != 0:
                raise BackendError(
                    f"node {node.name} unreachable or missing docker: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            docker_ver, nv_runtime, gpu_count = _parse_probe(result.stdout)
            self._state.touch_node(
                node.name,
                gpu_count_real=gpu_count,
                docker_version=docker_ver,
            )
            if node.gpu_count > 0 and nv_runtime != "yes":
                raise BackendError(
                    f"node {node.name} declares gpu_count={node.gpu_count} but "
                    f"docker has no 'nvidia' runtime. Install NVIDIA Container "
                    f"Toolkit on the node."
                )


# ---------- helpers ----------


def _spec_to_json(spec: JobSpec) -> str:
    """Serialise a JobSpec to JSON for state-store storage.

    Frozen dataclasses with tuples don't go through ``json.dumps`` cleanly
    (tuples become lists, which is fine; enums need ``str()``). We hand-roll
    a minimal dict to keep the on-disk format stable.
    """
    return json.dumps(
        {
            "name": spec.name,
            "namespace": spec.namespace,
            "kind": spec.kind.value,
            "image": spec.image,
            "command": list(spec.command),
            "args": list(spec.args),
            "env": [list(p) for p in spec.env],
            "cpu_millicores": spec.cpu_millicores,
            "memory_bytes": spec.memory_bytes,
            "gpu_count": spec.gpu_count,
            "gpu_type": spec.gpu_type,
            "pool": spec.pool,
            "replicas": spec.replicas,
            "port": spec.port,
            "health_check": spec.health_check,
            "workdirs": [
                {
                    "host_path": w.host_path,
                    "container_path": w.container_path,
                    "read_only": w.read_only,
                }
                for w in spec.workdirs
            ],
            "priority": spec.priority.value,
            "labels": dict(spec.labels),
            "annotations": dict(spec.annotations),
            "image_pull_secret": spec.image_pull_secret,
            "long_running": spec.long_running,
            "restart_policy": spec.restart_policy,
        },
        sort_keys=True,
    )


def _status_lost(row: JobRow) -> JobStatus:
    return JobStatus(
        name=row.name,
        namespace=row.namespace,
        kind=Kind(row.kind),
        state=JobState.LOST,
        backend="ssh",
        node=row.node,
        container_id=row.container_id,
        started_at=None,
        finished_at=None,
        exit_code=None,
        message=f"node {row.node!r} no longer in inventory",
        raw={"row": asdict(row)},
    )


from dataclasses import dataclass as _dc


@_dc(frozen=True)
class _ParsedInspect:
    state: JobState
    started_at: str | None
    finished_at: str | None
    exit_code: int | None
    message: str | None
    raw: dict


def _state_from_inspect(result: ExecResult) -> _ParsedInspect:
    # Container removed or never created.
    if result.exit_code != 0 or not result.stdout.strip():
        msg = result.stderr.strip() or "container not found"
        return _ParsedInspect(
            state=JobState.LOST,
            started_at=None,
            finished_at=None,
            exit_code=None,
            message=msg,
            raw={"exit_code": result.exit_code, "stderr": result.stderr},
        )
    parsed = runtime.parse_inspect_state(result.stdout)
    if not parsed:
        return _ParsedInspect(
            state=JobState.UNKNOWN,
            started_at=None,
            finished_at=None,
            exit_code=None,
            message="docker inspect returned no usable data",
            raw={"stdout": result.stdout[:512]},
        )
    docker_status = parsed.get("status")
    if parsed.get("running"):
        state = JobState.RUNNING
    elif docker_status == "exited":
        ec = parsed.get("exit_code")
        state = JobState.SUCCEEDED if ec == 0 else JobState.FAILED
    elif docker_status == "created":
        state = JobState.PENDING
    elif docker_status in ("dead", "removing"):
        state = JobState.FAILED
    else:
        state = JobState.UNKNOWN
    return _ParsedInspect(
        state=state,
        started_at=parsed.get("started_at"),
        finished_at=parsed.get("finished_at"),
        exit_code=parsed.get("exit_code"),
        message=parsed.get("error") or None,
        raw=parsed,
    )


def _parse_probe(stdout: str) -> tuple[str | None, str, int | None]:
    line = stdout.strip().splitlines()[-1] if stdout.strip() else ""
    parts = line.split("|")
    if len(parts) != 3:
        return (None, "no", None)
    docker_ver = parts[0].strip() or None
    nv_runtime = parts[1].strip() or "no"
    try:
        gpu_count = int(parts[2].strip())
    except ValueError:
        gpu_count = None
    return (docker_ver, nv_runtime, gpu_count)


# Keeps the unused-imports linter happy and reserves the helper for future
# use; remove if it stays unused after v0.11.
_ = time
