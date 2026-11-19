# GroundedKB 新项目交接文档

> 项目名：高保真知识库（GroundedKB）  
> 定位：可溯源的 Agentic RAG 知识库平台  
> 技术栈：Go + Python  
> 状态：**Go/Python 骨架、BM25 检索、10 文档本地语料与契约 v0 草案已落地；Agent/ingest 待实现**  
> 创建日期：2026-11-18

---

## 1. 交接摘要

当前目录是 GroundedKB 的新项目起点，Go 骨架、Python retrieval 服务与 10 文档本地语料可运行，但还不是完整系统。

已完成：

- 项目命名与定位；
- Go + Python 技术栈边界；
- 目录骨架；
- 架构原则；
- 旧项目资产迁移清单；
- 风险与里程碑；
- Go 服务骨架（gateway / ingest / agent / model-gateway + `/healthz`）；
- Python retrieval：BM25 + hit window + RRF + finance profile（`/search` 可用）；
- Retrieval 增强：metadata filters（company/year/doc_type/document_id）+ 简繁归一；
- RAG 资产：财务名词表（terms.json）+ embedding provider（lsa/openai）+ dense channel + RAG notes；
- 四通路通用化：bm25 / expanded / dense / hybrid，由 `config/retrieval.yaml` 驱动；
- 10 文档本地语料：PDF parser + manifest + 页级 JSONL（美的/腾讯/中芯国际/小米）；
- 10 题 retrieval eval：Hit@4=1.000 / Recall@4=0.975 / MRR=1.000，与旧 `bm25` 一致；
- 跨文档 40 题 A/B：修正 Gold 后 hybrid 与 expanded 持平，默认保持 expanded；
- 契约 v0 草案（13 个 JSON Schema + OpenAPI）；
- Compose / Dockerfile 骨架（`config` 校验通过，未在会话内运行）；
- CI 骨架。

未完成：

- 契约 v0 评审与冻结；
- Xiaomi 3 份 OCR 重抽取（当前 text_quality=low）；
- dense / embedding 通道；
- ingest pipeline（数据库/索引服务）；
- 跨文档 10 题（腾讯/中芯/小米）；
- benchmark；
- Web/API。

接手人应先阅读：

1. `README.md`
2. `docs/architecture.md`
3. `docs/migration-from-annual-report.md`
4. 旧项目 `../annual-report-qa-agent/HANDOVER.md`

---

## 2. 项目定位

### 一句话

> 让每个答案都能回到原文：可溯源的 Agentic RAG 知识库平台。

### 高保真的定义

不是营销词，而是三项可度量能力：

1. **Citation fidelity**：答案能定位到文档、页码、行、原文片段；
2. **Answer faithfulness**：事实能被证据支持；
3. **Abstention fidelity**：没有证据时明确拒答。

加上检索和 Agent 的可观测性：

- hybrid retrieval（BM25 + dense + RRF）；
- metadata filter；
- 工具调用 trace；
- 成本/token/延迟统计。

### 非目标

第一版不做完整 SaaS、多租户计费、自研向量库、GPU 推理、全类型 OCR。

---

## 3. 架构决策

### 3.1 Go + Python 分界

| 层 | 语言 | 职责 |
|---|---|---|
| API Gateway | Go | HTTP/认证/限流/请求追踪 |
| Ingest Worker | Go | 上传、任务队列、状态、幂等 |
| Agent Runtime | Go | 工具注册、策略、超时、trace |
| Model Gateway | Go | provider 路由、重试、成本统计 |
| Retrieval Service | Python 先复用 | 检索算法、窗口、过滤 |
| Embedding Worker | Python | bge-m3 / API embedding |
| Parser / OCR | Python | PDF/HTML/DOCX、表格、OCR |
| Eval Service | Python | benchmark、citation、abstention |
| Web | TypeScript（后续） | 文档库、问答、证据面板 |

**不要第一周就把 BM25 重写成 Go。** 先用 Python 包住已验证的检索逻辑，Go 负责服务边界；只有在 benchmark 证明瓶颈后才迁移热点。

