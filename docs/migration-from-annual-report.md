# 从 annual-report-qa-agent 迁移资产

> 源项目：`../annual-report-qa-agent`  
> 冻结基线：`c89b37c`（`feat: add line-aware hit windows to search_report`）  
> 源项目交接：`../annual-report-qa-agent/HANDOVER.md`

---

## 1. 迁移原则

1. **先冻结源项目**：打 tag，不再加功能；
2. **不复制 git history**：新仓库独立；
3. **不复制 `.env`、缓存、虚拟环境**；
4. **先迁契约和评测，再迁实现**；
5. **先包服务，再重写热点**；
6. **保留旧 baseline 对比**，避免“重写后指标不可比”。

---

## 2. 资产分级

### A. 可直接复用/小改

| 源文件 | 目标位置 | 说明 |
|---|---|---|
| `src/embedding.py` | `workers/embedding` | Embedder 协议、LSA、OpenAI 兼容端点、缓存 |
| `src/policy.py` | `core/security` | 端点/截断/审计 |
| `src/llm_config.py` | `services/model-gateway` | provider/model/key/timeout |
| `src/llm_policy.py` | `services/model-gateway` | OpenAI function calling |
| `src/agent.py` | `services/agent` | 循环模式参考 |
| `src/tools.py` | `core/tools` + `domains/finance/tools` | 拆通用调度与财务工具 |
| `scripts/check_llm.py` | `scripts/check_llm.py` | 配置 smoke check |
| `scripts/extract_pages.py` | `workers/parser` | PDF → 文本；后续扩格式 |

### B. 重点重构后复用

| 源文件 | 目标位置 | 重构点 |
|---|---|---|
| `src/retrieval.py` | `workers/retrieval` + `core/retrieval` | `page→locator`、`report→document`；保留 BM25/窗口/RRF |
| `evals/run_eval.py` | `eval` | 通用 schema、指标插件 |
| `evals/agent_eval.py` | `eval` | 通用 EvalCase、trace |
| `tests/test_retrieval*.py` | `tests` | 重写 fixture，保留行为断言 |
| `tests/test_embedding.py` | `tests` | 复用协议/缓存测试 |
| `tests/test_llm_config.py` | `tests` | 复用配置测试 |

### C. 迁移到 finance domain

| 源文件 | 目标位置 |
|---|---|
| `src/contracts/financial.py` | `domains/finance/contracts` |
| `src/data/csv_store.py` | `domains/finance/data` |
| `src/capabilities/financial_analysis/` | `domains/finance/capabilities` |
| `src/lexicon.py` | `domains/finance/terms.json` + `core/retrieval/terms.py` |
| `data/financial_facts.csv` | `domains/finance/data` |
| `corpus/pages.jsonl` | `domains/finance/corpus`（确认许可） |
| `evals/questions.json` | `domains/finance/eval`（扩题） |

### D. 不迁移

- `.env`、`.venv`、`.cache`、`.ruff_cache`、`__pycache__`；
- 旧 CLI 入口；
- 旧 README 定位；
- 旧 `pyproject.toml`；
- 本地评测输出 JSON。

---

## 3. 迁移顺序

### Step 0：冻结源项目

```bash
cd ../annual-report-qa-agent
git add README.md HANDOVER.md
git commit -m "docs: add project handover guide"
git tag v0.1.0-legacy
git push origin main --tags
```

### Step 1：新项目契约

- `Document` / `Chunk` / `SearchRequest` / `SearchHit` / `Answer` / `Citation` / `EvalCase`；
- OpenAPI + JSON Schema；
- 先不写业务逻辑。

### Step 2：评测 baseline

- 迁 `questions.json` 到新 schema；
- 用旧 Python 检索跑出 baseline；
- 新服务必须对比 baseline。

### Step 3：检索服务

- 复制 `retrieval.py` 的 chunking/BM25/hit window；
- 改成 `document/locator`；
- 保留 `chunk_id` 稳定；
- 测试 q01 跨 chunk 窗口。

### Step 4：ingest

- 上传/解析/chunk/metadata；
- 队列、幂等、失败状态；
- 先 PDF，再 HTML/DOCX。

### Step 5：Agent / Model Gateway

- 迁 `llm_config` / `llm_policy`；
- 工具注册表；
- trace/timeout/retry/abstention；
- 先 DeepSeek/OpenAI 兼容端点。

### Step 6：数据与评测扩展

- 100+ 文档；
- 100+ 题，Gold Evidence；
- Hit@4/Recall@4/MRR、citation、faithfulness、abstention。

---

## 4. 不要照抄的部分

- 年报专用 system prompt；
- 旧 CLI 参数；
- `page: int` 作为全局主键；
- 财务 CSV 作为 core 数据模型；
- 旧 README 的“Agent”叙事。

---

## 5. 资产验收

迁移完成时，新项目应能回答：

- 旧项目 q01 的 199 页窗口能否在新检索服务复现？
- 旧项目 158 个测试中，哪些行为在新项目仍有对应测试？
- 新 benchmark 的 baseline 是否与旧项目一致？
- 引用能否定位到 document/page/line？
- 无证据时是否拒答？

---

## 6. 关联文档

- 旧项目交接：`../annual-report-qa-agent/HANDOVER.md`
- 旧项目迁移盘点：`../TRANSITION_PLAN.md`
- 新项目架构：`architecture.md`
- 新项目交接：`../HANDOVER.md`
