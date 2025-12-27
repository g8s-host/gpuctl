import yaml
from typing import Any
from pydantic import ValidationError
from gpuctl.api.training import TrainingJob
from gpuctl.api.inference import InferenceJob
from gpuctl.api.notebook import NotebookJob
from gpuctl.api.pool import ResourcePool
from gpuctl.api.compute import ComputeJob


class ParserError(Exception):
    """Parser error exception"""
    pass


class BaseParser:
    """Base parser"""

    KIND_MAPPING = {
        "training": TrainingJob,
        "inference": InferenceJob,
        "notebook": NotebookJob,
        "pool": ResourcePool,
        "resource": ResourcePool,
        "compute": ComputeJob
    }

    @classmethod
    def parse_yaml(cls, yaml_content: str) -> Any:
        """Parse YAML content"""
        try:
            data = yaml.safe_load(yaml_content)
            if not data or 'kind' not in data:
                raise ParserError("Invalid YAML: missing 'kind' field")

            kind = data['kind']
            if kind not in cls.KIND_MAPPING:
                raise ParserError(f"Unsupported kind: {kind}")

            model_class = cls.KIND_MAPPING[kind]
            return model_class(**data)

        except yaml.YAMLError as e:
            raise ParserError(f"YAML parsing error: {e}")
        except ValidationError as e:
            raise ParserError(f"Validation error: {e}")

    @classmethod
    def parse_yaml_file(cls, file_path: str) -> Any:
        """Parse YAML from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return cls.parse_yaml(content)
        except FileNotFoundError:
            raise ParserError(f"File not found: {file_path}")
        except IOError as e:
            raise ParserError(f"File reading error: {e}")