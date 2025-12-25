from .base_parser import BaseParser, ParserError
from gpuctl.api.compute import ComputeJob


class ComputeParser(BaseParser):
    """计算任务解析器"""

    @classmethod
    def validate_resources(cls, compute_job: ComputeJob) -> None:
        """验证资源需求"""
        resources = compute_job.resources

        # 计算任务默认不需要GPU
        if resources.gpu < 0:
            raise ParserError("GPU数量不能为负数")

        # 验证CPU和内存格式
        if isinstance(resources.cpu, str):
            if not resources.cpu.endswith('m') and not resources.cpu.isdigit():
                raise ParserError("CPU格式错误，应为数字或毫核数（如8000m）")

        if not resources.memory.upper().endswith(('GI', 'MI', 'KI')):
            raise ParserError("内存格式错误，应为如32Gi格式")

    @classmethod
    def parse_and_validate(cls, yaml_content: str) -> ComputeJob:
        """解析并验证计算任务"""
        compute_job = cls.parse_yaml(yaml_content)
        if not isinstance(compute_job, ComputeJob):
            raise ParserError("YAML内容不是计算任务")

        cls.validate_resources(compute_job)
        return compute_job