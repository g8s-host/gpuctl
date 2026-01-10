import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)


@patch('server.auth.AuthValidator.validate_token')
def test_get_permissions(mock_validate_token):
    """测试获取权限列表API"""
    # 设置模拟返回值
    mock_validate_token.return_value = "test-token"
    
    # 发送API请求
    response = client.get(
        "/api/v1/permissions",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@patch('server.auth.AuthValidator.validate_token')
def test_create_permission(mock_validate_token):
    """测试创建权限API"""
    # 设置模拟返回值
    mock_validate_token.return_value = "test-token"
    
    # 发送API请求
    response = client.post(
        "/api/v1/permissions",
        json={
            "name": "test-permission",
            "description": "Test permission",
            "actions": ["read", "write"],
            "resources": ["jobs", "pools"]
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 201
    assert response.json() == {
        "name": "test-permission",
        "message": "权限创建成功"
    }


@patch('server.auth.AuthValidator.validate_token')
def test_delete_permission(mock_validate_token):
    """测试删除权限API"""
    # 设置模拟返回值
    mock_validate_token.return_value = "test-token"
    
    # 发送API请求
    response = client.delete(
        "/api/v1/permissions/test-permission",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "name": "test-permission",
        "message": "权限删除成功"
    }


@patch('server.auth.AuthValidator.validate_token')
def test_get_permission_detail(mock_validate_token):
    """测试获取权限详情API"""
    # 设置模拟返回值
    mock_validate_token.return_value = "test-token"
    
    # 发送API请求
    response = client.get(
        "/api/v1/permissions/test-permission",
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json()["name"] == "test-permission"


@patch('server.auth.AuthValidator.validate_token')
def test_update_permission(mock_validate_token):
    """测试更新权限API"""
    # 设置模拟返回值
    mock_validate_token.return_value = "test-token"
    
    # 发送API请求
    response = client.put(
        "/api/v1/permissions/test-permission",
        json={
            "description": "Updated test permission",
            "actions": ["read", "write", "delete"],
            "resources": ["jobs", "pools", "nodes"]
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    # 断言结果
    assert response.status_code == 200
    assert response.json() == {
        "name": "test-permission",
        "message": "权限更新成功"
    }
