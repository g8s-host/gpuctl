package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// reporter 把样本 POST 给 console 的 ingest 端点。
// 上报失败可接受(live 遥测,丢点无妨),仅记日志。
type reporter struct {
	endpoint string
	client   *http.Client
}

func newReporter(endpoint string) *reporter {
	return &reporter{
		endpoint: endpoint,
		client: &http.Client{
			Timeout: 4 * time.Second,
		},
	}
}

func (r *reporter) send(ctx context.Context, s Sample) error {
	body, err := json.Marshal(s)
	if err != nil {
		return err
	}
	cctx, cancel := context.WithTimeout(ctx, 4*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(cctx, http.MethodPost, r.endpoint, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := r.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body)
	if resp.StatusCode >= 300 {
		return fmt.Errorf("ingest 返回 %d", resp.StatusCode)
	}
	return nil
}
