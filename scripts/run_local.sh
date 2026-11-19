#!/usr/bin/env bash
# Start retrieval + agent + gateway locally (no Docker).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  echo "missing .venv; run: make py-install" >&2
  exit 1
fi

# Load local secrets/config. Values are not printed.
if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/.env"
  set +a
fi

mkdir -p "$ROOT/.tools"
make -s build

export RETRIEVAL_MANIFEST="${RETRIEVAL_MANIFEST:-$ROOT/data/manifests/documents.json}"
if [ -f "${RETRIEVAL_CORPUS:-$ROOT/data/private/corpus/pages.jsonl}" ]; then
  export RETRIEVAL_CORPUS="${RETRIEVAL_CORPUS:-$ROOT/data/private/corpus/pages.jsonl}"
else
  echo "warning: corpus not found; /search returns no hits" >&2
  unset RETRIEVAL_CORPUS
fi
export RETRIEVAL_URL="${RETRIEVAL_URL:-http://127.0.0.1:8081}"
export AGENT_URL="${AGENT_URL:-http://127.0.0.1:8083}"
export MODEL_GATEWAY_URL="${MODEL_GATEWAY_URL:-http://127.0.0.1:8084}"

pids=()
cleanup() {
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

"$ROOT/.venv/bin/python" -m uvicorn workers.retrieval.app:app \
  --host 127.0.0.1 --port 8081 >"$ROOT/.tools/retrieval.log" 2>&1 &
pids+=("$!")

for _ in $(seq 1 50); do
  curl -fsS http://127.0.0.1:8081/healthz >/dev/null 2>&1 && break
  sleep 0.2
done

"$ROOT/bin/agent" >"$ROOT/.tools/agent.log" 2>&1 &
pids+=("$!")
for _ in $(seq 1 50); do
  curl -fsS http://127.0.0.1:8083/healthz >/dev/null 2>&1 && break
  sleep 0.2
done

"$ROOT/bin/model-gateway" >"$ROOT/.tools/model-gateway.log" 2>&1 &
pids+=("$!")
"$ROOT/bin/gateway" >"$ROOT/.tools/gateway.log" 2>&1 &
pids+=("$!")
for _ in $(seq 1 50); do
  curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1 && break
  sleep 0.2
done

echo "retrieval : http://127.0.0.1:8081"
echo "agent     : http://127.0.0.1:8083"
echo "model-gw  : http://127.0.0.1:8084"
echo "gateway   : http://127.0.0.1:8080"
echo "try: curl -s http://127.0.0.1:8080/search -H 'content-type: application/json' -d '{\"query\":\"营业收入\"}'"
echo "ctrl-c to stop"
wait
