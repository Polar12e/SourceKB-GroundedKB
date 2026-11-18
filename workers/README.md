# workers（待建）

Python worker：

| worker | 职责 | 复用来源 |
|---|---|---|
| `retrieval` | BM25 / dense / RRF / hit window | 旧项目 `src/retrieval.py` |
| `embedding` | bge-m3 / OpenAI 兼容 embedding | 旧项目 `src/embedding.py` |
| `parser` | PDF/HTML/DOCX、表格、OCR | 旧项目 `scripts/extract_pages.py` + 新增 |
| `eval` | Hit@k / Recall / citation / abstention | 旧项目 `evals/*` |

第一版 retrieval worker 先用 FastAPI 包住旧算法，不重写。
