"""统一错误格式(Agent-First PRD §4.8)。"""
from unittest.mock import patch

from server.errors import error_body


def test_plain_string_detail_gets_default_code_and_action():
    body = error_body(404, "Job not found")
    assert body == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Job not found",
            "action": "check_resource_name",
        }
    }


def test_unknown_status_falls_back_to_generic_defaults():
    body = error_body(418, "I'm a teapot")
    assert body["error"]["code"] == "ERROR"
    assert body["error"]["action"] == "retry"
    assert body["error"]["message"] == "I'm a teapot"


def test_structured_detail_is_preserved_and_completed():
    body = error_body(422, {
        "code": "GPU_UNAVAILABLE",
        "message": "No free GPU with type 'A100' found",
        "action": "submit_to_queue",
        "details": {"requested": {"type": "A100", "count": 1}},
    })
    assert body == {
        "error": {
            "code": "GPU_UNAVAILABLE",
            "message": "No free GPU with type 'A100' found",
            "action": "submit_to_queue",
            "details": {"requested": {"type": "A100", "count": 1}},
        }
    }


def test_structured_detail_without_action_gets_status_default():
    body = error_body(403, {"code": "FORBIDDEN", "message": "no scope"})
    assert body["error"]["action"] == "request_scope"
    assert "details" not in body["error"]


@patch("server.routes.jobs.JobClient")
def test_server_main_exception_handlers_use_structured_format(mock_job_client_cls, client):
    mock_job_client_cls.return_value.get_job.return_value = None
    mock_job_client_cls.return_value.get_pod.return_value = None

    r = client.get("/api/v1/jobs/does-not-exist")

    assert r.status_code == 404
    body = r.json()
    assert body == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Job not found",
            "action": "check_resource_name",
        }
    }
