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

```
┌─────────────────────────────────────────────────────────────────┐
│                      Algorithm Engineer                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        gpuctl CLI                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        gpuctl API                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                           │
└─────────────────────────────────────────────────────────────────┘
```

## Core Features

### 1. Multi-type Task Support

- **Training Tasks**: Support distributed training, integrated with acceleration frameworks like DeepSpeed
- **Inference Services**: Support model deployment with automatic scaling
- **Debugging Tasks**: Provide Jupyter Notebook environment for easy debugging

### 2. Resource Pool Management

- Support creation and management of resource pools
- Flexible binding and unbinding of nodes and resource pools
- Resource isolation and quota management at the resource pool level

### 3. Declarative Configuration

- Use terminology familiar to algorithm engineers
- Hide underlying infrastructure details
- Support YAML format for task definition

### 4. Rich CLI Commands

- Task lifecycle management
- Node and resource pool management
- Real-time log viewing
- Resource usage monitoring

## Installation

### Prerequisites

- Python 3.8+
- Kubernetes cluster access permissions
- Poetry (for dependency management)

### Installation Steps

1. Clone the repository

```bash
git clone https://github.com/your-org/gpuctl.git
cd gpuctl
```

2. Install dependencies

```bash
poetry install
```

3. Activate the virtual environment

```bash
poetry shell
```

4. Configure Kubernetes access

Ensure `kubectl` is properly configured and can access the target Kubernetes cluster.

## Quick Start

### 1. Create a Resource Pool

```yaml
# train-pool.yaml
kind: resource
version: v0.1

pool:
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

job:
  name: qwen2-7b-llamafactory-sft
  description: llama3 inference task
  epochs: 3
  batch_size: 8
  priority: high

environment:
  image: registry.example.com/llama-factory-deepspeed:v0.8.0
  imagePullSecret: my-secret
  command: ["llama-factory-cli", "train", "--stage", "sft", "--model_name_or_path", "/models/qwen2-7b", "--dataset", "alpaca-qwen", "--dataset_dir", "/datasets", "--output_dir", "/output/qwen2-sft", "--per_device_train_batch_size", "8", "--gradient_accumulation_steps", "4", "--learning_rate", "2e-5", "--deepspeed", "ds_config.json"]
  env:
    - name: NVIDIA_FLASH_ATTENTION
      value: "1"
    - name: LLAMA_FACTORY_CACHE
      value: "/cache/llama-factory"

resources:
  pool: training-pool
  gpu: 4
  cpu: 32
  memory: 128Gi
  gpu_share: 2Gi

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

### 3. Query Task Status

```bash
gpuctl get jobs
```

### 4. View Task Logs

```bash
gpuctl logs qwen2-7b-llamafactory-sft -f
```

## CLI Command Reference

### Task Management

| Command Example | Description |
|---------|---------|
| `gpuctl create -f train-job.yaml` | Submit a training task |
| `gpuctl get jobs` | List all tasks and core metrics |
| `gpuctl describe job <job-id>` | View detailed task information and resource usage curves |
| `gpuctl logs <job-id> -f` | View real-time task logs |
| `gpuctl delete -f job.yaml` | Delete/stop a task |
| `gpuctl pause job <job-id>` | Pause a running task |
| `gpuctl resume job <job-id>` | Resume a paused task |

### Resource Pool Management

| Command Example | Description |
|---------|---------|
| `gpuctl get pools` | Query all resource pools and resource usage |
| `gpuctl create -f pool.yaml` | Create a new resource pool |
| `gpuctl delete -f pool.yaml` | Delete a resource pool |
| `gpuctl describe pool <pool-name>` | View detailed resource pool information |
| `gpuctl add node <node-name> --pool <pool-name>` | Add nodes to a resource pool |
| `gpuctl remove node <node-name> --pool <pool-name>` | Remove nodes from a resource pool |

### Node Management

| Command Example | Description |
|---------|---------|
| `gpuctl get nodes` | List basic information of all cluster nodes |
| `gpuctl get nodes --pool <pool-name>` | Filter nodes bound to a specific resource pool |
| `gpuctl get nodes --gpu-type <gpu-type>` | Filter nodes with a specific GPU type |
| `gpuctl describe node <node-name>` | View detailed information of a single node |
| `gpuctl label node <node-name> <label-key>=<label-value>` | Add a label to a specific node |
| `gpuctl label node <node-name> <label-key> --delete` | Delete a specific label from a node |

## API Documentation

The platform provides RESTful API interfaces that can be used to build third-party tools or integrate into existing systems.

### Basic Information

- **Base Path**: `/api/v1`
- **Data Format**: JSON/YAML
- **Authentication**: Bearer Token
- **Version Control**: Version number included in URL path

### Core API Endpoints

- **Task Management**: `/jobs`
- **Resource Pool Management**: `/pools`
- **Node Management**: `/nodes`
- **Label Management**: `/nodes/labels`
- **Monitoring Metrics**: `/jobs/{jobId}/metrics`
- **Log Query**: `/jobs/{jobId}/logs`

### Interactive API Documentation

After starting the server, you can access the interactive Swagger UI at:

```
http://localhost:8000/api/v1/docs
```

## Development Guide

### Directory Structure

```
gpuctl/
├── api/             # API definitions
├── builder/         # Task builders
├── cli/             # CLI command implementations
├── client/          # Client implementations
├── kind/            # Task type definitions
├── parser/          # YAML parsers
├── server/          # Server implementation
├── tests/           # Test cases
├── main.py          # Main entry point
├── poetry.lock      # Dependency lock file
└── pyproject.toml   # Project configuration
```

### Start Development Server

```bash
poetry run python server/main.py
```

### Run Tests

```bash
poetry run pytest
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

- Project Home: https://github.com/your-org/gpuctl
- Issue Tracker: https://github.com/your-org/gpuctl/issues
- Documentation: https://github.com/your-org/gpuctl/tree/main/doc

## Acknowledgments

Thank you to all developers and users who have contributed to the project!