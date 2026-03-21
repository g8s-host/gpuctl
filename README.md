<!-- Hero Section -->
<p align="center">
  <img src="docs/assets/gpuctl_logo.svg" width="200" alt="gpuctl logo">
</p>

<!-- Colorful Shields Badges -->
<p align="center">
  <a href="https://github.com/g8s-host/gpuctl/releases">
    <img src="https://img.shields.io/github/v/release/g8s-host/gpuctl?style=flat-square&color=blue&label=Release" alt="release">
  </a>
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="python">
  <img src="https://img.shields.io/badge/Kubernetes-1.24+-326CE5?style=flat-square&logo=kubernetes&logoColor=white" alt="kubernetes">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="license">
  <img src="https://img.shields.io/badge/Contributions-Welcome-orange?style=flat-square" alt="contributions">
</p>

<!-- One-liner Tagline -->
<h2 align="center">🚀 Schedule GPU Clusters Like Writing Python Scripts</h2>

<p align="center">
  <b>Declarative YAML</b> · <b>Zero K8s Knowledge</b> · <b>Resource Pool Isolation</b>
</p>

<p align="center">
  <a href="./README.zh-CN.md">简体中文</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-documentation">Documentation</a> •
  <a href="#-features">Features</a>
</p>

---

## ✨ Why gpuctl

<!-- Row 1: Core Values -->
<table align="center">
  <tr>
    <td align="center" width="25%">
      <img src="https://img.shields.io/badge/⚡-Minimal_CLI-FFD700?style=flat-square" alt="cli"><br><br>
      <b>One Command to Rule Them All</b><br>
      <code>gpuctl create -f job.yaml</code><br><br>
      <sub>Say goodbye to 100+ lines of K8s YAML, submit tasks with declarative configuration</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://img.shields.io/badge/🎯-Resource_Pool_Isolation-00C853?style=flat-square" alt="pool"><br><br>
      <b>Multi-Team Resource Isolation</b><br>
      Training Pool / Inference Pool / Dev Pool<br><br>
      <sub>Logical isolation prevents resource contention, with quota management per team</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://img.shields.io/badge/🔌-Seamless_Integration-2962FF?style=flat-square" alt="integration"><br><br>
      <b>AI Frameworks Ready-to-Use</b><br>
      DeepSpeed / VLLM / LlamaFactory<br><br>
      <sub>Auto-inject NCCL env vars and distributed training configuration</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://img.shields.io/badge/👁️-Unified_Observability-FF6D00?style=flat-square" alt="observability"><br><br>
      <b>One-Stop Monitoring</b><br>
      Logs / Events / Resource Usage<br><br>
      <sub>No more kubectl get pods to find pod names</sub>
    </td>
  </tr>
</table>

<!-- Row 2: Extended Benefits -->
<table align="center">
  <tr>
    <td align="center" width="25%">
      <img src="https://img.shields.io/badge/📝-Declarative_Config-9C27B0?style=flat-square" alt="declarative"><br><br>
      <b>ML Engineer Friendly</b><br>
      kind / job / resources<br><br>
      <sub>Familiar YAML syntax, no need to understand Pod/Deployment concepts</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://img.shields.io/badge/🔐-Auto_Quota-00BCD4?style=flat-square" alt="quota"><br><br>
      <b>Namespace-Level Quotas</b><br>
      CPU / Memory / GPU<br><br>
      <sub>Auto-bind ResourceQuota when creating Namespace</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://img.shields.io/badge/🌐-RESTful_API-E91E63?style=flat-square" alt="api"><br><br>
      <b>Complete API Support</b><br>
      HTTP / WebSocket<br><br>
      <sub>Easy integration with MLOps platforms or third-party tools</sub>
    </td>
    <td align="center" width="25%">
      <img src="https://img.shields.io/badge/🔧-Zero_Intrusion-795548?style=flat-square" alt="non-intrusive"><br><br>
      <b>Existing K8s Cluster</b><br>
      Ready to Use<br><br>
      <sub>No cluster configuration changes, no impact on existing workloads</sub>
    </td>
  </tr>
</table>

---

## 🚀 Quick Start

```bash
# 1. Install CLI
pip install gpuctl

# 2. Submit LLM fine-tuning task (4x A100)
cat > training.yaml << 'EOF'
kind: training
version: v0.1
job:
  name: qwen2-7b-sft
environment:
  image: llama-factory:latest
  command: ["llamafactory-cli", "train", "--stage", "sft"]
resources:
  pool: training-pool
  gpu: 4
  cpu: 32
  memory: 128Gi
EOF

gpuctl create -f training.yaml

# 3. Check task status
gpuctl get jobs

# 4. View logs in real-time
gpuctl logs qwen2-7b-sft -f
```

<!-- Demo GIF Placeholder - Replace with actual recording later -->
<p align="center">
  <img src="https://via.placeholder.com/800x400/1a1a2e/e94560?text=Demo+GIF+Placeholder" width="800" alt="demo">
  <br>
  <sub>👆 Terminal demo (replace with actual recording later)</sub>
</p>

---

## 🆚 gpuctl vs Native Kubectl

