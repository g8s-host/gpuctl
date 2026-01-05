# gpuctl - AI Computing Power Scheduling Platform

[简体中文](doc/README.zh-CN.md) | [English](README.md)

## Project Introduction

gpuctl is an AI computing power scheduling platform designed for algorithm engineers, aiming to lower the threshold for using GPU computing resources. Through declarative YAML configuration and simple CLI commands, algorithm engineers can efficiently submit and manage AI training and inference tasks without mastering complex knowledge of underlying infrastructure like Kubernetes.

### Core Pain Points Solved

- No need to learn complex Kubernetes concepts (Pod, Deployment, Service, etc.)
- Simplify the installation and configuration of GPU drivers, dependency libraries, and other cumbersome environments
- Provide high-performance, efficient computing execution environment supporting both training and inference scenarios
- Enable direct use of computing resources on existing Kubernetes clusters through declarative commands

## System Architecture

The platform adopts a layered design, exposing a user-friendly abstraction layer while being built on mature Kubernetes and containerization technologies, with an added resource pool management module to support fine-grained resource scheduling.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Algorithm Engineer                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Access Layer                              │
│                     (gpuctl CLI / REST API)                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Abstraction & Conversion Layer                │
│ (Parse YAML → Validate → Convert to K8s resources → Encapsulate │
│                          K8s complexity)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Scheduling & Execution Layer                     │
│ (Implement resource pooling based on Kubernetes and ecosystem,  │
│               allocate GPU resources by pool)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Monitoring & Feedback Layer                    │
│  (Build monitoring system based on Prometheus+Grafana, collect  │
│                     full task runtime data)                     │
└─────────────────────────────────────────────────────────────────┘
```

## Core Features

### 1. Multi-type Task Support

- **Training Tasks**: Support distributed training, integrated with acceleration frameworks like DeepSpeed
- **Inference Services**: Support model deployment with automatic scaling
- **Debugging Tasks**: Provide Jupyter Notebook environment for easy debugging
- **Compute Tasks**: Support for batch compute workloads with various resource configurations

### 2. Resource Pool Management

- Support creation and management of resource pools
- Flexible binding and unbinding of nodes and resource pools
- Resource isolation and quota management at the resource pool level

### 3. Resource Quota Management

- Declarative YAML-based quota configuration
- Set resource limits per namespace (CPU, Memory, GPU)
- View quota usage and consumption rates
- Automatic namespace creation for each namespace

### 4. Declarative Configuration

- Use terminology familiar to algorithm engineers
- Hide underlying infrastructure details
- Support YAML format for task definition

### 5. Rich CLI Commands

- Task lifecycle management
- Node and resource pool management
- Real-time log viewing
- Resource usage monitoring

## Installation

### Prerequisites

- Python 3.8+
- Kubernetes cluster access permissions

### Installation Methods

#### Method 1: Use Binary File (Recommended)

Download the binary file suitable for your system from GitHub Releases:

```bash
# Linux x86_64 architecture
wget https://github.com/g8s-host/gpuctl/releases/latest/download/gpuctl-linux-amd64 -O gpuctl

# macOS x86_64 architecture
curl -L https://github.com/g8s-host/gpuctl/releases/latest/download/gpuctl-macos-amd64 -o gpuctl

chmod +x gpuctl
sudo mv gpuctl /usr/local/bin/
gpuctl --help
```

#### Method 2: Install from Source (Recommended)

1. Clone the repository

```bash
git clone https://github.com/g8s-host/gpuctl.git
cd gpuctl
```

2. Install dependencies and the package

```bash
pip install -e .
```

3. Run gpuctl

```bash
gpuctl --help
```

or

```bash
python main.py --help
```

### Configure Kubernetes Access

Ensure `kubectl` is properly configured and can access the target Kubernetes cluster.

## Quick Start

### 1. Create a Resource Pool

```yaml
# train-pool.yaml
kind: pool
version: v0.1

