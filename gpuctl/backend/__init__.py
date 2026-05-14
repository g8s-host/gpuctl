"""Pluggable execution backends for gpuctl.

The default backend (``kubernetes``) preserves all existing behaviour. A
second backend (``ssh``) targets bare GPU hosts reachable over SSH.

See ``docs/design/ssh-backend.md`` for the design.
"""

from gpuctl.backend.base import (
    Backend,
    JobHandle,
    JobSpec,
    JobStatus,
    JobState,
    VolumeMount,
)
from gpuctl.backend.errors import (
    BackendError,
    BackendNotConfiguredError,
    JobAlreadyExistsError,
    JobNotFoundError,
    NoCapacityError,
    UnsupportedFeatureError,
)
from gpuctl.backend.registry import get_backend, register_backend

__all__ = [
    "Backend",
    "BackendError",
    "BackendNotConfiguredError",
    "JobAlreadyExistsError",
    "JobHandle",
    "JobNotFoundError",
    "JobSpec",
    "JobState",
    "JobStatus",
    "NoCapacityError",
    "UnsupportedFeatureError",
    "VolumeMount",
    "get_backend",
    "register_backend",
]
