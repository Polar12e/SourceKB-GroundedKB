package main

import (
	"log/slog"
	"os"

	"grounded-kb.local/internal/platform/service"
)

func main() {
	if err := service.Run("model-gateway", "MODEL_GATEWAY_PORT", 8084); err != nil {
		slog.Error("service failed", "service", "model-gateway", "error", err)
		os.Exit(1)
	}
}