metadata:
  name: training-pool
  description: "Resource pool dedicated to training tasks"

nodes:
  node1:
    gpu-type: A100-100G
  node2:
    gpu-type: A800-20G
```

```bash
gpuctl create -f train-pool.yaml
```

### 2. Submit a Training Task

```yaml
# training-job.yaml
kind: training
version: v0.1

# Task identification and description (Llama Factory fine-tuning scenario)
job:
  name: qwen2-7b-llamafactory-sft
  priority: "high"
  description: "llama3 inference task"

# Environment and image - integrated with Llama Factory 0.8.0 + DeepSpeed 0.14.0
environment:
  image: registry.example.com/llama-factory-deepspeed:v0.8.0
  imagePullSecret: my-secret
  # Llama Factory fine-tuning core command
  command: ["llama-factory-cli", "train", "--stage", "sft", "--model_name_or_path", "/models/qwen2-7b", "--dataset", "alpaca-qwen", "--dataset_dir", "/datasets", "--output_dir", "/output/qwen2-sft", "--per_device_train_batch_size", "8", "--gradient_accumulation_steps", "4", "--learning_rate", "2e-5", "--deepspeed", "ds_config.json"]
  env:
    - name: NVIDIA_FLASH_ATTENTION
      value: "1"
    - name: LLAMA_FACTORY_CACHE
      value: "/cache/llama-factory"

# Resource requirements declaration (4x A100 cards)
resources:
  pool: training-pool
  gpu: 4
  gpu-type: A100-100G # Optional, if not filled, k8s scheduling is used
  cpu: 32
  memory: 128Gi
  gpu-share: 2Gi

# Data and model configuration
storage:
  workdirs:
    - path: /datasets/alpaca-qwen.json
    - path: /models/qwen2-7b
    - path: /cache/models
    - path: /output/qwen2-sft
    - path: /output/qwen2-sft/checkpoints
```

```bash
gpuctl create -f training-job.yaml
```

### 3. Submit an Inference Task

```yaml
# inference-service.yaml
kind: inference
version: v0.1

# Task identification
job:
  name: llama3-8b-inference
  priority: "medium"
  description: "llama3 inference task"

# Environment and image (integrated with VLLM 0.5.0+)
environment:
  image: vllm/vllm-serving:v0.5.0 # Optimized inference image
  command: ["python", "-m", "vllm.entrypoints.openai.api_server"] # Start command
  args:
    - "--model"
    - "/home/data/models/llama3-8b"
    - "--tensor-parallel-size"
    - "1"
    - "v2"
    - "--max-num-seqs"
    - "256"

# Service configuration
service:
  replicas: 2
  port: 8000
  health_check: /health

# Resource specifications (added pool field)
resources:
  pool: inference-pool # Dedicated inference resource pool, default is default
  gpu: 1
  gpu-type: A100-100G # Optional, if not filled, k8s scheduling is used
  cpu: 8
  memory: 32Gi
  gpu-share: 2Gi

storage:
  workdirs:
    - path: /home/data/ # Mount local storage directory
```

```bash
gpuctl create -f inference-service.yaml
```

### 4. Submit a Notebook Task

```yaml
# notebook-job.yaml
kind: notebook
version: v0.1

job:
  name: data-prep-notebook
  priority: medium
  description: llama3 inference task

environment:
  image: registry.example.com/jupyter-ai:v1.0
  command: ["jupyter-lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=ai-gpuctl-2025", "--NotebookApp.password="]

# Service configuration
service:
  port: 8888

resources:
  pool: dev-pool # Default is default
  gpu: 1
  gpu-type: a10-24g # Optional, if not filled, k8s scheduling is used
  cpu: 8
  memory: 32Gi
  gpu-share: 2Gi

storage:
  workdirs:
    - path: /home/jovyan/work # Code storage directory