<table width="100%">
  <tr>
    <th width="25%">Scenario</th>
    <th width="37.5%">✨ gpuctl Way</th>
    <th width="37.5%">Native Kubectl Way</th>
  </tr>
  <tr>
    <td><b>📝 Submit Training Task</b></td>
    <td><b>Just 15-20 lines of declarative config</b>, fill in familiar fields like kind, job.name, resources.gpu, and submit</td>
    <td>Write 120+ lines of K8s YAML, manually create Secret, ConfigMap, Job resources, understand PodSpec, ResourceRequirements, VolumeMounts</td>
  </tr>
  <tr>
    <td><b>📊 Check Task Status</b></td>
    <td><b>One command for all tasks</b> <code>gpuctl get jobs</code>, auto-aggregate Pod status, show task name, status, resource usage</td>
    <td><code>kubectl get jobs</code> to find Job, then <code>get pods -l job-name=xxx</code> to find Pod, finally <code>describe pod</code> for details, tedious process</td>
  </tr>
  <tr>
    <td><b>🔍 View Task Logs</b></td>
    <td><b>Use task name directly</b> <code>gpuctl logs &lt;job-name&gt; -f</code>, auto-track Pod changes, support multi-replica aggregated logs</td>
    <td>Remember Pod name (e.g. <code>training-job-7d9f4b8c5-x2mnp</code>), run <code>kubectl logs &lt;pod-name&gt; -f</code>, re-find after Pod restart</td>
  </tr>
  <tr>
    <td><b>🧠 Multi-GPU Training</b></td>
    <td><b>Just declare gpu count</b>, platform auto-injects NCCL_SOCKET_IFNAME, MASTER_ADDR, WORLD_SIZE env vars, auto-configures DeepSpeed</td>
    <td>Manually configure NCCL env vars, DeepSpeed hostfile, PyTorch launch parameters, understand GPU communication and process groups</td>
  </tr>
  <tr>
    <td><b>🏊 Resource Pool Management</b></td>
    <td><b>Declarative pool config</b>, <code>pool: training-pool</code> auto-schedules to corresponding node group, supports multi-team isolation and quota control</td>
    <td>Manually bind nodes via LabelSelector and NodeAffinity, maintain complex scheduling strategies and resource limits per team</td>
  </tr>
  <tr>
    <td><b>📋 Resource Quota Management</b></td>
    <td><b>Quota auto-created with Namespace</b>, <code>gpuctl describe quota</code> one-click view of used/total, auto-reject with friendly message when exceeded</td>
    <td>Manually create ResourceQuota and LimitRange, configure per Namespace, query usage multiple times for aggregation</td>
  </tr>
  <tr>
    <td><b>⚡ Deploy Inference Service</b></td>
    <td><b>Auto-create Deployment + Service</b>, declare replicas and port, auto-generate NodePort to expose service, built-in readiness probe</td>
    <td>Create Deployment, Service, Ingress/NodePort separately, configure HPA auto-scaling, understand Service types and network policies</td>
  </tr>
  <tr>
    <td><b>📓 Launch Notebook</b></td>
    <td><b>One-click JupyterLab launch</b>, auto-generate access link, support custom images and passwords, auto-mount storage volumes</td>
    <td>Manually create StatefulSet, Headless Service, Ingress, configure PVC storage, handle Jupyter Token and passwords</td>
  </tr>
</table>

---

## 🏗️ Architecture

<p align="center">
  <img src="docs/assets/architect.png" width="700" alt="gpuctl architecture">
</p>

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────┐
│   User      │────▶│  gpuctl CLI │────▶│  K8s Job/Deployment/        │
│  (YAML)     │     │   / REST API│     │  StatefulSet + Service      │
└─────────────┘     └─────────────┘     └─────────────────────────────┘
```

---

## 📚 Documentation

Complete documentation is available in the **[docs/](docs/)** directory, or check out the quick navigation below:

**Getting Started**
- [Quick Start](docs/user-guide/quickstart.md) — Get started with gpuctl in 5 minutes
- [Installation Guide](docs/install.md) — Detailed installation steps

**User Guides**
- [Training Tasks](docs/user-guide/training.md) — LLM fine-tuning, single-node multi-GPU training
- [Inference Services](docs/user-guide/inference.md) — VLLM inference deployment
- [Notebooks](docs/user-guide/notebook.md) — JupyterLab interactive development
- [Resource Pool Management](docs/user-guide/pool.md) — GPU resource pool configuration

**Reference**
- [CLI Commands](docs/cli/index.md) — Complete command reference
- [API Documentation](docs/developer-guide/api.md) — RESTful API specifications
- [FAQ](docs/faq.md) — Frequently asked questions and troubleshooting

**Development & Contribution**
- [Architecture Design](docs/developer-guide/architecture.md) — System design documentation
- [Local Development](docs/developer-guide/index.md) — Development environment setup
- [Contributing Guide](CONTRIBUTING.md) — How to contribute

---

## 💻 Installation

### Prerequisites
- Python 3.8+
- Kubernetes cluster access (via `kubectl`)

### From PyPI (Recommended)
```bash
pip install gpuctl
```

### From Source
```bash
git clone https://github.com/g8s-host/gpuctl.git
cd gpuctl
pip install -e .
```

### Binary Download
```bash
# Linux
wget https://github.com/g8s-host/gpuctl/releases/latest/download/gpuctl-linux-amd64
chmod +x gpuctl-linux-amd64
sudo mv gpuctl-linux-amd64 /usr/local/bin/gpuctl
```

---

## 🌟 Show Your Support

If gpuctl helps you, please give us a ⭐️ Star!

<a href="https://github.com/g8s-host/gpuctl/stargazers">
  <img src="https://img.shields.io/github/stars/g8s-host/gpuctl?style=social" alt="stars">
</a>

---

## 📄 License

[MIT License](LICENSE) © 2024 GPU Control Team
