package main

import (
	"log/slog"
	"os"

	"grounded-kb.local/internal/platform/service"
)

func main() {
	if err := service.Run("gateway", "GATEWAY_PORT", 8080); err != nil {
		slog.Error("service failed", "service", "gateway", "error", err)
		os.Exit(1)
	}
}
