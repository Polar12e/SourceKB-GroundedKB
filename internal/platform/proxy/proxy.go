// Package proxy provides small JSON-friendly reverse proxies.
package proxy

import (
	"net/http"
	"net/http/httputil"
	"net/url"
)

// New returns a reverse proxy for target. The target path is preserved from the
// incoming request, so /search -> {target}/search.
func New(target string) (http.Handler, error) {
	parsed, err := url.Parse(target)
	if err != nil {
		return nil, err
	}
	reverse := httputil.NewSingleHostReverseProxy(parsed)
	reverse.ErrorHandler = func(w http.ResponseWriter, _ *http.Request, _ error) {
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.WriteHeader(http.StatusBadGateway)
		_, _ = w.Write([]byte(`{"error":{"code":"upstream_unavailable","message":"upstream service unavailable"}}`))
	}
	return reverse, nil
}
