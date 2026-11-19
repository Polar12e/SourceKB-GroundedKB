# workers/retrieval

Python retrieval worker，负责四通路检索（`bm25` / `expanded` / `dense` / `hybrid`）、hit window 与 filters。T1.2 已从旧项目迁移：

- **Chunking**：行感知切块、字符重叠、稳定 `chunk_id = document_id:p<page>:c<index>`；
- **BM25**：数字归一化 + 中文 bigram，`k1=1.5`、`b=0.75`，chunk 级排序（页面分组后置）；
- **简繁归一**：`zhconv` 将繁體转简体，腾讯/中芯港股文档可用简体 query 命中；
- **Metadata filters**：`company` / `year` / `doc_type` / `document_id`，未知字段返回 400；
- **Hit window / anchor**：`locator`/`text` 是展示窗口；`anchor`/`anchor_text` 是命中 chunk 原文与行区间；
- **Hit channels**：`channels` 累积所有命中通道，供 rerank/verifier 使用；
- **四通路**：`pipeline.py` 从 `config/retrieval.yaml` 构建 `bm25`、`expanded`、`dense`、`hybrid`；`hybrid` 按 `chunk_id` 融合，页面分组后置；
- **Profile**：`profile.py` 读取 `profiles.finance`（模式、内置扩展、报表页乘法 prior α）；名词表由 `domains/finance/terms.json` 提供；
- **Embedding**：`workers/embedding/` 提供 LSA 与 OpenAI 兼容 provider；`pipeline.create_embedder` 按 `dense.provider: lsa|openai` 分发，openai 需要 `model/base_url/dim` 与 `api_key_env` 指定的环境变量。离线 LSA 实测弱于 BM25，默认不启用 dense。

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

# 切换通路（默认取 config/retrieval.yaml 的 default_channel）
RETRIEVAL_CORPUS=data/private/corpus/pages.jsonl \
RETRIEVAL_CHANNEL=expanded \
  make py-run-retrieval

curl -X POST http://127.0.0.1:8081/search \
  -H 'content-type: application/json' \
  -d '{"query":"营业成本重述","top_k":3}'

# 10 文档 + metadata filter
curl -X POST http://127.0.0.1:8081/search \
  -H 'content-type: application/json' \
  -d '{"query":"2025年营业收入","top_k":3,"filters":{"company":"688981.SH"}}'
```

`RETRIEVAL_CORPUS` 为 JSONL，每行：`{"document_id": "...", "page": 1, "text": "..."}`；`document_id` 可省略（默认 `legacy`）。`RETRIEVAL_MANIFEST` 默认 `data/manifests/documents.json`，用于 metadata filters。

## 名词表转换

财务名词配置在 `domains/finance/terms.json`。查询先做简繁/数字/空白归一，再按中文 bigram 与名词表各组匹配；命中的同组名词以 0.45 权重加入，原 query 词保持 1.0。`auto` 模式只在 query coverage < 0.5 时启用。完整步骤见 [domains/finance/README.md](../../domains/finance/README.md)。

## 边界

- dense / embedding 已迁移（`workers/embedding/`、`dense.py`），但默认关闭；旧 LSA 实测弱于 BM25，等真实 embedding 模型再切换。
- 旧 corpus 不提交到仓库；只使用合成 fixture 和外部路径做 baseline。
