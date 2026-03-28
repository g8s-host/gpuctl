"""gpuctl init command — register NFS storage configuration"""
from typing import Dict, Any
from gpuctl.client.base_client import KubernetesClient

_CONFIGMAP_NAME = "gpuctl-config"
_CONFIGMAP_NS = "kube-system"


def init_storage(nfs_server: str, nfs_path: str) -> Dict[str, Any]:
    """Write NFS connection config to cluster ConfigMap.

    Args:
        nfs_server: NFS server IP or hostname (required, non-empty)
        nfs_path:   NFS export root path (required, must start with '/')

    Returns:
        Dict with 'status' key ('created' or 'updated')

    Raises:
        ValueError: if arguments are invalid
    """
    if not nfs_server:
        raise ValueError("--nfs-server is required and must be non-empty")
    if not nfs_path or not nfs_path.startswith("/"):
        raise ValueError("--nfs-path must be non-empty and start with '/'")

    k8s = KubernetesClient()
    status = k8s.create_or_patch_config_map(
        name=_CONFIGMAP_NAME,
        namespace=_CONFIGMAP_NS,
        data={
            "nfs.server": nfs_server,
            "nfs.path": nfs_path,
        },
    )

    return {
        "nfs_server": nfs_server,
        "nfs_path": nfs_path,
        "configmap": f"{_CONFIGMAP_NS}/{_CONFIGMAP_NAME}",
        "status": status,
    }


def init_command(args) -> int:
    """CLI entry-point for `gpuctl init`"""
    try:
        result = init_storage(args.nfs_server, args.nfs_path)
        print(f"NFS storage initialized:")
        print(f"  Server: {result['nfs_server']}")
        print(f"  Path:   {result['nfs_path']}")
        print(f"  Config stored in: {result['configmap']}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        print("Usage: gpuctl init --nfs-server <IP> --nfs-path <PATH>")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
