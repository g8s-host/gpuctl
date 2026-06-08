"""Tests for gpuctl init command"""
import pytest
from unittest.mock import patch, MagicMock
from kubernetes.client.rest import ApiException


class TestInitCommand:
    """Test gpuctl init command"""

    @patch("gpuctl.cli.init.KubernetesClient")
    def test_init_writes_configmap(self, mock_k8s_class):
        """Given valid args, init delegates to create_or_patch_config_map with correct data"""
        from gpuctl.cli.init import init_storage

        mock_client = MagicMock()
        mock_k8s_class.return_value = mock_client
        mock_client.create_or_patch_config_map.return_value = "created"

        result = init_storage("192.168.1.100", "/exports")

        mock_client.create_or_patch_config_map.assert_called_once_with(
            name="gpuctl-config",
            namespace="kube-system",
            data={"nfs.server": "192.168.1.100", "nfs.path": "/exports"},
        )
        assert result["status"] == "created"

    @patch("gpuctl.cli.init.KubernetesClient")
    def test_init_updates_existing_configmap(self, mock_k8s_class):
        """Given existing config, init returns 'updated' status"""
        from gpuctl.cli.init import init_storage

        mock_client = MagicMock()
        mock_k8s_class.return_value = mock_client
        mock_client.create_or_patch_config_map.return_value = "updated"

        result = init_storage("192.168.1.100", "/exports")

        assert result["status"] == "updated"
        assert result["nfs_server"] == "192.168.1.100"

    def test_init_raises_on_missing_server(self):
        """Missing --nfs-server raises ValueError"""
        from gpuctl.cli.init import init_storage

        with pytest.raises(ValueError, match="nfs-server"):
            init_storage("", "/exports")

    def test_init_raises_on_invalid_path(self):
        """Path not starting with / raises ValueError"""
        from gpuctl.cli.init import init_storage

        with pytest.raises(ValueError, match="nfs-path"):
            init_storage("192.168.1.100", "exports")
