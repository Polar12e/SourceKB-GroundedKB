# 高保真知识库（GroundedKB）

> **可溯源的 Agentic RAG 知识库平台**  
> 技术栈：Go + Python  
> 状态：项目脚手架 / 迁移准备中（2026-11-18）  
> 当前没有可运行代码；先固定架构、契约、资产迁移和交接边界。

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
│  └─ check_contracts.py      # JSON Schema / OpenAPI 校验
├─ data/                      # manifest 提交；private 语料忽略
├─ docs/
│  ├─ architecture.md
│  └─ migration-from-annual-report.md
├─ contracts/                 # v0 草案
│  ├─ openapi.yaml
│  ├─ schemas/
│  └─ examples/
├─ services/                  # Go 服务（骨架）
│  ├─ gateway/
│  ├─ ingest/
│  ├─ agent/
│  └─ model-gateway/
├─ internal/                  # Go 共享平台包（config/health/httpserver/service）
├─ workers/                   # Python worker
│  ├─ retrieval/              # BM25 + hit window + RRF
│  ├─ embedding/              # LSA / OpenAI-compatible
│  ├─ parser/                 # PDF 解析 + 可选 OCR
│  └─ eval/                   # 待建
├─ core/                      # 共享文本/切分（text.py 已落地）
├─ domains/
│  └─ finance/                # finance 检索 profile（部分落地）
├─ deploy/                    # Compose + Dockerfile（骨架）
│  ├─ compose.yaml
│  └─ docker/go-service.Dockerfile
└─ tests/                     # 跨服务测试（待建）
```

当前已有 Go 服务骨架、Python retrieval 服务、契约 v0 草案、10 文档本地语料、10 题 retrieval eval、Compose/Dockerfile 与 CI 骨架；ingest、Agent 业务与 Web 待落地。

---

## 5. 当前状态

- [x] 项目命名与定位
- [x] 技术栈边界：Go + Python
- [x] 架构文档
- [x] 旧项目资产盘点与迁移原则
- [x] Go 服务骨架：gateway / ingest / agent / model-gateway + `/healthz`
- [x] Python retrieval：BM25 + hit window + RRF + finance profile
- [x] Retrieval 增强：metadata filters（company/year/doc_type/document_id）+ 简繁归一
- [x] RAG 资产：财务名词表（terms.json）/ embedding provider / dense channel + RAG notes
- [x] 10 文档本地语料：PDF parser + manifest + 页级 JSONL
- [x] 契约 v0 草案：13 个 JSON Schema + OpenAPI（待评审冻结）
- [x] Compose + Dockerfile 骨架（`config` 校验通过；未在会话内运行）
- [x] CI 骨架
- [ ] 契约 v0 评审冻结
- [ ] dense / embedding 通道
- [ ] Xiaomi 3 份 OCR 重抽取
- [ ] 第一个 ingest pipeline（数据库/索引服务）
- [ ] Agent 业务、引用校验与拒答
- [x] 第一个 10 题 retrieval benchmark（Midea；Hit@4=1.000 / Recall@4=0.975 / MRR=1.000）
- [ ] 跨文档 10 题 benchmark（腾讯/中芯/小米）
- [ ] 第一个 Web/API demo

---

## 6. 快速开始

当前可运行 Go 服务与 Python retrieval 服务；Compose 文件可校验，但真正 `up` 需要宿主机可访问 Docker socket。

Go 服务：

```bash
source scripts/goenv.sh   # 把 Go 缓存放到 .tools/，避免 home 只读

make test
make build

# 启动 gateway（默认 :8080）
make run-gateway
# 另开终端验证
curl http://127.0.0.1:8080/healthz
```

其他服务：`make run-ingest`（:8082）、`make run-agent`（:8083）、`make run-model-gateway`（:8084）。

Python retrieval：

```bash
make py-install
make py-test
make contracts

RETRIEVAL_CORPUS=workers/retrieval/tests/fixtures/sample_pages.jsonl \
  make py-run-retrieval
# 或使用已解析的 10 文档本地语料
# RETRIEVAL_CORPUS=data/private/corpus/pages.jsonl make py-run-retrieval
# 另开终端
curl http://127.0.0.1:8081/healthz
curl -X POST http://127.0.0.1:8081/search \
  -H 'content-type: application/json' \
  -d '{"query":"营业成本重述","top_k":3}'
```

10 文档 + metadata filter：

```bash
RETRIEVAL_CORPUS=data/private/corpus/pages.jsonl \
RETRIEVAL_MANIFEST=data/manifests/documents.json \
  make py-run-retrieval

curl -X POST http://127.0.0.1:8081/search \
  -H 'content-type: application/json' \
  -d '{"query":"2025年营业收入","top_k":3,"filters":{"company":"688981.SH"}}'
```

Compose：

```bash
docker compose -f deploy/compose.yaml config
docker compose -f deploy/compose.yaml up --build
```

当前会话无法连接 Docker socket；`up` 请在宿主机终端执行。

Retrieval eval：

```bash
make eval
# Hit@4=1.000 / Recall@4=0.975 / MRR=1.000（Midea 10 题）
```

设计背景与迁移边界见：

- [docs/architecture.md](docs/architecture.md)
- [docs/migration-from-annual-report.md](docs/migration-from-annual-report.md)
- [contracts/README.md](contracts/README.md)
- [eval/README.md](eval/README.md)
- [deploy/README.md](deploy/README.md)
- [workers/retrieval/README.md](workers/retrieval/README.md)
- [HANDOVER.md](HANDOVER.md)

---

## 7. 文档

| 文档 | 内容 |
|---|---|
| [HANDOVER.md](HANDOVER.md) | 交接状态、决策、风险、里程碑 |
| [docs/task-log.md](docs/task-log.md) | 任务 backlog、会话记录、偏差与决策 |
| [docs/architecture.md](docs/architecture.md) | 服务边界、契约、数据流 |
| [docs/rag-notes.md](docs/rag-notes.md) | 旧项目 RAG 实验笔记与检索取舍 |
| [contracts/README.md](contracts/README.md) | 契约 v0、字段约定、校验方式 |
| [data/README.md](data/README.md) | 语料 manifest 与私有数据约定 |
| [deploy/README.md](deploy/README.md) | Compose、Dockerfile、端口 |
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
