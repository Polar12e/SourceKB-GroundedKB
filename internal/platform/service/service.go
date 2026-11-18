// Package service wires shared configuration, health checks and lifecycle.
package service

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"grounded-kb.local/internal/platform/config"
	"grounded-kb.local/internal/platform/health"
	"grounded-kb.local/internal/platform/httpserver"
)

const shutdownTimeout = 10 * time.Second

// NewMux returns the HTTP routes shared by every service.
func NewMux(name string) *http.ServeMux {
	mux := http.NewServeMux()
	mux.Handle("GET /healthz", health.Handler(name))
	return mux
}

// Run starts the named service on portEnv/defaultPort and blocks until shutdown.
func Run(name, portEnv string, defaultPort int) error {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	port, err := config.Port(portEnv, defaultPort)
	if err != nil {
		return err
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	srv := httpserver.New(config.Addr(port), NewMux(name))
	logger.Info("service starting", "service", name, "addr", srv.Addr)

	if err := httpserver.Run(ctx, srv, shutdownTimeout); err != nil {
		return fmt.Errorf("%s: %w", name, err)
	}

	logger.Info("service stopped", "service", name)
	return nil
}
