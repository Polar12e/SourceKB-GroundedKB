// Package health provides the shared liveness endpoint for all services.
package health

import (
	"encoding/json"
	"net/http"
)

// Response is the JSON body returned by /healthz.
type Response struct {
	Status  string `json:"status"`
	Service string `json:"service"`
}

// Handler returns a handler that reports the named service as healthy.
func Handler(service string) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(Response{Status: "ok", Service: service})
	})
}