### 3.2 存储

计划：

- PostgreSQL：文档元数据、任务状态、评测结果；
- 对象存储：PDF/原始文件/页面图；
- Redis：缓存、限流、任务锁；
- 向量库：Milvus / pgvector / OpenSearch（第一版择一）。

第一版不需要分布式部署。

### 3.3 契约优先

先定义接口，再写服务：

- `Document`
- `Chunk`
- `SearchRequest` / `SearchHit`
- `Answer` / `Citation`
- `ToolCall` / `Trace`
- `EvalCase` / `EvalResult`

建议 OpenAPI + JSON Schema 先落地；服务内部可用 protobuf/gRPC。

---

## 4. 从旧项目迁移什么

旧项目：`../annual-report-qa-agent`，基线 commit `c89b37c`。

### 优先迁移

| 旧资产 | 新用途 | 处理 |
|---|---|---|
| `src/retrieval.py` | `core/retrieval` + Python retrieval service | 复制后去 `page/report` 领域化 |
| `src/embedding.py` | embedding worker | 修 policy/cache key 后复用 |
| `src/policy.py` | core/security | 通用端点/截断/审计 |
| `src/llm_config.py` | model gateway 配置 | 加 temperature |
| `src/llm_policy.py` | model adapter | 去财务 prompt |
| `src/agent.py` | agent runtime 参考 | 保留循环/Step 思路 |
| `src/tools.py` | 工具注册表 | 拆分通用与财务工具 |
| `evals/run_eval.py` | eval runner | 重写 schema |
| `evals/agent_eval.py` | eval runner | 重写 schema |
| `evals/questions.json` | finance seed | 扩题、补 Gold Evidence |

### 移到 `domains/finance`

- `contracts/financial.py`
- `data/csv_store.py`
- `capabilities/financial_analysis/`
- `lexicon.py`
- `financial_facts.csv`
- `corpus/pages.jsonl`
- 财务专用 prompt/工具描述

### 不迁移

- `.env`、`.venv`、`.cache`、`.ruff_cache`、`__pycache__`
- 旧 CLI
- 旧 README / 应用定位
- 旧 pyproject

### 迁移原则

1. 先迁评测/契约，再迁实现；
2. 先包服务，再重写热点；
3. 每次迁移保留旧 baseline 对比；
4. 不复制 git history；
5. 旧项目打 tag `v0.1.0-legacy`，只做交接/bugfix。

详细清单见 `docs/migration-from-annual-report.md`。

---

## 5. 新项目目录

```text
grounded-kb/
├─ README.md
├─ HANDOVER.md
├─ Makefile                   # Go / Python / 契约入口
├─ go.mod
├─ requirements-dev.txt
├─ .env.example
├─ .gitignore
├─ .dockerignore
├─ .github/workflows/ci.yml
├─ scripts/
│  ├─ goenv.sh
│  └─ check_contracts.py
├─ config/                    # 四通路参数
├─ data/                      # manifest 提交；private 语料忽略
├─ eval/                      # EvalCase + retrieval eval runner
├─ docs/
│  ├─ architecture.md
│  └─ migration-from-annual-report.md
├─ contracts/
│  ├─ openapi.yaml
│  ├─ schemas/
│  └─ examples/
├─ services/
│  ├─ gateway/                # Go
│  ├─ ingest/                 # Go
│  ├─ agent/                  # Go
│  └─ model-gateway/          # Go
├─ internal/                  # Go 共享平台包
├─ workers/
│  ├─ retrieval/              # 四通路
│  ├─ embedding/              # LSA / OpenAI-compatible
│  ├─ parser/                 # PDF + OCR
│  └─ eval/                   # 待建（根目录 eval/ 已有 runner）
├─ core/                      # 算法/协议（text.py + terms.py）
├─ domains/finance/           # 财务名词配置 + 参数
├─ deploy/
│  ├─ compose.yaml
│  └─ docker/go-service.Dockerfile
└─ tests/
```

