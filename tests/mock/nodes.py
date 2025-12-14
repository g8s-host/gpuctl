# Mock data for Kubernetes nodes

# 模拟节点数据
mock_nodes = [
    {
        "name": "node-1",
        "status": "active",
        "gpu_total": 8,
        "gpu_used": 4,
        "gpu_free": 4,
        "gpu_types": ["A100"],
        "labels": {
            "g8s.host/pool": "training-pool",
            "nvidia.com/gpu-type": "a100-80g"
        },
        "creation_timestamp": "2023-01-01T12:00:00Z"
    },
    {
        "name": "node-2",
        "status": "active",
        "gpu_total": 4,
        "gpu_used": 0,
        "gpu_free": 4,
        "gpu_types": ["V100"],
        "labels": {
            "g8s.host/pool": "inference-pool",
            "nvidia.com/gpu-type": "v100-32g"
        },
        "creation_timestamp": "2023-01-02T12:00:00Z"
    },
    {
        "name": "node-3",
        "status": "active",
        "gpu_total": 8,
        "gpu_used": 2,
        "gpu_free": 6,
        "gpu_types": ["H100"],
        "labels": {
            "g8s.host/pool": "training-pool",
            "nvidia.com/gpu-type": "h100-80g"
        },
        "creation_timestamp": "2023-01-03T12:00:00Z"
    }
]

# 模拟节点详情数据
mock_node_details = {
    "node-1": {
        "name": "node-1",
        "status": "active",
        "k8sStatus": {
            "conditions": [
                {"type": "Ready", "status": "True", "lastHeartbeatTime": "2023-01-01T12:00:00Z"}
            ],
            "kernelVersion": "5.4.0-1090-ubuntu",
            "osImage": "Ubuntu 20.04 LTS"
        },
        "resources": {
            "cpuTotal": 64,
            "cpuUsed": 32,
            "memoryTotal": "256Gi",
            "memoryUsed": "128Gi",
            "gpuTotal": 8,
            "gpuUsed": 4,
            "gpuFree": 4
        },
        "gpuDetail": [
            {"gpuId": "gpu-0", "type": "a100-80g", "status": "used", "utilization": 89.2, "memoryUsage": "72Gi/80Gi"},
            {"gpuId": "gpu-1", "type": "a100-80g", "status": "used", "utilization": 91.5, "memoryUsage": "75Gi/80Gi"},
            {"gpuId": "gpu-2", "type": "a100-80g", "status": "free", "utilization": 0, "memoryUsage": "0Gi/80Gi"},
            {"gpuId": "gpu-3", "type": "a100-80g", "status": "free", "utilization": 0, "memoryUsage": "0Gi/80Gi"},
            {"gpuId": "gpu-4", "type": "a100-80g", "status": "used", "utilization": 78.3, "memoryUsage": "68Gi/80Gi"},
            {"gpuId": "gpu-5", "type": "a100-80g", "status": "used", "utilization": 85.7, "memoryUsage": "70Gi/80Gi"},
            {"gpuId": "gpu-6", "type": "a100-80g", "status": "free", "utilization": 0, "memoryUsage": "0Gi/80Gi"},
            {"gpuId": "gpu-7", "type": "a100-80g", "status": "free", "utilization": 0, "memoryUsage": "0Gi/80Gi"}
        ],
        "labels": [
            {"key": "nvidia.com/gpu-type", "value": "a100-80g"},
            {"key": "g8s.host/pool", "value": "training-pool"},
            {"key": "kubernetes.io/hostname", "value": "node-1"}
        ],
        "boundPools": ["training-pool"],
        "runningJobs": [
            {"jobId": "test-job-1", "name": "test-job-1", "gpu": 4}
        ],
        "createdAt": "2023-01-01T12:00:00Z",
        "lastUpdatedAt": "2023-01-01T12:00:00Z"
    }
}