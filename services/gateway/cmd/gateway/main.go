package main

import (
	"log/slog"
	"net/http"
	"os"

	"grounded-kb.local/internal/platform/proxy"
	"grounded-kb.local/internal/platform/service"
)

func envOr(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func main() {
	retrievalURL := envOr("RETRIEVAL_URL", "http://127.0.0.1:8081")
	agentURL := envOr("AGENT_URL", "http://127.0.0.1:8083")

	if err := service.RunWithRoutes("gateway", "GATEWAY_PORT", 8080, func(mux *http.ServeMux) error {
		retrievalProxy, err := proxy.New(retrievalURL)
		if err != nil {
			return err
		}
		agentProxy, err := proxy.New(agentURL)
		if err != nil {
			return err
		}
		mux.Handle("/search", retrievalProxy)
		mux.Handle("/ask", agentProxy)
		return nil
	}); err != nil {
		slog.Error("service failed", "service", "gateway", "error", err)
		os.Exit(1)
	}
}
