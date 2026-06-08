"""Tests for gpuctl config commands."""
from __future__ import annotations

from argparse import Namespace

from gpuctl.cli.config import config_command
from gpuctl.kube_config import load_gpuctl_config


def test_config_set_kubeconfig(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GPUCTL_CONFIG_HOME", str(tmp_path / "gpuctl"))
    kubeconfig = tmp_path / "admin.conf"
    kubeconfig.write_text("apiVersion: v1\n", encoding="utf-8")

    rc = config_command(Namespace(config_action="set-kubeconfig", file=str(kubeconfig), context="prod"))

    assert rc == 0
    settings = load_gpuctl_config()
    assert settings.kubeconfig == str(kubeconfig)
    assert settings.context == "prod"
    assert "Kubernetes config saved" in capsys.readouterr().out


def test_config_view_defaults(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GPUCTL_CONFIG_HOME", str(tmp_path / "gpuctl"))

    rc = config_command(Namespace(config_action="view"))

    assert rc == 0
    out = capsys.readouterr().out
    assert "standard KUBECONFIG" in out
    assert "current-context" in out


def test_config_unset_kubeconfig(tmp_path, monkeypatch):
    monkeypatch.setenv("GPUCTL_CONFIG_HOME", str(tmp_path / "gpuctl"))
    kubeconfig = tmp_path / "admin.conf"
    kubeconfig.write_text("apiVersion: v1\n", encoding="utf-8")
    config_command(Namespace(config_action="set-kubeconfig", file=str(kubeconfig), context=None))

    rc = config_command(Namespace(config_action="unset-kubeconfig"))

    assert rc == 0
    assert load_gpuctl_config().kubeconfig is None

