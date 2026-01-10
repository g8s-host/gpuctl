# Mock data for Kubernetes jobs

# 模拟作业数据
mock_jobs = [
    {
        "name": "test-training-job",
        "namespace": "default",
        "labels": {
            "g8s.host/job-type": "training",
            "g8s.host/pool": "training-pool"
        },
        "status": {
            "active": 1,
            "succeeded": 0,
            "failed": 0
        },
        "creation_timestamp": "2023-01-01T12:00:00Z"
    },
    {
        "name": "test-inference-job",
        "namespace": "default",
        "labels": {
            "g8s.host/job-type": "inference",
            "g8s.host/pool": "inference-pool"
        },
        "status": {
            "active": 1,
            "succeeded": 0,
            "failed": 0
        },
        "creation_timestamp": "2023-01-02T12:00:00Z"
    },
    {
        "name": "test-notebook-job",
        "namespace": "default",
        "labels": {
            "g8s.host/job-type": "notebook",
            "g8s.host/pool": "notebook-pool"
        },
        "status": {
            "active": 1,
            "succeeded": 0,
            "failed": 0
        },
        "creation_timestamp": "2023-01-03T12:00:00Z"
    }
]

# 模拟Pod数据
mock_pods = [
    {
        "name": "test-training-job-pod-1",
        "namespace": "default",
        "labels": {
            "job-name": "test-training-job",
            "g8s.host/job-type": "training"
        },
        "status": {
            "phase": "Running"
        },
        "creation_timestamp": "2023-01-01T12:00:00Z"
    },
    {
        "name": "test-inference-job-pod-1",
        "namespace": "default",
        "labels": {
            "app": "test-inference-job",
            "g8s.host/job-type": "inference"
        },
        "status": {
            "phase": "Running"
        },
        "creation_timestamp": "2023-01-02T12:00:00Z"
    }
]

# 模拟作业日志数据
mock_job_logs = {
    "test-training-job": [
        "2023-01-01T12:00:00Z INFO: Job started",
        "2023-01-01T12:01:00Z INFO: Training epoch 1/3 started",
        "2023-01-01T12:02:00Z INFO: Loss: 0.87",
        "2023-01-01T12:03:00Z INFO: Training epoch 1/3 completed",
        "2023-01-01T12:04:00Z INFO: Training epoch 2/3 started"
    ],
    "test-inference-job": [
        "2023-01-02T12:00:00Z INFO: Inference service started",
        "2023-01-02T12:01:00Z INFO: Model loaded successfully",
        "2023-01-02T12:02:00Z INFO: Listening on port 8000"
    ]
}