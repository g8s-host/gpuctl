# rw-telemetry-agent 镜像:多阶段构建,产出静态小二进制。
# 运行期用 debian-slim —— 提供 nvidia-container-runtime 注入 nvidia-smi/libs 所需的
# 标准 FHS 目录;静态二进制(CGO 关)无 libc 依赖。比 cuda base(~200MB+)小得多。
FROM golang:1.22-bookworm AS build
WORKDIR /src
COPY go.mod ./
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/rw-telemetry-agent .

FROM debian:bookworm-slim
COPY --from=build /out/rw-telemetry-agent /usr/local/bin/rw-telemetry-agent
ENTRYPOINT ["/usr/local/bin/rw-telemetry-agent"]
