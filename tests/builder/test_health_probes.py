"""BaseBuilder.build_health_probes: the shared startup / liveness / readiness probes
used by both inference and compute, supporting an HTTP path or a 'tcp' socket check
(so non-HTTP services like redis can have probes too)."""
import pytest
from gpuctl.builder.base_builder import BaseBuilder
from gpuctl.api.common import ServiceConfig


def test_http_path_produces_httpget_probes():
    s = ServiceConfig(port=8000, healthCheck="/health")   # no startupTimeout -> default 10m
    startup, live, ready = BaseBuilder.build_health_probes(s)
    assert startup.http_get.path == "/health"
    assert startup.http_get.port == 8000
    assert startup.tcp_socket is None
    assert startup.failure_threshold == 60                # 10m / 10s
    assert startup.timeout_seconds == 5 and startup.period_seconds == 10
    assert live.failure_threshold == 3 and ready.failure_threshold == 3


def test_startup_timeout_drives_failure_threshold():
    s = ServiceConfig(port=8000, healthCheck="/health", startupTimeout="5m")
    startup, _, _ = BaseBuilder.build_health_probes(s)
    assert startup.failure_threshold == 30                # 5m / 10s


def test_tcp_produces_tcpsocket_probes():
    s = ServiceConfig(port=6379, healthCheck="tcp")
    startup, live, ready = BaseBuilder.build_health_probes(s)
    assert startup.tcp_socket is not None
    assert startup.tcp_socket.port == 6379
    assert startup.http_get is None
    assert live.tcp_socket.port == 6379 and ready.tcp_socket.port == 6379


def test_tcp_with_explicit_port():
    s = ServiceConfig(port=8000, healthCheck="tcp:6380")
    startup, _, _ = BaseBuilder.build_health_probes(s)
    assert startup.tcp_socket.port == 6380


def test_no_health_check_returns_none_triplet():
    assert BaseBuilder.build_health_probes(ServiceConfig(port=8000)) == (None, None, None)
    assert BaseBuilder.build_health_probes(None) == (None, None, None)
