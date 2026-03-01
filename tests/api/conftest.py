import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_auth_validator():
    """Mock 认证验证器"""
    with patch('server.auth.AuthValidator.validate_token', return_value='test-token'):
        yield


@pytest.fixture
def client():
    """创建测试客户端"""
    from fastapi.testclient import TestClient
    from server.main import app
    return TestClient(app)
