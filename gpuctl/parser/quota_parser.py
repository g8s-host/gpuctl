from .base_parser import BaseParser, ParserError
from gpuctl.api.quota import QuotaConfig


class QuotaParser(BaseParser):
    """Quota config parser"""

    @classmethod
    def validate_quota(cls, quota: QuotaConfig) -> None:
        """Validate quota configuration"""
        if not quota.users:
            raise ParserError("At least one user must be defined in users")

        for user_name, user_quota in quota.users.items():
            if user_quota.gpu:
                try:
                    gpu_count = int(user_quota.gpu)
                    if gpu_count < 0:
                        raise ParserError(f"GPU count must be non-negative for user {user_name}")
                except ValueError:
                    raise ParserError(f"Invalid GPU format for user {user_name}, should be a number")

    @classmethod
    def parse_and_validate(cls, yaml_content: str) -> QuotaConfig:
        """Parse and validate quota config"""
        quota = cls.parse_yaml(yaml_content)
        if not isinstance(quota, QuotaConfig):
            raise ParserError("YAML content is not a quota config")

        cls.validate_quota(quota)
        return quota
