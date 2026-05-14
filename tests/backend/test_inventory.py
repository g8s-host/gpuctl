"""Unit tests for ``gpuctl.backend.ssh.inventory``."""

from __future__ import annotations

import textwrap

import pytest

from gpuctl.backend.errors import BackendNotConfiguredError
from gpuctl.backend.ssh.inventory import load_inventory


def _write(tmp_path, body: str):
    p = tmp_path / "inv.yaml"
    p.write_text(textwrap.dedent(body))
    return p


class TestLoadInventory:
    def test_valid(self, tmp_path):
        p = _write(
            tmp_path,
            """
            version: v1
            nodes:
              - name: a
                host: 10.0.0.1
                user: ubuntu
                gpu_count: 8
                gpu_type: a100-80g
                pool: train
              - name: b
                host: 10.0.0.2
                user: ubuntu
            """,
        )
        inv = load_inventory(p)
        assert {n.name for n in inv.nodes} == {"a", "b"}
        a = inv.by_name("a")
        assert a.gpu_count == 8
        assert a.pool == "train"
        assert a.port == 22  # default

    def test_missing_file(self, tmp_path):
        with pytest.raises(BackendNotConfiguredError, match="not found"):
            load_inventory(tmp_path / "nope.yaml")

    def test_missing_required_field(self, tmp_path):
        p = _write(
            tmp_path,
            """
            nodes:
              - name: a
                host: 10.0.0.1
            """,
        )
        with pytest.raises(BackendNotConfiguredError, match="missing required field: user"):
            load_inventory(p)

    def test_duplicate_name(self, tmp_path):
        p = _write(
            tmp_path,
            """
            nodes:
              - {name: a, host: 1.1.1.1, user: x}
              - {name: a, host: 1.1.1.2, user: x}
            """,
        )
        with pytest.raises(BackendNotConfiguredError, match="duplicate node name"):
            load_inventory(p)

    def test_empty_nodes(self, tmp_path):
        p = _write(tmp_path, "nodes: []\n")
        with pytest.raises(BackendNotConfiguredError, match="no nodes"):
            load_inventory(p)

    def test_in_pool_default(self, tmp_path):
        p = _write(
            tmp_path,
            """
            nodes:
              - {name: a, host: h, user: u, pool: default}
              - {name: b, host: h, user: u, pool: training}
            """,
        )
        inv = load_inventory(p)
        assert [n.name for n in inv.in_pool(None)] == ["a"]
        assert [n.name for n in inv.in_pool("training")] == ["b"]
