# workers/retrieval

Python retrieval worker，负责 BM25 / hit window / RRF。T1.2 已从旧项目迁移：

- **Chunking**：行感知切块、字符重叠、稳定 `chunk_id = document_id:p<page>:c<index>`；
- **BM25**：数字归一化 + 中文 bigram，`k1=1.5`、`b=0.75`，按页聚合最佳 chunk；
- **Hit window**：从 chunk 的 page/line locator 向上下扩展 2 行，跨 chunk 边界；
- **RRF**：`fusion.py` 提供加权 reciprocal-rank fusion（当前 API 只启用 BM25 单通道）；
- **Finance profile**：`domains/finance/retrieval.py` 保留旧 `bm25` 的 ratio/restatement 扩展和报表页 +18 加分。

## API

- `GET /healthz`：`{"status":"ok","service":"retrieval"}`
- `POST /search`：返回 `SearchResponse`；每个 hit 带 `chunk_id`、page/line locator、score、matched_terms。
- 未加载 corpus 时返回 `{"hits": []}`，不伪造命中。

## 本地运行

```bash
make py-install
make py-test

RETRIEVAL_CORPUS=workers/retrieval/tests/fixtures/sample_pages.jsonl \
  make py-run-retrieval

curl -X POST http://127.0.0.1:8081/search \
  -H 'content-type: application/json' \
  -d '{"query":"营业成本重述","top_k":3}'
```

`RETRIEVAL_CORPUS` 为 JSONL，每行：`{"document_id": "...", "page": 1, "text": "..."}`；`document_id` 可省略（默认 `legacy`）。

## 边界

- dense / embedding 通道尚未迁移；`HybridIndex` 已就绪，等 `workers/embedding` 接入。
- 旧项目的完整口语词表（`src/lexicon.py`）尚未迁移，当前只保留 builtin 财务扩展。
- 旧 corpus 不提交到仓库；只使用合成 fixture 和外部路径做 baseline。
