"""Docker command builders for the SSH backend.

Pure functions only — no SSH, no I/O. Test by string-equality.

Command construction uses ``shlex.quote`` for every user-controlled value, so
no field can break out of the command line. The output is a single shell
command suitable for ``ssh user@host 'cmd'``.
"""

from __future__ import annotations

import hashlib
import shlex
from typing import Sequence

from gpuctl.backend.base import JobSpec
from gpuctl.constants import Kind, Labels

# All gpuctl-managed containers carry this label so we can list + reap them.
MANAGED_BY_LABEL = "runwhere.ai/managed-by"
MANAGED_BY_VALUE = "gpuctl"

# Docker container name max length is 64 chars including leading ``/``;
# practically anything ≤ 63 of [a-zA-Z0-9_.-] is safe.
_MAX_CONTAINER_NAME = 63


def container_name(spec: JobSpec) -> str:
    """Deterministic container name from (namespace, kind, name).

    Long names are truncated and suffixed with a hash so two different jobs
    that share a 50-char prefix don't collide.
    """
    base = f"gpuctl-{spec.namespace}-{spec.kind.value}-{spec.name}".lower()
    base = "".join(c if c.isalnum() or c in "_.-" else "-" for c in base)
    if len(base) <= _MAX_CONTAINER_NAME:
        return base
    digest = hashlib.sha1(base.encode()).hexdigest()[:8]
    return f"{base[:_MAX_CONTAINER_NAME - 9]}-{digest}"


def build_run_command(spec: JobSpec, *, name: str) -> str:
    """Render the full ``docker run`` command for ``spec``.

    Long-running specs use ``-d``; one-shot training uses ``--rm``.
    """
    parts: list[str] = ["docker", "run"]
    if spec.long_running:
        parts += ["-d", _restart_flag(spec.restart_policy)]
    else:
        parts += ["-d", "--rm=false"]
        # Training: detach (-d) so we can poll for completion via inspect,
        # but don't auto-remove; we want exit code retrievable.
    parts += ["--name", shlex.quote(name)]
    parts += _resource_flags(spec)
    parts += _env_flags(spec.env)
    parts += _port_flags(spec)
    parts += _volume_flags(spec)
    parts += _label_flags(spec, name)
    parts.append(shlex.quote(spec.image))
    if spec.command:
        parts += [shlex.quote(c) for c in spec.command]
    if spec.args:
        parts += [shlex.quote(a) for a in spec.args]
    return " ".join(parts)


def build_inspect_command(container: str) -> str:
    """Return a JSON-emitting inspect command. Caller parses ``stdout``."""
    return f"docker inspect {shlex.quote(container)}"


def build_logs_command(container: str, *, tail: int, follow: bool) -> str:
    tail_arg = "all" if tail < 0 else str(int(tail))
    flags = "-f " if follow else ""
    return f"docker logs {flags}--tail={shlex.quote(tail_arg)} {shlex.quote(container)}"


def build_rm_command(container: str) -> str:
    # Force-rm: stops the container first if running. Idempotent: docker rm
    # of a missing container returns non-zero, but caller checks for that.
    return f"docker rm -f {shlex.quote(container)}"


def build_list_command(namespace: str | None = None) -> str:
    """List all gpuctl-managed containers; optionally filter by namespace."""
    filters = [f"label={MANAGED_BY_LABEL}={MANAGED_BY_VALUE}"]
    if namespace:
        filters.append(f"label={Labels.NAMESPACE}={namespace}")
    parts = ["docker", "ps", "-a", "--format", "{{json .}}"]
    for f in filters:
        parts += ["--filter", shlex.quote(f)]
    return " ".join(parts)


def build_probe_command() -> str:
    """One-line probe to verify a node has docker + nvidia runtime.

    Emits a single line: ``docker_version|nvidia_runtime_present|gpu_count``.
    """
    return (
        'printf "%s|%s|%s\\n" '
        '"$(docker version --format \'{{.Server.Version}}\' 2>/dev/null)" '
        '"$(docker info --format \'{{json .Runtimes}}\' 2>/dev/null '
        '| grep -q nvidia && echo yes || echo no)" '
        '"$(nvidia-smi -L 2>/dev/null | wc -l)"'
    )


# ----- flag builders -----


def _restart_flag(policy: str) -> str:
    # Map gpuctl restart semantics to docker. ``Always`` → unless-stopped is
    # the kamal convention (don't restart if user manually stops).
    if policy == "Always":
        return "--restart=unless-stopped"
    if policy == "OnFailure":
        return "--restart=on-failure"
    return "--restart=no"


def _resource_flags(spec: JobSpec) -> list[str]:
    flags: list[str] = []
    if spec.cpu_millicores > 0:
        flags += [f"--cpus={spec.cpu_millicores / 1000:g}"]
    if spec.memory_bytes > 0:
        flags += [f"--memory={spec.memory_bytes}"]
    if spec.gpu_count > 0:
        # NVIDIA Container Toolkit form. ``count=N`` allocates any N visible
        # GPUs; gpu_type filtering happens at scheduler level (node pinning),
        # not via --gpus.
        flags += [f"--gpus", f"count={spec.gpu_count}"]
    return flags


def _env_flags(env: Sequence[tuple[str, str]]) -> list[str]:
    flags: list[str] = []
    for k, v in env:
        flags += ["-e", shlex.quote(f"{k}={v}")]
    return flags


def _port_flags(spec: JobSpec) -> list[str]:
    if spec.port is None or not spec.long_running:
        return []
    p = int(spec.port)
    return ["-p", f"{p}:{p}"]


def _volume_flags(spec: JobSpec) -> list[str]:
    flags: list[str] = []
    for m in spec.workdirs:
        bind = f"{m.host_path}:{m.container_path}"
        if m.read_only:
            bind += ":ro"
        flags += ["-v", shlex.quote(bind)]
    return flags


def _label_flags(spec: JobSpec, name: str) -> list[str]:
    flags: list[str] = []
    base = {
        MANAGED_BY_LABEL: MANAGED_BY_VALUE,
        Labels.JOB_TYPE: spec.kind.value,
        Labels.NAMESPACE: spec.namespace,
        Labels.PRIORITY: spec.priority.value,
        "runwhere.ai/name": spec.name,
    }
    base.update(dict(spec.labels))
    for k, v in base.items():
        flags += ["--label", shlex.quote(f"{k}={v}")]
    return flags


# ----- inspect parsing -----


def parse_inspect_state(stdout: str) -> dict:
    """Parse ``docker inspect`` JSON; return ``{}`` on any failure.

    Callers should treat ``{}`` as 'container gone'. Failures here include:
    docker not installed, container removed between list and inspect,
    truncated stdout.
    """
    import json

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    if not data:
        return {}
    entry = data[0] if isinstance(data, list) else data
    state = entry.get("State") or {}
    return {
        "status": state.get("Status"),  # created/running/paused/restarting/exited/dead
        "running": bool(state.get("Running")),
        "exit_code": state.get("ExitCode"),
        "started_at": state.get("StartedAt"),
        "finished_at": state.get("FinishedAt"),
        "error": state.get("Error"),
        "id": entry.get("Id"),
    }
