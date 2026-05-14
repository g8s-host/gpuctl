"""Backend registry and lookup.

Backends are registered lazily (import-on-demand) so that an environment that
only uses the Kubernetes backend never has to import paramiko, and vice
versa.
"""

from __future__ import annotations

import os
from typing import Callable

from gpuctl.backend.base import Backend
from gpuctl.backend.errors import BackendNotConfiguredError

DEFAULT_BACKEND = "kubernetes"
BACKEND_ENV = "GPUCTL_BACKEND"

# name -> factory returning a Backend instance
_FACTORIES: dict[str, Callable[[], Backend]] = {}
# cached instances (one per backend name)
_INSTANCES: dict[str, Backend] = {}


def register_backend(name: str, factory: Callable[[], Backend]) -> None:
    """Register a backend factory.

    ``factory`` is called at most once per process and may raise
    ``BackendNotConfiguredError`` if its prerequisites aren't met.
    """
    _FACTORIES[name] = factory


def _kubernetes_factory() -> Backend:
    from gpuctl.backend.kubernetes.backend import KubernetesBackend

    return KubernetesBackend()


def _ssh_factory() -> Backend:
    from gpuctl.backend.ssh.backend import SshBackend

    return SshBackend.from_env()


register_backend("kubernetes", _kubernetes_factory)
register_backend("ssh", _ssh_factory)


def _selected_backend_name() -> str:
    return os.environ.get(BACKEND_ENV, DEFAULT_BACKEND).strip().lower()


def get_backend(name: str | None = None) -> Backend:
    """Return the configured backend (cached after first call).

    Selection precedence: explicit ``name`` argument, then ``$GPUCTL_BACKEND``,
    then ``"kubernetes"``.
    """
    target = name or _selected_backend_name()
    if target in _INSTANCES:
        return _INSTANCES[target]
    factory = _FACTORIES.get(target)
    if factory is None:
        registered = ", ".join(sorted(_FACTORIES)) or "<none>"
        raise BackendNotConfiguredError(
            f"Unknown backend '{target}'. Registered: {registered}."
        )
    instance = factory()
    _INSTANCES[target] = instance
    return instance


def reset_cache() -> None:
    """Drop cached backend instances. Intended for tests."""
    _INSTANCES.clear()
