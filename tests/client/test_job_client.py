"""
回归测试：JobClient 中的 label selector、pod 状态访问、delete 策略与超时
"""
import pytest
import time
from unittest.mock import patch, MagicMock, call
from kubernetes.client.rest import ApiException
from kubernetes import client as k8s_client


@patch('gpuctl.client.job_client.KubernetesClient.__init__', return_value=None)
def test_get_all_gpuctl_namespaces_uses_valid_label_selector(mock_init):
    """回归测试：_get_all_gpuctl_namespaces 应使用 g8s.host/job-type 而非无效的 g8s.host/"""
    from gpuctl.client.job_client import JobClient

    client = JobClient.__new__(JobClient)
    client.core_v1 = MagicMock()
    client.batch_v1 = MagicMock()
    client.apps_v1 = MagicMock()

    # list_namespace 两次调用：一次带 label_selector，一次不带
    labeled_ns_result = MagicMock()
    labeled_ns_result.items = []
    all_ns_result = MagicMock()
    mock_ns = MagicMock()
    mock_ns.metadata.name = "test-ns"
    all_ns_result.items = [mock_ns]
    client.core_v1.list_namespace.side_effect = [labeled_ns_result, all_ns_result]

    jobs_result = MagicMock()
    jobs_result.items = []
    deployments_result = MagicMock()
    deployments_result.items = []
    statefulsets_result = MagicMock()
    statefulsets_result.items = []

    client.batch_v1.list_namespaced_job.return_value = jobs_result
    client.apps_v1.list_namespaced_deployment.return_value = deployments_result
    client.apps_v1.list_namespaced_stateful_set.return_value = statefulsets_result

    result = client._get_all_gpuctl_namespaces()

    # 验证使用了合法的 label selector（key 存在性检查）
    client.batch_v1.list_namespaced_job.assert_called_once_with(
        "test-ns", label_selector="g8s.host/job-type"
    )
    client.apps_v1.list_namespaced_deployment.assert_called_once_with(
        "test-ns", label_selector="g8s.host/job-type"
    )
    client.apps_v1.list_namespaced_stateful_set.assert_called_once_with(
        "test-ns", label_selector="g8s.host/job-type"
    )

    # default 始终在结果中
    assert "default" in result


@patch('gpuctl.client.job_client.KubernetesClient.__init__', return_value=None)
def test_get_all_gpuctl_namespaces_includes_namespace_with_gpuctl_jobs(mock_init):
    """验证：若某 namespace 下有 gpuctl 作业，该 namespace 会被收集"""
    from gpuctl.client.job_client import JobClient

    client = JobClient.__new__(JobClient)
    client.core_v1 = MagicMock()
    client.batch_v1 = MagicMock()
    client.apps_v1 = MagicMock()

    labeled_ns_result = MagicMock()
    labeled_ns_result.items = []
    all_ns_result = MagicMock()
    mock_ns = MagicMock()
    mock_ns.metadata.name = "ml-team"
    all_ns_result.items = [mock_ns]
    client.core_v1.list_namespace.side_effect = [labeled_ns_result, all_ns_result]

    # ml-team 下有一个 gpuctl job
    jobs_result = MagicMock()
    jobs_result.items = [MagicMock()]  # non-empty → namespace should be added
    client.batch_v1.list_namespaced_job.return_value = jobs_result

    result = client._get_all_gpuctl_namespaces()

    assert "ml-team" in result
    assert "default" in result


# ── _wait_for_resource_deletion 超时回归测试 ──────────────────────────────────

@patch('gpuctl.client.job_client.KubernetesClient.__init__', return_value=None)
def test_wait_for_resource_deletion_returns_quickly_on_success(mock_init):
    """回归测试：资源已删除时应立即返回 True，不应阻塞"""
    from gpuctl.client.job_client import JobClient

    client = JobClient.__new__(JobClient)
    check_func = MagicMock(return_value=False)  # 资源已不存在

    start = time.time()
    result = client._wait_for_resource_deletion(check_func, "test-dep", "Deployment")
    elapsed = time.time() - start

    assert result is True
    assert elapsed < 2, f"should return immediately but took {elapsed:.1f}s"
    check_func.assert_called_once()


@patch('gpuctl.client.job_client.KubernetesClient.__init__', return_value=None)
def test_wait_for_resource_deletion_timeout_within_30s(mock_init):
    """回归测试：超时应 <= 30 秒（修复前是 600 秒会导致阻塞）"""
    from gpuctl.client.job_client import JobClient

    client = JobClient.__new__(JobClient)
    check_func = MagicMock(return_value=True)  # 资源一直存在

    start = time.time()
    result = client._wait_for_resource_deletion(check_func, "stuck-dep", "Deployment", timeout=1)
    elapsed = time.time() - start

    assert result is True
    assert elapsed < 3, f"timeout=1 should finish within ~1s but took {elapsed:.1f}s"


# ── delete_deployment/statefulset 使用 Background 策略回归测试 ─────────────────

@patch('gpuctl.client.job_client.KubernetesClient.__init__', return_value=None)
def test_delete_deployment_uses_background_propagation(mock_init):
    """回归测试：delete_deployment 应使用 Background 策略避免 API 阻塞"""
    from gpuctl.client.job_client import JobClient

    client = JobClient.__new__(JobClient)
    client.apps_v1 = MagicMock()
    client.apps_v1.read_namespaced_deployment.side_effect = ApiException(status=404)

    result = client.delete_deployment("test-dep", "default")

    call_args = client.apps_v1.delete_namespaced_deployment.call_args
    delete_options = call_args.kwargs.get('body') or call_args[1].get('body')
    assert delete_options.propagation_policy == "Background"


@patch('gpuctl.client.job_client.KubernetesClient.__init__', return_value=None)
def test_delete_statefulset_uses_background_propagation(mock_init):
    """回归测试：delete_statefulset 应使用 Background 策略避免 API 阻塞"""
    from gpuctl.client.job_client import JobClient

    client = JobClient.__new__(JobClient)
    client.apps_v1 = MagicMock()
    client.apps_v1.read_namespaced_stateful_set.side_effect = ApiException(status=404)

    result = client.delete_statefulset("test-sts", "default")

    call_args = client.apps_v1.delete_namespaced_stateful_set.call_args
    delete_options = call_args.kwargs.get('body') or call_args[1].get('body')
    assert delete_options.propagation_policy == "Background"


@patch('gpuctl.client.job_client.KubernetesClient.__init__', return_value=None)
def test_delete_service_uses_background_propagation(mock_init):
    """回归测试：delete_service 应使用 Background 策略避免 API 阻塞"""
    from gpuctl.client.job_client import JobClient

    client = JobClient.__new__(JobClient)
    client.core_v1 = MagicMock()
    client.core_v1.read_namespaced_service.side_effect = ApiException(status=404)

    result = client.delete_service("svc-test", "default")

    call_args = client.core_v1.delete_namespaced_service.call_args
    delete_options = call_args.kwargs.get('body') or call_args[1].get('body')
    assert delete_options.propagation_policy == "Background"
