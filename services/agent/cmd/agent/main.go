package main

import (
	"log/slog"
	"os"

	"grounded-kb.local/internal/platform/service"
)

func main() {
	if err := service.Run("agent", "AGENT_PORT", 8083); err != nil {
		slog.Error("service failed", "service", "agent", "error", err)
		os.Exit(1)
	}
}
