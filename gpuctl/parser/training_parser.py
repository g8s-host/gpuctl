from .base_parser import BaseParser, ParserError
from gpuctl.api.training import TrainingJob


class TrainingParser(BaseParser):
    """Training job parser"""

    @classmethod
    def validate_resources(cls, training_job: TrainingJob) -> None:
        """Validate resource requirements"""
        spec = training_job.spec
        resources = spec.resources

        if resources.accelerator_count > 8:
            raise ParserError("GPU count cannot exceed 8")

        if not resources.cpu.endswith('m') and not resources.cpu.isdigit():
            raise ParserError("Invalid CPU format, should be a number or millicores (e.g., 8000m)")

        if not resources.memory.upper().endswith(('GI', 'MI', 'KI')):
            raise ParserError("Invalid memory format, should be like 32Gi")

    @classmethod
    def parse_and_validate(cls, yaml_content: str) -> TrainingJob:
        """Parse and validate training job"""
        training_job = cls.parse_yaml(yaml_content)
        if not isinstance(training_job, TrainingJob):
            raise ParserError("YAML content is not a training job")

        cls.validate_resources(training_job)
        return training_job