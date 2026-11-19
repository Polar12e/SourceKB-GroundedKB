package modelgateway

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestDisabledHandlerReturns503(t *testing.T) {
	handler := NewHandler(Config{Enabled: false})
	request := httptest.NewRequest(http.MethodPost, "/v1/chat/completions", strings.NewReader(`{}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	if response.Code != http.StatusServiceUnavailable {
		t.Fatalf("status = %d", response.Code)
	}
	if !strings.Contains(response.Body.String(), "llm_disabled") {
		t.Fatalf("body = %s", response.Body.String())
	}
}

func TestMissingKeyReturns503(t *testing.T) {
	handler := NewHandler(Config{Enabled: true, BaseURL: "https://example.com", Model: "deepseek-chat", APIKeyEnv: "MISSING_KEY"})
	request := httptest.NewRequest(http.MethodPost, "/v1/chat/completions", strings.NewReader(`{}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	if response.Code != http.StatusServiceUnavailable || !strings.Contains(response.Body.String(), "llm_unconfigured") {
		t.Fatalf("status/body = %d %s", response.Code, response.Body.String())
	}
}

func TestEnabledHandlerForwardsWithConfiguredModel(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/chat/completions" {
			t.Fatalf("path = %s", r.URL.Path)
		}
		if r.Header.Get("Authorization") != "Bearer test-key" {
			t.Fatalf("authorization = %q", r.Header.Get("Authorization"))
		}
		body, _ := io.ReadAll(r.Body)
		if !strings.Contains(string(body), `"model":"deepseek-chat"`) {
			t.Fatalf("body did not contain configured model: %s", body)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"choices":[{"message":{"content":"ok"}}]}`))
	}))
	defer upstream.Close()

	handler := NewHandler(Config{
		Enabled: true, BaseURL: upstream.URL, Model: "deepseek-chat",
		APIKeyEnv: "TEST_KEY", APIKey: "test-key", Timeout: time.Second,
	})
	request := httptest.NewRequest(http.MethodPost, "/v1/chat/completions", strings.NewReader(`{"model":"expensive-model","messages":[]}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	if response.Code != http.StatusOK {
		t.Fatalf("status = %d body = %s", response.Code, response.Body.String())
	}
}
