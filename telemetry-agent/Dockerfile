# rw-telemetry-agent 镜像:多阶段构建,产出静态小二进制。
# 运行期用 debian-slim —— 提供 nvidia-container-runtime 注入 nvidia-smi/libs 所需的
# 标准 FHS 目录;静态二进制(CGO 关)无 libc 依赖。比 cuda base(~200MB+)小得多。
#
# REGISTRY 默认 docker.io(可移植);docker daemon 直连 docker.io 受阻的环境(如 runw)
# 用 --build-arg REGISTRY=docker.m.daocloud.io 走国内 mirror(docker 构建不吃 k3s 的
# registries.yaml,故经此 ARG 而非 daemon 配置)。
# 用在 FROM 里的 ARG 必须在首个 FROM 之前【全局】声明。
# REGISTRY:docker daemon 直连 docker.io 受阻时(如 runw)用 --build-arg REGISTRY=docker.m.daocloud.io。
# RUNTIME_IMAGE:运行镜像默认 debian-slim(小、可移植);受阻环境可用
#   --build-arg RUNTIME_IMAGE=nvidia/cuda:12.2.2-base-ubuntu22.04 复用本地已缓存镜像、免拉取。
ARG REGISTRY=docker.io
ARG RUNTIME_IMAGE=debian:bookworm-slim

FROM ${REGISTRY}/library/golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/rw-telemetry-agent .

FROM ${RUNTIME_IMAGE}
COPY --from=build /out/rw-telemetry-agent /usr/local/bin/rw-telemetry-agent
ENTRYPOINT ["/usr/local/bin/rw-telemetry-agent"]
