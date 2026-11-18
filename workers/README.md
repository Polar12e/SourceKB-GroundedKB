# workers（骨架）

Python worker：

| worker | 职责 | 状态 |
|---|---|---|
| `retrieval` | BM25 / dense / RRF / hit window | 骨架：`/healthz`；`/search` 返回 501，待 T1.2 迁移 |
| `embedding` | bge-m3 / OpenAI 兼容 embedding | 待建 |
| `parser` | PDF/HTML/DOCX、表格、OCR | 待建 |
| `eval` | Hit@k / Recall / citation / abstention | 待建 |

当前只落地 retrieval 的 FastAPI 骨架，不重写旧算法：

- 依赖：`workers/retrieval/requirements.txt`；
- 测试：`make py-test`；
- 启动：`make py-run-retrieval`（:8081）；
- 契约：`contracts/schemas/search-*.schema.json`。

真实 LLM 调用不进入默认 CI。
