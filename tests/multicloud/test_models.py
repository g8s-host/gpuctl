"""测试多云集群管理模型"""

import pytest
from datetime import datetime
from gpuctl.multicloud.models import ClusterConfig, ClusterRegistry, ClusterStatus


class TestClusterConfig:
    """测试 ClusterConfig 模型"""
    
    def test_valid_cluster_config(self):
        """测试有效的集群配置"""
        config = ClusterConfig(
            name="prod",
            provider="ack",
            region="cn-hangzhou",
            kubeconfig_path="/home/user/.kube/config"
        )
        assert config.name == "prod"
        assert config.provider == "ack"
        assert config.region == "cn-hangzhou"
        assert config.kubeconfig_path == "/home/user/.kube/config"
    
    def test_invalid_provider(self):
        """测试无效的云厂商"""
        with pytest.raises(ValueError):
            ClusterConfig(
                name="prod",
                provider="invalid",
                kubeconfig_path="/home/user/.kube/config"
            )
    
    def test_invalid_name(self):
        """测试无效的集群名称"""
        with pytest.raises(ValueError):
            ClusterConfig(
                name="",  # 空名称
                provider="ack",
                kubeconfig_path="/home/user/.kube/config"
            )
    
    def test_relative_path_rejected(self):
        """测试相对路径被拒绝"""
        with pytest.raises(ValueError):
            ClusterConfig(
                name="prod",
                provider="ack",
                kubeconfig_path="./config"  # 相对路径
            )


class TestClusterRegistry:
    """测试 ClusterRegistry 模型"""
    
    def test_add_cluster(self):
        """测试添加集群"""
        registry = ClusterRegistry()
        cluster = ClusterConfig(
            name="prod",
            provider="ack",
            kubeconfig_path="/home/user/.kube/config"
        )
        registry.add_cluster(cluster)
        assert len(registry.clusters) == 1
        assert registry.cluster_exists("prod")
    
    def test_add_duplicate_cluster(self):
        """测试添加重复集群"""
        registry = ClusterRegistry()
        cluster = ClusterConfig(
            name="prod",
            provider="ack",
            kubeconfig_path="/home/user/.kube/config"
        )
        registry.add_cluster(cluster)
        with pytest.raises(ValueError):
            registry.add_cluster(cluster)
    
    def test_remove_cluster(self):
        """测试删除集群"""
        registry = ClusterRegistry()
        cluster = ClusterConfig(
            name="prod",
            provider="ack",
            kubeconfig_path="/home/user/.kube/config"
        )
        registry.add_cluster(cluster)
        assert registry.remove_cluster("prod")
        assert not registry.cluster_exists("prod")
    
    def test_remove_nonexistent_cluster(self):
        """测试删除不存在的集群"""
        registry = ClusterRegistry()
        assert not registry.remove_cluster("nonexistent")
    
    def test_set_default(self):
        """测试设置默认集群"""
        registry = ClusterRegistry()
        cluster = ClusterConfig(
            name="prod",
            provider="ack",
            kubeconfig_path="/home/user/.kube/config"
        )
        registry.add_cluster(cluster)
        registry.set_default("prod")
        assert registry.default_cluster == "prod"
    
    def test_set_default_nonexistent(self):
        """测试设置不存在的集群为默认"""
        registry = ClusterRegistry()
        with pytest.raises(ValueError):
            registry.set_default("nonexistent")
    
    def test_remove_default_cluster(self):
        """测试删除默认集群会清空默认设置"""
        registry = ClusterRegistry()
        cluster = ClusterConfig(
            name="prod",
            provider="ack",
            kubeconfig_path="/home/user/.kube/config"
        )
        registry.add_cluster(cluster)
        registry.set_default("prod")
        registry.remove_cluster("prod")
        assert registry.default_cluster is None


class TestClusterStatus:
    """测试 ClusterStatus 枚举"""
    
    def test_status_values(self):
        """测试状态值"""
        assert ClusterStatus.HEALTHY.value == "healthy"
        assert ClusterStatus.UNHEALTHY.value == "unhealthy"
        assert ClusterStatus.UNKNOWN.value == "unknown"
