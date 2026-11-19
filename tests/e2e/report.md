# System test report

- cases: 14
- passed: 14
- failed: 0
- generated: 2026-11-19 19:27:31

| case | service | endpoint | status | result | latency |
|---|---|---|---:|---|---:|
| health_gateway | gateway | `GET /healthz` | 200 | PASS | 7 ms |
| health_retrieval | retrieval | `GET /healthz` | 200 | PASS | 2 ms |
| health_agent | agent | `GET /healthz` | 200 | PASS | 0 ms |
| search_expanded_hit | gateway | `POST /search` | 200 | PASS | 3 ms |
| search_metadata_filter | gateway | `POST /search` | 200 | PASS | 2 ms |
| search_oov_empty | gateway | `POST /search` | 200 | PASS | 2 ms |
| search_unknown_filter_error | retrieval | `POST /search` | 400 | PASS | 1 ms |
| search_empty_query_validation | retrieval | `POST /search` | 422 | PASS | 1 ms |
| ask_extractive_answer | gateway | `POST /ask` | 200 | PASS | 3 ms |
| ask_metadata_filter | agent | `POST /ask` | 200 | PASS | 2 ms |
| ask_abstains_oov | gateway | `POST /ask` | 200 | PASS | 2 ms |
| ask_empty_question | agent | `POST /ask` | 400 | PASS | 1 ms |
| health_model_gateway | model-gateway | `GET /healthz` | 200 | PASS | 1 ms |
| llm_disabled | model-gateway | `POST /v1/chat/completions` | 503 | PASS | 1 ms |
