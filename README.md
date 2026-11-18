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
├─ Makefile                   # Go 开发入口
├─ go.mod
├─ .env.example
├─ .gitignore
├─ scripts/                   # 本地工具（goenv.sh）
├─ docs/
│  ├─ architecture.md
│  └─ migration-from-annual-report.md
├─ contracts/                 # OpenAPI / protobuf / JSON schema（待建）
├─ services/                  # Go 服务（骨架）
│  ├─ gateway/
│  ├─ ingest/
│  ├─ agent/
│  └─ model-gateway/
├─ internal/                  # Go 共享平台包（config/health/httpserver/service）
├─ workers/                   # Python worker（待建）
│  ├─ retrieval/
│  ├─ embedding/
│  ├─ parser/
│  └─ eval/
├─ core/                      # 可复用的算法与协议（待建）
├─ domains/
│  └─ finance/                # 第一个 vertical（待建）
├─ deploy/                    # docker compose / migrations（待建）
└─ tests/                     # 跨服务测试（待建）
```

当前已有 Go 服务骨架（gateway / ingest / agent / model-gateway）；契约、Python worker 与 Docker Compose 仍待落地。

---

## 5. 当前状态

- [x] 项目命名与定位
- [x] 技术栈边界：Go + Python
- [x] 架构文档
- [x] 旧项目资产盘点与迁移原则
- [x] Go 服务骨架：gateway / ingest / agent / model-gateway + `/healthz`
- [ ] Python worker 骨架
- [ ] 第一个 retrieval service
- [ ] 第一个 ingest pipeline
- [ ] 第一个 10 题 benchmark
- [ ] 第一个 Web/API demo

---

## 6. 快速开始

当前 Go 服务骨架可运行；Python worker、契约和 Docker Compose 尚未落地。

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

后续目标入口（计划中）：

```bash
docker compose up
```

Python worker / eval 待代码落地后启用：

```bash
python -m pytest
python -m eval.run --dataset finance_v1
```

设计背景与迁移边界见：

- [docs/architecture.md](docs/architecture.md)
- [docs/migration-from-annual-report.md](docs/migration-from-annual-report.md)
- [HANDOVER.md](HANDOVER.md)

---

## 7. 文档

| 文档 | 内容 |
|---|---|
| [HANDOVER.md](HANDOVER.md) | 交接状态、决策、风险、里程碑 |
| [docs/task-log.md](docs/task-log.md) | 任务 backlog、会话记录、偏差与决策 |
| [docs/architecture.md](docs/architecture.md) | 服务边界、契约、数据流 |
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
