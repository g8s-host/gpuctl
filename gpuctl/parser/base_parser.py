import yaml
from typing import Any
from pydantic import ValidationError
from gpuctl.api.training import TrainingJob
from gpuctl.api.inference import InferenceJob
from gpuctl.api.notebook import NotebookJob
from gpuctl.api.compute import ComputeJob
from gpuctl.api.pool import ResourcePool


class ParserError(Exception):
    """解析错误异常"""
    pass


class BaseParser:
    """基础解析器"""

    KIND_MAPPING = {
        "training": TrainingJob,
        "inference": InferenceJob,
        "notebook": NotebookJob,
        "compute": ComputeJob,
        "pool": ResourcePool,
        "resource": ResourcePool
    }

    @classmethod
    def parse_yaml(cls, yaml_content: str) -> Any:
        """解析YAML内容"""
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
        """从文件解析YAML"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return cls.parse_yaml(content)
        except FileNotFoundError:
            raise ParserError(f"File not found: {file_path}")
        except IOError as e:
            raise ParserError(f"File reading error: {e}")