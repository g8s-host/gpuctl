# Quota and Namespace Management

gpuctl uses the Kubernetes ResourceQuota mechanism to set CPU, memory, and GPU resource limits per namespace (team/user), preventing resource abuse and enabling multi-tenant isolation.

## Core Concepts

- **Namespace**: A K8s logical isolation unit; each team or user gets a dedicated namespace
- **Quota**: Limits the maximum resources (CPU/memory/GPU/Pod count) usable within a namespace
- **Auto-creation**: Running `gpuctl create -f quota.yaml` automatically creates both the namespace and its resource quota

---

## Creating Quotas

### Quota YAML Format

```yaml title="team-quota.yaml"
kind: quota
version: v0.1

quota:
  name: team-resource-quota
  description: "Resource quotas for each team"

namespace:
  team-alice:          # Namespace name (auto-created)
    cpu: 16            # CPU core limit
    memory: 64Gi       # Memory limit
    gpu: 8             # GPU count limit
  team-bob:
    cpu: 8
    memory: 32Gi
    gpu: 4
  team-charlie:
    cpu: 4
    memory: 16Gi
    gpu: 2
```

```bash
gpuctl create -f team-quota.yaml
```

The platform automatically:
1. Creates `team-alice`, `team-bob`, and `team-charlie` namespaces
2. Creates the corresponding `ResourceQuota` in each namespace
3. Labels the namespaces as gpuctl-managed (`runwhere.ai/namespace=true`)

---

## Querying Quotas

```bash
# List all quotas
gpuctl get quotas
```

Example output:

```
NAMESPACE       CPU (USED/TOTAL)   MEMORY (USED/TOTAL)   GPU (USED/TOTAL)   STATUS
team-alice      4/16               12Gi/64Gi             2/8                Active
team-bob        2/8                8Gi/32Gi              1/4                Active
team-charlie    0/4                0/16Gi                0/2                Active
default         -                  -                     -                  Active
```

```bash
# View quota for a specific namespace
gpuctl get quotas team-alice

# View quota details (including utilization)
gpuctl describe quota team-alice
```

---

## Submitting Jobs in a Specific Namespace

Once quotas are created, team members specify the namespace with `-n` when submitting jobs:

```bash
# Alice's team submits a training job
gpuctl create -f training-job.yaml -n team-alice

# View Alice's team jobs
gpuctl get jobs -n team-alice
```

---

## Querying Namespaces

```bash
# List all namespaces managed by gpuctl
gpuctl get ns
# or
gpuctl get namespaces
```

Example output:

```
NAME            STATUS   AGE
team-alice      Active   5d
team-bob        Active   5d
team-charlie    Active   2d
default         Active   30d
```

```bash
# View namespace details (including quota info)
gpuctl describe ns team-alice
```

Example output:

```
Name:    team-alice
Status:  Active
Age:     5d

Labels:
  runwhere.ai/namespace: true

Quota:
  CPU:    4/16
  Memory: 12Gi/64Gi
  GPU:    2/8
```

---

## Deleting Quotas

```bash
# Delete via YAML file (deletes all quotas defined in the file)
gpuctl delete -f team-quota.yaml

# Delete a specific namespace's quota
gpuctl delete quota team-charlie

# Delete a namespace (and all resources within it)
gpuctl delete ns team-charlie

# Force delete (skip confirmation prompt)
gpuctl delete ns team-charlie --force
```

!!! danger "Deleting a Namespace"
    Deleting a namespace **deletes all resources within it** (including running jobs, Services, etc.). This operation is **irreversible**. Make sure to back up any important data first.

!!! tip "Only Manages gpuctl-Created Namespaces"
    gpuctl only manages namespaces with the `runwhere.ai/namespace=true` label (created by gpuctl) and the `default` namespace. System namespaces like `kube-system` are out of scope.