```

```bash
gpuctl create -f notebook-job.yaml
```

### 5. Submit a Compute Task

```yaml
# compute-job.yaml
kind: compute
version: v0.1

job:
  name: batch-compute-job
  priority: medium
  description: "Batch compute task"

environment:
  image: registry.example.com/compute:v1.0
  command: ["python", "compute.py"]
  args:
    - "--input"
    - "/data/input"
    - "--output"
    - "/data/output"

resources:
  pool: default
  gpu: 1
  gpu-type: a10-24g
  cpu: 4
  memory: 16Gi
  gpu-share: 2Gi
  pods: 3

storage:
  workdirs:
    - path: /data/input
    - path: /data/output
```

```bash
gpuctl create -f compute-job.yaml
```

### 6. Configure Resource Quota

```yaml
# quota-config.yaml
kind: quota
version: v0.1

metadata:
  name: team-resource-quota
  description: "Team resource quota configuration"

# Namespace resource allocation (automatically creates namespace for each namespace)
namespace:
  elon-musk:
    cpu: 10
    memory: 20Gi
    gpu: 4
  sam-altman:
    cpu: 10
    memory: 20Gi
    gpu: 4
```

```bash
gpuctl create -f quota-config.yaml
```

### 7. Query Task Status

```bash
gpuctl get jobs
```

### 8. View Task Logs

```bash
gpuctl logs qwen2-7b-llamafactory-sft -f
```

## CLI Command Reference

### Task Management

| Command Example | Description |
|---------|---------|
| `gpuctl create -f train-job.yaml` | Submit a training task |
| `gpuctl create -f task1.yaml -f task2.yaml` | Batch submit multiple tasks |
| `gpuctl get jobs` | List all tasks (training/inference) and core metrics |
| `gpuctl get jobs --pool training-pool` | List tasks in a specified resource pool |
| `gpuctl get jobs --type training` | List tasks of a specific type |
| `gpuctl describe job <job-id>` | View detailed task information and resource usage curves |
| `gpuctl logs <job-id> -f` | View real-time task logs, supports keyword filtering |
| `gpuctl delete -f job.yaml` | Delete/stop a task, supports --force for forced deletion |

### Resource Pool Management

| Command Example | Description |
|---------|---------|
| `gpuctl get pools` | List all resource pools and basic information |
| `gpuctl create -f pool.yaml` | Create a new resource pool |
| `gpuctl delete -f pool.yaml` | Delete a resource pool |
| `gpuctl describe pool <pool-name>` | View detailed resource pool information |
| `gpuctl add node <node-name> --pool <pool-name>` | Add nodes to a resource pool |
| `gpuctl remove node <node-name> --pool <pool-name>` | Remove nodes from a resource pool |

### Node Management

| Command Example | Description |
|---------|---------|
| `gpuctl get nodes` | List basic information of all cluster nodes (name, status, total GPUs, bound resource pools) |
| `gpuctl get nodes --pool <pool-name>` | Filter nodes bound to a specific resource pool |
| `gpuctl get nodes --gpu-type <gpu-type>` | Filter nodes with a specific GPU type |
| `gpuctl describe node <node-name>` | View detailed information of a single node (CPU/GPU resources, GPU type/quantity, label list, bound resource pools, K8s node details) |
| `gpuctl label node <node-name> g8s.host/gpu-type=a100-80g` | Mark GPU type label for a specific node (default label key) |
| `gpuctl label node <node-name> <label-key>=<label-value> --overwrite` | Mark a label for a specific node, supports overwriting existing labels with the same key |
| `gpuctl get label <node-name> --key=g8s.host/gpu-type` | Query the value of a specific GPU type label for a node |
| `gpuctl label node <node-name> <label-key> --delete` | Delete a specific label from a node |

### Resource Quota Management

| Command Example | Description |
|---------|---------|
| `gpuctl create -f quota.yaml` | Create resource quota configuration |
| `gpuctl get quotas` | List all resource quotas |
| `gpuctl get quotas <namespace-name>` | View quota for a specific namespace |
| `gpuctl describe quota <namespace-name>` | View detailed quota usage (used/total) |
| `gpuctl delete -f quota.yaml` | Delete resource quota |

## API Documentation

The platform provides RESTful API interfaces that can be used to build third-party tools or integrate into existing systems.

### Basic Information

- **Base Path**: `/api/v1`
- **Data Format**: Requests/responses use JSON format, YAML configuration is transmitted via `application/yaml` media type
- **Authentication**: Bearer Token authentication, passed through HTTP header `Authorization: Bearer <token>`
- **Version Control**: URL path includes version (e.g., `v1`), supporting multi-version parallel maintenance
- **Status Code Specifications**:
  - 200: Request successful
  - 201: Resource created successfully
  - 400: Invalid request parameters (e.g., invalid YAML format)
  - 401: Unauthenticated (invalid or expired Token)
  - 403: Insufficient permissions (e.g., non-admin operating resource pools)
  - 404: Resource not found (e.g., invalid task ID)
  - 500: Server internal error (e.g., Kubernetes cluster exception)

### Core API Endpoints

#### Task Management API

| Endpoint | Method | Function |
|----------|--------|----------|
| `/jobs` | POST | Create task |
| `/jobs/batch` | POST | Batch create tasks |
| `/jobs` | GET | Query task list |
| `/jobs/{jobId}` | GET | Query task details |
| `/jobs/{jobId}` | DELETE | Delete task |
| `/jobs/{jobId}/logs` | GET | Get task real-time logs |
| `/jobs/{jobId}/metrics` | GET | Get task metric time-series data |

#### Resource Pool Management API

| Endpoint | Method | Function |
|----------|--------|----------|
| `/pools` | GET | Query resource pool list |
| `/pools/{poolName}` | GET | Query resource pool details |
| `/pools` | POST | Create resource pool |
| `/pools/{poolName}` | DELETE | Delete resource pool |

#### Node Management API

| Endpoint | Method | Function |
|----------|--------|----------|
| `/nodes` | GET | Query node list |
| `/nodes/{nodeName}` | GET | Query node details |
| `/nodes/{nodeName}/labels` | POST | Add labels to node |
| `/nodes/labels` | GET | Query node labels |
| `/nodes/{nodeName}/labels/{key}` | DELETE | Delete node label |

#### Resource Quota Management API

| Endpoint | Method | Function |
|----------|--------|----------|
| `/quotas` | GET | Query quota list |
| `/quotas/{namespaceName}` | GET | Query quota details with usage |
| `/quotas` | POST | Create resource quota |
| `/quotas/{namespaceName}` | DELETE | Delete resource quota |

### Interactive API Documentation

After starting the server, you can access the interactive Swagger UI at:

```
http://localhost:8000/api/v1/docs
```

## Development Guide

### Directory Structure

```
gpuctl/
├── api/                  # API definitions
│   ├── training.py       # Training task model
│   ├── inference.py      # Inference task model
│   ├── notebook.py       # Notebook task model
│   ├── compute.py        # Compute task model
│   ├── quota.py          # Resource quota model
│   ├── pool.py           # Resource pool model
│   └── common.py         # Common data models
├── parser/               # YAML parsing and validation
│   ├── base_parser.py    # Basic parsing logic
│   ├── training_parser.py # Training task parsing
│   ├── inference_parser.py # Inference task parsing
│   ├── notebook_parser.py # Notebook task parsing
│   ├── compute_parser.py # Compute task parsing
│   ├── quota_parser.py   # Resource quota parsing
│   └── pool_parser.py    # Resource pool parsing
├── builder/              # Model to K8s resource conversion
│   ├── training_builder.py # Training task → K8s Job
│   ├── inference_builder.py # Inference task → Deployment+HPA
│   ├── notebook_builder.py # Notebook → StatefulSet+Service
│   ├── compute_builder.py # Compute task → K8s Job/Deployment
│   └── base_builder.py   # Basic building logic
├── client/               # K8s operation encapsulation
│   ├── base_client.py    # Basic K8s client
│   ├── job_client.py     # Task management
│   ├── quota_client.py   # Resource quota management
│   ├── pool_client.py    # Resource pool management
│   └── log_client.py     # Log retrieval
├── kind/                 # Scenario-specific logic
│   ├── training_kind.py  # Multi-GPU training/distributed scheduling
│   ├── inference_kind.py # Inference service scaling
│   ├── notebook_kind.py  # Notebook lifecycle management
│   └── compute_kind.py   # Batch compute task management
├── cli/                  # CLI command implementations
│   ├── main.py           # Main command entry
│   ├── job.py            # Task-related commands
│   ├── pool.py           # Resource pool-related commands
│   ├── quota.py          # Resource quota commands
│   └── node.py           # Node-related commands
├── server/               # API server implementation
│   ├── main.py           # Server entry point
│   ├── models.py         # Data models
│   ├── auth.py           # Authentication and authorization
│   ├── dependencies.py   # Dependency injection
│   └── routes/           # API routes
│       ├── jobs.py        # Task management routes
│       ├── pools.py       # Resource pool management routes
│       ├── quotas.py      # Resource quota routes
│       ├── nodes.py       # Node management routes
│       ├── labels.py      # Label management routes
│       └── auth.py        # Authentication routes
├── tests/                # Test cases
│   ├── conftest.py       # Test configuration
│   ├── test_gpuctl.py    # Core functionality tests
│   ├── api/              # API tests
│   │   ├── test_jobs.py   # Task API tests
│   │   ├── test_pools.py  # Resource pool API tests
│   │   ├── test_nodes.py  # Node API tests
│   │   └── test_labels.py # Label management API tests
│   └── cli/              # CLI tests
│       ├── test_job_commands.py   # Task command tests
│       ├── test_pool_commands.py  # Resource pool command tests
│       └── test_node_commands.py  # Node command tests
├── main.py               # Main entry point
├── poetry.lock           # Dependency lock file
└── pyproject.toml        # Project configuration
```

### Start Development Server

```bash
python server/main.py
```

### Run Tests

```bash
pytest
```

### Build Binary

You can build a standalone binary file using PyInstaller. This allows you to run gpuctl without a Python environment.

#### Prerequisites

- PyInstaller 5.0+
- Python 3.12 (recommended)

#### Build Steps

1. Install dependencies

```bash
pip install kubernetes>=24.2.0 PyYAML>=6.0 pydantic>=2.0 pyinstaller
```

2. Build the binary for Linux/macOS

```bash
# Build for Linux
pyinstaller --onefile --name="gpuctl-linux-amd64" --hidden-import=yaml --hidden-import=PyYAML main.py

# Build for macOS
pyinstaller --onefile --name="gpuctl-macos-amd64" --hidden-import=yaml --hidden-import=PyYAML main.py
```

3. Build the binary for Windows

```bash
pyinstaller --onefile --name="gpuctl-windows-amd64.exe" --hidden-import=yaml --hidden-import=PyYAML main.py
```

4. Find the built binary

```bash
ls -la dist/
```

The built binary will be in the `dist/` directory.

5. Use the binary

```bash
# Linux/macOS
chmod +x dist/gpuctl-linux-amd64
./dist/gpuctl-linux-amd64 --help

# Windows
./dist/gpuctl-windows-amd64.exe --help
```

## Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- Project Home: https://github.com/g8s-host/gpuctl
- Issue Tracker: https://github.com/g8s-host/gpuctl/issues
- Documentation: https://github.com/g8s-host/gpuctl/tree/main/doc

## Acknowledgments

Thank you to all developers and users who have contributed to the project!
