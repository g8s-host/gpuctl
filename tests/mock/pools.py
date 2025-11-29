# Mock data for resource pools

# 模拟资源池数据
mock_pools = [
    {
        "name": "training-pool",
        "description": "用于模型训练的资源池",
        "gpu_total": 32,
        "gpu_used": 16,
        "gpu_free": 16,
        "gpu_types": ["a100-80g", "a100-40g"],
        "status": "active",
        "nodes": ["node-1", "node-3"]
    },
    {
        "name": "inference-pool",
        "description": "用于推理服务的资源池",
        "gpu_total": 16,
        "gpu_used": 8,
        "gpu_free": 8,
        "gpu_types": ["v100-32g", "t4-16g"],
        "status": "active",
        "nodes": ["node-2"]
    },
    {
        "name": "notebook-pool",
        "description": "用于Jupyter Notebook的资源池",
        "gpu_total": 8,
        "gpu_used": 2,
        "gpu_free": 6,
        "gpu_types": ["a10-24g"],
        "status": "active",
        "nodes": ["node-4"]
    }
]

# 模拟资源池详情数据
mock_pool_details = {
    "training-pool": {
        "name": "training-pool",
        "description": "用于模型训练的资源池",
        "nodes": ["node-1", "node-3"],
        "gpu_total": 32,
        "gpu_used": 16,
        "gpu_free": 16,
        "gpu_types": {
            "a100-80g": 24,
            "a100-40g": 8
        },
        "quota": {
            "maxJobs": 100,
            "maxGpuPerJob": 8
        },
        "jobs": [
            {"jobId": "test-training-job", "name": "test-training-job", "gpu": 4}
        ]
    },
    "inference-pool": {
        "name": "inference-pool",
        "description": "用于推理服务的资源池",
        "nodes": ["node-2"],
        "gpu_total": 16,
        "gpu_used": 8,
        "gpu_free": 8,
        "gpu_types": {
            "v100-32g": 16
        },
        "quota": {
            "maxJobs": 50,
            "maxGpuPerJob": 4
        },
        "jobs": [
            {"jobId": "test-inference-job", "name": "test-inference-job", "gpu": 2}
        ]
    }
}