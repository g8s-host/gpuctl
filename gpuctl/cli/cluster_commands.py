"""集群管理 CLI 命令"""

import os
import sys
from datetime import datetime
from pathlib import Path

from gpuctl.multicloud.config import (
    ClusterExistsError,
    ClusterNotFoundError,
    add_cluster,
    get_cluster,
    get_current_kubeconfig,
    load_config,
    remove_cluster,
    save_config,
    set_default_cluster,
)
from gpuctl.multicloud.models import ClusterConfig
from gpuctl.multicloud.validator import check_cluster_health, get_cluster_health


def cluster_add_command(args):
    """添加集群命令"""
    # 获取参数
    name = args.name
    provider = args.provider
    kubeconfig = args.kubeconfig
    region = getattr(args, 'region', None)
    
    # 验证 kubeconfig 路径
    kubeconfig = os.path.expanduser(kubeconfig)
    if not os.path.isabs(kubeconfig):
        kubeconfig = os.path.abspath(kubeconfig)
    
    if not os.path.exists(kubeconfig):
        print(f"Error: kubeconfig file not found: {kubeconfig}", file=sys.stderr)
        return 1
    
    # 验证 kubeconfig 有效性
    print(f"Validating kubeconfig for '{name}'...")
    is_valid, message, node_count = check_cluster_health(kubeconfig)
    
    if not is_valid:
        print(f"Error: Failed to connect to cluster: {message}", file=sys.stderr)
        return 1
    
    # 创建集群配置
    cluster = ClusterConfig(
        name=name,
        provider=provider,
        region=region,
        kubeconfig_path=kubeconfig,
        created_at=datetime.utcnow()
    )
    
    # 保存配置
    try:
        add_cluster(cluster)
        print(f"Cluster '{name}' added successfully.")
        print(f"Status: healthy ({node_count} nodes)")
        
        # 如果是第一个集群，自动设为默认
        registry = load_config()
        if len(registry.clusters) == 1:
            set_default_cluster(name)
            print(f"Auto-set '{name}' as default cluster (first cluster)")
        
        return 0
    except ClusterExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: Failed to add cluster: {e}", file=sys.stderr)
        return 1


def cluster_list_command(args):
    """列出集群命令"""
    registry = load_config()
    
    if not registry.clusters:
        print("No clusters configured. Run 'gpuctl cluster add' to add one.")
        return 0
    
    # 准备输出
    clusters_data = []
    for cluster in registry.clusters:
        # 检查健康状态
        health = get_cluster_health(cluster.name, cluster.kubeconfig_path)
        is_default = registry.default_cluster == cluster.name
        
        clusters_data.append({
            'name': cluster.name,
            'provider': cluster.provider,
            'region': cluster.region or '-',
            'status': health.status.value,
            'nodes': health.node_count or '-',
            'default': is_default
        })
    
    # 输出表格
    print(f"{'NAME':<15} {'PROVIDER':<10} {'REGION':<15} {'STATUS':<10} {'NODES':<8} {'DEFAULT'}")
    print("-" * 70)
    for c in clusters_data:
        default_mark = "*" if c['default'] else ""
        print(f"{c['name']:<15} {c['provider']:<10} {c['region']:<15} "
              f"{c['status']:<10} {c['nodes']:<8} {default_mark}")
    
    print(f"\nTotal: {len(clusters_data)} clusters")
    if registry.default_cluster:
        print(f"Default: {registry.default_cluster}")
    else:
        print("Default: (not set)")
    
    return 0


def cluster_use_command(args):
    """切换默认集群命令"""
    name = args.name
    
    try:
        set_default_cluster(name)
        print(f"Default cluster set to '{name}'")
        return 0
    except ClusterNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(f"Run 'gpuctl cluster list' to see available clusters.", file=sys.stderr)
        return 1


def cluster_current_command(args):
    """查看当前默认集群命令"""
    registry = load_config()
    
    if registry.default_cluster:
        cluster = get_cluster(registry.default_cluster)
        if cluster:
            print(f"Default cluster: {cluster.name}")
            print(f"  Provider: {cluster.provider}")
            print(f"  Region: {cluster.region or '-'}")
            print(f"  Kubeconfig: {cluster.kubeconfig_path}")
            
            # 检查健康状态
            health = get_cluster_health(cluster.name, cluster.kubeconfig_path)
            print(f"  Status: {health.status.value}")
            if health.message:
                print(f"  Message: {health.message}")
        else:
            print(f"Default cluster '{registry.default_cluster}' not found in config.")
            print("It may have been removed. Please set a new default.")
    else:
        print("No default cluster set.")
        print("Run 'gpuctl cluster use <name>' to set one.")
    
    return 0


def cluster_remove_command(args):
    """删除集群命令"""
    name = args.name
    force = getattr(args, 'force', False)
    
    # 确认删除
    if not force:
        response = input(f"Are you sure you want to remove cluster '{name}'? [y/N] ")
        if response.lower() not in ['y', 'yes']:
            print("Cancelled.")
            return 0
    
    try:
        remove_cluster(name)
        print(f"Cluster '{name}' removed successfully.")
        
        # 提示默认集群变化
        registry = load_config()
        if registry.default_cluster:
            print(f"Current default: {registry.default_cluster}")
        else:
            print("Note: No default cluster is now set.")
        
        return 0
    except ClusterNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cluster_get_command(args):
    """获取集群详情命令"""
    name = args.name
    
    cluster = get_cluster(name)
    if not cluster:
        print(f"Error: Cluster '{name}' not found", file=sys.stderr)
        return 1
    
    registry = load_config()
    is_default = registry.default_cluster == name
    
    # 检查健康状态
    health = get_cluster_health(name, cluster.kubeconfig_path)
    
    print(f"Name: {cluster.name}")
    print(f"Provider: {cluster.provider}")
    print(f"Region: {cluster.region or '-'}")
    print(f"Default: {'Yes' if is_default else 'No'}")
    print(f"Status: {health.status.value}")
    print(f"Message: {health.message}")
    print(f"Kubeconfig: {cluster.kubeconfig_path}")
    print(f"Created: {cluster.created_at}")
    
    return 0
