# GroundedKB 架构设计

> 状态：设计稿；Go 服务骨架已落地，契约与 Python worker 待建。  
> 目标：可溯源的 Agentic RAG 知识库平台；Go 负责服务边界，Python 负责检索/模型/评测。

---

## 1. 设计目标

1. **可溯源**：答案能回到文档、页码、行、原文片段；
2. **可拒答**：没有证据时明确说“不够”，不硬答；
3. **可评测**：检索、答案、引用、拒答、成本都可离线回归；
4. **可服务化**：多文档、多请求、异步 ingest、trace、限流；
5. **可迁移**：先复用旧年报项目的检索/评测，再逐步服务化。

---

## 2. 总体架构

```text
                ┌────────────────────┐
                │ Web / SDK / CLI     │
                └─────────┬──────────┘
                          │ HTTP / gRPC
                ┌─────────▼──────────┐
                │ API Gateway (Go)    │
                │ auth / rate limit   │
                │ request trace       │
                └─────────┬──────────┘
                          │
                ┌─────────▼──────────┐
                │ Agent Runtime (Go)  │
                │ tool registry       │
                │ policy / timeout    │
                │ step trace          │
                └───┬────────┬───────┘
                    │        │
        ┌───────────▼──┐  ┌──▼─────────────┐
        │ Retrieval    │  │ Model Gateway  │
        │ Service      │  │ (Go)           │
        │ (Python)     │  │ provider/retry │
        └───┬──────┬───┘  └──┬─────────────┘
            │      │         │
      ┌─────▼─┐  ┌─▼─────┐   │
      │ BM25  │  │ Vector│   │
      │ index │  │ DB    │   │
      └───────┘  └───────┘   │
                              │
                ┌─────────────▼──────────┐
                │ Python workers         │
                │ embedding / parser /   │
                │ eval                   │
                └────────────────────────┘

Ingest:
  upload → object store → queue → ingest worker (Go)
        → parser/OCR (Python) → chunks → metadata → index

Storage:
  Postgres: documents / jobs / eval results / trace metadata
  Object store: original files / page images
  Redis: cache / locks / rate limit
  Vector DB: Milvus / pgvector / OpenSearch
```

---

## 3. 服务职责

### Gateway（Go）

- HTTP API / SDK 入口；
- 认证/租户（第一版可简化）；
- 限流、请求 ID、超时；
- 把请求路由到 Agent Runtime；
- 不直接访问向量库。

### Ingest Worker（Go）

- 接收上传事件/任务；
- 任务状态机：`queued → parsing → indexing → ready/failed`；
- 幂等键：`document_hash`；
- 失败重试/死信；
- 调用 Python parser worker；
- 写入 Postgres/对象存储。

### Retrieval Service（Python 先复用）

- 文档/块索引；
- BM25 + dense + RRF；
- metadata filter；
- hit window（页标题 + 行号）；
- 返回 `document_id/page/line/text/score/matched_terms`；
- 第一版可以 FastAPI；后续热点可迁 Go。

### Agent Runtime（Go）

- 工具注册表；
- 单步/多步策略；
- 工具超时、重试、取消；
- `trace_id` / `step_id`；
- max_steps、拒答、最终答案校验；
- 不直接算财务数字，调用工具。

### Model Gateway（Go）

- OpenAI 兼容 provider 路由；
- API key 管理（secret manager）；
- 超时/重试/熔断/fallback；
- token/成本统计；
- 不允许绕过的端点策略。

### Python workers

- parser：PDF/HTML/DOCX、表格、OCR；
- embedding：bge-m3 / API embedding；
- eval：benchmark、citation、faithfulness、abstention。

---

## 4. 核心契约

### Document

```json
{
  "document_id": "midea-2024",
  "source": "upload|url",
  "title": "美的集团 2024 年年度报告",
  "company": "000333.SZ",
  "year": 2024,
  "doc_type": "annual_report",
  "sha256": "...",
  "page_count": 452,
  "status": "ready"
}
```

### Chunk

