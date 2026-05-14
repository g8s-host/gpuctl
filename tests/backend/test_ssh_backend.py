"""End-to-end tests for ``SshBackend`` using a fake executor.

These exercise the orchestration logic — scheduling, state persistence,
state-store ↔ docker inspect reconciliation — without any real SSH.
"""

from __future__ import annotations

import pytest

from gpuctl.backend.base import JobState
from gpuctl.backend.errors import (
    JobAlreadyExistsError,
    UnsupportedFeatureError,
)
from gpuctl.backend.ssh.backend import SshBackend
from gpuctl.backend.ssh.connection import ExecResult


@pytest.fixture
def backend(inventory, state_store, executor):
    return SshBackend(inventory=inventory, state=state_store, executor=executor)


_RUNNING_INSPECT = (
    '[{"Id":"sha256:abc","State":{"Status":"running","Running":true,'
    '"ExitCode":0,"StartedAt":"2026-05-14T01:00:00Z",'
    '"FinishedAt":"0001-01-01T00:00:00Z","Error":""}}]'
)
_EXITED_OK_INSPECT = (
    '[{"Id":"sha256:abc","State":{"Status":"exited","Running":false,'
    '"ExitCode":0,"StartedAt":"2026-05-14T01:00:00Z",'
    '"FinishedAt":"2026-05-14T02:00:00Z","Error":""}}]'
)


class TestCreateJob:
    def test_happy_path_picks_node_and_records_state(
        self, backend, executor, training_spec
    ):
        executor.set_response(
            "gpu-01",
            "docker run",
            ExecResult(exit_code=0, stdout="sha256:abc\n", stderr=""),
        )
        handle = backend.create_job(training_spec)
        assert handle.backend == "ssh"
        assert handle.backend_ref == "sha256:abc"
        assert handle.namespace == "acme"
        # State row exists.
        row = backend._state.get_job(training_spec.name, training_spec.namespace)
        assert row.node == "gpu-01"
        assert row.container_id == "sha256:abc"
        assert row.status == JobState.RUNNING.value

    def test_docker_run_failure_rolls_back_state(
        self, backend, executor, training_spec
    ):
        executor.set_response(
            "gpu-01",
            "docker run",
            ExecResult(exit_code=125, stdout="", stderr="no such image"),
        )
        from gpuctl.backend.errors import BackendError

        with pytest.raises(BackendError, match="docker run failed"):
            backend.create_job(training_spec)
        # No ghost row left behind.
        from gpuctl.backend.errors import JobNotFoundError

        with pytest.raises(JobNotFoundError):
            backend._state.get_job(training_spec.name, training_spec.namespace)

    def test_duplicate_create_raises(self, backend, executor, training_spec):
        executor.set_response(
            "gpu-01",
            "docker run",
            ExecResult(exit_code=0, stdout="sha256:abc\n", stderr=""),
        )
        backend.create_job(training_spec)
        with pytest.raises(JobAlreadyExistsError):
            backend.create_job(training_spec)

    def test_replicas_gt_one_rejected(self, backend, training_spec):
        spec = training_spec.__class__(**{**training_spec.__dict__, "replicas": 2})
        with pytest.raises(UnsupportedFeatureError, match="replicas > 1"):
            backend.create_job(spec)


class TestGetJob:
    def test_running_state_propagates(self, backend, executor, training_spec):
        executor.set_response(
            "gpu-01",
            "docker run",
            ExecResult(exit_code=0, stdout="sha256:abc\n", stderr=""),
        )
        backend.create_job(training_spec)
        executor.set_response(
            "gpu-01",
            "docker inspect",
            ExecResult(exit_code=0, stdout=_RUNNING_INSPECT, stderr=""),
        )
        status = backend.get_job(training_spec.name, training_spec.namespace)
        assert status.state == JobState.RUNNING
        assert status.node == "gpu-01"
        assert status.exit_code == 0

    def test_exited_success(self, backend, executor, training_spec):
        executor.set_response(
            "gpu-01",
            "docker run",
            ExecResult(exit_code=0, stdout="sha256:abc\n", stderr=""),
        )
        backend.create_job(training_spec)
        executor.set_response(
            "gpu-01",
            "docker inspect",
            ExecResult(exit_code=0, stdout=_EXITED_OK_INSPECT, stderr=""),
        )
        status = backend.get_job(training_spec.name, training_spec.namespace)
        assert status.state == JobState.SUCCEEDED
        assert status.finished_at == "2026-05-14T02:00:00Z"

    def test_inspect_missing_marks_lost(self, backend, executor, training_spec):
        executor.set_response(
            "gpu-01",
            "docker run",
            ExecResult(exit_code=0, stdout="sha256:abc\n", stderr=""),
        )
        backend.create_job(training_spec)
        executor.set_response(
            "gpu-01",
            "docker inspect",
            ExecResult(exit_code=1, stdout="", stderr="No such object: c"),
        )
        status = backend.get_job(training_spec.name, training_spec.namespace)
        assert status.state == JobState.LOST


class TestDelete:
    def test_delete_removes_state_and_calls_docker_rm(
        self, backend, executor, training_spec
    ):
        executor.set_response(
            "gpu-01",
            "docker run",
            ExecResult(exit_code=0, stdout="sha256:abc\n", stderr=""),
        )
        backend.create_job(training_spec)
        backend.delete_job(training_spec.name, training_spec.namespace)
        # State gone.
        from gpuctl.backend.errors import JobNotFoundError

        with pytest.raises(JobNotFoundError):
            backend._state.get_job(training_spec.name, training_spec.namespace)
        # docker rm -f was called.
        assert any(
            c.command.startswith("docker rm -f") for c in executor.calls
        )

    def test_delete_unknown_is_noop(self, backend):
        backend.delete_job("does-not-exist", "ns")
