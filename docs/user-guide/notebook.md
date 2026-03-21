# Notebook Interactive Development

Notebook jobs (`kind: notebook`) provide a JupyterLab interactive development environment, ideal for code debugging, data exploration, and model prototyping. They map to a Kubernetes **StatefulSet + NodePort Service** to ensure storage state persistence.

## Full YAML Fields

```yaml
kind: notebook
version: v0.1

job:
  name: <env-name>
  priority: medium
  description: "..."

environment:
  image: <image with JupyterLab>
  command: [...]    # JupyterLab startup command

service:
  port: 8888        # JupyterLab default port

resources:
  pool: dev-pool    # Recommended: use a dedicated dev resource pool
  gpu: 1
  gpu-type: A10-24G # Optional — debugging doesn't need high-end GPUs
  cpu: 8
  memory: 32Gi

storage:
  workdirs:
    - path: /home/jovyan/work  # Code working directory
    - path: /models            # Model cache directory
```

---

## Example: Launch an AI Development Notebook

Deploy a JupyterLab environment with PyTorch 2.x, common data science libraries, and GPU support:

```yaml title="dev-notebook.yaml"
kind: notebook
version: v0.1

job:
  name: ai-dev-notebook
  priority: medium
  description: "AI development environment (PyTorch + GPU)"

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
# Start the Notebook environment
gpuctl create -f dev-notebook.yaml

# Check status and access address
gpuctl describe job ai-dev-notebook
```

**Access address output:**

```
Access Methods:
  Pod IP Access:    http://10.42.0.49:8888
  Node Port Access: http://192.168.1.102:30088
```

Open the NodePort address in a browser and enter token `ai-gpuctl-2025` to access JupyterLab.

---

## CPU-Only Notebook

For data preprocessing and other scenarios that don't require a GPU:

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
  gpu: 0        # CPU-only, preserves GPU resources
  cpu: 4
  memory: 16Gi

storage:
  workdirs:
    - path: /home/jovyan/work
    - path: /data
```

---

## Viewing Notebook Logs

```bash
# View startup logs to confirm JupyterLab is ready
gpuctl logs ai-dev-notebook

# Stream logs in real time
gpuctl logs ai-dev-notebook -f
```

## Deleting a Notebook Environment

```bash
gpuctl delete job ai-dev-notebook
```

!!! tip "Code Persistence"
    The Notebook environment mounts host directories into the container via `storage.workdirs`. Deleting the Notebook Pod does **not** delete data in mounted directories — recreate the Notebook and remount to restore your work state.

!!! warning "StatefulSet Behavior"
    Notebooks use a StatefulSet, so the Pod name is `{name}-0` (e.g. `ai-dev-notebook-0`). You can still use the job name directly with `gpuctl logs` — the platform locates the Pod automatically.
