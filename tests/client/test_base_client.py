"""
回归测试：KubernetesClient.handle_api_exception 中的裸 except 修复
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from kubernetes.client.rest import ApiException


@patch('gpuctl.client.base_client.KubernetesClient.__init__', return_value=None)
def test_handle_api_exception_404_returns_detailed_message(mock_init):
    """回归测试：404 异常应返回 JSON body 中的 message，而非被裸 except 截断"""
    from gpuctl.client.base_client import KubernetesClient

    client = KubernetesClient.__new__(KubernetesClient)

    error_detail = {"message": "jobs.batch 'missing-job' not found", "reason": "NotFound"}
    mock_exc = MagicMock(spec=ApiException)
    mock_exc.status = 404
    mock_exc.body = json.dumps(error_detail)

    with pytest.raises(FileNotFoundError) as exc_info:
        client.handle_api_exception(mock_exc, "get job")

    # 应包含 JSON body 中的 detailed message
    assert "missing-job" in str(exc_info.value)
    assert "get job" in str(exc_info.value)


@patch('gpuctl.client.base_client.KubernetesClient.__init__', return_value=None)
def test_handle_api_exception_404_non_json_body(mock_init):
    """回归测试：404 body 非合法 JSON 时，不应抛出 ValueError/TypeError，仍返回 FileNotFoundError"""
    from gpuctl.client.base_client import KubernetesClient

    client = KubernetesClient.__new__(KubernetesClient)

    mock_exc = MagicMock(spec=ApiException)
    mock_exc.status = 404
    mock_exc.body = "plain text error"  # 非 JSON

    with pytest.raises(FileNotFoundError) as exc_info:
        client.handle_api_exception(mock_exc, "get deployment")

    assert "get deployment" in str(exc_info.value)


@patch('gpuctl.client.base_client.KubernetesClient.__init__', return_value=None)
def test_handle_api_exception_500_returns_detailed_message(mock_init):
    """回归测试：500 异常应正确解析 JSON body 的 message"""
    from gpuctl.client.base_client import KubernetesClient

    client = KubernetesClient.__new__(KubernetesClient)

    error_detail = {"message": "etcd cluster is unavailable"}
    mock_exc = MagicMock(spec=ApiException)
    mock_exc.status = 500
    mock_exc.body = json.dumps(error_detail)

    with pytest.raises(RuntimeError) as exc_info:
        client.handle_api_exception(mock_exc, "list pods")

    assert "etcd cluster is unavailable" in str(exc_info.value)


@patch('gpuctl.client.base_client.KubernetesClient.__init__', return_value=None)
def test_handle_api_exception_401(mock_init):
    """验证 401 异常返回 PermissionError"""
    from gpuctl.client.base_client import KubernetesClient

    client = KubernetesClient.__new__(KubernetesClient)
    mock_exc = MagicMock(spec=ApiException)
    mock_exc.status = 401

    with pytest.raises(PermissionError) as exc_info:
        client.handle_api_exception(mock_exc, "create job")

    assert "Authentication failed" in str(exc_info.value)
