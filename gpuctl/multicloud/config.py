"""集群配置管理"""

import os
import tempfile
from pathlib import Path
from typing import Optional

import yaml

from .models import ClusterConfig, ClusterRegistry

CONFIG_PATH = Path.home() / ".gpuctl" / "clusters.yaml"


class ConfigError(Exception):
    """配置错误基类"""
    pass


class ConfigNotFoundError(ConfigError):
    """配置文件不存在"""
    pass


class ConfigParseError(ConfigError):
    """YAML 解析错误"""
    def __init__(self, message: str, line: Optional[int] = None):
        self.line = line
        super().__init__(f"Parse error at line {line}: {message}" if line else message)


class ClusterExistsError(ConfigError):
    """集群已存在"""
    pass


class ClusterNotFoundError(ConfigError):
    """集群不存在"""
    pass


def load_config() -> ClusterRegistry:
    """从文件加载配置
    
    Returns:
        ClusterRegistry: 配置对象
        
    Raises:
        ConfigNotFoundError: 配置文件不存在
        ConfigParseError: YAML 格式错误
    """
    if not CONFIG_PATH.exists():
        return ClusterRegistry()
    
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return ClusterRegistry(**data)
    except yaml.YAMLError as e:
        raise ConfigParseError(str(e))
    except Exception as e:
        raise ConfigError(f"Failed to load config: {e}")


def save_config(registry: ClusterRegistry) -> None:
    """保存配置到文件（原子写入）
    
    Args:
        registry: 要保存的配置
        
    Side Effects:
        - 自动创建 ~/.gpuctl/ 目录
        - 原子写入（先写临时文件再重命名）
    """
    # 确保目录存在
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 准备数据
    data = registry.model_dump(mode='json', exclude_none=True)
    
    # 原子写入
    fd, temp_path = tempfile.mkstemp(
        dir=CONFIG_PATH.parent,
        prefix=f".{CONFIG_PATH.name}.tmp."
    )
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
        os.replace(temp_path, CONFIG_PATH)
    except Exception:
        # 失败时清理临时文件
        try:
            os.unlink(temp_path)
        except:
            pass
        raise


def get_cluster(name: str) -> Optional[ClusterConfig]:
    """获取指定集群配置"""
    registry = load_config()
    return registry.get_cluster(name)


def add_cluster(cluster: ClusterConfig) -> None:
    """添加集群配置
    
    Args:
        cluster: 集群配置
        
    Raises:
        ClusterExistsError: 集群已存在
    """
    registry = load_config()
    if registry.cluster_exists(cluster.name):
        raise ClusterExistsError(f"Cluster '{cluster.name}' already exists")
    registry.add_cluster(cluster)
    save_config(registry)


def remove_cluster(name: str) -> bool:
    """删除集群配置
    
    Args:
        name: 集群名称
        
    Returns:
        bool: 是否成功删除
        
    Raises:
        ClusterNotFoundError: 集群不存在
    """
    registry = load_config()
    if not registry.cluster_exists(name):
        raise ClusterNotFoundError(f"Cluster '{name}' not found")
    registry.remove_cluster(name)
    save_config(registry)
    return True


def set_default_cluster(name: str) -> None:
    """设置默认集群
    
    Args:
        name: 集群名称
        
    Raises:
        ClusterNotFoundError: 集群不存在
    """
    registry = load_config()
    if not registry.cluster_exists(name):
        raise ClusterNotFoundError(f"Cluster '{name}' not found")
    registry.set_default(name)
    save_config(registry)


def get_current_kubeconfig(cluster: Optional[str] = None) -> str:
    """获取当前使用的 kubeconfig 路径
    
    优先级：
    1. 参数指定的 cluster
    2. default_cluster
    3. 环境变量 KUBECONFIG
    4. 默认路径 ~/.kube/config
    
    Args:
        cluster: 指定的集群名称
        
    Returns:
        str: kubeconfig 文件路径
        
    Raises:
        ClusterNotFoundError: 指定集群不存在
        ConfigNotFoundError: 没有配置且没有默认 kubeconfig
    """
    if cluster:
        c = get_cluster(cluster)
        if c:
            return c.kubeconfig_path
        raise ClusterNotFoundError(f"Cluster '{cluster}' not found")
    
    registry = load_config()
    if registry.default_cluster:
        return get_current_kubeconfig(registry.default_cluster)
    
    # 回退到环境变量或默认路径
    kubeconfig = os.environ.get('KUBECONFIG')
    if kubeconfig:
        return kubeconfig
    
    default_path = Path.home() / ".kube" / "config"
    if default_path.exists():
        return str(default_path)
    
    raise ConfigNotFoundError(
        "No cluster configured and no default kubeconfig found. "
        "Please run 'gpuctl cluster add' or set KUBECONFIG environment variable."
    )
