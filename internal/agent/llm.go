package agent

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"net/http"
	"regexp"
	"strconv"
	"strings"
)

const (
	extractiveWarning = "【当前为抽取式基线，尚未接入 LLM 生成】\n\n"
	fallbackWarning   = "【LLM 调用未通过校验，以下为抽取式回答】\n\n"
)

type chatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type chatRequest struct {
	Model       string        `json:"model"`
	Messages    []chatMessage `json:"messages"`
	Temperature float64       `json:"temperature"`
	MaxTokens   int           `json:"max_tokens"`
}

type chatResponse struct {
	Choices []struct {
		Message chatMessage `json:"message"`
	} `json:"choices"`
}

type llmAnswer struct {
	Answer    string   `json:"answer"`
	Status    string   `json:"status"`
	Citations []string `json:"citations"`
}

type citationIndex struct {
	hit searchHit
}

var numberPattern = regexp.MustCompile(`\d[\d,]*(?:\.\d+)?`)

func parseNumber(raw string) (float64, bool) {
	value, err := strconv.ParseFloat(strings.ReplaceAll(raw, ",", ""), 64)
	return value, err == nil
}

func nearlyEqual(a, b float64) bool {
	scale := math.Max(math.Abs(a), math.Abs(b))
	return math.Abs(a-b) <= 1e-6*math.Max(scale, 1)
}

// numberSupported accepts the same measurement even when the model converts
// units (for example 130,115 百万元 -> 1,301.15 亿元).
func numberSupported(answerNumber, citedText string) bool {
	if strings.Contains(citedText, answerNumber) {
		return true
	}
	answerValue, ok := parseNumber(answerNumber)
	if !ok {
		return false
	}
	for _, citedNumber := range numberPattern.FindAllString(citedText, -1) {
		citedValue, ok := parseNumber(citedNumber)
		if !ok {
			continue
		}
		if nearlyEqual(answerValue, citedValue) ||
			nearlyEqual(answerValue*100, citedValue) ||
			nearlyEqual(answerValue, citedValue*100) {
			return true
		}
	}
	return false
}

func (h *Handler) answerWithLLM(ctx context.Context, question string, hits []searchHit) (answer, error) {
	if h.modelURL == "" {
		return answer{}, errors.New("model gateway URL is empty")
	}
	byID := make(map[string]searchHit, len(hits))
	var evidence strings.Builder
	for index, hit := range hits {
		if index >= 5 {
			break
		}
		byID[hit.ChunkID] = hit
		fmt.Fprintf(&evidence, "[%s]\n%s\n\n", hit.ChunkID, strings.TrimSpace(hit.AnchorText))
	}

	system := "You are a grounded financial-document assistant. " +
		"Answer only from the supplied evidence. Do not add facts, numbers, years, or entities absent from cited evidence. " +
		"Return ONLY a JSON object with keys: answer (string), citations (array of exact chunk ids), status (\"ok\" or \"insufficient_evidence\"). " +
		"Do not include markdown fences."
	user := "Question:\n" + question + "\n\nEvidence:\n" + evidence.String() +
		"\nIf evidence is insufficient, return status=\"insufficient_evidence\" and no citations."

	requestBody := chatRequest{
		Model:       "deepseek-chat",
		Messages:    []chatMessage{{Role: "system", Content: system}, {Role: "user", Content: user}},
		Temperature: 0,
		MaxTokens:   1024,
	}
	payload, err := json.Marshal(requestBody)
	if err != nil {
		return answer{}, err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, h.modelURL+"/v1/chat/completions", bytes.NewReader(payload))
	if err != nil {
		return answer{}, err
	}
	request.Header.Set("Content-Type", "application/json")
	response, err := h.modelClient.Do(request)
	if err != nil {
		return answer{}, err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(response.Body, 512))
		return answer{}, fmt.Errorf("model gateway %d: %s", response.StatusCode, strings.TrimSpace(string(body)))
	}
	var chat chatResponse
	if err := json.NewDecoder(response.Body).Decode(&chat); err != nil {
		return answer{}, err
	}
	if len(chat.Choices) == 0 {
		return answer{}, errors.New("model returned no choices")
	}
	raw := strings.TrimSpace(chat.Choices[0].Message.Content)
	raw = strings.TrimPrefix(raw, "```json")
	raw = strings.TrimPrefix(raw, "```")
	raw = strings.TrimSuffix(raw, "```")
	var parsed llmAnswer
	if err := json.Unmarshal([]byte(strings.TrimSpace(raw)), &parsed); err != nil {
		return answer{}, err
	}
	if parsed.Status == "insufficient_evidence" {
		return answer{
			Answer:    extractiveWarning + "insufficient evidence",
			Status:    "insufficient_evidence",
			Citations: []citation{},
		}, nil
	}
	if parsed.Status != "ok" || strings.TrimSpace(parsed.Answer) == "" || len(parsed.Citations) == 0 {
		return answer{}, errors.New("model output is not a supported grounded answer")
	}

	chosen := make([]citationIndex, 0, len(parsed.Citations))
	seen := map[string]bool{}
	for _, id := range parsed.Citations {
		if seen[id] {
			continue
		}
		hit, ok := byID[id]
		if !ok {
			return answer{}, fmt.Errorf("model cited unknown chunk: %s", id)
		}
		seen[id] = true
		chosen = append(chosen, citationIndex{hit: hit})
	}
	if len(chosen) == 0 {
		return answer{}, errors.New("model returned no known citations")
	}

	citedText := ""
	for _, item := range chosen {
		citedText += "\n" + item.hit.AnchorText
	}
	for _, number := range numberPattern.FindAllString(parsed.Answer, -1) {
		if !numberSupported(number, citedText) {
			return answer{}, fmt.Errorf("answer number %q is not present in cited evidence", number)
		}
	}

	citations := make([]citation, 0, 3)
	for _, item := range chosen {
		if len(citations) == 3 {
			break
		}
		hit := item.hit
		citations = append(citations, citation{
			DocumentID: hit.DocumentID,
			Page:       hit.Locator.Page,
			LineStart:  hit.Anchor.LineStart,
			LineEnd:    hit.Anchor.LineEnd,
			Quote:      strings.TrimSpace(hit.AnchorText),
		})
	}
	return answer{Answer: parsed.Answer, Status: "ok", Citations: citations}, nil
}
