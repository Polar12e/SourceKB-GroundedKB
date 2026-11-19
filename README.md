# 高保真知识库（GroundedKB）

> **可溯源的 Agentic RAG 知识库平台**
> 技术栈：Go + Python
> 状态：M1 检索切片 / 本地可运行 / LLM + 拒答三态（2026-11-19）
> 已打通 **Gateway → Agent → Retrieval → DeepSeek** 的本地链路；ingest、Web UI、LLM 质量评测仍在后续。

---

## 1. 项目要解决什么

企业内部文档和专业知识库通常有三个问题：

1. **答案没有依据**：模型说得像真的，但无法定位原文；
2. **引用不可核对**：只给文档名，不给页码/行/片段；
3. **没有拒答**：没有证据时仍然硬答。

GroundedKB 的目标是把“高保真”变成可度量的系统能力：

- **Citation fidelity**：每个结论能定位到文档/页码/行/原文；
- **Answer faithfulness**：答案中的事实能被证据支持；
- **Abstention fidelity**：没有证据时明确拒答；
- **Retrieval quality**：混合检索 + 可评估的召回；
- **Agent traceability**：工具调用、检索、回答都有 trace。

---

## 2. 非目标

第一版不做：

- 通用行业知识库 SaaS；
- 完整多租户/计费/合规；
- 自研向量数据库/ANN；
- 全类型文档 OCR；
- 模型训练/微调；
- 生产级高可用。

第一版的目标是：

> 一条可复现、可评测、可解释的文档 RAG + Agent 平台切片。

---

## 3. 技术栈与边界

```text
Web / SDK
   ↓
API Gateway (Go)
   ↓
Agent Runtime (Go)
   ├─ Retrieval Service (Python 先复用，后续可 Go)
   ├─ Model Gateway (Go)
   └─ Tool Services (Python/Go)

Ingest Worker (Go)
   └─ Parser / OCR / chunking (Python)

Eval Service (Python)
   └─ Benchmark / citation / abstention / cost

Storage
   Postgres + Object Storage + Redis + Vector DB
```

原则：

- **Go 负责服务、并发、状态、部署；**
- **Python 负责检索算法、embedding、解析、评测；**
- **C++ 暂不引入；只有 benchmark 证明热点后再考虑；**
- 先做模块化单体 + 清晰的进程边界，不提前上微服务/K8s。

---

## 4. 目录规划

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
├─ .github/workflows/ci.yml   # CI 骨架
├─ scripts/
│  ├─ goenv.sh                # Go 缓存重定向
│  ├─ check_contracts.py      # JSON Schema / OpenAPI 校验
│  └─ run_local.sh            # retrieval + agent + gateway 一键启动
├─ config/                    # 四通路参数（retrieval.yaml）
├─ data/                      # manifest 提交；private 语料忽略
├─ docs/
│  ├─ architecture.md
│  ├─ rag-notes.md
│  ├─ task-log.md
│  └─ migration-from-annual-report.md
├─ contracts/                 # v0 草案
│  ├─ openapi.yaml
│  ├─ schemas/
│  └─ examples/
├─ services/                  # Go 服务
│  ├─ gateway/                # /healthz + /search + /ask 代理
│  ├─ ingest/                 # 健康检查骨架
│  ├─ agent/                  # /ask 抽取式回答
│  └─ model-gateway/          # /v1/chat/completions（DeepSeek）
├─ internal/                  # Go 共享包：config/health/httpserver/service/proxy/agent
├─ workers/                   # Python worker
│  ├─ retrieval/              # 四通路：bm25/expanded/dense/hybrid
│  ├─ embedding/              # LSA / OpenAI-compatible
│  └─ parser/                 # PDF 解析 + 可选 OCR
├─ eval/                      # dataset / runner / reports
├─ core/                      # 共享文本/名词表/算法
├─ domains/
│  └─ finance/                # 财务名词配置 + 参数
├─ deploy/                    # Compose + Dockerfile
│  ├─ compose.yaml
│  └─ docker/go-service.Dockerfile
└─ tests/e2e/                 # 黑盒系统测试
```

当前可运行的是：Python retrieval（四通路 + filters + 简繁）、Go gateway/agent/model-gateway 本地切片、10 文档语料、Midea 10 题与跨文档 40 题评测，以及默认关闭的 DeepSeek 回答路径。ingest 上传/索引、Web UI、LLM 质量评测仍是后续。

---

## 5. 当前状态

- [x] 项目命名与定位
- [x] 技术栈边界：Go + Python
- [x] 架构文档
- [x] 旧项目资产盘点与迁移原则
- [x] Go 服务框架：gateway / ingest / agent / model-gateway + `/healthz`
- [x] Python retrieval：BM25 + hit window + filters + 简繁归一
- [x] 四通路通用化：bm25 / expanded / dense / hybrid 由 config/retrieval.yaml 驱动
- [x] 证据级评测：chunk anchor、channels、chunk Hit/Recall/nDCG、报告指纹
- [x] Dense provider：lsa / openai（base_url/model/dim + env key + cache identity）
- [x] RAG 资产：财务名词表（terms.json）/ LSA / OpenAI-compatible provider
- [x] 本地端到端切片：gateway → agent → retrieval（默认抽取式 + 拒答兜底）
- [x] Midea 10 题 benchmark：Hit@4=1.000 / Recall@4=0.975 / MRR=1.000
- [x] 跨文档 40 题 A/B：chunk 级 + 尺度无关 prior 后 expanded 0.875 / hybrid 0.850，默认保持 expanded
- [x] 10 文档本地语料：PDF parser + manifest + 页级 JSONL
- [x] 契约 v0 草案：13 个 JSON Schema + OpenAPI（待评审冻结）
- [x] Compose + Dockerfile（`config` 校验通过；未在会话内运行）
- [x] CI 骨架
- [x] 88 个 Python 测试 + 33 个 Go 测试（service / proxy / agent / model-gateway）
- [x] 14 条黑盒系统测试：retrieval/agent/gateway/model-gateway + 错误契约
- [x] LLM 路径：DeepSeek `deepseek-chat` + Agent 调用/校验/fallback（默认关闭，抽取式警告）
- [x] DeepSeek live probe：HTTP 200，真实 `/ask` 返回 ok + citation
- [x] 拒答三态：LLM 生成 / 校验失败回退抽取式 / 确定性拒答；拒答路径不调用模型
- [x] 引用与数值 verifier：anchor + locator + score + matched_terms、单位换算（百万元 ↔ 亿元）、中文数字年份折叠（`二零二六年` ↔ `2026年`）
- [ ] 契约 v0 评审冻结
- [x] Xiaomi 3 份 OCR：415/127/127 页，已合入 corpus，manifest=ocr
- [ ] 第一个 ingest pipeline（数据库/索引服务）
- [ ] LLM 质量评测与拒答指标（abstention precision/recall、false-answer rate）
- [ ] 默认开启 LLM（当前 `LLM_ENABLED=false`）
- [ ] 40 题 `acceptable_evidence` / `hard_negatives` 人工复核
- [ ] Web UI（HTTP API 基础已可用）

---

## 6. 快速开始

### 6.1 本地端到端（推荐）

前置：Python 依赖 + Go 工具链，已解析的本地语料：

```bash
make py-install
source scripts/goenv.sh   # 把 Go 缓存放到 .tools/，避免 home 只读

