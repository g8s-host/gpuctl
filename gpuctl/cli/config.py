"""gpuctl config commands."""
from __future__ import annotations

from gpuctl.kube_config import clear_kubeconfig, get_config_path, load_gpuctl_config, save_kubeconfig


def set_kubeconfig_command(args) -> int:
    settings = save_kubeconfig(args.file, args.context)
    print("Kubernetes config saved:")
    print(f"  File:    {settings.kubeconfig}")
    print(f"  Context: {settings.context or '<current-context>'}")
    print(f"  Config:  {get_config_path()}")
    return 0


def view_config_command(args) -> int:
    settings = load_gpuctl_config()
    print("gpuctl config:")
    print(f"  Config:     {get_config_path()}")
    print(f"  Kubeconfig: {settings.kubeconfig or '<standard KUBECONFIG / ~/.kube/config>'}")
    print(f"  Context:    {settings.context or '<current-context>'}")
    return 0


def unset_kubeconfig_command(args) -> int:
    clear_kubeconfig()
    print("Kubernetes config cleared; gpuctl will use standard KUBECONFIG / ~/.kube/config.")
    return 0


def config_command(args) -> int:
    if args.config_action == "set-kubeconfig":
        return set_kubeconfig_command(args)
    if args.config_action == "view":
        return view_config_command(args)
    if args.config_action == "unset-kubeconfig":
        return unset_kubeconfig_command(args)
    print(f"Unknown config action: {args.config_action}")
    return 1

