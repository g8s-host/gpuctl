# Resource Pool Management

Resource pools (Pool) are gpuctl's core resource isolation mechanism. They partition cluster nodes into multiple logical pools, enabling isolation between training, inference, development, and other workloads to prevent GPU contention.

## How It Works

```
Cluster Nodes
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   node-1    │  │   node-2    │  │   node-3    │  │   node-4    │
│  A100×8     │  │  A100×8     │  │   A10×4     │  │   A10×4     │
│ pool=train  │  │ pool=train  │  │pool=infer   │  │  pool=dev   │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘

     Training Pool               Inference Pool       Dev Pool
   (training-pool)             (inference-pool)      (dev-pool)
```

Nodes are bound to a pool via the Kubernetes label `runwhere.ai/pool=<pool-name>`. Jobs specify the target pool with `resources.pool`, and the platform uses `nodeSelector` to schedule Pods onto pool nodes.

---

## Creating a Resource Pool

### Pool YAML Format

```yaml title="training-pool.yaml"
kind: pool
version: v0.1

pool:
  name: training-pool
  description: "Dedicated pool for training jobs"

nodes:
  node-1:              # Node hostname (matches kubectl get nodes output)
    gpuType: A100-100G
  node-2:
    gpuType: A100-100G
```

```bash
gpuctl create -f training-pool.yaml
```

### Creating Multiple Pools

Create multiple pools separately:

```bash
gpuctl create -f training-pool.yaml
gpuctl create -f inference-pool.yaml
gpuctl create -f dev-pool.yaml
```

---

## Recommended Pool Layout

### Four-Pool Design

```yaml title="training-pool.yaml"
kind: pool
version: v0.1
pool:
  name: training-pool
  description: "Large model training (high-end GPUs)"
nodes:
  gpu-node-1:
    gpuType: A100-100G
  gpu-node-2:
    gpuType: A100-100G
```

```yaml title="inference-pool.yaml"
kind: pool
version: v0.1
pool:
  name: inference-pool
  description: "Inference services (mid-range GPUs)"
nodes:
  gpu-node-3:
    gpuType: A10-24G
  gpu-node-4:
    gpuType: A10-24G
```

```yaml title="dev-pool.yaml"
kind: pool
version: v0.1
pool:
  name: dev-pool
  description: "Notebook development and debugging (low-end GPUs)"
nodes:
  gpu-node-5:
    gpuType: RTX4090-24G
```

```yaml title="compute-pool.yaml"
kind: pool
version: v0.1
pool:
  name: compute-pool
  description: "CPU compute services (no GPU nodes)"
nodes:
  cpu-node-1:
    gpuType: ""
  cpu-node-2:
    gpuType: ""
```

---

## Querying Resource Pools

```bash
# List all resource pools
gpuctl get pools
```

Example output:

```
POOL NAME        STATUS   GPU TOTAL  GPU USED  GPU FREE  NODE COUNT
training-pool    active   16         12        4         2
inference-pool   active   8          4         4         2
dev-pool         active   4          2         2         1
default          active   0          0         0         0
```

```bash
# View pool details (including node list and running jobs)
gpuctl describe pool training-pool
```

---

## Node Label Management

Resource pools are implemented via node labels. You can also manage node-pool bindings directly through label commands:

```bash
# Add node-6 to training-pool
gpuctl label node node-6 runwhere.ai/pool=training-pool

# Overwrite an existing pool label
gpuctl label node node-6 runwhere.ai/pool=inference-pool --overwrite

# View a node's pool label
gpuctl get labels node-6 --key=runwhere.ai/pool

# Set GPU type label
gpuctl label node node-6 runwhere.ai/gpu-type=A100-100G
```

!!! warning "Label Key Convention"
    Labels managed by gpuctl **must be prefixed with `runwhere.ai/`** to avoid conflicts with other systems.

---

## Using a Resource Pool in Jobs

Specify the target resource pool in the `resources.pool` field of your YAML:

```yaml
resources:
  pool: training-pool   # Must be an already-created pool name
  gpu: 4
  cpu: 32
  memory: 128Gi
```

```bash
# View jobs in a specific pool
gpuctl get jobs --pool training-pool
```

---

## Deleting a Resource Pool

```bash
# Delete via YAML file
gpuctl delete -f training-pool.yaml

# Or delete by name directly
gpuctl delete pool training-pool
```

!!! danger "Confirm Before Deleting"
    Deleting a resource pool removes the pool label bindings from nodes, but does **not** terminate running jobs. It is recommended to stop all jobs in the pool before deleting it.
