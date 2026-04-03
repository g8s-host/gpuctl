"""kubeconfig 验证和集群健康检查"""

from typing import Tuple

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from .models import ClusterHealth, ClusterStatus


class KubeconfigError(Exception):
    """kubeconfig 错误"""
    pass


def validate_kubeconfig(path: str) -> bool:
    """验证 kubeconfig 是否有效
    
    Args:
        path: kubeconfig 文件路径
        
    Returns:
        bool: 是否有效
    """
    try:
        # 尝试加载配置
        config.load_kube_config(config_file=path)
        # 尝试连接集群 - 获取 API 版本信息
        client.CoreV1Api().get_api_resources()
        return True
    except Exception:
        return False


def check_cluster_health(path: str) -> Tuple[bool, str, int]:
    """检查集群健康状态
    
    Args:
        path: kubeconfig 文件路径
        
    Returns:
        Tuple[bool, str, int]: (是否健康, 消息, 节点数)
    """
    try:
        # 加载配置
        config.load_kube_config(config_file=path)
        
        # 获取节点信息
        v1 = client.CoreV1Api()
        nodes = v1.list_node()
        node_count = len(nodes.items)
        
        # 检查是否有可调度节点
        ready_nodes = 0
        for node in nodes.items:
            for condition in node.status.conditions:
                if condition.type == "Ready" and condition.status == "True":
                    ready_nodes += 1
                    break
        
        if ready_nodes == 0:
            return False, f"No ready nodes found (total: {node_count})", node_count
        
        return True, f"Connected, {ready_nodes}/{node_count} nodes ready", node_count
        
    except ApiException as e:
        if e.status == 401:
            return False, "Authentication failed: invalid credentials", 0
        elif e.status == 403:
            return False, "Permission denied: insufficient privileges", 0
        else:
            return False, f"API error: {e.reason}", 0
    except FileNotFoundError:
        return False, f"kubeconfig file not found: {path}", 0
    except Exception as e:
        return False, f"Connection failed: {str(e)}", 0


def get_cluster_health(name: str, kubeconfig_path: str) -> ClusterHealth:
    """获取集群健康状态（完整信息）
    
    Args:
        name: 集群名称
        kubeconfig_path: kubeconfig 文件路径
        
    Returns:
        ClusterHealth: 健康状态对象
    """
    from datetime import datetime
    
    is_healthy, message, node_count = check_cluster_health(kubeconfig_path)
    
    return ClusterHealth(
        name=name,
        status=ClusterStatus.HEALTHY if is_healthy else ClusterStatus.UNHEALTHY,
        message=message,
        checked_at=datetime.utcnow(),
        node_count=node_count if node_count > 0 else None
    )