make run-local
```

会启动：

| 服务 | 端口 | 说明 |
|---|---:|---|
| gateway | 8080 | `/healthz`、`/search`、`/ask` |
| retrieval | 8081 | FastAPI `/search` |
| agent | 8083 | `/ask`；LLM 关闭时抽取式，开启后经 verifier 生成或拒答 |
| model-gateway | 8084 | DeepSeek `/v1/chat/completions`（默认关闭） |

另开终端验证：

```bash
curl http://127.0.0.1:8080/healthz

curl -X POST http://127.0.0.1:8080/search \
  -H 'content-type: application/json' \
  -d '{"query":"营业收入","top_k":3}'

curl -X POST http://127.0.0.1:8080/ask \
  -H 'content-type: application/json' \
  -d '{"question":"2023年营业成本为什么重述？","top_k":3}'
```

`/ask` 有三种结局，用响应里的 `status` 区分：

| 结局 | `status` | 触发条件 | 是否调用模型 |
|---|---|---|---|
| LLM 生成 | `ok` | 模型返回合法 JSON，citation 命中本次检索的 chunk，答案中每个数字都能在被引用原文中找到 | 是 |
| 抽取式回退 | `ok` | LLM 未启用；或调用/解析失败、citation 未知、数字无依据；答案前缀标明回退原因 | 否 / 是 |
| 拒答 | `insufficient_evidence`、`unverified` | 检索无命中、片段页码或行号不合法、或模型自判证据不足 | 前两种否 |

答案前缀会显式标明结局与回退原因：

- 抽取式基线：`【当前为抽取式基线，尚未接入 LLM 生成】`；
- 校验失败回退：`【LLM 调用未通过校验，以下为抽取式回答】`；
- 拒答：`【未检索到可引用的证据，已拒答】` / `【证据未通过定位校验，已拒答】` / `【证据不足，已拒答】`。拒答是**规则决策**而不是能力缺口，因此不会借用“尚未接入”的提示。

无证据时由确定性规则直接拒答、**不调用模型**，避免模型改用参数记忆硬答；拒答响应始终返回空 `citations`，不会伪造引用。

### 6.1.1 启用 LLM（可选）

```bash
# .env（不要提交）
LLM_ENABLED=true
LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=<your-key>
```

`make run-local` 会自动加载 `.env`，但不打印 key。启用后 `/ask` 走：

```text
agent → model-gateway → DeepSeek → verifier
```

如果 `LLM_ENABLED=false` 或 key 缺失，仍返回抽取式回答，不影响检索和评测。

verifier 逐项核对，任一项失败即回退抽取式答案（并保留 `citations` 供人工核对）：

1. citation 必须命中本次检索返回的 chunk id，未知 chunk 直接判失败；
2. 答案中的每个数字必须能在被引用原文中找到，允许单位换算（`130,115 百万元` ≈ `1,301.15 亿元`）；
3. 中文数字年份先折叠再比对（原文 `二零二六年` 可支撑答案 `2026年`），只折叠 4 位数字串，避免把 `一千三百` 之类的量级读成数字；
4. `status` 只能是 `ok` / `insufficient_evidence`，`ok` 必须带非空答案和引用，否则按失败处理。

默认读取 `data/private/corpus/pages.jsonl`；如果没有 corpus，脚本会警告，`/search` 返回空、`/ask` 拒答。详细数据约定见 [data/README.md](data/README.md)。

### 6.2 单独运行服务

```bash
make test          # Go 测试
make vet
make build

