# Persistent Storage

gpuctl provides **transparent persistent storage** backed by NFS. Once an operator registers an NFS share once, **every** job a user submits automatically gets a persistent home directory and a shared read-only datasets directory — with **zero storage configuration in the job YAML**.

!!! tip "Design goal"
    Engineers should focus on training code, not storage. The amount of storage-related config in a user's job YAML is **0 lines**: no mount paths, no storage classes, no PVCs. Files written to `/home/jovyan` survive job restarts and are shared across all of a user's jobs.

---

## How it works at a glance

```text
                gpuctl init  (operator, once)
                      │
                      ▼
        ConfigMap kube-system/gpuctl-config
            nfs.server: <IP>
            nfs.path:   /exports
                      │
        every job (training / inference / notebook / compute)
                      │  reads the ConfigMap at build time
                      ▼
   ┌──────────────────────────────────────────────────┐
   │ Pod                                                │
   │   /home/jovyan  ←─ nfs:<server>:/exports/home/<ns> │  read-write, per namespace
   │   /datasets     ←─ nfs:<server>:/exports/datasets  │  read-only, shared
   └──────────────────────────────────────────────────┘
```

- The user's namespace **is** the user identity. Each namespace gets its own isolated `home/<namespace>` directory.
- Mounts are injected by the platform for all job kinds — nothing to declare in YAML.
- If NFS is not configured, jobs still run normally without these mounts (see [Backward compatibility](#backward-compatibility)).

---

## Step 1: Operator registers the NFS share (once)

NFS storage is registered with a single command. gpuctl does **not** set up the NFS server itself — it only records where the existing share lives.

```bash
gpuctl init --nfs-server <IP_OR_HOST> --nfs-path <EXPORT_ROOT>
```

| Option | Required | Description |
|--------|----------|-------------|
| `--nfs-server` | Yes | NFS server IP or hostname |
| `--nfs-path` | Yes | NFS export root path (must start with `/`) |

**Example:**

```bash
gpuctl init --nfs-server 192.168.1.100 --nfs-path /exports
```

Output:

```
NFS storage initialized:
  Server: 192.168.1.100
  Path:   /exports
  Config stored in: kube-system/gpuctl-config
```

The configuration is stored in the `kube-system/gpuctl-config` ConfigMap.

!!! info "Idempotent and live"
    Running `gpuctl init` again updates the existing ConfigMap (patch). The new value takes effect immediately for **newly created** jobs — no service restart required. Already-running jobs are unaffected.

---

## Step 2: Users get persistent storage automatically

Once NFS is registered, the platform mounts two paths into every job's container — with no YAML changes:

| Path | Backing | Access | Scope |
|------|---------|--------|-------|
| `/home/jovyan` | `nfs:<server>:<path>/home/<namespace>` | **read-write** | Per namespace (per user) |
| `/datasets` | `nfs:<server>:<path>/datasets` | **read-only** | Shared by all users |

What this means in practice:

- **Survives restarts.** Anything written to `/home/jovyan` is still there after a job ends or is recreated.
- **Shared across a user's jobs.** A Training job and a Notebook in the same namespace see the exact same `/home/jovyan` — no copying or syncing. A Notebook can prepare code/data/conda envs, and a Training job reads them directly. See [Training jobs → conda env reuse](training.md#example-2-reuse-a-notebook-environment-conda).
- **Isolated per user.** `alice`'s `/home/jovyan` and `bob`'s `/home/jovyan` are different directories (`home/alice` vs `home/bob`) and never overlap.
- **Datasets are read-only.** `/datasets` is content managed by the operator and mounted read-only everywhere.

A minimal job that gets persistent storage automatically — note there is no `storage` section at all:

```yaml title="notebook.yaml"
kind: notebook
version: v0.1

job:
  name: alice-dev

environment:
  image: jupyter/scipy-notebook:latest

service:
  port: 8888

resources:
  pool: dev-pool
  gpu: 1
  cpu: 8
  memory: 32Gi
```

```bash
# Submit into the user's namespace
gpuctl create -f notebook.yaml -n alice
```

Files written under `/home/jovyan` by this Notebook persist and are visible to any other job `alice` submits.

---

## User home provisioning on quota apply

When an operator allocates quota for a new user, that user's storage directory is created at the same time — no separate step.

```bash
gpuctl apply -f quota.yaml
```

When `apply` creates a new namespace, gpuctl runs a short-lived `busybox` Job in `kube-system` that `mkdir -p`s the user's `home/<namespace>` directory on the NFS share. By the time the user submits their first job, `/home/jovyan` is ready and writable.

- **Idempotent.** Re-applying a quota for an existing user does not touch existing files.
- **Symmetric cleanup.** Deleting a namespace (`gpuctl delete ns <name>`) runs a matching `busybox` Job that removes the user's home directory, so no orphaned data is left behind.
- **No-op without NFS.** If NFS is not registered, quota creation skips the provisioning step and works exactly as before.

!!! warning "Deleting a namespace deletes the user's files"
    Because cleanup runs `rm -rf` on `home/<namespace>`, deleting a namespace permanently removes that user's persistent data. Make sure it is backed up first if you need to keep it.

---

## Backward compatibility

Transparent storage is purely additive — it never breaks existing jobs:

- **NFS not registered:** jobs of every kind still submit and run; no NFS volumes are mounted; no error.
- **Old YAML with no `storage` section:** unchanged behavior, plus automatic NFS mounts if NFS is registered.
- **Old YAML with `storage.workdirs`:** the `hostPath` workdirs keep mounting; NFS mounts are added on top (if registered). See the next section for the difference.

---

## `storage.workdirs` vs transparent NFS

These are two **separate** mechanisms. For most users, transparent NFS is all you need and `storage.workdirs` can be omitted entirely.

| | Transparent NFS (`/home/jovyan`, `/datasets`) | `storage.workdirs` |
|---|---|---|
| Declared in YAML? | No — fully automatic | Yes — you list each path |
| Backing volume | NFS (network, shared, persistent) | `hostPath` (the node's local disk) |
| Survives reschedule to another node? | Yes | No — `hostPath` is node-local |
| Multi-node distributed sharing? | Yes — all workers see the same files | No |
| When to use | Default for persistent user data and shared datasets | Advanced cases needing a specific node-local path |

```yaml
# storage.workdirs is OPTIONAL and only for hostPath mounts.
# Most jobs should omit this section and rely on transparent NFS.
storage:
  workdirs:
    - path: /scratch/local-cache
```

---

## See also

- [`gpuctl init` in the CLI reference](../cli/index.md#init)
- [Training jobs](training.md) — uses `/home/jovyan` for checkpoints, including multi-node distributed training where all workers share one home
- [Quotas & Namespaces](quota.md) — namespace creation triggers home provisioning
