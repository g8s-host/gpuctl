"""Tests for shared gpuctl Kubernetes config."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gpuctl.kube_config import (
    clear_kubeconfig,
    get_config_path,
    kubeconfig_kwargs,
    load_gpuctl_config,
    load_k8s_config,
    save_kubeconfig,
)


def test_save_load_and_clear_kubeconfig(tmp_path, monkeypatch):
    monkeypatch.setenv("GPUCTL_CONFIG_HOME", str(tmp_path / "home"))
    kubeconfig = tmp_path / "admin.conf"
    kubeconfig.write_text("apiVersion: v1\n", encoding="utf-8")

    saved = save_kubeconfig(str(kubeconfig), "prod")
    assert saved.kubeconfig == str(kubeconfig)
    assert saved.context == "prod"
    assert get_config_path() == tmp_path / "home" / "config.json"

    loaded = load_gpuctl_config()
    assert loaded.kubeconfig == str(kubeconfig)
    assert loaded.context == "prod"
    assert kubeconfig_kwargs() == {"config_file": str(kubeconfig), "context": "prod"}

    clear_kubeconfig()
    assert load_gpuctl_config().kubeconfig is None


def test_save_rejects_missing_kubeconfig(tmp_path, monkeypatch):
    monkeypatch.setenv("GPUCTL_CONFIG_HOME", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        save_kubeconfig(str(tmp_path / "missing.conf"))


def test_load_k8s_config_uses_incluster_when_service_host_present(monkeypatch):
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    k8s_config = MagicMock()

    assert load_k8s_config(k8s_config) == "incluster"
    k8s_config.load_incluster_config.assert_called_once_with()
    k8s_config.load_kube_config.assert_not_called()


def test_load_k8s_config_uses_saved_kubeconfig_outside_cluster(tmp_path, monkeypatch):
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    monkeypatch.setenv("GPUCTL_CONFIG_HOME", str(tmp_path / "gpuctl"))
    kubeconfig = tmp_path / "admin.conf"
    kubeconfig.write_text("apiVersion: v1\n", encoding="utf-8")
    save_kubeconfig(str(kubeconfig), "prod")
    k8s_config = MagicMock()

    assert load_k8s_config(k8s_config) == "kubeconfig"
    k8s_config.load_kube_config.assert_called_once_with(config_file=str(kubeconfig), context="prod")