make run-gateway         # :8080
make run-agent           # :8083（LLM_ENABLED=false 时抽取式）
make run-ingest          # :8082（健康检查骨架）
make run-model-gateway   # :8084（DeepSeek 路由，默认关闭）
```

注意：单独启动 gateway 时，`/search` 需要 retrieval 可达，`/ask` 需要 agent + retrieval 可达；启用 LLM 时还需要 model-gateway 可达；否则返回 502。

### 6.3 Python retrieval

```bash
make py-test
make contracts

# 合成 fixture
RETRIEVAL_CORPUS=workers/retrieval/tests/fixtures/sample_pages.jsonl \
  make py-run-retrieval

# 10 文档 + filters
RETRIEVAL_CORPUS=data/private/corpus/pages.jsonl \
RETRIEVAL_MANIFEST=data/manifests/documents.json \
  make py-run-retrieval

curl -X POST http://127.0.0.1:8081/search \
  -H 'content-type: application/json' \
  -d '{"query":"2025年营业收入","top_k":3,"filters":{"company":"688981.SH"}}'
```

### 6.4 Compose

```bash
docker compose -f deploy/compose.yaml config
docker compose -f deploy/compose.yaml up --build
```

Retrieval 容器挂载 `../data:/data:ro`，读取 `/data/private/corpus/pages.jsonl` 与 `/data/manifests/documents.json`。当前会话无法连接 Docker socket；`up` 请在宿主机终端执行。

### 6.5 评测

```bash
make eval          # Midea 10 题
make eval-ab       # Midea 四通路 A/B
make eval-crossdoc # 跨文档 40 题，按 company/split 分组
make check-all     # Go + Python + contracts + compose config
make test-system   # 14 条黑盒系统测试（fixture）
```

Midea baseline：**Hit@4=1.000 / Recall@4=0.975 / MRR=1.000**。跨文档结论与失败分析见 [eval/reports/channels_crossdoc_v1.md](eval/reports/channels_crossdoc_v1.md)。

设计背景与迁移边界见：

- [docs/architecture.md](docs/architecture.md)
- [docs/migration-from-annual-report.md](docs/migration-from-annual-report.md)
- [contracts/README.md](contracts/README.md)
- [eval/README.md](eval/README.md)
- [deploy/README.md](deploy/README.md)
- [workers/retrieval/README.md](workers/retrieval/README.md)
- [HANDOVER.md](HANDOVER.md)

## 7. 文档

| 文档 | 内容 |
|---|---|
| [HANDOVER.md](HANDOVER.md) | 交接状态、决策、风险、里程碑 |
| [docs/task-log.md](docs/task-log.md) | 任务 backlog、会话记录、偏差与决策 |
| [docs/architecture.md](docs/architecture.md) | 服务边界、契约、数据流 |
| [docs/rag-notes.md](docs/rag-notes.md) | 旧项目 RAG 实验笔记与检索取舍 |
| [config/README.md](config/README.md) | 四通路检索参数与切换方式 |
| [contracts/README.md](contracts/README.md) | 契约 v0、字段约定、校验方式 |
| [data/README.md](data/README.md) | 语料 manifest 与私有数据约定 |
| [deploy/README.md](deploy/README.md) | Compose、Dockerfile、端口 |
| [eval/README.md](eval/README.md) | 评测集、合法答案页标准、四通路结果 |
| [services/README.md](services/README.md) | Go 服务职责与当前状态 |
| [tests/e2e/README.md](tests/e2e/README.md) | 黑盒系统测试集与运行方式 |
| [docs/migration-from-annual-report.md](docs/migration-from-annual-report.md) | 从旧年报项目迁移哪些资产 |

---

## 8. 关联旧项目

旧项目 `annual-report-qa-agent` 已冻结为 legacy baseline：

- 交接基线 commit：`c89b37c`
- 交接文档：`../annual-report-qa-agent/HANDOVER.md`
- 迁移方案：`../TRANSITION_PLAN.md`

旧项目继续作为：

- 检索算法参考；
- 评测题种子；
- 财务 domain 的 demo；
- 失败案例库。

新项目不复制旧 git history，不复制 `.env`，不复制缓存/构建产物。
