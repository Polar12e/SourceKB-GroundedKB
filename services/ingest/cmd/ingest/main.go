package main

import (
	"log/slog"
	"os"

	"grounded-kb.local/internal/platform/service"
)

func main() {
	if err := service.Run("ingest", "INGEST_PORT", 8082); err != nil {
		slog.Error("service failed", "service", "ingest", "error", err)
		os.Exit(1)
	}
}
