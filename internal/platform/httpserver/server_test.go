package httpserver

import (
	"net/http"
	"testing"
)

func TestNew(t *testing.T) {
	handler := http.NewServeMux()
	srv := New(":8080", handler)

	if srv.Addr != ":8080" {
		t.Fatalf("Addr = %q, want :8080", srv.Addr)
	}
	if srv.Handler == nil {
		t.Fatal("Handler = nil, want non-nil")
	}
	if srv.ReadHeaderTimeout <= 0 || srv.ReadTimeout <= 0 || srv.WriteTimeout <= 0 || srv.IdleTimeout <= 0 {
		t.Fatalf("timeouts must be positive: %+v", srv)
	}
}
