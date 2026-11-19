// Package agent provides a minimal extractive RAG answer handler.
package agent

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type askRequest struct {
	Question string            `json:"question"`
	Filters  map[string]string `json:"filters,omitempty"`
	TopK     int               `json:"top_k,omitempty"`
}

type locator struct {
	Page      int `json:"page"`
	LineStart int `json:"line_start"`
	LineEnd   int `json:"line_end"`
}

type searchHit struct {
	DocumentID string  `json:"document_id"`
	Text       string  `json:"text"`
	Locator    locator `json:"locator"`
}

type searchResponse struct {
	Hits []searchHit `json:"hits"`
}

type citation struct {
	DocumentID string `json:"document_id"`
	Page       int    `json:"page"`
	LineStart  int    `json:"line_start"`
	LineEnd    int    `json:"line_end"`
	Quote      string `json:"quote"`
}

type answer struct {
	Answer    string     `json:"answer"`
	Status    string     `json:"status"`
	Citations []citation `json:"citations"`
	TraceID   string     `json:"trace_id"`
}

type errorBody struct {
	Error struct {
		Code    string `json:"code"`
		Message string `json:"message"`
	} `json:"error"`
}

// Handler answers /ask by calling the retrieval service and returning the best
// hit as an extractive answer. It is deliberately deterministic: no LLM yet.
type Handler struct {
	retrievalURL string
	client       *http.Client
}

func NewHandler(retrievalURL string) (*Handler, error) {
	parsed, err := url.Parse(strings.TrimRight(retrievalURL, "/"))
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return nil, fmt.Errorf("invalid retrieval URL: %q", retrievalURL)
	}
	return &Handler{
		retrievalURL: parsed.String(),
		client:       &http.Client{Timeout: 30 * time.Second},
	}, nil
}

func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed", "POST required")
		return
	}

	var request askRequest
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	if err := decoder.Decode(&request); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_request", "invalid JSON body")
		return
	}
	request.Question = strings.TrimSpace(request.Question)
	if request.Question == "" {
		writeError(w, http.StatusBadRequest, "invalid_request", "question must not be empty")
		return
	}
	if request.TopK == 0 {
		request.TopK = 4
	}
	if request.TopK < 1 || request.TopK > 50 {
		writeError(w, http.StatusBadRequest, "invalid_request", "top_k must be 1-50")
		return
	}

	filters := request.Filters
	if filters == nil {
		filters = map[string]string{}
	}
	payload, err := json.Marshal(map[string]any{
		"query":   request.Question,
		"filters": filters,
		"top_k":   request.TopK,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal_error", "encode retrieval request")
		return
	}

	httpRequest, err := http.NewRequestWithContext(
		r.Context(),
		http.MethodPost,
		h.retrievalURL+"/search",
		bytes.NewReader(payload),
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal_error", "build retrieval request")
		return
	}
	httpRequest.Header.Set("Content-Type", "application/json")

	httpResponse, err := h.client.Do(httpRequest)
	if err != nil {
		writeError(w, http.StatusBadGateway, "retrieval_unavailable", err.Error())
		return
	}
	defer httpResponse.Body.Close()
	if httpResponse.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(httpResponse.Body, 512))
		writeError(w, http.StatusBadGateway, "retrieval_error", strings.TrimSpace(string(body)))
		return
	}

	var results searchResponse
	if err := json.NewDecoder(httpResponse.Body).Decode(&results); err != nil {
		writeError(w, http.StatusBadGateway, "retrieval_error", "invalid retrieval JSON")
		return
	}

	traceID := fmt.Sprintf("trace_%d", time.Now().UnixNano())
	if len(results.Hits) == 0 {
		writeJSON(w, http.StatusOK, answer{
			Answer:    "insufficient evidence",
			Status:    "insufficient_evidence",
			Citations: []citation{},
			TraceID:   traceID,
		})
		return
	}

	hit := results.Hits[0]
	quote := strings.TrimSpace(hit.Text)
	if quote == "" {
		writeJSON(w, http.StatusOK, answer{
			Answer:    "insufficient evidence",
			Status:    "insufficient_evidence",
			Citations: []citation{},
			TraceID:   traceID,
		})
		return
	}

	writeJSON(w, http.StatusOK, answer{
		Answer: quote,
		Status: "ok",
		Citations: []citation{{
			DocumentID: hit.DocumentID,
			Page:       hit.Locator.Page,
			LineStart:  hit.Locator.LineStart,
			LineEnd:    hit.Locator.LineEnd,
			Quote:      quote,
		}},
		TraceID: traceID,
	})
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, status int, code, message string) {
	var body errorBody
	body.Error.Code = code
	body.Error.Message = message
	writeJSON(w, status, body)
}
