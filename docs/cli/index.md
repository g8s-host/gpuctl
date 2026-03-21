# CLI Command Reference

The gpuctl CLI mirrors `kubectl` but with semantics optimized for ML engineers.

## Command Overview

| Command | Description |
|---------|-------------|
| `create` | Create resources from YAML (jobs, resource pools, quotas) |
| `apply` | Apply configuration (create or update — equivalent to delete + create) |
| `get` | List resources |
| `describe` | View resource details |
| `delete` | Delete resources |
| `logs` | View job logs |
| `label` | Manage node labels |

---

## create

Create resources from a YAML file.

```bash
gpuctl create -f <file> [-n <namespace>] [--json]
```

| Option | Description | Required |
|--------|-------------|----------|
| `-f, --file` | YAML file path (can be specified multiple times) | Yes |
| `-n, --namespace` | Namespace (default: `default`) | No |
| `--json` | Output in JSON format | No |

**Examples:**

```bash
# Submit a single job
gpuctl create -f training-job.yaml

# Submit multiple jobs at once
gpuctl create -f task1.yaml -f task2.yaml

# Specify a namespace
gpuctl create -f job.yaml -n team-alice

# JSON output
gpuctl create -f job.yaml --json
```

---

## apply

Apply resource configuration (deletes the existing resource, then creates a new one).

```bash
gpuctl apply -f <file> [-n <namespace>] [--json]
```

| Option | Description | Required |
|--------|-------------|----------|
| `-f, --file` | YAML file path (can be specified multiple times) | Yes |
| `-n, --namespace` | Namespace (default: `default`) | No |
| `--json` | Output in JSON format | No |

**Examples:**

```bash
# Update a job configuration
gpuctl apply -f job.yaml

# Update with a specific namespace
gpuctl apply -f job.yaml -n team-alice
```

---

## get

List resources. Supports multiple resource types and filter options.

### get jobs

```bash
gpuctl get jobs [-n <namespace>] [--pool <pool>] [--kind <kind>] [--pods] [--json]
```

| Option | Description |
|--------|-------------|
| `-n, --namespace` | Filter by namespace (all namespaces if omitted) |
| `--pool` | Filter by resource pool |
| `--kind` | Filter by job type: `training` / `inference` / `notebook` / `compute` |
| `--pods` | Show Pod-level info (instead of Deployment/StatefulSet level) |
| `--json` | JSON output |

**Output columns:**

| Column | Meaning |
|--------|---------|
| JOB ID | Pod name (with K8s auto-generated hash suffix) |
| NAME | `job.name` from the YAML |
| NAMESPACE | Namespace |
| KIND | Job type |
| STATUS | Pod running status |
| READY | Ready/total containers (e.g. `1/1`) |
| NODE | Node the pod was scheduled to |
| IP | Pod IP |
| AGE | Time since creation |

**Examples:**

```bash
gpuctl get jobs
gpuctl get jobs -n team-alice
gpuctl get jobs --pool training-pool
gpuctl get jobs --kind training
gpuctl get jobs --pods
```

### get pools

```bash
gpuctl get pools [--json]
```

**Example:**

```bash
gpuctl get pools
```

### get nodes

```bash
gpuctl get nodes [--pool <pool>] [--gpu-type <type>] [--json]
```

| Option | Description |
|--------|-------------|
| `--pool` | Filter by resource pool |
| `--gpu-type` | Filter by GPU model |

**Examples:**

```bash
gpuctl get nodes
gpuctl get nodes --pool training-pool
gpuctl get nodes --gpu-type A100-100G
```

### get labels

```bash
gpuctl get labels [<node_name>] [--key <key>] [--json]
```

**Examples:**

```bash
# View all labels on a node
gpuctl get labels node-1

# View a specific label
gpuctl get labels node-1 --key=runwhere.ai/gpu-type
```

### get quotas

```bash
gpuctl get quotas [<namespace>] [--json]
```

**Examples:**

```bash
gpuctl get quotas
gpuctl get quotas team-alice
```

### get ns / namespaces

```bash
gpuctl get ns [--json]
gpuctl get namespaces [--json]
```

---

## describe

View detailed resource information.

### describe job

```bash
gpuctl describe job <job_name> [-n <namespace>] [--json]
```

**Output includes:**

- Basic info: Name, Kind, Resource Type, Namespace, Status, Age, Priority, Pool
- Resource config: CPU, Memory, GPU
- Raw YAML: gpuctl YAML config reverse-mapped from the K8s resource
- Events: Last 10 K8s events
- Access Methods (inference / notebook / compute only): Pod IP and NodePort addresses

**Examples:**

```bash
gpuctl describe job my-training-job
gpuctl describe job my-training-job -n team-alice
```

### describe pool

```bash
gpuctl describe pool <pool_name> [--json]
```

