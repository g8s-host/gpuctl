from kubernetes import client
from .base_builder import BaseBuilder
from gpuctl.api.training import TrainingJob


class TrainingBuilder(BaseBuilder):
    """训练任务构建器"""

    @classmethod
    def build_job(cls, training_job: TrainingJob) -> client.V1Job:
        """构建K8s Job资源"""
        # 构建容器
        container = cls.build_container_spec(training_job.environment, training_job.resources)

        # 构建Pod模板
        pod_spec_extras = {}
        if training_job.environment.image_pull_secret:
            pod_spec_extras['image_pull_secrets'] = [
                client.V1LocalObjectReference(name=training_job.environment.image_pull_secret)
            ]

        if training_job.resources.pool:
            pod_spec_extras['node_selector'] = {
                "gpuctl/pool": training_job.resources.pool
            }

        template = cls.build_pod_template_spec(container, pod_spec_extras)

        # 构建Job规格
        job_spec = client.V1JobSpec(
            template=template,
            backoff_limit=3,
            ttl_seconds_after_finished=86400  # 24小时后自动清理
        )

        # 构建Job元数据
        metadata = client.V1ObjectMeta(
            name=f"{training_job.job.name}-{training_job.job.priority}",
            labels={
                "gpuctl/job-type": "training",
                "gpuctl/priority": training_job.job.priority,
                "gpuctl/pool": training_job.resources.pool or "default"
            }
        )

        return client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=metadata,
            spec=job_spec
        )