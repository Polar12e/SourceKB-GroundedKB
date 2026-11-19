package main

import (
	"log/slog"
	"net/http"
	"os"

	"grounded-kb.local/internal/modelgateway"
	"grounded-kb.local/internal/platform/service"
)

func main() {
	config := modelgateway.ConfigFromEnv()
	handler := modelgateway.NewHandler(config)
	if err := service.RunWithRoutes("model-gateway", "MODEL_GATEWAY_PORT", 8084, func(mux *http.ServeMux) error {
		mux.Handle("POST /v1/chat/completions", handler)
		return nil
	}); err != nil {
		slog.Error("service failed", "service", "model-gateway", "error", err)
		os.Exit(1)
	}
}