```json
{
  "chunk_id": "midea-2024:p199:c0",
  "document_id": "midea-2024",
  "text": "...",
  "locator": {
    "page": 199,
    "line_start": 1,
    "line_end": 18,
    "section": "财务报表附注"
  },
  "metadata": {
    "company": "000333.SZ",
    "year": 2024
  }
}
```

### SearchRequest / SearchHit

```json
{
  "query": "2023年营业成本为什么重述？",
  "filters": {"company": "000333.SZ", "year": 2024},
  "top_k": 5
}
```

```json
{
  "document_id": "midea-2024",
  "page": 199,
  "line_start": 1,
  "line_end": 18,
  "score": 46.575,
  "matched_terms": ["营业", "成本", "重述"],
  "text": "1: ...\n17: 营业成本  2,928,031 -"
}
```

### Answer / Citation

```json
{
  "answer": "...",
  "status": "ok|insufficient_evidence|error",
  "citations": [
    {
      "document_id": "midea-2024",
      "page": 199,
      "line_start": 16,
      "line_end": 17,
      "quote": "销售费用 (2,928,031) - / 营业成本 2,928,031 -"
    }
  ],
  "trace_id": "trace_..."
}
```

### EvalCase

```json
{
  "case_id": "finance-001",
  "question": "...",
  "type": "lookup|explain|compare|multihop|table|negative|ambiguous",
  "gold_evidence": [
    {"document_id": "midea-2024", "page": 199, "line_start": 16, "line_end": 17}
  ],
  "expected": {"value": "...", "unit": "千元"},
  "split": "dev|holdout|diagnostic"
}
```

---

## 5. 关键流程

### 5.1 文档入库

```text
POST /documents
  → 保存原文件 + hash
  → 创建 document 记录（status=queued）
  → 投递 ingest job
  → parser worker 抽取文本/表格/OCR
  → chunker 生成 chunk_id + locator
  → embedding worker 生成向量
  → index writer 写 BM25/向量
  → status=ready
```

幂等：

- 同一 `sha256` 不重复入库；
- 任务重试使用同一 `document_id`；
- 索引写入按 `document_id` 覆盖。

### 5.2 问答

```text
POST /ask
  → gateway 限流/认证
  → agent runtime 创建 trace
  → route: retrieval / structured tool / abstain
  → retrieval service 返回 top-k windows
  → agent 选择 read/tool
  → answer + citations
  → verifier 检查 citation/数字
  → 返回 answer + trace
```

### 5.3 评测

```text
eval runner
  → 加载 EvalCase
  → 调 retrieval / agent
  → 计算 Hit@k / Recall@k / MRR / citation / abstention
  → 写 Postgres/JSON
  → 生成 Markdown 报告
```

---

## 6. 可观测性

每次请求记录：

- `trace_id` / `request_id`；
- 检索耗时、top-k、filters；
- LLM provider/model、tokens、成本；
- 工具调用序列、错误码；
- 是否拒答、citation 数量；
- 总延迟。

指标：

- QPS、P50/P95/P99；
- 错误率、超时率；
- 检索召回/引用；
- 每查询 token/成本；
- ingest 队列积压/失败率。

---

## 7. 第一版边界

- 单租户/单组织足够；
- 不做复杂权限；
- 不做全类型 OCR；
- 不做自研 ANN/BM25；
- 不做 GPU serving；
- 不做完整 UI，先 API + 简单证据页。

---

## 8. 关键决策

| 决策 | 原因 |
|---|---|
| Go + Python | Go 服务边界/并发；Python 检索/模型/评测生态 |
| Python retrieval 先复用 | 避免重写已验证算法导致指标退化 |
| 契约优先 | 多服务/多语言需要稳定接口 |
| 引用优先 | “高保真”必须可验证 |
| 拒答是一等能力 | 无证据硬答比不答更糟 |
| 不自研向量库 | 第一版用 Milvus/pgvector/OpenSearch |
| C++ 暂不引入 | 没有 benchmark 证明热点前不增加复杂度 |
