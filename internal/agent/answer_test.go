package agent

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

func TestHandlerReturnsExtractiveAnswer(t *testing.T) {
	retrieval := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost || r.URL.Path != "/search" {
			t.Fatalf("unexpected request: %s %s", r.Method, r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"hits":[{"document_id":"doc","text":"1: 营业收入 42\n2: 单位：千元","anchor_text":"营业收入 42","locator":{"page":3,"line_start":1,"line_end":2},"anchor":{"line_start":2,"line_end":2},"channels":["expanded","dense"],"score":2.5,"matched_terms":["营业","收入"]}]}`))
	}))
	defer retrieval.Close()

	handler, err := NewHandler(retrieval.URL)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/ask", strings.NewReader(`{"question":"收入是多少？"}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	if response.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", response.Code, response.Body.String())
	}
	var body answer
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Status != "ok" || !strings.Contains(body.Answer, "营业收入 42") || !strings.Contains(body.Answer, "抽取式") {
		t.Fatalf("body = %+v", body)
	}
	if len(body.Citations) != 1 || body.Citations[0].Page != 3 {
		t.Fatalf("citations = %+v", body.Citations)
	}
	if body.Citations[0].LineStart != 2 || body.Citations[0].Quote != "营业收入 42" {
		t.Fatalf("citation must use anchor, got %+v", body.Citations[0])
	}
}

func TestHandlerAbstainsWithoutHits(t *testing.T) {
	retrieval := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"hits":[]}`))
	}))
	defer retrieval.Close()

	handler, err := NewHandler(retrieval.URL)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/ask", strings.NewReader(`{"question":"未知问题"}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	var body answer
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Status != "insufficient_evidence" || len(body.Citations) != 0 {
		t.Fatalf("body = %+v", body)
	}
}

func TestHandlerRejectsEmptyQuestion(t *testing.T) {
	handler, err := NewHandler("http://127.0.0.1:1")
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/ask", strings.NewReader(`{"question":"  "}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	if response.Code != http.StatusBadRequest {
		t.Fatalf("status = %d", response.Code)
	}
}

func TestNewHandlerRejectsInvalidURL(t *testing.T) {
	if _, err := NewHandler("not-a-url"); err == nil {
		t.Fatal("expected error")
	}
}

func TestHandlerMarksMalformedEvidenceUnverified(t *testing.T) {
	retrieval := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"hits":[{"document_id":"doc","text":"window","anchor_text":"","locator":{"page":3,"line_start":1,"line_end":2},"anchor":{"line_start":2,"line_end":2},"channels":["expanded"],"score":2.0,"matched_terms":["收入"]}]}`))
	}))
	defer retrieval.Close()

	handler, err := NewHandler(retrieval.URL)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/ask", strings.NewReader(`{"question":"收入"}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	var body answer
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Status != "unverified" || len(body.Citations) != 0 {
		t.Fatalf("body = %+v", body)
	}
}

func retrievalWithHit(t *testing.T) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"hits":[{"chunk_id":"doc:p3:c0","document_id":"doc","text":"window","anchor_text":"营业收入 42","locator":{"page":3,"line_start":1,"line_end":2},"anchor":{"line_start":2,"line_end":2},"channels":["expanded"],"score":2.5,"matched_terms":["营业","收入"]}]}`))
	}))
}

func modelWithContent(t *testing.T, content string) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/chat/completions" {
			t.Fatalf("model path = %s", r.URL.Path)
		}
		_, _ = w.Write([]byte(`{"choices":[{"message":{"content":` + strconv.Quote(content) + `}}]}`))
	}))
}

func TestLLMAnswerMustCiteKnownChunk(t *testing.T) {
	retrieval := retrievalWithHit(t)
	defer retrieval.Close()
	model := modelWithContent(t, `{"answer":"营业收入 42","citations":["doc:p3:c0"],"status":"ok"}`)
	defer model.Close()

	handler, err := NewHandlerWithLLM(retrieval.URL, model.URL, true)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/ask", strings.NewReader(`{"question":"营业收入是多少？"}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	var body answer
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Status != "ok" || body.Answer != "营业收入 42" {
		t.Fatalf("body = %+v", body)
	}
	if len(body.Citations) != 1 || body.Citations[0].Quote != "营业收入 42" {
		t.Fatalf("citations = %+v", body.Citations)
	}
}

func TestLLMFallsBackWhenCitationIsUnknown(t *testing.T) {
	retrieval := retrievalWithHit(t)
	defer retrieval.Close()
	model := modelWithContent(t, `{"answer":"营业收入 42","citations":["missing-chunk"],"status":"ok"}`)
	defer model.Close()

	handler, err := NewHandlerWithLLM(retrieval.URL, model.URL, true)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/ask", strings.NewReader(`{"question":"营业收入是多少？"}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	var body answer
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(body.Answer, "抽取式") || !strings.Contains(body.Answer, "营业收入 42") {
		t.Fatalf("fallback body = %+v", body)
	}
}
