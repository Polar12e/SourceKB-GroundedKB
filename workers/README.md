# workers（进行中）

Python worker：

| worker | 职责 | 状态 |
|---|---|---|
| `retrieval` | BM25 / hit window / RRF | 已落地 BM25 + finance profile；dense 待建 |
| `embedding` | bge-m3 / OpenAI 兼容 embedding | LsaEmbedder + OpenAICompatibleEmbedder 已迁移 |
| `parser` | PDF/HTML/DOCX、表格、OCR | PDF 解析 + 可选 OCR 已落地 |
| `eval` | Hit@k / Recall / citation / abstention | 待建 |

retrieval 入口：

- 依赖：`workers/retrieval/requirements.txt`；
- 测试：`make py-test`（66 项，含 API↔契约、manifest、filters、embedding、dense、四通路、eval metrics）；
- 启动：`RETRIEVAL_CORPUS=... make py-run-retrieval`（:8081）；
- 契约：`contracts/schemas/search-*.schema.json`。

真实 LLM 调用不进入默认 CI。
