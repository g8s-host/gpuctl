"""Unit tests for ``gpuctl.backend.ssh.scheduler``."""

from __future__ import annotations

import pytest

from gpuctl.backend.errors import NoCapacityError
from gpuctl.backend.ssh.scheduler import select_node


def _spec_with(training_spec, **overrides):
    return training_spec.__class__(**{**training_spec.__dict__, **overrides})


class TestSelectNode:
    def test_selects_node_with_most_free_gpus(self, training_spec, inventory):
        decision = select_node(training_spec, inventory, used_gpus={})
        # gpu-01 has 8 GPUs and matches a100-80g; gpu-02 has 4 but wrong type.
        assert decision.node.name == "gpu-01"
        assert decision.free_gpus == 8

    def test_filters_by_gpu_type(self, training_spec, inventory):
        spec = _spec_with(training_spec, gpu_type="a10-24g", gpu_count=1)
        decision = select_node(spec, inventory, used_gpus={})
        assert decision.node.name == "gpu-02"

    def test_filters_by_pool(self, training_spec, inventory):
        spec = _spec_with(training_spec, pool="default", gpu_count=0, gpu_type=None)
        decision = select_node(spec, inventory, used_gpus={})
        assert decision.node.name == "cpu-01"

    def test_no_pool_match_raises(self, training_spec, inventory):
        spec = _spec_with(training_spec, pool="nonexistent")
        with pytest.raises(NoCapacityError, match="no nodes registered in pool"):
            select_node(spec, inventory, used_gpus={})

    def test_insufficient_capacity_lists_state(self, training_spec, inventory):
        spec = _spec_with(training_spec, gpu_count=16)
        with pytest.raises(NoCapacityError) as excinfo:
            select_node(spec, inventory, used_gpus={})
        assert "gpu-01=(8/8 free)" in str(excinfo.value)

    def test_respects_used_gpu_count(self, training_spec, inventory):
        # spec.gpu_type="a100-80g" so only gpu-01 (8 GPU) qualifies. With 6
        # already used, only 2 are free → request for 4 must fail.
        spec = _spec_with(training_spec, gpu_count=4)
        with pytest.raises(NoCapacityError):
            select_node(spec, inventory, used_gpus={"gpu-01": 6})

    def test_gpu_type_none_allows_any_typed_node(self, training_spec, inventory):
        spec = _spec_with(training_spec, gpu_type=None, gpu_count=2)
        decision = select_node(spec, inventory, used_gpus={"gpu-01": 7})
        assert decision.node.name == "gpu-02"  # 4 free beats 1 free
