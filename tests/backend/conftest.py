"""Shared fixtures for backend tests.

Defines a fake ``Executor`` so SSH backend tests run without any real SSH
traffic. Tests can pre-register canned responses per (node, command-prefix).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

import pytest

from gpuctl.backend.base import JobSpec, VolumeMount
from gpuctl.backend.ssh.connection import ExecResult
from gpuctl.backend.ssh.inventory import Inventory, Node
from gpuctl.backend.ssh.state import StateStore
from gpuctl.constants import Kind, Priority


@dataclass
class _Call:
    node: str
    command: str
    timeout: int


class FakeExecutor:
    """In-process stub for the SSH executor.

    Responses are registered with ``set_response(node_name, prefix, ExecResult)``.
    The first matching prefix per call wins; unmatched commands return exit
    code 0 with empty stdout (cheerfully optimistic — tests that care should
    register explicit failures).
    """

    def __init__(self) -> None:
        self.calls: list[_Call] = []
        self._responses: list[tuple[str, str, ExecResult]] = []
        self._streams: dict[tuple[str, str], list[str]] = {}

    def set_response(self, node: str, prefix: str, result: ExecResult) -> None:
        self._responses.append((node, prefix, result))

    def set_stream(self, node: str, prefix: str, lines: list[str]) -> None:
        self._streams[(node, prefix)] = list(lines)

    def exec(self, node: Node, command: str, *, timeout: int) -> ExecResult:
        self.calls.append(_Call(node=node.name, command=command, timeout=timeout))
        for n, p, r in self._responses:
            if n == node.name and command.startswith(p):
                return r
        return ExecResult(exit_code=0, stdout="", stderr="")

    def stream(self, node: Node, command: str, *, timeout: int) -> Iterator[str]:
        self.calls.append(_Call(node=node.name, command=command, timeout=timeout))
        for (n, p), lines in self._streams.items():
            if n == node.name and command.startswith(p):
                yield from lines
                return
        return
        yield  # unreachable; preserves the generator type

    def close(self) -> None:
        pass


@pytest.fixture
def inventory() -> Inventory:
    return Inventory(
        nodes=(
            Node(
                name="gpu-01",
                host="10.0.0.11",
                user="ubuntu",
                pool="training-pool",
                gpu_count=8,
                gpu_type="a100-80g",
            ),
            Node(
                name="gpu-02",
                host="10.0.0.12",
                user="ubuntu",
                pool="training-pool",
                gpu_count=4,
                gpu_type="a10-24g",
            ),
            Node(
                name="cpu-01",
                host="10.0.0.21",
                user="ubuntu",
                pool="default",
                gpu_count=0,
            ),
        )
    )


@pytest.fixture
def state_store(tmp_path) -> StateStore:
    return StateStore(db_path=tmp_path / "state.db")


@pytest.fixture
def executor() -> FakeExecutor:
    return FakeExecutor()


@pytest.fixture
def training_spec() -> JobSpec:
    return JobSpec(
        name="demo-train",
        namespace="acme",
        kind=Kind.TRAINING,
        image="hiyouga/llamafactory:0.9.4",
        command=("bash", "-lc"),
        args=("python train.py",),
        env=(("NCCL_DEBUG", "INFO"),),
        cpu_millicores=8000,
        memory_bytes=34_359_738_368,
        gpu_count=2,
        gpu_type="a100-80g",
        pool="training-pool",
        replicas=1,
        port=None,
        health_check=None,
        workdirs=(
            VolumeMount(host_path="/data", container_path="/data"),
            VolumeMount(host_path="/output", container_path="/output"),
        ),
        priority=Priority.HIGH,
        labels=(
            ("runwhere.ai/job-type", "training"),
            ("runwhere.ai/pool", "training-pool"),
        ),
        annotations=(("runwhere.ai/description", "demo"),),
        image_pull_secret=None,
        long_running=False,
        restart_policy="Never",
    )
