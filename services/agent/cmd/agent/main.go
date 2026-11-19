package main

import (
	"log/slog"
	"net/http"
	"os"
	"strings"

	agentapi "grounded-kb.local/internal/agent"
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
	modelURL := envOr("MODEL_GATEWAY_URL", "http://127.0.0.1:8084")
	llmEnabled := strings.EqualFold(strings.TrimSpace(os.Getenv("LLM_ENABLED")), "true")
	handler, err := agentapi.NewHandlerWithLLM(retrievalURL, modelURL, llmEnabled)
	if err != nil {
		slog.Error("invalid retrieval URL", "error", err)
		os.Exit(1)
	}

	if err := service.RunWithRoutes("agent", "AGENT_PORT", 8083, func(mux *http.ServeMux) error {
		mux.Handle("POST /ask", handler)
		return nil
	}); err != nil {
		slog.Error("service failed", "service", "agent", "error", err)
		os.Exit(1)
	}
}
