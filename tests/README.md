# tests（待建）

分层：

- `unit`：chunking、BM25、RRF、citation、config；
- `contract`：Go/Python 契约一致性；
- `integration`：ingest → index → retrieve；
- `eval`：benchmark runner；
- `smoke`：Docker Compose 健康检查。

真实 LLM 不进默认 CI；使用 fake client 或 `--live` 手动触发。
