"""Convert gpuctl API models (TrainingJob, InferenceJob, ...) to ``JobSpec``.

The adapter is intentionally a pure function module — no I/O, no globals,
fully testable.
"""

from __future__ import annotations

import re
from typing import Iterable, Mapping

from gpuctl.api.common import (
    EnvironmentConfig,
    JobMetadata,
    ResourceRequest,
    ServiceConfig,
    StorageConfig,
)
from gpuctl.backend.base import JobSpec, VolumeMount
from gpuctl.constants import DEFAULT_POOL, Kind, Labels, Priority


# Memory unit suffixes per the Kubernetes resource grammar:
# https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
_MEMORY_UNITS = {
    "": 1,
    "k": 1000,
    "M": 1000**2,
    "G": 1000**3,
    "T": 1000**4,
    "P": 1000**5,
    "Ki": 1024,
    "Mi": 1024**2,
    "Gi": 1024**3,
    "Ti": 1024**4,
    "Pi": 1024**5,
}

_MEMORY_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]*)\s*$")


def parse_memory(value: str | int) -> int:
    """Parse a Kubernetes-style memory string to bytes.

    >>> parse_memory("32Gi")
    34359738368
    >>> parse_memory("512Mi")
    536870912
    >>> parse_memory(1024)
    1024
    """
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        raise ValueError(f"memory must be str or int, got {type(value).__name__}")
    match = _MEMORY_RE.match(value)
    if not match:
        raise ValueError(f"unparseable memory value: {value!r}")
    qty = float(match.group(1))
    unit = match.group(2)
    if unit not in _MEMORY_UNITS:
        raise ValueError(f"unknown memory unit: {unit!r} in {value!r}")
    return int(qty * _MEMORY_UNITS[unit])


def parse_cpu(value: str | int) -> int:
    """Parse a Kubernetes-style CPU value to integer millicores.

    >>> parse_cpu("8")
    8000
    >>> parse_cpu("8000m")
    8000
    >>> parse_cpu(2)
    2000
    >>> parse_cpu("1.5")
    1500
    """
    if isinstance(value, int):
        return value * 1000
    if not isinstance(value, str):
        raise ValueError(f"cpu must be str or int, got {type(value).__name__}")
    text = value.strip()
    if text.endswith("m"):
        return int(text[:-1])
    return int(float(text) * 1000)


def _normalise_env(env: Iterable[Mapping[str, str]]) -> tuple[tuple[str, str], ...]:
    """Flatten the gpuctl env-list-of-dicts shape into ``[(name, value)]``.

    Accepts both forms found in the codebase:
    - ``[{"name": "NCCL_DEBUG", "value": "INFO"}]`` (k8s-style)
    - ``[{"NCCL_DEBUG": "INFO"}]`` (gpuctl YAML shorthand)
    """
    pairs: list[tuple[str, str]] = []
    for item in env or []:
        if not isinstance(item, Mapping):
            continue
        if "name" in item and "value" in item:
            pairs.append((str(item["name"]), str(item["value"])))
            continue
        for k, v in item.items():
            pairs.append((str(k), str(v)))
    return tuple(pairs)


def _workdirs_to_volumes(storage: StorageConfig | None) -> tuple[VolumeMount, ...]:
    if storage is None or not getattr(storage, "workdirs", None):
        return ()
    mounts: list[VolumeMount] = []
    for entry in storage.workdirs:
        if not isinstance(entry, Mapping):
            continue
        path = entry.get("path")
        if not path:
            continue
        host = entry.get("hostPath") or path
        ro = bool(entry.get("readOnly", False))
        mounts.append(
            VolumeMount(host_path=str(host), container_path=str(path), read_only=ro)
        )
    return tuple(mounts)


def _base_labels(
    kind: Kind, job: JobMetadata, resources: ResourceRequest, namespace: str
) -> tuple[tuple[str, str], ...]:
    return (
        (Labels.JOB_TYPE, kind.value),
        (Labels.PRIORITY, Priority(job.priority).value),
        (Labels.POOL, resources.pool or DEFAULT_POOL),
        (Labels.NAMESPACE, namespace),
    )


def _annotations(job: JobMetadata) -> tuple[tuple[str, str], ...]:
    if job.description:
        return ((Labels.DESCRIPTION, job.description),)
    return ()


def _build(
    *,
    kind: Kind,
    job: JobMetadata,
    environment: EnvironmentConfig,
    resources: ResourceRequest,
    storage: StorageConfig | None,
    service: ServiceConfig | None,
    namespace: str,
    long_running: bool,
    restart_policy: str,
) -> JobSpec:
    return JobSpec(
        name=job.name,
        namespace=namespace,
        kind=kind,
        image=environment.image,
        command=tuple(environment.command or ()),
        args=tuple(environment.args or ()),
        env=_normalise_env(environment.env or []),
        cpu_millicores=parse_cpu(resources.cpu),
        memory_bytes=parse_memory(resources.memory),
        gpu_count=int(resources.gpu or 0),
        gpu_type=resources.gpu_type,
        pool=resources.pool,
        replicas=int(service.replicas) if service else 1,
        port=int(service.port) if service else None,
        health_check=service.health_check if service else None,
        workdirs=_workdirs_to_volumes(storage),
        priority=Priority(job.priority),
        labels=_base_labels(kind, job, resources, namespace),
        annotations=_annotations(job),
        image_pull_secret=environment.image_pull_secret,
        long_running=long_running,
        restart_policy=restart_policy,
    )


def training_to_spec(training_job, namespace: str) -> JobSpec:
    """Convert ``TrainingJob`` (gpuctl.api.training) to ``JobSpec``."""
    return _build(
        kind=Kind.TRAINING,
        job=training_job.job,
        environment=training_job.environment,
        resources=training_job.resources,
        storage=getattr(training_job, "storage", None),
        service=None,
        namespace=namespace,
        long_running=False,
        restart_policy="Never",
    )


def inference_to_spec(inference_job, namespace: str) -> JobSpec:
    """Convert ``InferenceJob`` to ``JobSpec``."""
    return _build(
        kind=Kind.INFERENCE,
        job=inference_job.job,
        environment=inference_job.environment,
        resources=inference_job.resources,
        storage=None,
        service=inference_job.service,
        namespace=namespace,
        long_running=True,
        restart_policy="Always",
    )


def compute_to_spec(compute_job, namespace: str) -> JobSpec:
    """Convert ``ComputeJob`` to ``JobSpec``."""
    return _build(
        kind=Kind.COMPUTE,
        job=compute_job.job,
        environment=compute_job.environment,
        resources=compute_job.resources,
        storage=getattr(compute_job, "storage", None),
        service=getattr(compute_job, "service", None),
        namespace=namespace,
        long_running=True,
        restart_policy="Always",
    )


def notebook_to_spec(notebook_job, namespace: str) -> JobSpec:
    """Convert ``NotebookJob`` to ``JobSpec``."""
    return _build(
        kind=Kind.NOTEBOOK,
        job=notebook_job.job,
        environment=notebook_job.environment,
        resources=notebook_job.resources,
        storage=getattr(notebook_job, "storage", None),
        service=getattr(notebook_job, "service", None),
        namespace=namespace,
        long_running=True,
        restart_policy="Always",
    )
