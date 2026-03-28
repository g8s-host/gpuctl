"""Tests for QuotaClient NFS home directory creation (US3)"""
import pytest
from unittest.mock import patch, MagicMock, call
from kubernetes.client.rest import ApiException


@patch("gpuctl.client.quota_client.QuotaClient.__init__", return_value=None)
class TestCreateNfsHome:

    def _make_client(self):
        from gpuctl.client.quota_client import QuotaClient
        c = QuotaClient.__new__(QuotaClient)
        c.core_v1 = MagicMock()
        c.batch_v1 = MagicMock()
        return c

    def test_creates_mkdir_job_when_nfs_configured(self, _init):
        from gpuctl.builder.base_builder import BaseBuilder
        c = self._make_client()

        with patch.object(BaseBuilder, "read_nfs_config", return_value=("192.168.1.100", "/exports")):
            c._create_nfs_home("alice")

        c.batch_v1.create_namespaced_job.assert_called_once()
        call_kwargs = c.batch_v1.create_namespaced_job.call_args
        assert call_kwargs[1]["namespace"] == "kube-system"
        job = call_kwargs[1]["body"]
        assert job.metadata.name == "nfs-init-alice"
        container = job.spec.template.spec.containers[0]
        assert "/nfs/home/alice" in container.command

    def test_skips_when_nfs_not_configured(self, _init):
        from gpuctl.builder.base_builder import BaseBuilder
        c = self._make_client()

        with patch.object(BaseBuilder, "read_nfs_config", return_value=None):
            c._create_nfs_home("alice")

        c.batch_v1.create_namespaced_job.assert_not_called()

    def test_idempotent_when_job_already_exists(self, _init):
        """409 Conflict (job already exists) should be silently ignored"""
        from gpuctl.builder.base_builder import BaseBuilder
        c = self._make_client()
        c.batch_v1.create_namespaced_job.side_effect = ApiException(status=409)

        with patch.object(BaseBuilder, "read_nfs_config", return_value=("10.0.0.1", "/data")):
            c._create_nfs_home("bob")  # should not raise

        c.batch_v1.create_namespaced_job.assert_called_once()


@patch("gpuctl.client.quota_client.QuotaClient.__init__", return_value=None)
class TestEnsureNamespaceExistsTriggerNfs:

    def _make_client(self):
        from gpuctl.client.quota_client import QuotaClient
        c = QuotaClient.__new__(QuotaClient)
        c.core_v1 = MagicMock()
        c.batch_v1 = MagicMock()
        return c

    def test_triggers_nfs_mkdir_on_new_namespace(self, _init):
        from gpuctl.builder.base_builder import BaseBuilder
        c = self._make_client()
        c.core_v1.read_namespace.side_effect = ApiException(status=404)
        c.core_v1.create_namespace.return_value = MagicMock()

        with patch.object(BaseBuilder, "read_nfs_config", return_value=("192.168.1.100", "/exports")):
            c._ensure_namespace_exists("alice")

        c.batch_v1.create_namespaced_job.assert_called_once()

    def test_no_nfs_job_for_existing_namespace(self, _init):
        from gpuctl.builder.base_builder import BaseBuilder
        c = self._make_client()
        c.core_v1.read_namespace.return_value = MagicMock()  # namespace exists

        with patch.object(BaseBuilder, "read_nfs_config", return_value=("192.168.1.100", "/exports")):
            c._ensure_namespace_exists("alice")

        c.batch_v1.create_namespaced_job.assert_not_called()

    def test_quota_creation_succeeds_when_nfs_not_configured(self, _init):
        """If NFS not configured, namespace creation still works fine"""
        from gpuctl.builder.base_builder import BaseBuilder
        c = self._make_client()
        c.core_v1.read_namespace.side_effect = ApiException(status=404)
        c.core_v1.create_namespace.return_value = MagicMock()

        with patch.object(BaseBuilder, "read_nfs_config", return_value=None):
            c._ensure_namespace_exists("carol")  # should not raise

        c.core_v1.create_namespace.assert_called_once()
        c.batch_v1.create_namespaced_job.assert_not_called()
