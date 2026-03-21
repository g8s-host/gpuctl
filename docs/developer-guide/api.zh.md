# REST API 参考

gpuctl 提供完整的 RESTful API，基于 FastAPI 构建。启动后可通过 Swagger UI 进行交互式调试。

## 基础信息

| 项目 | 值 |
|------|-----|
| Base URL | `http://localhost:8000` |
| API 前缀 | `/api/v1` |
| 响应格式 | JSON |
| 错误格式 | `{"error": "错误信息"}` |
| Swagger UI | `http://localhost:8000/docs` |

## 启动 API 服务

```bash
python server/main.py
```

---

## 基础接口

### `GET /`

返回服务基本信息。

```json
{
    "message": "GPU Control API",
    "version": "1.0.0"
}
```

### `GET /health`

健康检查接口。

```json
{
    "status": "healthy",
    "timestamp": "2026-03-01T00:00:00"
}
```

---

## 任务 API

Base Path: `/api/v1/jobs`

### `POST /api/v1/jobs` — 创建任务

**请求体：**
```json
{
    "yamlContent": "kind: training\nversion: v0.1\njob:\n  name: my-job\n..."
}
```

**响应 (201)：**
```json
{
    "jobId": "my-job",
    "name": "my-job",
    "kind": "training",
    "status": "pending",
    "createdAt": "2024-01-01T00:00:00",
    "message": "任务已提交至资源池"
}
```

---

### `POST /api/v1/jobs/batch` — 批量创建任务

**请求体：**
```json
{
    "yamlContents": [
        "kind: training\nversion: v0.1\n...",
        "kind: inference\nversion: v0.1\n..."
    ]
}
```

**响应 (201)：**
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

---

### `GET /api/v1/jobs` — 查询任务列表

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `kind` | string | 任务类型过滤：training / inference / notebook / compute |
| `pool` | string | 资源池名称过滤 |
| `status` | string | 状态过滤 |
| `namespace` | string | 命名空间过滤 |
| `page` | int | 页码，默认 1 |
| `pageSize` | int | 每页数量，默认 20，最大 100 |

**响应 (200)：**
```json
{
    "total": 5,
    "items": [
        {
            "jobId": "my-inference-854c6c5cd-76ztc",
            "name": "my-inference",
            "namespace": "default",
            "kind": "inference",
            "status": "Running",
            "ready": "1/1",
            "node": "node-1",
            "ip": "10.42.0.43",
            "age": "2h"
        }
    ]
}
```

---

### `GET /api/v1/jobs/{jobId}` — 查询任务详情

**路径参数：** `jobId` — 任务名称或 Pod 名称均可

**查询参数：** `namespace` — 可选，不指定则搜索所有 gpuctl 命名空间

**响应 (200)：**
```json
{
    "job_id": "my-notebook-job-0",
    "name": "my-notebook-job-0",
    "namespace": "team-alice",
    "kind": "notebook",
    "resource_type": "StatefulSet",
    "status": "Running",
    "age": "25m",
    "started": "2026-03-01T03:30:39+00:00",
    "completed": null,
    "priority": "medium",
    "pool": "dev-pool",
    "resources": { "cpu": "8", "memory": "32Gi", "gpu": 1 },
    "metrics": {},
    "yaml_content": {
        "kind": "notebook",
        "version": "v0.1",
        "job": { "name": "my-notebook-job", "namespace": "team-alice" },
        "environment": { "image": "jupyter/base-notebook:latest", "command": [] },
        "service": { "port": 8888 },
        "resources": { "pool": "dev-pool", "gpu": 1, "cpu": 8, "memory": "32Gi" }
    },
    "events": [
        {
            "age": "24m",
            "type": "Normal",
            "reason": "Started",
            "from": "kubelet",
            "object": "Pod/my-notebook-job-0",
            "message": "Started container notebook"
        }
    ],
    "access_methods": {
        "pod_ip_access": { "pod_ip": "10.42.0.49", "port": 8888, "url": "http://10.42.0.49:8888" },
        "node_port_access": { "node_ip": "192.168.1.100", "node_port": 30001, "url": "http://192.168.1.100:30001" }
    }
}
```

