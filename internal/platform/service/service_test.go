package service

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"grounded-kb.local/internal/platform/health"
)

func TestNewMuxHealth(t *testing.T) {
	srv := httptest.NewServer(NewMux("gateway"))
	defer srv.Close()

	resp, err := http.Get(srv.URL + "/healthz")
	if err != nil {
		t.Fatalf("GET /healthz: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusOK)
	}

	var got health.Response
	if err := json.NewDecoder(resp.Body).Decode(&got); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if got.Status != "ok" || got.Service != "gateway" {
		t.Fatalf("body = %+v, want status=ok service=gateway", got)
	}
}

func TestNewMuxRejectsNonGET(t *testing.T) {
	srv := httptest.NewServer(NewMux("gateway"))
	defer srv.Close()

	resp, err := http.Post(srv.URL+"/healthz", "application/json", nil)
	if err != nil {
		t.Fatalf("POST /healthz: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Fatalf("status = %d, want %d", resp.StatusCode, http.StatusMethodNotAllowed)
	}
}
