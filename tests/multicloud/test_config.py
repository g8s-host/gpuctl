"""测试配置管理"""

import os
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from gpuctl.multicloud import config
from gpuctl.multicloud.config import (
    load_config,
    save_config,
    add_cluster,
    remove_cluster,
    set_default_cluster,
    get_cluster,
    ClusterExistsError,
    ClusterNotFoundError,
)
from gpuctl.multicloud.models import ClusterConfig, ClusterRegistry


class TestConfigOperations:
    """测试配置操作"""
    
    def setup_method(self):
        """每个测试前创建临时配置文件路径"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_config_path = config.CONFIG_PATH
        # CONFIG_PATH 是 Path(生产代码用 .exists()/.parent/.name),patch 也必须给 Path,
        # 不能用 os.path.join 的 str(否则 load_config 里 CONFIG_PATH.exists() 报 AttributeError)。
        config.CONFIG_PATH = Path(self.temp_dir) / "clusters.yaml"
    
    def teardown_method(self):
        """每个测试后恢复原始配置路径"""
        config.CONFIG_PATH = self.original_config_path
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_empty_config(self):
        """测试加载空配置"""
        registry = load_config()
        assert isinstance(registry, ClusterRegistry)
        assert len(registry.clusters) == 0
        assert registry.default_cluster is None
    
    def test_save_and_load_config(self):
        """测试保存和加载配置"""
        registry = ClusterRegistry()
        cluster = ClusterConfig(
            name="prod",
            provider="ack",
            region="cn-hangzhou",
            kubeconfig_path="/home/user/.kube/config"
        )
        registry.add_cluster(cluster)
        registry.set_default("prod")
        
        save_config(registry)
        
        loaded = load_config()
        assert len(loaded.clusters) == 1
        assert loaded.default_cluster == "prod"
        assert loaded.clusters[0].name == "prod"
    
    def test_add_cluster_via_function(self):
        """测试通过函数添加集群"""
        cluster = ClusterConfig(
            name="dev",
            provider="tke",
            kubeconfig_path="/home/user/.kube/dev-config"
        )
        add_cluster(cluster)
        
        registry = load_config()
        assert registry.cluster_exists("dev")
    
    def test_add_duplicate_cluster_fails(self):
        """测试添加重复集群失败"""
        cluster = ClusterConfig(
            name="dev",
            provider="tke",
            kubeconfig_path="/home/user/.kube/dev-config"
        )
        add_cluster(cluster)
        
        with pytest.raises(ClusterExistsError):
            add_cluster(cluster)
    
    def test_remove_cluster_via_function(self):
        """测试通过函数删除集群"""
        cluster = ClusterConfig(
            name="dev",
            provider="tke",
            kubeconfig_path="/home/user/.kube/dev-config"
        )
        add_cluster(cluster)
        remove_cluster("dev")
        
        registry = load_config()
        assert not registry.cluster_exists("dev")
    
    def test_remove_nonexistent_cluster_fails(self):
        """测试删除不存在集群失败"""
        with pytest.raises(ClusterNotFoundError):
            remove_cluster("nonexistent")
    
    def test_set_default_cluster_via_function(self):
        """测试通过函数设置默认集群"""
        cluster = ClusterConfig(
            name="prod",
            provider="ack",
            kubeconfig_path="/home/user/.kube/prod-config"
        )
        add_cluster(cluster)
        set_default_cluster("prod")
        
        registry = load_config()
        assert registry.default_cluster == "prod"
    
    def test_set_nonexistent_default_fails(self):
        """测试设置不存在集群为默认失败"""
        with pytest.raises(ClusterNotFoundError):
            set_default_cluster("nonexistent")
    
    def test_get_cluster(self):
        """测试获取集群"""
        cluster = ClusterConfig(
            name="prod",
            provider="ack",
            kubeconfig_path="/home/user/.kube/prod-config"
        )
        add_cluster(cluster)
        
        found = get_cluster("prod")
        assert found is not None
        assert found.name == "prod"
    
    def test_get_nonexistent_cluster(self):
        """测试获取不存在集群返回 None"""
        found = get_cluster("nonexistent")
        assert found is None
