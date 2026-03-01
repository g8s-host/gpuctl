import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)


@patch('server.auth.AuthValidator.validate_token')
def test_check_auth(mock_validate_token):
    """测试认证检查API"""
    mock_validate_token.return_value = True

    response = client.post(
        "/api/v1/auth/check",
        json={
            "pool": "test-pool",
            "resource": "jobs",
            "action": "create"
        },
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert "test-pool" in response.json()["message"]
