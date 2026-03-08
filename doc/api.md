# GPU Control API 详细文档

## 概述

GPU Control API 是一个面向算法工程师的 AI 算力调度平台 REST API，基于 FastAPI 构建。

### 基础信息

| 项目 | 值 |
|------|-----|
| Base URL | `http://localhost:8000` |
| API 版本 | v1 |

### 通用说明

- 响应格式默认 JSON
- 错误响应格式: `{"error": "错误信息"}`

---

## 目录

1. [基础接口](#基础接口)
2. [任务 API](#任务-api)
3. [资源池 API](#资源池-api)
4. [节点 API](#节点-api)
5. [标签 API](#标签-api)
6. [配额 API](#配额-api)
7. [命名空间 API](#命名空间-api)
8. [错误响应](#错误响应)
9. [数据模型参考](#数据模型参考)

---

## 基础接口

### GET /

API 根路由，返回服务基本信息。

**响应 (200):**
```json
{
    "message": "GPU Control API",
    "version": "1.0.0"
}
```

### GET /health

健康检查接口。

**响应 (200):**
```json
{
    "status": "healthy",
    "timestamp": "2026-03-01T00:00:00"
}
```

---

## 任务 API

Base Path: `/api/v1/jobs`

### POST /api/v1/jobs

创建单个任务。

**请求头:**
```
Content-Type: application/json
```

**请求体:**
```json
{
    "yamlContent": "apiVersion: v1\nkind: training\n..."
}
```

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| yamlContent | string | 是 | Kubernetes Job YAML 配置 |

**支持的 Job 类型:**
- `training` - 训练任务
- `inference` - 推理服务
- `notebook` - Notebook 任务
- `compute` - 计算任务

**响应 (201):**
```json
{
    "jobId": "training-job-abc123",
    "name": "training-job",
    "kind": "training",
    "status": "pending",
    "createdAt": "2024-01-01T00:00:00",
    "message": "任务已提交至资源池"
}
```

### POST /api/v1/jobs/batch

批量创建任务。

**请求头:**
```
Content-Type: application/json
```

**请求体:**
```json
{
    "yamlContents": [
        "apiVersion: v1\nkind: training\n...",
        "apiVersion: v1\nkind: inference\n..."
    ]
}
```

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| yamlContents | array[string] | 是 | YAML 配置数组 |

**响应 (201):**
```json
{
    "success": [
        {"jobId": "job-1", "name": "training-1"},
        {"jobId": "job-2", "name": "inference-1"}
    ],
    "failed": [
        {"index": 2, "error": "Unsupported kind: unknown"}
    ]
}
```

### GET /api/v1/jobs

获取任务列表（支持分页和过滤）。

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| kind | string | 否 | 任务类型过滤 (training/inference/notebook/compute) |
| pool | string | 否 | 资源池名称过滤 |
| status | string | 否 | 状态过滤 (Pending/Running/Failed/ContainerCreating 等) |
| namespace | string | 否 | 命名空间过滤 |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 20，最大 100 |

**响应 (200):**

返回 Pod 级别数据，与 CLI `gpuctl get jobs` 输出一致。

```json
{
    "total": 5,
    "items": [
        {
            "jobId": "new-test-inference-job-854c6c5cd-76ztc",
            "name": "new-test",
            "namespace": "default",
            "kind": "inference",
            "status": "Failed",
            "ready": "0/1",
            "node": "leon-host",
            "ip": "10.42.0.43",
            "age": "13h"
        }
    ]
}
```

### GET /api/v1/jobs/{jobId}

获取任务详情，与 CLI `describe job --json` 输出一致。支持按控制器名称或 Pod 名称查询。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| jobId | string | 任务 ID（控制器名或 Pod 名均可） |

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| namespace | string | 否 | 命名空间，不指定时搜索所有 gpuctl 命名空间 |

**响应 (200):**
```json
{
    "job_id": "new-test-notebook-job-0",
    "name": "new-test-notebook-job-0",
    "namespace": "new-test",
    "kind": "notebook",
    "resource_type": "StatefulSet",
    "status": "Running",
    "age": "25m",
    "started": "2026-03-01T03:30:39+00:00",
    "completed": null,
    "priority": "medium",
    "pool": "default",
    "resources": {
        "cpu": "1",
        "memory": "2Gi",
        "gpu": 0
    },
    "metrics": {},
    "yaml_content": {
        "kind": "notebook",
        "version": "v0.1",
        "job": {
            "name": "new-test-notebook-job",
            "namespace": "new-test",
            "priority": "medium",
            "description": ""
        },
        "environment": {
            "image": "jupyter/base-notebook:latest",
            "command": []
        },
        "service": {
            "port": 8888
        },
        "resources": {
            "pool": "default",
            "gpu": 0,
            "cpu": 1,
            "memory": "2Gi",
            "gpuShare": "2Gi"
        }
    },
    "events": [
        {
            "age": "24m",
            "type": "Normal",
            "reason": "Pulled",
            "from": "kubelet",
            "object": "Pod/new-test-notebook-job-0",
            "message": "Container image already present on machine"
        },
        {
            "age": "24m",
            "type": "Normal",
            "reason": "Started",
            "from": "kubelet",
            "object": "Pod/new-test-notebook-job-0",
            "message": "Started container notebook"
        }
    ],
    "access_methods": {
        "pod_ip_access": {
            "pod_ip": "10.42.0.49",
            "port": 8888,
            "url": "http://10.42.0.49:8888"
        },
        "node_port_access": {
            "node_ip": "192.168.1.100",
            "node_port": 30001,
            "url": "http://192.168.1.100:30001"
        }
    }
}
```

> **说明：**
> - `resource_type`：实际 Kubernetes 资源类型（`Pod`、`Job`、`Deployment`、`StatefulSet`）
> - `yaml_content`：从 Kubernetes 资源反映射回的 gpuctl YAML 结构（dict 格式）
> - `events`：最近 10 条 Kubernetes 事件，按时间倒序排列
> - `access_methods`：仅 `inference`、`compute`、`notebook` 类型返回此字段；`training` 类型为 `null`

### DELETE /api/v1/jobs/{jobId}

删除任务。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| jobId | string | 任务 ID |

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| force | boolean | 否 | 是否强制删除，默认 false |

**响应 (200):**
```json
{
    "jobId": "training-job-abc123",
    "status": "terminating",
    "message": "任务删除指令已下发"
}
```

### GET /api/v1/jobs/{jobId}/logs

获取任务日志（一次性拉取）。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| jobId | string | 任务 ID |

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| tail | int | 否 | 返回最近 N 行日志，默认 100 |
| pod | string | 否 | 指定 Pod 名称（多 Pod 任务时使用） |

**响应 (200):**
```json
{
    "logs": [
        "2024-01-01 00:00:00 Starting training...",
        "2024-01-01 00:00:01 Loading dataset...",
        "2024-01-01 00:00:05 Training started..."
    ],
    "lastTimestamp": "2024-01-01T00:05:00"
}
```

### WS /api/v1/jobs/{jobId}/logs/ws

WebSocket 实时日志流。连接后服务端持续推送最新日志，每次推送格式为 JSON。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| jobId | string | 任务 ID |

**推送消息格式:**
```json
{"type": "log", "data": "2024-01-01 00:00:10 Step 100/1000 loss=0.32"}
```

> 使用 `Ctrl+C` 或关闭 WebSocket 连接停止推送。

---

## 资源池 API

Base Path: `/api/v1/pools`

### GET /api/v1/pools

获取资源池列表。

**响应 (200):**
```json
[
    {
        "name": "default",
        "description": "默认资源池",
        "gpuTotal": 16,
        "gpuUsed": 8,
        "gpuFree": 8,
        "gpuType": ["A100", "H100"],
        "status": "active"
    },
    {
        "name": "gpu-pool",
        "description": "GPU 资源池",
        "gpuTotal": 32,
        "gpuUsed": 16,
        "gpuFree": 16,
        "gpuType": ["A100"],
        "status": "active"
    }
]
```

### GET /api/v1/pools/{poolName}

获取资源池详情。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| poolName | string | 资源池名称 |

**响应 (200):**
```json
{
    "name": "default",
    "description": "default resource pool",
    "nodes": ["node-1", "node-2"],
    "gpu_total": 16,
    "gpu_used": 8,
    "gpu_free": 8,
    "gpu_types": ["A100", "H100"],
    "status": "active"
}
```

### POST /api/v1/pools

创建资源池。

**请求头:**
```
Content-Type: application/json
```

**请求体:**
```json
{
    "name": "new-pool",
    "description": "新的资源池",
    "nodes": ["node-1", "node-2"],
    "gpuType": ["A100", "H100"],
    "quota": {
        "maxJobs": 10,
        "maxGpuPerJob": 4
    }
}
```

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| name | string | 是 | 资源池名称 |
| description | string | 否 | 资源池描述 |
| nodes | array[string] | 否 | 节点列表 |
| gpuType | array[string] | 否 | GPU 类型列表 |
| quota | object | 否 | 配额配置 |

**响应 (201):**
```json
{
    "name": "new-pool",
    "status": "created",
    "message": "资源池创建成功"
}
```

### DELETE /api/v1/pools/{poolName}

删除资源池。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| poolName | string | 资源池名称 |

**响应 (200):**
```json
{
    "name": "new-pool",
    "status": "deleted",
    "message": "资源池删除成功"
}
```

---

## 节点 API

Base Path: `/api/v1/nodes`

### GET /api/v1/nodes

获取节点列表（支持分页和过滤）。

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| pool | string | 否 | 资源池名称过滤 |
| gpuType | string | 否 | GPU 类型过滤 |
| status | string | 否 | 节点状态过滤（active / not_ready） |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 20，最大 100 |

**响应 (200):**
```json
{
    "total": 4,
    "items": [
        {
            "nodeName": "node-1",
            "status": "active",
            "gpuTotal": 8,
            "gpuUsed": 4,
            "gpuFree": 4,
            "boundPools": ["default"],
            "cpu": "unknown",
            "memory": "unknown",
            "gpuType": "A100",
            "createdAt": null
        }
    ]
}
```

> **说明：** `status` 取值为 `"active"`（节点就绪）或 `"not_ready"`（节点未就绪）。`cpu`、`memory` 当前返回 `"unknown"`（未从 Kubernetes 节点容量映射）。

### GET /api/v1/nodes/{nodeName}

获取节点详情。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| nodeName | string | 节点名称 |

**响应 (200):**
```json
{
    "nodeName": "node-1",
    "status": "active",
    "resources": {
        "cpuTotal": 0,
        "cpuUsed": 0,
        "memoryTotal": "0",
        "memoryUsed": "0",
        "gpuTotal": 8,
        "gpuUsed": 4,
        "gpuFree": 4
    },
    "labels": [
        {"key": "gpu-type", "value": "A100"},
        {"key": "g8s.host/pool", "value": "default"}
    ],
    "boundPools": ["default"],
    "createdAt": null,
    "lastUpdatedAt": null
}
```

> **说明：** `status` 取值为 `"active"`（节点就绪）或 `"not_ready"`（节点未就绪）。`resources` 中 `cpuTotal`/`cpuUsed`/`memoryTotal`/`memoryUsed` 当前均为占位值。

### GET /api/v1/nodes/gpu-detail

获取所有节点 GPU 详情。

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 20，最大 100 |

**响应 (200):**
```json
{
    "total": 4,
    "items": [
        {
            "nodeName": "node-1",
            "gpuCount": 8,
            "gpus": [
                {
                    "gpuId": "gpu-0",
                    "type": "A100",
                    "status": "free",
                    "utilization": 0.0,
                    "memoryUsage": "0Gi/0Gi"
                }
            ]
        }
    ]
}
```

### POST /api/v1/nodes/{nodeName}/pools

节点加入资源池。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| nodeName | string | 节点名称 |

**请求头:**
```
Content-Type: application/json
```

**请求体:**
```json
{
    "pool": "default"
}
```

**响应 (200):**
```json
{
    "node": "node-1",
    "pool": "default",
    "message": "节点已成功添加到资源池"
}
```

### DELETE /api/v1/nodes/{nodeName}/pools/{poolName}

节点离开资源池。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| nodeName | string | 节点名称 |
| poolName | string | 资源池名称 |

**响应 (200):**
```json
{
    "node": "node-1",
    "pool": "default",
    "message": "节点已成功从资源池移除"
}
```

### GET /api/v1/nodes/{nodeName}/labels

获取节点标签。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| nodeName | string | 节点名称 |

**响应 (200):**
```json
{
    "node": "node-1",
    "labels": {
        "gpu-type": "A100",
        "g8s.host/pool": "default"
    }
}
```

---

## 标签 API

Base Path: `/api/v1/nodes`

### POST /api/v1/nodes/{nodeName}/labels

给节点添加标签。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| nodeName | string | 节点名称 |

**请求头:**
```
Content-Type: application/json
```

**请求体:**
```json
{
    "key": "gpu-type",
    "value": "A100",
    "overwrite": false
}
```

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| key | string | 是 | 标签键 |
| value | string | 是 | 标签值 |
| overwrite | boolean | 否 | 是否覆盖已存在的标签 |

**响应 (200):**
```json
{
    "nodeName": "node-1",
    "label": {
        "gpu-type": "A100"
    },
    "message": "标签添加成功"
}
```

### POST /api/v1/nodes/labels/batch

批量添加节点标签。

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| nodeNames | array[string] | 是 | 节点名称列表（重复参数传递） |
| key | string | 是 | 标签键 |
| value | string | 是 | 标签值 |
| overwrite | boolean | 否 | 是否覆盖，默认 false |

**示例:**
```
POST /api/v1/nodes/labels/batch?nodeNames=node-1&nodeNames=node-2&key=gpu-type&value=A100&overwrite=true
```

**响应 (200):**
```json
{
    "success": ["node-1", "node-2"],
    "failed": [],
    "message": "批量标记节点 Label 完成"
}
```

失败时 `failed` 数组元素格式：`{"nodeName": "节点名", "error": "错误信息"}`

### GET /api/v1/nodes/{nodeName}/labels/{key}

获取节点特定标签。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| nodeName | string | 节点名称 |
| key | string | 标签键 |

**响应 (200):**
```json
{
    "nodeName": "node-1",
    "label": {
        "key": "gpu-type",
        "value": "A100",
        "createdAt": "2024-01-01T00:00:00",
        "lastUpdatedAt": "2024-01-01T00:00:00"
    }
}
```

### GET /api/v1/labels

获取所有节点标签概览（按标签键聚合，返回每个键对应的所有取值）。

**响应 (200):**
```json
{
    "gpu-type": ["A100", "H100"],
    "g8s.host/pool": ["default", "gpu-pool"]
}
```

### GET /api/v1/nodes/labels

查询所有节点的指定标签（需提供 key 查询参数）。

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| key | string | 是 | 要查询的标签键 |
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 20，最大 100 |

**响应 (200):**
```json
{
    "total": 4,
    "items": [
        {
            "nodeName": "node-1",
            "labelKey": "gpu-type",
            "labelValue": "A100"
        }
    ]
}
```

### GET /api/v1/nodes/labels/all

获取所有节点的 GPU 相关标签及绑定资源池。

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页数量，默认 20，最大 100 |

**响应 (200):**
```json
{
    "total": 8,
    "items": [
        {
            "nodeName": "node-1",
            "gpuLabels": [
                {"key": "nvidia.com/gpu-type", "value": "A100"}
            ],
            "boundPools": ["default"]
        }
    ]
}
```

### DELETE /api/v1/nodes/{nodeName}/labels/{key}

删除节点标签。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| nodeName | string | 节点名称 |
| key | string | 标签键 |

**响应 (200):**
```json
{
    "node": "node-1",
    "label": "gpu-type",
    "message": "标签删除成功"
}
```

### PUT /api/v1/nodes/{nodeName}/labels/{key}

更新节点标签。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| nodeName | string | 节点名称 |
| key | string | 标签键 |

**请求体:**
```json
{
    "value": "H100"
}
```

**响应 (200):**
```json
{
    "node": "node-1",
    "label": "gpu-type=H100",
    "message": "标签更新成功"
}
```

---

## 配额 API

Base Path: `/api/v1/quotas`

### POST /api/v1/quotas

创建配额（通过 YAML 配置）。

**请求头:**
```
Content-Type: application/json
```

**请求体:**
```json
{
    "yamlContent": "kind: quota\nversion: v0.1\nquota:\n  name: default-quota\n  description: 默认配额\nnamespace:\n  team-a:\n    cpu: 10\n    memory: 20Gi\n    gpu: 4"
}
```

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| yamlContent | string | 是 | 配额 YAML 配置 |

**响应 (201):**
```json
{
    "message": "配额创建成功",
    "name": "default-quota",
    "created": [
        {
            "name": "default-quota",
            "namespace": "team-a",
            "cpu": "10",
            "memory": "20Gi",
            "gpu": "4",
            "status": "created"
        }
    ]
}
```

### GET /api/v1/quotas

获取配额列表。支持 `namespace` 查询参数过滤特定命名空间，若指定则直接返回该命名空间配额对象。

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| namespace | string | 否 | 命名空间过滤，指定时返回单个配额对象 |

**响应 (200) - 列表:**
```json
{
    "total": 2,
    "items": [
        {
            "name": "default",
            "namespace": "default",
            "hard": {
                "cpu": "100",
                "memory": "200Gi",
                "nvidia.com/gpu": "16",
                "pods": "unlimited"
            },
            "used": {
                "cpu": "50",
                "memory": "100Gi",
                "nvidia.com/gpu": "8"
            },
            "status": "Active"
        }
    ]
}
```

### GET /api/v1/quotas/{namespaceName}

获取命名空间配额详情（含使用量）。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| namespaceName | string | 命名空间名称 |

**响应 (200):**
```json
{
    "name": "default",
    "namespace": "default",
    "hard": {
        "cpu": "100",
        "memory": "200Gi",
        "nvidia.com/gpu": "16",
        "pods": "unlimited"
    },
    "used": {
        "cpu": "50",
        "memory": "100Gi",
        "nvidia.com/gpu": "8"
    },
    "status": "Active"
}
```

### DELETE /api/v1/quotas/{namespaceName}

删除命名空间配额。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| namespaceName | string | 命名空间名称 |

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| force | boolean | 否 | 是否强制删除，默认 false |

**响应 (200):**
```json
{
    "jobId": "default",
    "status": "deleted",
    "message": "配额删除成功"
}
```

注意：响应中的 `jobId` 字段表示被删除的命名空间名称。

---

## 命名空间 API

Base Path: `/api/v1/namespaces`

> 仅管理由 gpuctl 创建的命名空间（带有 `g8s.host/namespace=true` 标签），同时包含 `default` 命名空间。

### GET /api/v1/namespaces

获取 gpuctl 管理的命名空间列表。

**响应 (200):**
```json
{
    "total": 3,
    "items": [
        {
            "name": "team-a",
            "status": "Active",
            "age": "2026-01-03 23:34:16+00:00"
        },
        {
            "name": "team-b",
            "status": "Active",
            "age": "2026-01-08 00:20:56+00:00"
        },
        {
            "name": "default",
            "status": "Active",
            "age": "2025-12-01 00:00:00+00:00"
        }
    ]
}
```

### GET /api/v1/namespaces/{namespaceName}

获取命名空间详情，含配额信息。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| namespaceName | string | 命名空间名称 |

**响应 (200):**
```json
{
    "name": "team-a",
    "status": "Active",
    "age": "2026-01-03 23:34:16+00:00",
    "labels": {
        "g8s.host/namespace": "true"
    },
    "quota": {
        "name": "default-quota",
        "namespace": "team-a",
        "hard": {
            "cpu": "10",
            "memory": "20Gi",
            "nvidia.com/gpu": "4",
            "pods": "unlimited"
        },
        "used": {
            "cpu": "2",
            "memory": "4Gi",
            "nvidia.com/gpu": "1"
        },
        "status": "Active"
    }
}
```

> `quota` 字段在该命名空间未配置配额时为 `null`。

### DELETE /api/v1/namespaces/{namespaceName}

删除命名空间（仅限由 gpuctl 创建的命名空间）。

**路径参数:**

| 参数 | 类型 | 描述 |
|------|------|------|
| namespaceName | string | 命名空间名称 |

**查询参数:**

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| force | boolean | 否 | 是否强制删除，默认 false |

**响应 (200):**
```json
{
    "name": "team-a",
    "status": "deleted",
    "message": "命名空间 team-a 已成功删除"
}
```

**错误响应 (403):**
```json
{
    "error": "Namespace 'kube-system' was not created by gpuctl and cannot be deleted via this API"
}
```

---

## 错误响应

所有 API 错误返回统一格式：

### 400 Bad Request
```json
{
    "error": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
    "error": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
    "error": "Internal server error"
}
```

---

## 数据模型参考

### JobCreateRequest
```python
{
    "yamlContent": str        # YAML 配置内容
}
```

### BatchCreateRequest
```python
{
    "yamlContents": list[str]  # YAML 配置数组
}
```

### JobResponse
```python
{
    "jobId": str,              # 任务 ID
    "name": str,               # 任务名称
    "kind": str,               # 任务类型
    "status": str,             # 任务状态
    "createdAt": datetime,     # 创建时间（可选）
    "message": str             # 提示信息（可选）
}
```

### JobItem
```python
{
    "jobId": str,              # Pod 名称
    "name": str,               # 简化名称
    "namespace": str,          # 命名空间
    "kind": str,               # 任务类型
    "status": str,             # 状态
    "ready": str,              # 就绪状态（如 "1/1"）
    "node": str,               # 所在节点
    "ip": str,                 # Pod IP
    "age": str                 # 运行时长
}
```

### JobListResponse
```python
{
    "total": int,              # 总数
    "items": list[JobItem]     # 任务列表
}
```

### JobDetailResponse
```python
{
    "job_id": str,             # 任务 ID
    "name": str,               # 任务名称
    "namespace": str,          # 命名空间
    "kind": str,               # 任务类型
    "resource_type": str,      # K8s 资源类型（Pod/Job/Deployment/StatefulSet）
    "status": str,             # 状态
    "age": str,                # 运行时长
    "started": str | None,     # 启动时间
    "completed": str | None,   # 完成时间
    "priority": str,           # 优先级，默认 "medium"
    "pool": str,               # 资源池，默认 "default"
    "resources": dict,         # 资源配置（cpu/memory/gpu）
    "metrics": dict,           # 监控指标
    "yaml_content": dict,      # 反映射的 gpuctl YAML 配置
    "events": list[dict],      # 最近事件列表
    "access_methods": dict | None  # 访问方式（仅服务类型任务）
}
```

### BatchCreateResponse
```python
{
    "success": list[dict],     # 成功列表 [{"jobId": str, "name": str}]
    "failed": list[dict]       # 失败列表 [{"index": int, "error": str}]
}
```

### DeleteResponse
```python
{
    "jobId": str,              # 被删除资源的标识
    "status": str,             # 状态
    "message": str             # 提示信息
}
```

### LogResponse
```python
{
    "logs": list[str],         # 日志行列表
    "lastTimestamp": datetime   # 最后一条日志时间戳（可选）
}
```

### PoolResponse
```python
{
    "name": str,               # 资源池名称
    "description": str | None, # 描述
    "gpuTotal": int,           # GPU 总数
    "gpuUsed": int,            # 已使用 GPU 数
    "gpuFree": int,            # 空闲 GPU 数
    "gpuType": list[str],      # GPU 类型列表
    "status": str              # 状态
}
```

### PoolCreateRequest
```python
{
    "name": str,               # 资源池名称
    "description": str | None, # 描述
    "nodes": list[str],        # 节点列表
    "gpuType": list[str] | None,  # GPU 类型
    "quota": dict | None       # 配额配置
}
```

### NodeDetailResponse
```python
{
    "nodeName": str,           # 节点名称
    "status": str,             # 状态（active / not_ready）
    "resources": dict,         # 资源详情（cpuTotal/cpuUsed/memoryTotal/memoryUsed/gpuTotal/gpuUsed/gpuFree）
    "labels": list[dict],      # 标签列表 [{"key": str, "value": str}]
    "boundPools": list[str],   # 绑定的资源池
    "createdAt": datetime | None,     # 创建时间
    "lastUpdatedAt": datetime | None  # 最后更新时间
}
```

### LabelRequest
```python
{
    "key": str,                # 标签键
    "value": str,              # 标签值
    "overwrite": bool          # 是否覆盖，默认 false
}
```

### LabelResponse
```python
{
    "nodeName": str,           # 节点名称
    "label": dict,             # 标签键值对
    "message": str             # 提示信息
}
```
