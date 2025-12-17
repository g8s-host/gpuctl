from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.training import TrainingJob


class TrainingBuilder(BaseBuilder):
    """训练任务构建器"""

    @classmethod
    def build_job(cls, training_job: TrainingJob) -> client.V1Job:
        """构建K8s Job资源"""
        # 获取workdirs
        workdirs = training_job.storage.workdirs if hasattr(training_job.storage, 'workdirs') else []
        
        # 构建容器
        container = cls.build_container_spec(training_job.environment, training_job.resources, workdirs)

        # 构建Pod模板
        pod_spec_extras = {}
        if training_job.environment.image_pull_secret:
            pod_spec_extras['image_pull_secrets'] = [
                client.V1LocalObjectReference(name=training_job.environment.image_pull_secret)
            ]

        node_selector = {}
        if training_job.resources.pool:
            node_selector["g8s.host/pool"] = training_job.resources.pool
        if training_job.resources.gpu_type:
            node_selector["g8s.host/gpu-type"] = training_job.resources.gpu_type
        if node_selector:
            pod_spec_extras['node_selector'] = node_selector

        template = cls.build_pod_template_spec(container, pod_spec_extras, workdirs=workdirs)

        # 构建Job规格
        job_spec = client.V1JobSpec(
            template=template,
            backoff_limit=3,
            ttl_seconds_after_finished=86400  # 24小时后自动清理
        )

        # 构建Job元数据，使用一致的前缀格式：g8s-host-{job_type}-{job_name}
        metadata = client.V1ObjectMeta(
            name=f"g8s-host-training-{training_job.job.name}",
            labels={
                "g8s.host/job-type": "training",
                "g8s.host/priority": training_job.job.priority,
                "g8s.host/pool": training_job.resources.pool or "default"
            }
        )

        return client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=metadata,
            spec=job_spec
        )