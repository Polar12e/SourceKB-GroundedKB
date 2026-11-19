// Package modelgateway provides a controlled DeepSeek/OpenAI-compatible LLM proxy.
package modelgateway

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	Enabled   bool
	BaseURL   string
	Model     string
	APIKeyEnv string
	APIKey    string
	Timeout   time.Duration
}

func envBool(key string) bool {
	return strings.EqualFold(strings.TrimSpace(os.Getenv(key)), "true")
}

func envOr(key, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(key)); value != "" {
		return value
	}
	return fallback
}

func ConfigFromEnv() Config {
	timeoutSeconds := 60
	if raw := os.Getenv("LLM_TIMEOUT"); raw != "" {
		if parsed, err := strconv.Atoi(raw); err == nil && parsed > 0 {
			timeoutSeconds = parsed
		}
	}
	keyEnv := envOr("LLM_API_KEY_ENV", "DEEPSEEK_API_KEY")
	return Config{
		Enabled:   envBool("LLM_ENABLED"),
		BaseURL:   strings.TrimRight(envOr("LLM_BASE_URL", "https://api.deepseek.com"), "/"),
		Model:     envOr("LLM_MODEL", "deepseek-chat"),
		APIKeyEnv: keyEnv,
		APIKey:    os.Getenv(keyEnv),
		Timeout:   time.Duration(timeoutSeconds) * time.Second,
	}
}

type Handler struct {
	config Config
	client *http.Client
}

func NewHandler(config Config) *Handler {
	return &Handler{
		config: config,
		client: &http.Client{Timeout: config.Timeout},
	}
}

func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed", "POST required")
		return
	}
	if !h.config.Enabled {
		writeError(w, http.StatusServiceUnavailable, "llm_disabled", "LLM integration is disabled")
		return
	}
	if h.config.APIKey == "" {
		writeError(w, http.StatusServiceUnavailable, "llm_unconfigured", "missing LLM API key env: "+h.config.APIKeyEnv)
		return
	}

	body, err := io.ReadAll(http.MaxBytesReader(w, r.Body, 2<<20))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_request", "request body too large")
		return
	}
	var payload map[string]any
	if err := json.Unmarshal(body, &payload); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_request", "invalid JSON body")
		return
	}
	// The gateway owns the model and endpoint choice; callers cannot redirect
	// cost or traffic by changing the model field.
	payload["model"] = h.config.Model
	body, err = json.Marshal(payload)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal_error", "encode model request")
		return
	}

	request, err := http.NewRequestWithContext(
		r.Context(), http.MethodPost, h.config.BaseURL+"/chat/completions", bytes.NewReader(body),
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal_error", "build model request")
		return
	}
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+h.config.APIKey)

	response, err := h.client.Do(request)
	if err != nil {
		writeError(w, http.StatusBadGateway, "llm_unavailable", err.Error())
		return
	}
	defer response.Body.Close()
	w.Header().Set("Content-Type", response.Header.Get("Content-Type"))
	w.WriteHeader(response.StatusCode)
	_, _ = io.Copy(w, io.LimitReader(response.Body, 4<<20))
}

func writeError(w http.ResponseWriter, status int, code, message string) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"error": map[string]string{"code": code, "message": message},
	})
}

func (c Config) String() string {
	return fmt.Sprintf("enabled=%t model=%s base=%s key_env=%s", c.Enabled, c.Model, c.BaseURL, c.APIKeyEnv)
}
