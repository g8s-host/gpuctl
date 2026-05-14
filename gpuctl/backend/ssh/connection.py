"""SSH execution via paramiko, with a small abstraction so unit tests can
inject a fake transport.

The pool is intentionally tiny: one client per (user, host, port). gpuctl is
a CLI tool — we don't need an industrial connection pool.

paramiko is an optional dependency (extras = ssh). Import is deferred to the
first time ``ParamikoExecutor`` is instantiated; users who only use the k8s
backend won't import it.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Iterator, Protocol

from gpuctl.backend.errors import BackendError
from gpuctl.backend.ssh.inventory import Node


@dataclass(frozen=True)
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str


class SshExecError(BackendError):
    """Raised on transport-level SSH failure (connection refused, auth, etc.).

    Distinct from a non-zero exit code, which is reported via ExecResult and
    callers decide how to interpret.
    """


class Executor(Protocol):
    """Abstract SSH executor. Tests substitute a fake."""

    def exec(self, node: Node, command: str, *, timeout: int) -> ExecResult: ...

    def stream(
        self, node: Node, command: str, *, timeout: int
    ) -> Iterator[str]: ...

    def close(self) -> None: ...


class ParamikoExecutor:
    """Real SSH executor backed by paramiko.

    Connection caching: per-(user, host, port) ``SSHClient``. We re-open
    transparently on failure (typical pattern for long-lived CLI sessions).
    """

    def __init__(self) -> None:
        try:
            import paramiko  # noqa: F401
        except ImportError as exc:
            raise BackendError(
                "paramiko is not installed. Install gpuctl with the 'ssh' "
                "extra: pip install 'gpuctl[ssh]'"
            ) from exc
        self._lock = threading.RLock()
        self._clients: dict[tuple[str, str, int], object] = {}

    def _connect(self, node: Node):
        import paramiko

        client = paramiko.SSHClient()
        # We do not auto-add unknown hosts: that's a security footgun. Users
        # should pre-populate known_hosts, or set GPUCTL_SSH_INSECURE=1 for
        # lab use.
        client.load_system_host_keys()
        if os.environ.get("GPUCTL_SSH_INSECURE") == "1":
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        else:
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            client.connect(
                hostname=node.host,
                port=node.port,
                username=node.user,
                key_filename=node.key_path,
                look_for_keys=node.key_path is None,
                allow_agent=True,
                timeout=int(os.environ.get("GPUCTL_SSH_CONNECT_TIMEOUT", "10")),
                auth_timeout=10,
                banner_timeout=10,
            )
        except Exception as exc:
            raise SshExecError(
                f"SSH connect to {node.address} failed: {exc}"
            ) from exc
        return client

    def _get(self, node: Node):
        key = (node.user, node.host, node.port)
        with self._lock:
            existing = self._clients.get(key)
            if existing is not None:
                # paramiko's transport may have died silently; probe.
                transport = existing.get_transport()  # type: ignore[attr-defined]
                if transport is not None and transport.is_active():
                    return existing
                existing.close()  # type: ignore[attr-defined]
            client = self._connect(node)
            self._clients[key] = client
            return client

    def exec(self, node: Node, command: str, *, timeout: int) -> ExecResult:
        client = self._get(node)
        try:
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)  # type: ignore[attr-defined]
            stdin.close()
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            code = stdout.channel.recv_exit_status()
            return ExecResult(exit_code=code, stdout=out, stderr=err)
        except Exception as exc:
            raise SshExecError(
                f"SSH exec on {node.address} failed: {exc}\ncommand: {command}"
            ) from exc

    def stream(
        self, node: Node, command: str, *, timeout: int
    ) -> Iterator[str]:
        client = self._get(node)
        try:
            _, stdout, _ = client.exec_command(command, timeout=timeout)  # type: ignore[attr-defined]
        except Exception as exc:
            raise SshExecError(
                f"SSH stream on {node.address} failed: {exc}\ncommand: {command}"
            ) from exc
        buf = b""
        for chunk in iter(lambda: stdout.channel.recv(4096), b""):
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                yield line.decode("utf-8", errors="replace")
        if buf:
            yield buf.decode("utf-8", errors="replace")

    def close(self) -> None:
        with self._lock:
            for c in self._clients.values():
                try:
                    c.close()  # type: ignore[attr-defined]
                except Exception:
                    pass
            self._clients.clear()
