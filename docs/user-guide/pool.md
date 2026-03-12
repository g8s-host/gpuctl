# 资源池管理

资源池（Pool）是 gpuctl 的核心资源隔离机制，将集群节点划分为多个逻辑资源池，实现训练/推理/实验/开发等不同场景的资源隔离，避免任务间 GPU 资源争抢。

## 工作原理

```
集群节点
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   node-1    │  │   node-2    │  │   node-3    │  │   node-4    │
│  A100×8     │  │  A100×8     │  │   A10×4     │  │   A10×4     │
│ pool=train  │  │ pool=train  │  │pool=infer   │  │  pool=dev   │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘

        训练资源池                推理资源池         开发资源池
     (training-pool)          (inference-pool)    (dev-pool)
```

节点通过 Kubernetes Label `g8s.host/pool=<pool-name>` 绑定到资源池，任务在提交时通过 `resources.pool` 字段指定目标资源池，平台使用 `nodeSelector` 将 Pod 调度到池内节点。

---

## 创建资源池

### 资源池 YAML 格式

```yaml title="training-pool.yaml"
kind: pool
version: v0.1

pool:
  name: training-pool
  description: "训练任务专用资源池"

nodes:
  node-1:              # 节点主机名（与 kubectl get nodes 一致）
    gpu-type: A100-100G
  node-2:
    gpu-type: A100-100G
```

```bash
gpuctl create -f training-pool.yaml
```

### 多资源池同时创建

在一个 YAML 文件中使用 `---` 分隔多个资源池定义（不支持），或分别创建：

```bash
gpuctl create -f training-pool.yaml
gpuctl create -f inference-pool.yaml
gpuctl create -f dev-pool.yaml
```

---

## 典型资源池规划方案

### 推荐的四池划分

```yaml title="training-pool.yaml"
kind: pool
version: v0.1
pool:
  name: training-pool
  description: "大模型训练专用（高端 GPU）"
nodes:
  gpu-node-1:
    gpu-type: A100-100G
  gpu-node-2:
    gpu-type: A100-100G
```

```yaml title="inference-pool.yaml"
kind: pool
version: v0.1
pool:
  name: inference-pool
  description: "推理服务专用（中端 GPU）"
nodes:
  gpu-node-3:
    gpu-type: A10-24G
  gpu-node-4:
    gpu-type: A10-24G
```

```yaml title="dev-pool.yaml"
kind: pool
version: v0.1
pool:
  name: dev-pool
  description: "Notebook 开发调试（低端 GPU）"
nodes:
  gpu-node-5:
    gpu-type: RTX4090-24G
```

```yaml title="compute-pool.yaml"
kind: pool
version: v0.1
pool:
  name: compute-pool
  description: "CPU 计算服务（无 GPU 节点）"
nodes:
  cpu-node-1:
    gpu-type: ""
  cpu-node-2:
    gpu-type: ""
```

---

## 查询资源池

```bash
# 列出所有资源池
gpuctl get pools
```

输出示例：

```
POOL NAME        STATUS   GPU TOTAL  GPU USED  GPU FREE  NODE COUNT
training-pool    active   16         12        4         2
inference-pool   active   8          4         4         2
dev-pool         active   4          2         2         1
default          active   0          0         0         0
```

```bash
# 查看资源池详情（含节点列表和运行中任务）
gpuctl describe pool training-pool
```

---

## 节点标签管理

资源池通过节点标签实现，你也可以直接通过标签命令管理节点与资源池的绑定：

```bash
# 将 node-6 加入 training-pool
gpuctl label node node-6 g8s.host/pool=training-pool

# 覆盖已有的 pool 标签
gpuctl label node node-6 g8s.host/pool=inference-pool --overwrite

# 查看节点的 pool 标签
gpuctl get labels node-6 --key=g8s.host/pool

# 标记 GPU 类型
gpuctl label node node-6 g8s.host/gpu-type=A100-100G
```

!!! warning "标签键规范"
    gpuctl 管理的标签键**必须以 `g8s.host/` 开头**，以避免与其他系统的标签冲突。

---

## 在任务中使用资源池

在 YAML 的 `resources.pool` 字段指定目标资源池：

```yaml
resources:
  pool: training-pool   # 必须是已创建的资源池名
  gpu: 4
  cpu: 32
  memory: 128Gi
```

```bash
# 查看指定资源池的任务
gpuctl get jobs --pool training-pool
```

---

## 删除资源池

```bash
# 通过 YAML 文件删除
gpuctl delete -f training-pool.yaml

# 或通过名称直接删除
gpuctl delete pool training-pool
```

!!! danger "删除前确认"
    删除资源池会移除节点上的资源池标签绑定，但**不会终止**正在运行的任务。建议先停止池内所有任务，再删除资源池。
