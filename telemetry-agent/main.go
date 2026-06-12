// rw-telemetry-agent — runwhere 任务遥测 sidecar(P0b)。
//
// 作为 gpuctl 注入的 native sidecar 运行在每个任务 pod 里,周期性采集信号并 POST 给
// console。设计为【探针框架】:每个 Probe 贡献若干字段,合并成一条样本上报。P0b 仅含
// GPU 设备级探针;后续 Tier B(jupyter 空闲、推理 /metrics、训练吞吐等)只需新增 Probe。
//
// 纯标准库 + exec nvidia-smi(由 nvidia runtime 注入),无第三方依赖 → 静态小二进制。
// 配置全部来自环境变量(见 README / gpuctl build_telemetry_sidecar)。
package main

import (
	"context"
	"log"
	"os"
	"os/exec"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"
)

// Sample 是一次采集合并后的字段集合(probe 各自往里写)。
type Sample map[string]any

// Probe 是一个可插拔的采集器。返回的字段会被合并进上报样本。
// 返回 error 时该 probe 本轮被跳过,不影响其它 probe。
type Probe interface {
	Name() string
	Collect(ctx context.Context) (Sample, error)
}

// ── GPU 探针:exec nvidia-smi 读设备级利用率/显存 ────────────────────────────────
type gpuProbe struct{}

func (gpuProbe) Name() string { return "gpu" }

func (gpuProbe) Collect(ctx context.Context) (Sample, error) {
	cctx, cancel := context.WithTimeout(ctx, 4*time.Second)
	defer cancel()
	out, err := exec.CommandContext(cctx, "nvidia-smi",
		"--query-gpu=index,utilization.gpu,memory.used,memory.total",
		"--format=csv,noheader,nounits").Output()
	if err != nil {
		return nil, err
	}
	line := strings.TrimSpace(string(out))
	if i := strings.IndexByte(line, '\n'); i >= 0 {
		line = line[:i] // 多卡时先取第 0 张(P0b 设备级)
	}
	f := strings.Split(line, ",")
	if len(f) < 4 {
		return nil, errShort
	}
	atoi := func(s string) float64 {
		v, _ := strconv.ParseFloat(strings.TrimSpace(s), 64)
		return v
	}
	return Sample{
		"gpu_index":  int(atoi(f[0])),
		"gpu_util":   atoi(f[1]),
		"mem_used":   atoi(f[2]),
		"mem_total":  atoi(f[3]),
	}, nil
}

type sentinel string

func (s sentinel) Error() string { return string(s) }

const errShort = sentinel("nvidia-smi: unexpected field count")

// ── 配置 ───────────────────────────────────────────────────────────────────────
type config struct {
	endpoint  string
	interval  time.Duration
	namespace string
	pod       string
	jobType   string
}

func envOr(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func loadConfig() config {
	iv, _ := strconv.Atoi(envOr("RW_T_INTERVAL", "5"))
	if iv < 1 {
		iv = 5
	}
	return config{
		endpoint:  os.Getenv("RW_TELEMETRY_ENDPOINT"),
		interval:  time.Duration(iv) * time.Second,
		namespace: envOr("RW_POD_NAMESPACE", "default"),
		pod:       os.Getenv("RW_POD_NAME"),
		jobType:   envOr("RW_JOB_TYPE", "unknown"),
	}
}

func main() {
	cfg := loadConfig()
	if cfg.endpoint == "" || cfg.pod == "" {
		log.Fatal("[rw-telemetry] RW_TELEMETRY_ENDPOINT 和 RW_POD_NAME 必须设置")
	}
	log.Printf("[rw-telemetry] %s/%s type=%s -> %s every %s",
		cfg.namespace, cfg.pod, cfg.jobType, cfg.endpoint, cfg.interval)

	probes := []Probe{gpuProbe{}}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer stop()

	r := newReporter(cfg.endpoint)
	tick := time.NewTicker(cfg.interval)
	defer tick.Stop()

	collectAndSend(ctx, cfg, probes, r) // 立即来一发,别等第一个 tick
	for {
		select {
		case <-ctx.Done():
			log.Printf("[rw-telemetry] 收到终止信号,退出")
			return
		case <-tick.C:
			collectAndSend(ctx, cfg, probes, r)
		}
	}
}

func collectAndSend(ctx context.Context, cfg config, probes []Probe, r *reporter) {
	s := Sample{
		"namespace": cfg.namespace,
		"pod":       cfg.pod,
		"job_type":  cfg.jobType,
	}
	for _, p := range probes {
		fields, err := p.Collect(ctx)
		if err != nil {
			log.Printf("[rw-telemetry] probe %s 跳过: %v", p.Name(), err)
			continue
		}
		for k, v := range fields {
			s[k] = v
		}
	}
	if err := r.send(ctx, s); err != nil {
		log.Printf("[rw-telemetry] 上报失败: %v", err)
	}
}
