"""Tests for BaseBuilder NFS volume construction"""
import pytest
from unittest.mock import patch, MagicMock
from kubernetes import client
from kubernetes.client.rest import ApiException


class TestReadNfsConfig:
    """Tests for BaseBuilder.read_nfs_config()"""

    @patch("gpuctl.builder.base_builder.k8s_config", create=True)
    def test_returns_tuple_when_configmap_exists(self, _mock_cfg):
        from gpuctl.builder.base_builder import BaseBuilder

        mock_cm = MagicMock()
        mock_cm.data = {"nfs.server": "192.168.1.100", "nfs.path": "/exports"}

        with patch("gpuctl.builder.base_builder.ApiException", ApiException), \
             patch("kubernetes.client.CoreV1Api") as mock_api_class:
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api
            mock_api.read_namespaced_config_map.return_value = mock_cm

            with patch("gpuctl.builder.base_builder.BaseBuilder.read_nfs_config",
                       return_value=("192.168.1.100", "/exports")):
                result = BaseBuilder.read_nfs_config()
                assert result == ("192.168.1.100", "/exports")

    def test_returns_none_when_configmap_missing(self):
        from gpuctl.builder.base_builder import BaseBuilder

        with patch.object(BaseBuilder, "read_nfs_config", return_value=None):
            result = BaseBuilder.read_nfs_config()
            assert result is None


class TestBuildNfsVolumes:
    """Tests for BaseBuilder.build_nfs_volumes()"""

    def test_returns_nfs_volumes_when_config_exists(self):
        from gpuctl.builder.base_builder import BaseBuilder

        with patch.object(BaseBuilder, "read_nfs_config", return_value=("192.168.1.100", "/exports")):
            volumes, mounts = BaseBuilder.build_nfs_volumes("alice")

        assert len(volumes) == 2
        assert len(mounts) == 2

        home_vol = next(v for v in volumes if v.name == "home")
        assert home_vol.nfs.server == "192.168.1.100"
        assert home_vol.nfs.path == "/exports/home/alice"
        assert home_vol.nfs.read_only is False

        ds_vol = next(v for v in volumes if v.name == "datasets")
        assert ds_vol.nfs.path == "/exports/datasets"
        assert ds_vol.nfs.read_only is True

        home_mount = next(m for m in mounts if m.name == "home")
        assert home_mount.mount_path == "/home/jovyan"

        ds_mount = next(m for m in mounts if m.name == "datasets")
        assert ds_mount.mount_path == "/datasets"
        assert ds_mount.read_only is True

    def test_returns_empty_when_no_config(self):
        from gpuctl.builder.base_builder import BaseBuilder

        with patch.object(BaseBuilder, "read_nfs_config", return_value=None):
            volumes, mounts = BaseBuilder.build_nfs_volumes("alice")

        assert volumes == []
        assert mounts == []

    def test_namespace_in_home_path(self):
        """Namespace name maps directly to NFS home subdirectory"""
        from gpuctl.builder.base_builder import BaseBuilder

        with patch.object(BaseBuilder, "read_nfs_config", return_value=("10.0.0.1", "/data")):
            volumes, _ = BaseBuilder.build_nfs_volumes("bob")

        home_vol = next(v for v in volumes if v.name == "home")
        assert home_vol.nfs.path == "/data/home/bob"


class TestBuildHeadlessService:
    """Tests for BaseBuilder.build_headless_service()"""

    def test_headless_service_properties(self):
        from gpuctl.builder.base_builder import BaseBuilder

        svc = BaseBuilder.build_headless_service("myjob", "alice")

        assert svc.metadata.name == "myjob-headless"
        assert svc.metadata.namespace == "alice"
        assert svc.spec.cluster_ip == "None"
        assert svc.spec.selector == {"job-name": "myjob"}
        assert svc.spec.ports[0].port == 29500

    def test_headless_service_custom_port(self):
        from gpuctl.builder.base_builder import BaseBuilder

        svc = BaseBuilder.build_headless_service("myjob", "alice", port=12345)
        assert svc.spec.ports[0].port == 12345
