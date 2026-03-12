# Notebook 交互式开发

Notebook 任务（`kind: notebook`）提供 JupyterLab 交互式开发环境，适合代码调试、数据探索和模型原型验证。底层对应 Kubernetes **StatefulSet + NodePort Service**，保证存储状态持久化。

## YAML 完整字段

```yaml
kind: notebook
version: v0.1

job:
  name: <环境名称>
  priority: medium
  description: "描述"

environment:
  image: <包含 JupyterLab 的镜像>
  command: [...]    # JupyterLab 启动命令

service:
  port: 8888        # JupyterLab 默认端口

resources:
  pool: dev-pool    # 建议使用开发专用资源池
  gpu: 1
  gpu-type: A10-24G # 可选，调试无需高端 GPU
  cpu: 8
  memory: 32Gi

storage:
  workdirs:
    - path: /home/jovyan/work  # 代码工作目录
    - path: /models            # 模型缓存目录
```

---

## 场景：启动 AI 开发 Notebook

部署包含 PyTorch 2.x、常用数据科学库及 GPU 支持的 JupyterLab 环境：

```yaml title="dev-notebook.yaml"
kind: notebook
version: v0.1

job:
  name: ai-dev-notebook
  priority: medium
  description: "AI 开发调试环境（PyTorch + GPU）"

environment:
  image: registry.example.com/jupyter-ai:v1.0
  command:
    - "jupyter-lab"
    - "--ip=0.0.0.0"
    - "--port=8888"
    - "--no-browser"
    - "--allow-root"
    - "--NotebookApp.token=ai-gpuctl-2025"
    - "--NotebookApp.password="

service:
  port: 8888

resources:
  pool: dev-pool
  gpu: 1
  gpu-type: A10-24G
  cpu: 8
  memory: 32Gi

storage:
  workdirs:
    - path: /home/jovyan/work
    - path: /models
    - path: /datasets
```

```bash
# 启动 Notebook 环境
gpuctl create -f dev-notebook.yaml

# 查看状态和访问地址
gpuctl describe job ai-dev-notebook
```

**获取访问地址：**

```
Access Methods:
  Pod IP Access:    http://10.42.0.49:8888
  Node Port Access: http://192.168.1.102:30088
```

在浏览器打开 NodePort 地址，输入 token `ai-gpuctl-2025` 即可进入 JupyterLab。

---

## 使用纯 CPU Notebook

对于数据预处理等不需要 GPU 的场景：

```yaml title="data-prep-notebook.yaml"
kind: notebook
version: v0.1

job:
  name: data-prep-notebook
  priority: low

environment:
  image: jupyter/datascience-notebook:latest
  command:
    - "jupyter-lab"
    - "--ip=0.0.0.0"
    - "--port=8888"
    - "--no-browser"
    - "--allow-root"

service:
  port: 8888

resources:
  pool: default
  gpu: 0        # 纯 CPU，节省 GPU 资源
  cpu: 4
  memory: 16Gi

storage:
  workdirs:
    - path: /home/jovyan/work
    - path: /data
```

---

## 查看 Notebook 日志

```bash
# 查看启动日志，确认 JupyterLab 已就绪
gpuctl logs ai-dev-notebook

# 实时跟踪日志
gpuctl logs ai-dev-notebook -f
```

## 删除 Notebook 环境

```bash
gpuctl delete job ai-dev-notebook
```

!!! tip "代码持久化"
    Notebook 环境通过 `storage.workdirs` 将宿主机目录挂载到容器内，删除 Notebook Pod 后，挂载目录中的代码和数据**不会丢失**，下次创建时重新挂载即可恢复工作状态。

!!! warning "StatefulSet 特性"
    Notebook 使用 StatefulSet 管理，Pod 名称为 `{name}-0`，如 `ai-dev-notebook-0`。查看日志时可以直接用任务名，平台会自动定位 Pod。
