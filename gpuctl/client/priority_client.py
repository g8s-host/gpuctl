from kubernetes import client, config
from typing import List, Dict, Any, Optional
from enum import Enum
from .base_client import KubernetesClient


class PriorityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PriorityConfig:
    """优先级配置"""
    PRIORITY_CLASSES = {
        PriorityLevel.HIGH: {
            "name": "gpuctl-high",
            "value": 1000000,
            "preemption_policy": "PreemptLowerPriority",
            "description": "High priority for critical business applications"
        },
        PriorityLevel.MEDIUM: {
            "name": "gpuctl-medium",
            "value": 500000,
            "preemption_policy": "PreemptLowerPriority",
            "description": "Medium priority for regular microservices"
        },
        PriorityLevel.LOW: {
            "name": "gpuctl-low",
            "value": 100,
            "preemption_policy": "Never",
            "description": "Low priority for batch processing tasks"
        }
    }


class PriorityClient(KubernetesClient):
    """PriorityClass管理客户端"""
    
    def __init__(self):
        super().__init__()  # 调用基类的__init__方法，加载Kubernetes配置
        self._scheduling_api = client.SchedulingV1Api()  # 添加scheduling API客户端
    
    def create_priority_classes(self) -> List[Dict[str, Any]]:
        """创建所有优先级类"""
        results = []
        for priority_level, config in PriorityConfig.PRIORITY_CLASSES.items():
            result = self.create_priority_class(**config)
            results.append(result)
        return results
    
    def create_priority_class(self, name: str, value: int, preemption_policy: str, description: str) -> Dict[str, Any]:
        """创建单个优先级类"""
        priority_class = client.V1PriorityClass(
            api_version="scheduling.k8s.io/v1",
            kind="PriorityClass",
            metadata=client.V1ObjectMeta(name=name),
            value=value,
            preemption_policy=preemption_policy,
            description=description,
            global_default=False
        )
        
        try:
            # 尝试创建优先级类，如果已存在则更新
            self._scheduling_api.create_priority_class(priority_class)
            return {
                "name": name,
                "status": "created",
                "value": value,
                "preemption_policy": preemption_policy
            }
        except client.rest.ApiException as e:
            if e.status == 409:  # 资源已存在
                try:
                    self._scheduling_api.replace_priority_class(name, priority_class)
                    return {
                        "name": name,
                        "status": "updated",
                        "value": value,
                        "preemption_policy": preemption_policy
                    }
                except Exception as update_e:
                    return {
                        "name": name,
                        "status": "failed",
                        "error": str(update_e)
                    }
            return {
                "name": name,
                "status": "failed",
                "error": str(e)
            }
    
    def get_priority_class(self, name: str) -> Optional[client.V1PriorityClass]:
        """获取单个优先级类"""
        try:
            return self._scheduling_api.read_priority_class(name)
        except client.rest.ApiException as e:
            if e.status == 404:
                return None
            raise
    
    def list_priority_classes(self) -> List[client.V1PriorityClass]:
        """列出所有优先级类"""
        try:
            result = self._scheduling_api.list_priority_class()
            return result.items
        except Exception as e:
            raise
    
    def delete_priority_class(self, name: str) -> Dict[str, Any]:
        """删除优先级类"""
        try:
            self._scheduling_api.delete_priority_class(name)
            return {
                "name": name,
                "status": "deleted"
            }
        except Exception as e:
            return {
                "name": name,
                "status": "failed",
                "error": str(e)
            }
    
    def get_priority_class_name(self, priority_level: PriorityLevel) -> str:
        """根据优先级级别获取优先级类名称"""
        return PriorityConfig.PRIORITY_CLASSES[priority_level]["name"]
    
    def get_priority_class_by_value(self, value: int) -> Optional[Dict[str, Any]]:
        """根据数值获取优先级类配置"""
        for config in PriorityConfig.PRIORITY_CLASSES.values():
            if config["value"] == value:
                return config
        return None
    
    def ensure_priority_classes(self) -> List[Dict[str, Any]]:
        """确保所有优先级类存在"""
        return self.create_priority_classes()