Go/Python 骨架、BM25 检索、10 文档本地语料、10 题 eval 与契约草案已落地；Xiaomi OCR、跨文档题、dense、ingest、Agent 业务与 Compose 运行待补。

---

## 6. 里程碑

### M0：契约与骨架

- 写 OpenAPI/JSON Schema；
- 创建 Go service skeleton / Python worker skeleton；
- Docker Compose：Postgres + Redis + 一个 Python retrieval service；
- README 可运行。

验收：`docker compose up` 能启动；`/healthz` 可用。

### M1：检索切片

- 导入 10 份文档；
- chunk + metadata；
- BM25 + dense + RRF；
- `POST /search` 返回 citation locator；
- 10 题 retrieval eval。

验收：Hit@4、Recall@4 有 baseline；页面/行号可回链。

### M2：Agent + 引用

- Go agent runtime；
- 工具注册：search/read/financial；
- 答案必须带 citation；
- 无证据拒答；
- trace 记录工具序列。

验收：10~20 题端到端；引用可核对；拒答不编造。

### M3：100 文档 / 100 题

- finance vertical 扩文档；
- 100 题 Gold Evidence；
- 对比 BM25 / dense / hybrid / agentic；
- 输出 benchmark 报告。

### M4：平台化

- ingest 异步任务；
- 索引版本/重建；
- 模型网关 fallback；
- 指标/日志/成本；
- 基础 Web 证据面板。

---

## 7. 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 一开始追求全平台 | 无法交付切片 | 先做 M0/M1 单垂直 |
| 重写所有 Python | 指标退化、周期失控 | 先包服务，后迁热点 |
| 语料/PDF 许可 | 无法公开仓库 | 只存 manifest/hash 或样例 |
| Gold Evidence 标注成本 | benchmark 不可信 | 先 20 题，双人核对 |
| 多语言过度设计 | 增加调试成本 | Go/Python 两语言封顶 |
| 高保真不可度量 | 变成营销词 | 定义 citation/faithfulness/abstention 指标 |
| 长上下文模型绕过 RAG | demo 说服力下降 | 强调成本/引用/多文档/审计 |

---

## 8. 需要确认的问题

1. 新仓库远程地址：已确认 `https://github.com/Polar12e/SourceKB-GroundedKB`，`main` 已推送；
2. 第一个 finance vertical 的文档范围（仅年报？公告？审计报告？）；
3. 向量库选型：Milvus / pgvector / OpenSearch；
4. 是否第一步就做 Web，还是先 API + CLI；
5. 是否保留旧项目作为 demo，还是只作为 benchmark 数据源。

---

## 9. 交接检查清单

```text
[ ] 阅读 README.md / docs/architecture.md
[ ] 阅读旧项目 HANDOVER.md
[ ] 确认旧项目已 tag v0.1.0-legacy
[ ] 确认新仓库 remote
[ ] 确认 Python/Go 版本
[ ] 确认 .env.example 无真实密钥
[ ] 确认没有复制旧 .env / 缓存
[ ] M0 契约评审
[ ] M0 Docker Compose 可启动
[ ] M1 10 文档/10 题 baseline
```

---

## 10. 安全与凭据

- 新项目不继承旧 `.env`；
- `.env` 必须被 `.gitignore` 忽略；
- `.env.example` 只放占位符；
- API key 只通过环境变量/secret manager 注入；
- 日志不得打印完整 key；
- 外部模型端点默认拒绝，显式 allow；
- 公开仓库中的 PDF/语料需确认许可。

---

## 11. 关联文档

- 旧项目交接：`../annual-report-qa-agent/HANDOVER.md`
- 旧项目迁移盘点：`../TRANSITION_PLAN.md`
- 新项目架构：`docs/architecture.md`
- 资产迁移：`docs/migration-from-annual-report.md`
- 任务日志：`docs/task-log.md`

---

## 12. 一句话

> GroundedKB 的目标不是“再做一个 RAG demo”，而是把 **检索、引用、拒答、评测、服务化** 做成一个可复用的知识库平台；金融年报只是第一个 vertical。
