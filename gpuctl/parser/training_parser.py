from .base_parser import BaseParser, ParserError
from gpuctl.api.training import TrainingJob


class TrainingParser(BaseParser):
    """训练任务解析器"""

    @classmethod
    def validate_resources(cls, training_job: TrainingJob) -> None:
        """验证资源需求"""
        spec = training_job.spec
        resources = spec.resources

        # 验证GPU类型和数量
        if resources.accelerator_count > 8:
            raise ParserError("GPU数量不能超过8个")

        # 验证CPU和内存格式
        if not resources.cpu.endswith('m') and not resources.cpu.isdigit():
            raise ParserError("CPU格式错误，应为数字或毫核数（如8000m）")

        if not resources.memory.upper().endswith(('GI', 'MI', 'KI')):
            raise ParserError("内存格式错误，应为如32Gi格式")

    @classmethod
    def parse_and_validate(cls, yaml_content: str) -> TrainingJob:
        """解析并验证训练任务"""
        training_job = cls.parse_yaml(yaml_content)
        if not isinstance(training_job, TrainingJob):
            raise ParserError("YAML内容不是训练任务")

        cls.validate_resources(training_job)
        return training_job