!!! note
    - `resource_type`：实际 K8s 资源类型（Pod / Job / Deployment / StatefulSet）
    - `yaml_content`：从 K8s 资源反映射回的 gpuctl YAML 结构
    - `access_methods`：仅 inference / compute / notebook 返回，training 为 null

---

### `DELETE /api/v1/jobs/{jobId}` — 删除任务

**查询参数：** `force=true` — 强制删除

**响应 (200)：**
```json
{
    "jobId": "my-job",
    "status": "terminating",
    "message": "任务删除指令已下发"
}
```

---

### `GET /api/v1/jobs/{jobId}/logs` — 获取日志

**查询参数：**

| 参数 | 说明 |
|------|------|
| `tail` | 返回最近 N 行，默认 100 |
| `pod` | 指定 Pod 名称（多 Pod 时使用） |

**响应 (200)：**
```json
{
    "logs": ["2024-01-01 00:00:00 Starting...", "..."],
    "lastTimestamp": "2024-01-01T00:05:00"
}
```

---

### `WS /api/v1/jobs/{jobId}/logs/ws` — WebSocket 实时日志

连接后持续推送日志，每条消息格式：

```json
{"type": "log", "data": "2024-01-01 00:00:10 Step 100/1000 loss=0.32"}
```

---

## 资源池 API

Base Path: `/api/v1/pools`

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/v1/pools` | 获取资源池列表 |
| GET | `/api/v1/pools/{poolName}` | 获取资源池详情 |
| POST | `/api/v1/pools` | 创建资源池 |
| DELETE | `/api/v1/pools/{poolName}` | 删除资源池 |

---

## 节点 API

Base Path: `/api/v1/nodes`

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/v1/nodes` | 节点列表（支持 pool/gpuType/status 过滤） |
| GET | `/api/v1/nodes/{nodeName}` | 节点详情（含 Labels、资源使用） |
| GET | `/api/v1/nodes/gpu-detail` | 所有节点 GPU 详细信息 |
| POST | `/api/v1/nodes/{nodeName}/pools` | 节点加入资源池 |
| DELETE | `/api/v1/nodes/{nodeName}/pools/{poolName}` | 节点离开资源池 |
| GET | `/api/v1/nodes/{nodeName}/labels` | 获取节点所有标签 |

---

## 标签 API

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/v1/nodes/{nodeName}/labels` | 给节点添加标签 |
| POST | `/api/v1/nodes/labels/batch` | 批量添加节点标签 |
| GET | `/api/v1/nodes/{nodeName}/labels/{key}` | 获取节点特定标签 |
| PUT | `/api/v1/nodes/{nodeName}/labels/{key}` | 更新节点标签 |
| DELETE | `/api/v1/nodes/{nodeName}/labels/{key}` | 删除节点标签 |
| GET | `/api/v1/labels` | 获取所有节点标签概览（按键聚合） |
| GET | `/api/v1/nodes/labels` | 查询所有节点的指定标签（需 key 参数） |
| GET | `/api/v1/nodes/labels/all` | 所有节点的 GPU 相关标签及绑定资源池 |

---

## 配额 API

Base Path: `/api/v1/quotas`

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/v1/quotas` | 创建配额（YAML 格式） |
| GET | `/api/v1/quotas` | 获取配额列表（支持 namespace 过滤） |
| GET | `/api/v1/quotas/{namespaceName}` | 获取命名空间配额详情（含使用量） |
| DELETE | `/api/v1/quotas/{namespaceName}` | 删除命名空间配额 |

---

## 命名空间 API

Base Path: `/api/v1/namespaces`

!!! info "仅管理 gpuctl 创建的命名空间"
    带有 `runwhere.ai/namespace=true` 标签的命名空间，以及 `default` 命名空间。

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/v1/namespaces` | 获取命名空间列表 |
| GET | `/api/v1/namespaces/{namespaceName}` | 获取命名空间详情（含配额信息） |
| DELETE | `/api/v1/namespaces/{namespaceName}` | 删除命名空间 |

---

## 错误响应

所有 API 使用统一错误格式：

| HTTP 状态码 | 含义 |
|------------|------|
| 400 | 请求参数无效（如 YAML 格式错误） |
| 404 | 资源不存在 |
| 409 | 资源冲突（如标签已存在且未设置 overwrite） |
| 500 | 服务器内部错误（如 K8s 集群异常） |

```json
{
    "error": "具体错误信息"
}
```
