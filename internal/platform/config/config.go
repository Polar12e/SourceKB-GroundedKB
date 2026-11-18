// Package config reads service configuration from environment variables.
package config

import (
	"fmt"
	"os"
	"strconv"
)

// Port returns the TCP port from envName, or fallback when the variable is unset.
// Values must be integers in the range 1-65535.
func Port(envName string, fallback int) (int, error) {
	raw := os.Getenv(envName)
	if raw == "" {
		return fallback, nil
	}

	port, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("%s must be an integer: %q", envName, raw)
	}
	if port < 1 || port > 65535 {
		return 0, fmt.Errorf("%s must be between 1 and 65535: %d", envName, port)
	}
	return port, nil
}

// Addr formats a port as a listen address for all interfaces.
func Addr(port int) string {
	return ":" + strconv.Itoa(port)
}
