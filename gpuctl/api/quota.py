from pydantic import BaseModel, Field
from typing import Dict, Optional, Union


class UserQuota(BaseModel):
    cpu: Optional[Union[str, int]] = None
    memory: Optional[str] = None
    gpu: Optional[Union[str, int]] = None

    model_config = {
        "populate_by_name": True
    }

    def get_cpu_str(self) -> Optional[str]:
        """Get CPU as string"""
        if self.cpu is None:
            return None
        return str(self.cpu)

    def get_gpu_str(self) -> Optional[str]:
        """Get GPU as string"""
        if self.gpu is None:
            return None
        return str(self.gpu)


class QuotaInfo(BaseModel):
    name: str
    description: Optional[str] = None


class QuotaConfig(BaseModel):
    kind: str = "quota"
    version: str = "v0.1"
    quota: QuotaInfo
    namespace: Dict[str, UserQuota] = Field(default_factory=dict)
    default: Optional[UserQuota] = None

    model_config = {
        "populate_by_name": True,
        "alias_generator": lambda s: s.replace("_", "-")
    }

    @property
    def users(self) -> Dict[str, UserQuota]:
        """Backward compatibility: return namespace as users"""
        return self.namespace
