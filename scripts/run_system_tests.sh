#!/usr/bin/env bash
# Start the local stack against synthetic fixtures and run black-box tests.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/.tools"

make -s build

export RETRIEVAL_CORPUS="$ROOT/tests/e2e/fixtures/pages.jsonl"
export RETRIEVAL_MANIFEST="$ROOT/tests/e2e/fixtures/documents.json"
export RETRIEVAL_URL="http://127.0.0.1:8081"
export AGENT_URL="http://127.0.0.1:8083"

pids=()
cleanup() {
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

"$ROOT/.venv/bin/python" -m uvicorn workers.retrieval.app:app \
  --host 127.0.0.1 --port 8081 >"$ROOT/.tools/system-retrieval.log" 2>&1 &
pids+=("$!")
for _ in $(seq 1 60); do
  curl -fsS http://127.0.0.1:8081/healthz >/dev/null 2>&1 && break
  sleep 0.2
done

"$ROOT/bin/agent" >"$ROOT/.tools/system-agent.log" 2>&1 &
pids+=("$!")
for _ in $(seq 1 60); do
  curl -fsS http://127.0.0.1:8083/healthz >/dev/null 2>&1 && break
  sleep 0.2
done

"$ROOT/bin/gateway" >"$ROOT/.tools/system-gateway.log" 2>&1 &
pids+=("$!")
for _ in $(seq 1 60); do
  curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1 && break
  sleep 0.2
done

set +e
"$ROOT/.venv/bin/python" "$ROOT/tests/e2e/run_system.py"
status=$?
set -e
exit "$status"
