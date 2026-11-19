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

func TestLLMAcceptsUnitConversionWhenNumberIsGrounded(t *testing.T) {
	retrieval := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"hits":[{"chunk_id":"doc:p1:c0","document_id":"doc","text":"window","anchor_text":"遊戲 130,115 百萬元","locator":{"page":1,"line_start":1,"line_end":2},"anchor":{"line_start":1,"line_end":2},"channels":["expanded"],"score":2.5,"matched_terms":["遊戲"]}]}`))
	}))
	defer retrieval.Close()
	model := modelWithContent(t, `{"answer":"遊戲收入為1,301.15億元","citations":["doc:p1:c0"],"status":"ok"}`)
	defer model.Close()

	handler, err := NewHandlerWithLLM(retrieval.URL, model.URL, true)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/ask", strings.NewReader(`{"question":"遊戲收入"}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	var body answer
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Status != "ok" || !strings.Contains(body.Answer, "1,301.15") {
		t.Fatalf("body = %+v", body)
	}
}

func TestLLMAcceptsYearWrittenInChineseNumerals(t *testing.T) {
	retrieval := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"hits":[{"chunk_id":"doc:p47:c0","document_id":"doc","text":"window","anchor_text":"二零二六年\n遊戲 130,115\n社交網絡 64,409","locator":{"page":47,"line_start":1,"line_end":3},"anchor":{"line_start":1,"line_end":3},"channels":["expanded"],"score":2.5,"matched_terms":["遊戲"]}]}`))
	}))
	defer retrieval.Close()
	model := modelWithContent(t, `{"answer":"2026年上半年游戏业务收入合计为人民币130,115百万元，社交网络收入为人民币64,409百万元。","citations":["doc:p47:c0"],"status":"ok"}`)
	defer model.Close()

	handler, err := NewHandlerWithLLM(retrieval.URL, model.URL, true)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/ask", strings.NewReader(`{"question":"2026年上半年游戏业务收入"}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	var body answer
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if body.Status != "ok" || strings.Contains(body.Answer, "未通过校验") || !strings.Contains(body.Answer, "130,115") {
		t.Fatalf("body = %+v", body)
	}
}

func TestLLMRejectsNumberAbsentFromCitedEvidence(t *testing.T) {
	retrieval := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"hits":[{"chunk_id":"doc:p1:c0","document_id":"doc","text":"window","anchor_text":"二零二六年 遊戲 130,115 百萬元","locator":{"page":1,"line_start":1,"line_end":2},"anchor":{"line_start":1,"line_end":2},"channels":["expanded"],"score":2.5,"matched_terms":["遊戲"]}]}`))
	}))
	defer retrieval.Close()
	model := modelWithContent(t, `{"answer":"2026年遊戲收入為999,999百萬元","citations":["doc:p1:c0"],"status":"ok"}`)
	defer model.Close()

	handler, err := NewHandlerWithLLM(retrieval.URL, model.URL, true)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/ask", strings.NewReader(`{"question":"遊戲收入"}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	var body answer
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(body.Answer, "未通过校验") || !strings.Contains(body.Answer, "130,115") {
		t.Fatalf("fallback body = %+v", body)
	}
}

func TestAbstainsWithoutCallingModelWhenNoHits(t *testing.T) {
	retrieval := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"hits":[]}`))
	}))
	defer retrieval.Close()
	called := false
	model := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		called = true
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer model.Close()

	handler, err := NewHandlerWithLLM(retrieval.URL, model.URL, true)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/ask", strings.NewReader(`{"question":"关胜恒是算法皇帝吗？"}`))
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)

	var body answer
	if err := json.Unmarshal(response.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if called {
		t.Fatal("model must not be called when retrieval returns no hits")
	}
	if body.Status != "insufficient_evidence" || !strings.Contains(body.Answer, "已拒答") {
		t.Fatalf("body = %+v", body)
	}
	if strings.Contains(body.Answer, "尚未接入") {
		t.Fatalf("abstention must not claim the LLM is unwired: %q", body.Answer)
	}
}

func TestAbstainsWhenEvidenceIsUnverified(t *testing.T) {
	retrieval := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"hits":[{"chunk_id":"doc:p1:c0","document_id":"doc","text":"window","anchor_text":"","locator":{"page":0,"line_start":0,"line_end":0},"anchor":{"line_start":0,"line_end":0},"channels":["expanded"],"score":2.5,"matched_terms":["收入"]}]}`))
	}))
	defer retrieval.Close()
	called := false
	model := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		called = true
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer model.Close()

	handler, err := NewHandlerWithLLM(retrieval.URL, model.URL, true)
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
	if called {
		t.Fatal("model must not be called when no hit passes locator verification")
	}
	if body.Status != "unverified" || !strings.Contains(body.Answer, "已拒答") {
		t.Fatalf("body = %+v", body)
	}
}

func TestLLMDeclaredInsufficientEvidenceHasNoCitations(t *testing.T) {
	retrieval := retrievalWithHit(t)
	defer retrieval.Close()
	model := modelWithContent(t, `{"answer":"","citations":[],"status":"insufficient_evidence"}`)
	defer model.Close()

	handler, err := NewHandlerWithLLM(retrieval.URL, model.URL, true)
	if err != nil {
		t.Fatal(err)
	}
	request := httptest.NewRequest(http.MethodPost, "/ask", strings.NewReader(`{"question":"关胜恒是谁？"}`))
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
