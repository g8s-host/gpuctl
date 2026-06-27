# Quickstart

Get gpuctl installed and submit your first job to a Kubernetes cluster in under 5 minutes.

## Prerequisites

- Python 3.8+
- Access to a Kubernetes cluster (`kubectl` configured with a valid kubeconfig)
- At least one available node in the cluster

## Step 1: Install gpuctl

=== "From Source (Recommended)"

    ```bash
    git clone https://github.com/g8s-host/gpuctl.git
    cd gpuctl
    pip install -e .
    ```

=== "Binary Install"

    ```bash
    # Linux x86_64
    wget https://github.com/g8s-host/gpuctl/releases/latest/download/gpuctl-linux-amd64 -O gpuctl
    chmod +x gpuctl
    sudo mv gpuctl /usr/local/bin/

    # macOS x86_64
    curl -L https://github.com/g8s-host/gpuctl/releases/latest/download/gpuctl-macos-amd64 -o gpuctl
    chmod +x gpuctl
    sudo mv gpuctl /usr/local/bin/
    ```

Verify the installation:

```bash
gpuctl --help
```

## Step 2: Verify Cluster Connection

```bash
gpuctl get nodes
```

!!! tip "Operators: enable persistent storage once"
    If you run the platform, register your NFS share a single time so that **every** job automatically gets a persistent `/home/jovyan` and a shared read-only `/datasets` — with no storage config in any job YAML:

    ```bash
    gpuctl init --nfs-server <IP> --nfs-path /exports
    ```

    This step is optional: without it, jobs still run, just without the auto-mounted NFS paths. See [Persistent Storage](storage.md).

Example output:

```
NODE NAME     STATUS   GPU TOTAL  GPU USED  GPU FREE  GPU TYPE    IP              POOL
node-1        Ready    8          0         8         A100-80G    192.168.1.101   default
node-2        Ready    4          0         4         A10-24G     192.168.1.102   default
```

## Step 3: Submit Your First Job

The following example uses the `nginx` image (no GPU required) to quickly verify the platform is working:

**1. Create a YAML file**

```yaml title="hello-gpuctl.yaml"
kind: compute
version: v0.1

job:
  name: hello-gpuctl
  priority: medium
  description: My first gpuctl job

environment:
  image: nginx:latest
  command: []
  args: []

service:
  replicas: 1
  port: 80

resources:
  pool: default
  gpu: 0
  cpu: 1
  memory: 512Mi
```

**2. Submit the job**

```bash
gpuctl create -f hello-gpuctl.yaml
```

Output:

```
Job created successfully: hello-gpuctl
Namespace: default
```

**3. Check job status**

```bash
gpuctl get jobs
```

```
JOB ID                              NAME          NAMESPACE  KIND     STATUS    READY  NODE    IP           AGE
hello-gpuctl-7d9c8b-xk2lp           hello-gpuctl  default    compute  Running   1/1    node-1  10.42.0.5    2m
```

**4. Inspect the job**

```bash
gpuctl describe job hello-gpuctl
```

**5. View logs**

```bash
gpuctl logs hello-gpuctl
```

**6. Delete the job**

```bash
gpuctl delete job hello-gpuctl
```

## Step 4: Submit a GPU Training Job (Optional)

If your cluster has GPU nodes, try submitting a simple training job:

```yaml title="simple-training.yaml"
kind: training
version: v0.1

job:
  name: simple-training
  priority: medium

environment:
  image: pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime
  command: ["python", "-c", "import torch; print(f'GPU available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"]

resources:
  pool: default
  gpu: 1
  cpu: 4
  memory: 16Gi
```

```bash
gpuctl create -f simple-training.yaml
gpuctl logs simple-training -f
```

## Common Commands Reference

| Scenario | Command |
|----------|---------|
| Submit a job | `gpuctl create -f job.yaml` |
| List all jobs | `gpuctl get jobs` |
| Filter by job type | `gpuctl get jobs --kind training` |
| Stream logs | `gpuctl logs <job-name> -f` |
| Job details | `gpuctl describe job <job-name>` |
| Delete a job | `gpuctl delete job <job-name>` |
| List resource pools | `gpuctl get pools` |
| List nodes | `gpuctl get nodes` |

## Next Steps

- [Training Jobs](training.md) — LlamaFactory / DeepSpeed, conda env reuse, and multi-node distributed training
- [Persistent Storage](storage.md) — transparent NFS `/home/jovyan` + `/datasets`, with zero config in job YAML
- [Inference Services](inference.md) — Deploy a VLLM inference API service
- [Resource Pool Management](pool.md) — Create and manage GPU resource pools
- [CLI Reference](../cli/index.md) — Full command documentation
