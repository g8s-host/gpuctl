"""Backend interface and the backend-neutral ``JobSpec``.

``JobSpec`` is the contract between the kind layer (which understands gpuctl's
YAML schema) and the execution backends. Builders produce a ``JobSpec``;
backends consume one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator, Protocol, runtime_checkable

from gpuctl.constants import Kind, Priority


@dataclass(frozen=True)
class VolumeMount:
    """A host-path bind mount.

    ``host_path`` and ``container_path`` are absolute paths. ``read_only``
    defaults to False to match the existing gpuctl behaviour where workdirs
    are writable.
    """

    host_path: str
    container_path: str
    read_only: bool = False


class JobState(str, Enum):
    """Coarse job state, normalised across backends."""

    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    UNKNOWN = "Unknown"
    LOST = "Lost"  # backend has a record but the runtime has no trace


@dataclass(frozen=True)
class JobSpec:
    """Backend-neutral description of a job.

    All sizes are normalised to integers so backends don't have to re-parse
    strings like ``"32Gi"``:

    - ``cpu_millicores``: 8 cores → ``8000``
    - ``memory_bytes``: ``"32Gi"`` → ``34359738368``

    ``env`` is a list of ``(name, value)`` tuples (order preserved, duplicates
    allowed; the last wins on most runtimes).
    """

    name: str
    namespace: str
    kind: Kind
    image: str
    command: tuple[str, ...]
    args: tuple[str, ...]
    env: tuple[tuple[str, str], ...]
    cpu_millicores: int
    memory_bytes: int
    gpu_count: int
    gpu_type: str | None
    pool: str | None
    replicas: int
    port: int | None
    health_check: str | None
    workdirs: tuple[VolumeMount, ...]
    priority: Priority
    labels: tuple[tuple[str, str], ...]
    annotations: tuple[tuple[str, str], ...]
    image_pull_secret: str | None
    long_running: bool  # training=False, inference/compute/notebook=True
    restart_policy: str  # Never / OnFailure / Always

    @property
    def labels_dict(self) -> dict[str, str]:
        return dict(self.labels)

    @property
    def annotations_dict(self) -> dict[str, str]:
        return dict(self.annotations)

    @property
    def env_dict(self) -> dict[str, str]:
        return dict(self.env)


@dataclass(frozen=True)
class JobHandle:
    """Opaque handle returned by ``Backend.create_job``.

    The backend is free to populate ``backend_ref`` with whatever it needs to
    locate the running workload later (k8s object name, container id, ...).
    """

    name: str
    namespace: str
    kind: Kind
    backend: str
    backend_ref: str  # opaque to callers


@dataclass(frozen=True)
class JobStatus:
    """A snapshot of a job's state at query time."""

    name: str
    namespace: str
    kind: Kind
    state: JobState
    backend: str
    node: str | None  # which node it ran on (SSH backend) or None
    container_id: str | None
    started_at: str | None  # ISO 8601
    finished_at: str | None
    exit_code: int | None
    message: str | None  # short human-readable reason
    raw: dict | None = None  # backend-specific extras


@runtime_checkable
class Backend(Protocol):
    """Execution backend interface.

    Backends are registered via ``gpuctl.backend.registry.register_backend``
    and looked up at runtime via ``get_backend()``. All methods raise a
    subclass of ``BackendError`` on failure — never the underlying transport
    exception.
    """

    name: str

    def create_job(self, spec: JobSpec) -> JobHandle:
        """Create a new job. Idempotency is *not* required at this layer;
        callers (kind handlers) decide whether to delete-then-create."""
        ...

    def delete_job(self, name: str, namespace: str) -> None:
        """Delete a job. Must be idempotent: deleting a missing job is a no-op."""
        ...

    def get_job(self, name: str, namespace: str) -> JobStatus:
        """Fetch current status. Raises ``JobNotFoundError`` if missing."""
        ...

    def list_jobs(
        self, namespace: str, labels: dict[str, str] | None = None
    ) -> list[JobStatus]:
        """List jobs in a namespace, optionally filtered by label match."""
        ...

    def stream_logs(
        self, name: str, namespace: str, tail: int = 100, follow: bool = False
    ) -> Iterator[str]:
        """Yield log lines. ``follow=True`` blocks until the job finishes."""
        ...

    def health_check(self) -> None:
        """Raise ``BackendNotConfiguredError`` if the backend can't run.

        Cheap probe used at CLI startup to fail fast (missing kubeconfig,
        empty inventory, etc.).
        """
        ...
