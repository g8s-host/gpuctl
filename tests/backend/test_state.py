"""Unit tests for ``gpuctl.backend.ssh.state.StateStore``."""

from __future__ import annotations

import json

import pytest

from gpuctl.backend.errors import JobAlreadyExistsError, JobNotFoundError
from gpuctl.backend.ssh.state import StateStore


@pytest.fixture
def store(tmp_path) -> StateStore:
    return StateStore(db_path=tmp_path / "s.db")


def _insert(
    store: StateStore,
    name: str = "j1",
    namespace: str = "ns",
    node: str = "gpu-01",
    gpu_count: int = 2,
    status: str = "Pending",
):
    return store.insert_job(
        name=name,
        namespace=namespace,
        kind="training",
        node=node,
        container_name=f"gpuctl-{namespace}-training-{name}",
        spec_json=json.dumps({"gpu_count": gpu_count}),
        labels={"runwhere.ai/job-type": "training"},
        status=status,
    )


class TestInsertGet:
    def test_roundtrip(self, store):
        row = _insert(store)
        got = store.get_job("j1", "ns")
        assert got.id == row.id
        assert got.name == "j1"
        assert got.status == "Pending"
        assert got.labels == {"runwhere.ai/job-type": "training"}

    def test_duplicate_raises(self, store):
        _insert(store)
        with pytest.raises(JobAlreadyExistsError):
            _insert(store)

    def test_missing_raises_not_found(self, store):
        with pytest.raises(JobNotFoundError):
            store.get_job("absent", "ns")


class TestUpdates:
    def test_set_container_id(self, store):
        row = _insert(store)
        store.set_container_id(row.id, "abc123")
        assert store.get_job("j1", "ns").container_id == "abc123"

    def test_update_status(self, store):
        _insert(store)
        store.update_status("j1", "ns", "Running")
        assert store.get_job("j1", "ns").status == "Running"

    def test_delete_is_idempotent(self, store):
        _insert(store)
        store.delete_job("j1", "ns")
        store.delete_job("j1", "ns")  # second call must not raise
        with pytest.raises(JobNotFoundError):
            store.get_job("j1", "ns")


class TestListing:
    def test_list_by_namespace(self, store):
        _insert(store, name="j1")
        _insert(store, name="j2")
        _insert(store, name="j3", namespace="other")
        rows = store.list_jobs("ns")
        names = {r.name for r in rows}
        assert names == {"j1", "j2"}

    def test_list_filters_labels(self, store):
        store.insert_job(
            name="j1",
            namespace="ns",
            kind="training",
            node="gpu-01",
            container_name="c1",
            spec_json="{}",
            labels={"app": "x"},
            status="Pending",
        )
        store.insert_job(
            name="j2",
            namespace="ns",
            kind="training",
            node="gpu-02",
            container_name="c2",
            spec_json="{}",
            labels={"app": "y"},
            status="Pending",
        )
        rows = store.list_jobs("ns", labels={"app": "x"})
        assert [r.name for r in rows] == ["j1"]


class TestUsedGpus:
    def test_sums_only_active_jobs(self, store):
        _insert(store, name="active", gpu_count=4, status="Running")
        _insert(store, name="done", gpu_count=8, status="Succeeded")
        _insert(store, name="failed", gpu_count=2, status="Failed")
        _insert(store, name="other-node", node="gpu-02", gpu_count=1, status="Running")
        usage = store.used_gpus_per_node()
        assert usage == {"gpu-01": 4, "gpu-02": 1}


class TestNodeRuntime:
    def test_upsert(self, store):
        store.touch_node("gpu-01", gpu_count_real=8, docker_version="25.0.3")
        store.touch_node("gpu-01", gpu_count_real=7, docker_version="25.0.4")
        # No public read API yet; confirm via direct query.
        cur = store._conn.execute(
            "SELECT gpu_count_real, docker_version FROM nodes_runtime WHERE name=?",
            ("gpu-01",),
        ).fetchone()
        assert cur["gpu_count_real"] == 7
        assert cur["docker_version"] == "25.0.4"
