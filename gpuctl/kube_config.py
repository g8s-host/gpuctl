"""Shared Kubernetes config resolution for gpuctl and runwhere-ai.

The CLI is the source of truth for user-level Kubernetes config. Operators can
persist a kubeconfig path/context with ``gpuctl config set-kubeconfig``; both
gpuctl commands and runwhere-ai read the same file.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


CONFIG_DIR_ENV = "GPUCTL_CONFIG_HOME"
CONFIG_FILE_ENV = "GPUCTL_CONFIG"
DEFAULT_CONFIG_DIR = ".gpuctl"
DEFAULT_CONFIG_FILE = "config.json"


@dataclass(frozen=True)
class GpuCtlConfig:
    kubeconfig: Optional[str] = None
    context: Optional[str] = None


def get_config_path() -> Path:
    explicit = os.getenv(CONFIG_FILE_ENV)
    if explicit:
        return Path(explicit).expanduser()
    home = os.getenv(CONFIG_DIR_ENV)
    config_dir = Path(home).expanduser() if home else Path.home() / DEFAULT_CONFIG_DIR
    return config_dir / DEFAULT_CONFIG_FILE


def load_gpuctl_config() -> GpuCtlConfig:
    path = get_config_path()
    if not path.exists():
        return GpuCtlConfig()
    try:
        data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return GpuCtlConfig()

    kube = data.get("kubeconfig")
    context = data.get("context")
    return GpuCtlConfig(
        kubeconfig=str(kube).strip() or None if kube is not None else None,
        context=str(context).strip() or None if context is not None else None,
    )


def save_kubeconfig(kubeconfig: str, context: Optional[str] = None) -> GpuCtlConfig:
    kube_path = Path(kubeconfig).expanduser()
    if not kube_path.exists():
        raise FileNotFoundError(f"kubeconfig file does not exist: {kube_path}")
    if not kube_path.is_file():
        raise ValueError(f"kubeconfig path is not a file: {kube_path}")

    settings = GpuCtlConfig(
        kubeconfig=str(kube_path),
        context=(context.strip() if context else None),
    )
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"kubeconfig": settings.kubeconfig, "context": settings.context},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return settings


def clear_kubeconfig() -> None:
    path = get_config_path()
    if path.exists():
        path.unlink()


def kubeconfig_kwargs() -> Dict[str, str]:
    settings = load_gpuctl_config()
    kwargs: Dict[str, str] = {}
    if settings.kubeconfig:
        kwargs["config_file"] = settings.kubeconfig
    if settings.context:
        kwargs["context"] = settings.context
    return kwargs


def load_k8s_config(k8s_config_module) -> str:
    """Load Kubernetes config using gpuctl's shared resolution rule."""
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        k8s_config_module.load_incluster_config()
        return "incluster"
    k8s_config_module.load_kube_config(**kubeconfig_kwargs())
    return "kubeconfig"


async def load_k8s_config_async(k8s_config_module) -> str:
    """Async equivalent for kubernetes_asyncio consumers."""
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        k8s_config_module.load_incluster_config()
        return "incluster"
    await k8s_config_module.load_kube_config(**kubeconfig_kwargs())
    return "kubeconfig"
