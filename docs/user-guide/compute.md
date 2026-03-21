# 计算任务

计算任务（`kind: compute`）适用于纯 CPU 服务部署，如 Web 服务、数据库、缓存、代理等。底层对应 Kubernetes **Deployment + NodePort Service**，支持多副本和健康检查。

## YAML 完整字段

```yaml
kind: compute
version: v0.1

job:
  name: <服务名称>
  priority: medium
  description: "描述"

environment:
  image: <镜像地址>
  command: [...]   # 可选，不填使用镜像默认 entrypoint
  args: [...]      # 可选
  env:
    - name: KEY
      value: VALUE

service:
  replicas: 1       # 副本数（默认 1）
  port: 80          # 服务端口
  healthCheck: /    # 健康检查路径（可选）

resources:
  pool: default
  gpu: 0            # 计算任务设置为 0（纯 CPU）
  cpu: 2
  memory: 4Gi

storage:
  workdirs:
    - path: /data
```

---

## 场景一：部署 Nginx Web 服务

```yaml title="nginx-service.yaml"
kind: compute
version: v0.1

job:
  name: nginx-web
  priority: medium
  description: "Nginx 静态 Web 服务"

environment:
  image: nginx:latest
  command: []
  args: []
  env:
    - name: NGINX_PORT
      value: "80"

service:
  replicas: 2
  port: 80
  healthCheck: /

resources:
  pool: compute-pool
  gpu: 0
  cpu: 2
  memory: 4Gi

storage:
  workdirs:
    - path: /etc/nginx/conf.d
    - path: /var/www/html
```

```bash
gpuctl create -f nginx-service.yaml
gpuctl describe job nginx-web    # 查看访问地址
```

---

## 场景二：部署 Redis 缓存

```yaml title="redis-cache.yaml"
kind: compute
version: v0.1

job:
  name: redis-cache
  priority: medium

environment:
  image: redis:7.0-alpine
  command: ["redis-server"]
  args: ["--maxmemory", "1gb", "--maxmemory-policy", "allkeys-lru"]

service:
  replicas: 1
  port: 6379

resources:
  pool: default
  gpu: 0
  cpu: 1
  memory: 2Gi

storage:
  workdirs:
    - path: /data   # Redis 持久化目录
```

---

## 场景三：部署自定义 Python API 服务

```yaml title="fastapi-service.yaml"
kind: compute
version: v0.1

job:
  name: my-fastapi-service
  priority: medium

environment:
  image: my-registry/fastapi-app:v1.0
  command: ["uvicorn", "main:app"]
  args: ["--host", "0.0.0.0", "--port", "8080"]
  env:
    - name: DATABASE_URL
      value: "postgresql://user:pass@db:5432/mydb"
    - name: LOG_LEVEL
      value: "info"

service:
  replicas: 3
  port: 8080
  healthCheck: /health

resources:
  pool: default
  gpu: 0
  cpu: 4
  memory: 8Gi
```

---

## 更新计算任务

```bash
# 修改 YAML（如调整副本数、镜像版本等）后执行：
gpuctl apply -f nginx-service.yaml
```

## 查看服务日志

```bash
gpuctl logs nginx-web -f
```

## 删除计算任务

```bash
gpuctl delete job nginx-web
```

!!! info "与推理任务的区别"
    `compute` 和 `inference` 底层都使用 K8s Deployment，主要区别在于语义标注（`runwhere.ai/job-type` label）和资源池选择。计算任务通常 `gpu: 0`，推理任务通常有 GPU 需求。
