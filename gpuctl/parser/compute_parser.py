from .base_parser import BaseParser, ParserError
from gpuctl.api.compute import ComputeJob


class ComputeParser(BaseParser):
    """Compute job parser"""

    @classmethod
    def validate_resources(cls, compute_job: ComputeJob) -> None:
        """Validate resource requirements"""
        resources = compute_job.resources

        if resources.gpu < 0:
            raise ParserError("GPU count cannot be negative")

        if isinstance(resources.cpu, str):
            if not resources.cpu.endswith('m') and not resources.cpu.isdigit():
                raise ParserError("Invalid CPU format, should be a number or millicores (e.g., 8000m)")

        if not resources.memory.upper().endswith(('GI', 'MI', 'KI')):
            raise ParserError("Invalid memory format, should be like 32Gi")

    @classmethod
    def parse_and_validate(cls, yaml_content: str) -> ComputeJob:
        """Parse and validate compute job"""
        compute_job = cls.parse_yaml(yaml_content)
        if not isinstance(compute_job, ComputeJob):
            raise ParserError("YAML content is not a compute job")

        cls.validate_resources(compute_job)
        return compute_job