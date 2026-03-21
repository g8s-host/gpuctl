# REST API Reference

gpuctl provides a complete RESTful API built on FastAPI. Once started, you can use the Swagger UI for interactive exploration.

## Basic Information

| Item | Value |
|------|-------|
| Base URL | `http://localhost:8000` |
| API Prefix | `/api/v1` |
| Response Format | JSON |
| Error Format | `{"error": "error message"}` |
| Swagger UI | `http://localhost:8000/docs` |

## Starting the API Server

```bash
python server/main.py
```

---

## Base Endpoints

### `GET /`

Returns basic service information.

```json
{
    "message": "GPU Control API",
    "version": "1.0.0"
}
```

### `GET /health`

Health check endpoint.

```json
{
    "status": "healthy",
    "timestamp": "2026-03-01T00:00:00"
}
```

---

## Job API

Base Path: `/api/v1/jobs`

### `POST /api/v1/jobs` — Create Job

**Request body:**
```json
{
    "yamlContent": "kind: training\nversion: v0.1\njob:\n  name: my-job\n..."
}
```

**Response (201):**
```json
{
    "jobId": "my-job",
    "name": "my-job",
    "kind": "training",
    "status": "pending",
    "createdAt": "2024-01-01T00:00:00",
    "message": "Job submitted to resource pool"
}
```

---

### `POST /api/v1/jobs/batch` — Batch Create Jobs

**Request body:**
```json
{
    "yamlContents": [
        "kind: training\nversion: v0.1\n...",
        "kind: inference\nversion: v0.1\n..."
    ]
}
```

**Response (201):**
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

### `GET /api/v1/jobs` — List Jobs

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `kind` | string | Filter by job type: training / inference / notebook / compute |
| `pool` | string | Filter by resource pool name |
| `status` | string | Filter by status |
| `namespace` | string | Filter by namespace |
| `page` | int | Page number, default 1 |
| `pageSize` | int | Items per page, default 20, max 100 |

**Response (200):**
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

### `GET /api/v1/jobs/{jobId}` — Get Job Details

**Path parameter:** `jobId` — accepts either the job name or Pod name

**Query parameter:** `namespace` — optional; searches all gpuctl namespaces if omitted

**Response (200):**
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
    - `resource_type`: actual K8s resource type (Pod / Job / Deployment / StatefulSet)
    - `yaml_content`: gpuctl YAML structure reverse-mapped from the K8s resource
    - `access_methods`: only returned for inference / compute / notebook; null for training

---

### `DELETE /api/v1/jobs/{jobId}` — Delete Job

**Query parameter:** `force=true` — force delete

**Response (200):**
```json
{
    "jobId": "my-job",
    "status": "terminating",
    "message": "Job deletion command issued"
}
```

---

### `GET /api/v1/jobs/{jobId}/logs` — Get Logs

**Query parameters:**

| Parameter | Description |
|-----------|-------------|
| `tail` | Return last N lines, default 100 |
| `pod` | Specify Pod name (for multi-Pod jobs) |

**Response (200):**
```json
{
    "logs": ["2024-01-01 00:00:00 Starting...", "..."],
    "lastTimestamp": "2024-01-01T00:05:00"
}
```

---

### `WS /api/v1/jobs/{jobId}/logs/ws` — WebSocket Streaming Logs

Streams logs continuously after connection. Each message format:

```json
{"type": "log", "data": "2024-01-01 00:00:10 Step 100/1000 loss=0.32"}
```

---

## Resource Pool API

Base Path: `/api/v1/pools`

| Method | Path | Function |
|--------|------|----------|
| GET | `/api/v1/pools` | List resource pools |
| GET | `/api/v1/pools/{poolName}` | Get pool details |
| POST | `/api/v1/pools` | Create resource pool |
| DELETE | `/api/v1/pools/{poolName}` | Delete resource pool |

---

## Node API

Base Path: `/api/v1/nodes`

| Method | Path | Function |
|--------|------|----------|
| GET | `/api/v1/nodes` | List nodes (supports pool/gpuType/status filters) |
| GET | `/api/v1/nodes/{nodeName}` | Node details (labels, resource usage) |
| GET | `/api/v1/nodes/gpu-detail` | GPU details for all nodes |
| POST | `/api/v1/nodes/{nodeName}/pools` | Add node to a resource pool |
| DELETE | `/api/v1/nodes/{nodeName}/pools/{poolName}` | Remove node from a pool |
| GET | `/api/v1/nodes/{nodeName}/labels` | Get all labels on a node |

---

## Label API

| Method | Path | Function |
|--------|------|----------|
| POST | `/api/v1/nodes/{nodeName}/labels` | Add label to a node |
| POST | `/api/v1/nodes/labels/batch` | Batch add node labels |
| GET | `/api/v1/nodes/{nodeName}/labels/{key}` | Get a specific label on a node |
| PUT | `/api/v1/nodes/{nodeName}/labels/{key}` | Update a node label |
| DELETE | `/api/v1/nodes/{nodeName}/labels/{key}` | Delete a node label |
| GET | `/api/v1/labels` | Overview of all node labels (aggregated by key) |
| GET | `/api/v1/nodes/labels` | Query a specific label across all nodes (requires `key` param) |
| GET | `/api/v1/nodes/labels/all` | GPU-related labels and pool bindings for all nodes |

---

## Quota API

Base Path: `/api/v1/quotas`

| Method | Path | Function |
|--------|------|----------|
| POST | `/api/v1/quotas` | Create quota (YAML format) |
| GET | `/api/v1/quotas` | List quotas (supports namespace filter) |
| GET | `/api/v1/quotas/{namespaceName}` | Get namespace quota details (with utilization) |
| DELETE | `/api/v1/quotas/{namespaceName}` | Delete namespace quota |

---

## Namespace API

Base Path: `/api/v1/namespaces`

!!! info "Manages only gpuctl-created namespaces"
    Namespaces with the `runwhere.ai/namespace=true` label, and the `default` namespace.

| Method | Path | Function |
|--------|------|----------|
| GET | `/api/v1/namespaces` | List namespaces |
| GET | `/api/v1/namespaces/{namespaceName}` | Get namespace details (including quota info) |
| DELETE | `/api/v1/namespaces/{namespaceName}` | Delete namespace |

---

## Error Responses

All APIs use a unified error format:

| HTTP Status | Meaning |
|-------------|---------|
| 400 | Invalid request parameters (e.g. malformed YAML) |
| 404 | Resource not found |
| 409 | Resource conflict (e.g. label already exists and overwrite not set) |
| 500 | Internal server error (e.g. K8s cluster issue) |

```json
{
    "error": "specific error message"
}
```
