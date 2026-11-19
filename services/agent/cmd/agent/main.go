package main

import (
	"log/slog"
	"net/http"
	"os"

	agentapi "grounded-kb.local/internal/agent"
	"grounded-kb.local/internal/platform/service"
)

func main() {
	retrievalURL := os.Getenv("RETRIEVAL_URL")
	if retrievalURL == "" {
		retrievalURL = "http://127.0.0.1:8081"
	}
	handler, err := agentapi.NewHandler(retrievalURL)
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