**Example:**

```bash
gpuctl describe pool training-pool
```

### describe node

```bash
gpuctl describe node <node_name> [--json]
```

**Example:**

```bash
gpuctl describe node node-1
```

### describe quota / ns / namespace

```bash
gpuctl describe quota <namespace_name> [--json]
gpuctl describe ns <namespace_name> [--json]
gpuctl describe namespace <namespace_name> [--json]
```

**Examples:**

```bash
gpuctl describe quota team-alice
gpuctl describe ns team-alice
```

---

## delete

Delete resources.

### Delete via YAML file

```bash
gpuctl delete -f <file> [-n <namespace>] [--force] [--json]
```

**Examples:**

```bash
gpuctl delete -f training-job.yaml
gpuctl delete -f pool.yaml
gpuctl delete -f quota.yaml
```

### delete job

```bash
gpuctl delete job <job_name> [-n <namespace>] [--force] [--json]
```

**Examples:**

```bash
gpuctl delete job my-training-job
gpuctl delete job my-training-job -n team-alice
gpuctl delete job my-training-job --force
```

### delete quota

```bash
gpuctl delete quota <namespace_name> [--force] [--json]
```

**Example:**

```bash
gpuctl delete quota team-alice
```

### delete ns / namespace

```bash
gpuctl delete ns <namespace_name> [--force] [--json]
gpuctl delete namespace <namespace_name> [--force] [--json]
```

**Examples:**

```bash
gpuctl delete ns team-alice
gpuctl delete ns team-alice --force
```

### delete pool

```bash
gpuctl delete pool <pool_name> [--force] [--json]
```

**Example:**

```bash
gpuctl delete pool training-pool
```

!!! warning "Delete Job Behavior"
    When a job is deleted, the platform also deletes:

    - The primary K8s resource (Job / Deployment / StatefulSet)
    - The associated NodePort Service (training jobs have no Service)
    - K8s controllers will automatically cascade-delete associated Pods

---

## logs

Retrieve job logs.

```bash
gpuctl logs <job_name> [-n <namespace>] [-f] [--json]
```

| Option | Description |
|--------|-------------|
| `<job_name>` | Job name |
| `-n, --namespace` | Namespace (default: `default`) |
| `-f, --follow` | Stream logs in real time (like `tail -f`) |
| `--json` | JSON output |

**Examples:**

```bash
# View recent logs (last 100 lines by default)
gpuctl logs my-training-job

# Stream logs
gpuctl logs my-training-job -f

# Specify namespace
gpuctl logs my-training-job -n team-alice -f
```

---

## label

Manage node labels.

```bash
gpuctl label <node_name> [node_name...] <label> [--delete] [--overwrite] [--json]
```

!!! warning "Label Key Convention"
    Label keys managed by gpuctl **must be prefixed with `runwhere.ai/`** to avoid conflicts with other systems.

| Option | Description |
|--------|-------------|
| `<node_name>` | Node name (multiple nodes can be specified) |
| `<label>` | `key=value` format (to add) or `key` format (when deleting) |
| `--delete` | Delete the label |
| `--overwrite` | Overwrite an existing label with the same key |

**Examples:**

```bash
# Add a GPU model label to a single node
gpuctl label node-1 runwhere.ai/gpu-type=A100-100G

# Add label to multiple nodes
gpuctl label node-1 node-2 runwhere.ai/gpu-type=A100-100G

# Overwrite an existing label
gpuctl label node-1 runwhere.ai/gpu-type=A10-24G --overwrite

# Delete a label
gpuctl label node-1 runwhere.ai/gpu-type --delete

# Assign a node to a resource pool
gpuctl label node-1 runwhere.ai/pool=training-pool
```

---

## Global Options

| Option | Description |
|--------|-------------|
| `--help` | Show help information |
| `--json` | Output in JSON format (supported by most commands) |

---

## Full Workflow Examples

### Training Job Lifecycle

```bash
# 1. Check available resources
gpuctl get nodes
gpuctl get pools

# 2. Submit a training job
gpuctl create -f training-job.yaml -n team-alice

# 3. Monitor status
gpuctl get jobs -n team-alice

# 4. Stream logs
gpuctl logs my-training -n team-alice -f

# 5. View job details
gpuctl describe job my-training -n team-alice

# 6. Clean up after completion
gpuctl delete job my-training -n team-alice
```

### Node and Resource Pool Management

```bash
# 1. List all nodes
gpuctl get nodes

# 2. Label a node with its GPU model
gpuctl label node-5 runwhere.ai/gpu-type=A100-100G

# 3. Create a resource pool (binding nodes)
gpuctl create -f training-pool.yaml

# 4. View resource pools
gpuctl get pools
gpuctl describe pool training-pool

# 5. View nodes in a pool
gpuctl get nodes --pool training-pool
```
