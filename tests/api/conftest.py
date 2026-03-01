import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)
