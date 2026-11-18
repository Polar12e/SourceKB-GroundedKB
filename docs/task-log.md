# GroundedKB 任务日志

> 建立日期：2026-11-18  
> 维护方式：任务表 + 追加式会话记录  
> 配套文档：[README](../README.md)、[HANDOVER](../HANDOVER.md)、[架构设计](architecture.md)、[迁移方案](migration-from-annual-report.md)

本文件是 GroundedKB 的唯一任务 backlog，同时记录已核实事实、文档偏差、决策和下一步。当前项目处于“文档与目录脚手架”阶段，首要目标是 M0（契约 + 骨架）。

---

## 0. 使用约定

- 任务 ID：`T<里程碑>.<序号>`；跨阶段依赖写在备注里，不重复建号。
- 状态：`TODO` / `DOING` / `BLOCKED` / `DONE` / `DROPPED`。
- 完成任务必须附验收证据（命令、测试数、接口返回、报告路径）。
- 每次会话在 §1 追加一条记录；任务表只更新状态，不删除历史。
- 发现文档/环境问题时先记入 §3，再决定是否修改文档或环境。

---

## 1. 会话记录

### 2026-11-18 · 工作区阅读与任务日志建立

**范围**

- 通读 `grounded-kb/` 下全部 14 个文档与配置文件；
- 核对旧项目 `../nianbao/annual-report-qa-agent` 的 git 基线、tag 与测试事实；
- 核对本机 Go / Python / Docker / Git 工具链；
- 建立本日志，并在 README 与 HANDOVER 中加入入口。

**已核实**

- 工作区只有文档与目录骨架：无 Go/Python 代码、无契约文件、无 Docker Compose、无 CI、无 Git 仓库。
- 旧项目位于 `../nianbao/annual-report-qa-agent`（不是文档所写的 `../annual-report-qa-agent`）。
- 旧项目 HEAD 为 `6341bf1`，冻结基线 `c89b37c`，tag `v0.1.0-legacy` 已存在，工作树干净。
- 旧项目 HANDOVER 记录：158 个测试通过、`run_eval` PASS、DeepSeek `deepseek-flash` 真实调用 6/6 PASS（本次未重跑）。
- 本机 Python 3.14.4、Git 2.53.0 可用；`go` 与 `docker` 命令不存在。

**本次变更**

- 新增 `docs/task-log.md`（本文件）。
- README §7 文档表、HANDOVER §11 关联文档加入本日志链接。

**本次未做**

- 未初始化 Git 仓库、未安装 Go/Docker、未写契约或代码；
- 未修改迁移文档中的旧路径引用（先记录为 D1，待仓库布局确认后再改）。

**结论**

项目准备度停留在“设计完成、实现未开始”。M0 的两条硬前置是：契约 v0 落地、Go/Docker 工具链可用。下一步见 §8。

### 2026-11-18 16:54 · 环境体检

**范围**

- 主机资源、OS、网络与代理；
- Go / Python / Docker / Postgres / Redis / Git 工具链；
- Python venv 与关键依赖（FastAPI、uvicorn、pydantic、pytest、numpy）；
- 旧项目 158 测试与检索评测的可复现性。

**结果**

- OS：Ubuntu 26.04.1 LTS，16 vCPU，14 GiB 内存（可用 6.7 GiB），根分区可用 142 GB；时区/编码正常。
- Python 3.14.4、pip 25.1.1、Git 2.53.0、Node 24.21.0、pnpm 12.4.1、GCC 15.2；`python3-venv` 可用，Python 头文件存在。
- Go 未安装；apt 候选 1.26，官方最新 1.27.4（`go.dev` 可下载）。
- Docker CE 29.10.0 + Compose v5.8.0 已安装，`systemd` 显示 active/enabled；但当前 shell 在 DSH bwrap 沙箱内，docker 组权限被剥离，`docker info`、`sg docker`、`setpriv`、`sudo` 均无法连接 `/var/run/docker.sock`，`danger-full-access` 重试仍报 permission denied。
- PostgreSQL / Redis 客户端与服务均未安装（计划由 Compose 提供）。
- Python venv 正常；经 Aliyun PyPI 镜像安装 FastAPI 0.163.2、uvicorn 0.54.0、pydantic 2.14.3、pytest 9.2.0、numpy 2.5.5 成功并可导入；`pypi.org` 直连失败，`mirrors.aliyun.com`、GitHub、npm、Go proxy 可达。pip 默认缓存目录不可写，安装时需设置 `PIP_CACHE_DIR` 或使用项目内 venv。
- 旧项目：直接在只读目录跑 158 测试时有 11 个 error，全部因测试写入项目内 `_test_tmp` 而只读；复制到可写临时目录后 **158 tests OK**，`run_eval` **PASS**，基线可复现。
- Git 全局 `user.name` / `user.email` 未配置；工作区无 `.env`，会话环境无真实 API key；8080/8081 端口空闲。

**结论**

- Python 侧与网络（走镜像/代理）已具备开工条件；
- Go 缺失、Docker 会话内不可达，M0 的 T0.6/T0.8 仍受阻；
- 旧项目基线可复现，M1 的对比基准可信。

**未做**

- 未安装 Go、未启动或修改 Docker、未改系统配置、未写业务代码。

### 2026-11-18 17:20 · 环境复查（Go 已装）

**变化**

- Go 1.27.4 已安装到 `/home/polarize/.local/go`，`go` / `gofmt` 通过 `~/.local/bin` 进入 PATH。

**复核结果**

- 最小模块 `go run` 成功（输出 `go-ok`），但仅在重定向缓存后：默认 `GOCACHE=/home/polarize/.cache/go-build` 在沙箱内只读，报 `read-only file system`；把 `GOCACHE`（及 `GOPATH` / `GOMODCACHE`）指到工作区或 `/tmp` 后正常。
- Docker 仍无法从会话访问：`docker info` 依旧 permission denied；`id` 中没有 docker 组，socket 仍为 `nobody:nogroup` 660；无 rootless socket、无 2375 TCP、无 podman/nerdctl 替代。
- Git 仍无仓库，`user.name` / `user.email` 未配置；工作区自上次检查只有任务日志变更。
- Python 系统环境仍未安装 FastAPI 等依赖（可经 Aliyun 镜像安装，前次已验证）；`psql` / `redis-cli` 仍缺失；8080/8081 空闲；无 API key。

**结论**

- Go 阻塞已解除，但本地构建必须显式设置 `GOCACHE` / `GOPATH`（D6）；T0.6 可从 `BLOCKED` 改为 `TODO`。
- Docker 仍是唯一硬阻塞（D3 / T0.8）；需宿主机终端或开放 socket。
- Git 身份与仓库初始化仍未完成（T0.1）。

**未做**

- 未改系统环境、未安装 Python 依赖、未初始化仓库、未修改 Docker 配置。

### 2026-11-18 17:23 · Go 复检

- `go` → `~/.local/bin/go` → `~/.local/go/bin/go`，1.27.4；登录 shell 可找到。
- 默认 `GOCACHE=/home/polarize/.cache/go-build` 仍只读，直接构建失败；重定向 `GOCACHE` / `GOPATH` / `GOMODCACHE` 到 `/tmp` 后正常。
- 标准库程序：`go run` 输出 `go-ok`；`go test ./...`、`go vet ./...`、`go build` 均通过（临时模块）。
- 依赖下载：`go get rsc.io/quote@v1.5.2` 成功，`go run` 输出“你好，世界。”；`sum.golang.org` 返回 200。
- 工作区仍无 `go.mod`、`.go` 文件、Makefile 或 `.tools/`；未创建项目代码。

### 2026-11-18 17:27 · T0.6 Go 服务骨架

**新增**

- `go.mod`：module `grounded-kb.local`，Go 1.27.4（临时 module path，待 remote 确认后统一替换）。
- `internal/platform/{config,health,httpserver,service}`：端口校验、`/healthz`、超时/优雅关闭、服务启动封装，含单测。
- `services/{gateway,ingest,agent,model-gateway}/cmd/.../main.go`。
- `Makefile`、`scripts/goenv.sh`；`.env.example` 补 8082/8083/8084 端口；`.gitignore` 增加 `.tools/`。

**验证**

- `make test`：4 个含测试的包全部通过。
- `make vet`：通过；`make build`：四个二进制生成到 `bin/`。
- 四个服务启动后 `/healthz` 均返回 `{"status":"ok","service":"..."}`，POST 返回 405；gateway 日志为 JSON。
- `GOCACHE` / `GOPATH` 指向 `.tools/`，不再触发 home 只读错误。

**未做**

- 未实现业务接口（`/documents`、`/ask`、`/search`），等待契约 v0。
- 未初始化 Git；Docker 仍不可从会话访问。

### 2026-11-18 17:37 · Git 初始化与首次提交

- 远程仓库：`https://github.com/Polar12e/SourceKB-GroundedKB`（空仓库，0 refs）。
- `git init -b main`；仓库级身份 `Zhang <2122163720@qq.com>`。
- 30 个文件暂存；`.tools/`、`bin/`、`.env` 被 `.gitignore` 忽略；密钥扫描无命中。
- 首次提交 `eac5219 chore: bootstrap GroundedKB Go service skeleton`，工作树干净。
- `origin` 已配置；`git push -u origin main` 因本机无 GitHub 凭据失败（`could not read Username`）；无 credential helper，SSH agent 无 key。
- 待办：在宿主机终端完成 GitHub 认证后推送；推送前可考虑把 module path 改为正式仓库路径。

---

## 2. 工作区清单（已读）

| 路径 | 内容 | 状态 |
|---|---|---|
| [README.md](../README.md) | 项目定位、非目标、技术栈、目录规划、当前状态、文档索引 | 已完成（设计稿） |
| [HANDOVER.md](../HANDOVER.md) | 交接摘要、Go/Python 分界、存储、迁移清单、M0–M4、风险、待确认问题、安全检查清单 | 已完成（设计稿） |
| [docs/architecture.md](architecture.md) | 总体架构、服务职责、核心契约示例、入库/问答/评测流程、可观测性、第一版边界 | 设计稿 |
| [docs/migration-from-annual-report.md](migration-from-annual-report.md) | 旧项目资产分级（A–D）、迁移顺序、不要照抄的部分、验收问题 | 设计稿 |
| [contracts/README.md](../contracts/README.md) | 契约目录说明（OpenAPI / JSON Schema / protobuf） | 占位，无契约文件 |
| [services/README.md](../services/README.md) | Go 服务边界与优先级 | 说明文件；Go 骨架已落地 |
| [workers/README.md](../workers/README.md) | Python worker 职责与复用来源 | 占位，无代码 |
| [core/README.md](../core/README.md) | 跨 domain 算法与协议范围 | 占位，无代码 |
| [domains/finance/README.md](../domains/finance/README.md) | finance vertical 迁移范围 | 占位，无代码 |
| [eval/README.md](../eval/README.md) | benchmark 目标、题目字段、指标 | 占位，无实现 |
| [deploy/README.md](../deploy/README.md) | Compose、健康检查、后续可选项 | 占位，无 Compose |
| [tests/README.md](../tests/README.md) | unit/contract/integration/eval/smoke 分层 | 占位，无测试 |
| [.env.example](../.env.example) | 本地配置占位（仍为 `FIN_AGENT_*` 前缀） | 待整理（D4） |
| [.gitignore](../.gitignore) | 已忽略 `.env`、缓存、构建产物、评测输出、`*.npz` | 可用 |

截至 2026-11-18 17:27，`contracts/`、`workers/`、`core/`、`domains/finance/`、`eval/`、`deploy/`、`tests/` 仍只有 README；`services/` 与 `internal/` 已有 Go 骨架与单测。工作区当前还有 `go.mod`、`Makefile`、`scripts/goenv.sh`、`.tools/`（缓存，已忽略）和 `bin/`（构建产物，已忽略）。

---

## 3. 偏差与缺口（待处理）

| ID | 现象 | 影响 | 建议处置 |
|---|---|---|---|
| D1 | README/HANDOVER/迁移文档引用 `../annual-report-qa-agent` 与 `../TRANSITION_PLAN.md`；实际位于 `../nianbao/` 下 | 接手人按文档路径找不到旧项目与迁移方案 | 先确认目标仓库布局：若维持当前嵌套，统一改为 `../nianbao/...`；若计划迁为兄弟目录，迁移后再改。两者取其一，避免长期漂移 |
| D2 | 已解决（17:37）：已初始化 `main` 并提交 `eac5219`；remote 已配置，push 待认证 | 变更已有历史；推送前仍无远程备份 | 完成 GitHub 认证后 `git push -u origin main`（D7） |
| D3 | Docker CE 29.10 + Compose v5.8 已安装且 systemd active，但当前 DSH bwrap 沙箱剥离 docker 组权限，无法连接 `/var/run/docker.sock`（`sg` / `setpriv` / `sudo` / `danger-full-access` 均失败）；无 rootless socket 或 TCP 入口 | `docker compose up` 无法在本会话验收；Postgres/Redis/服务容器无法启动 | 在宿主机终端运行 Docker/Compose，或为会话开放 socket 访问；Compose 文件可先写，验收放到宿主机 |
| D4 | `.env.example` 仍使用旧项目前缀 `FIN_AGENT_*`，未定义 temperature，端口与服务名也未对齐新架构 | 配置继承旧命名，后续 model gateway/agent 的边界不清 | T0.11：确定新前缀（建议 `GROUNDEDKB_*`），补 temperature/超时/端点白名单；如需兼容旧变量，记录映射关系 |
| D5 | `contracts/` 无任何契约文件，而文档要求“契约评审通过后再写服务” | 直接写代码会破坏契约优先原则，多语言联调返工 | T0.3 → T0.4 → T0.5，先冻结 v0 契约 |
| D6 | Go 1.27.4 已装，但默认 `GOCACHE=/home/polarize/.cache/go-build`、`GOPATH=/home/polarize/go` 在沙箱内只读，直接 `go run` / `go build` 报 `read-only file system`（已缓解） | 代码可编译但命令需额外环境变量；本地与 CI 行为不一致 | 已由 `scripts/goenv.sh` + Makefile 重定向到 `.tools/`；直接执行 `go` 前先 source（T0.13） |
| D7 | 本机无 GitHub PAT / credential helper / SSH key，`git push` 报 `could not read Username` | 首次提交未同步到远程，缺少异地备份与 CI 触发 | 在宿主机终端用 PAT 或 SSH 完成一次认证，再推送（T0.1） |

---

## 4. 任务清单

### M0：契约与骨架

目标：`docker compose up` 可启动，`/healthz` 可用；契约 v0 冻结。

| ID | 任务 | 状态 | 验收 / 备注 |
|---|---|---|---|
| T0.0 | 阅读工作区并建立任务日志 | `DONE` | 本文件；README/HANDOVER 已加链接 |
| T0.1 | 初始化 Git 仓库、复核 `.gitignore`、首次提交 | `DONE` | 本地完成：`main` + `eac5219`；remote 已配置；push 待 GitHub 认证（D7） |
| T0.2 | 统一旧项目与迁移文档的相对路径（D1） | `TODO` | 取决于目标仓库布局决策 |
| T0.3 | 编写契约 JSON Schema：`Document` / `Chunk` / `SearchRequest` / `SearchHit` / `Answer` / `Citation` / `EvalCase` / `EvalResult` | `TODO` | 放入 `contracts/`；字段与 `docs/architecture.md` §4 对齐 |
| T0.4 | 编写 OpenAPI：Gateway / Agent / Retrieval 端点 | `TODO` | 依赖 T0.3；至少 `/documents`、`/ask`、`/search`、`/healthz` |
| T0.5 | 契约评审并冻结 v0 | `TODO` | 评审记录附在本日志；冻结后才能改服务接口 |
| T0.6 | Go 服务骨架：`gateway` / `ingest` / `agent` / `model-gateway`，含 `/healthz` 与单测 | `DONE` | `make test` 4 个含测试包通过、`make vet` 通过、`make build` 四服务；`/healthz` 实测；D6 已由脚本处理 |
| T0.7 | Python retrieval worker 骨架（FastAPI + `/healthz` + pytest） | `TODO` | 先只包健康检查与假检索，不迁算法 |
| T0.8 | Docker Compose：Postgres + Redis + retrieval + gateway + 健康检查 | `BLOCKED` | Docker 已装但沙箱不可达；需宿主机终端或开放 socket（D3） |
| T0.9 | README 快速开始与 Makefile/脚本对齐，确保 `docker compose up` 可跑 | `TODO` | 验收命令写入 README |
| T0.10 | CI 骨架：Go test、Python pytest、契约校验 | `TODO` | 真实 LLM 不进默认 CI |
| T0.11 | 配置基线：确定环境变量前缀、补 temperature、端点白名单占位 | `TODO` | 对应 D4；禁止提交真实 key |
| T0.12 | 向量库选型 ADR（pgvector / Milvus / OpenSearch） | `TODO` | 对应 Q3；第一版只选一个，写入 `docs/adr/` 或本日志决策表 |
| T0.13 | 环境引导：Go 缓存、venv、pip 镜像、Docker 访问方式 | `DOING` | Go 缓存已固化（Makefile / scripts/goenv.sh）；venv/pip/Docker 待补 |

### M1：检索切片

目标：10 份文档、10 题 retrieval eval；Hit@4/Recall@4 有 baseline，页面/行号可回链。

| ID | 任务 | 状态 | 验收 / 备注 |
|---|---|---|---|
| T1.1 | 将旧项目 32 题 `questions.json` 迁为 `EvalCase` schema，补 `gold_evidence` | `TODO` | 先 10 题可跑，再补全 32 题 |
| T1.2 | 迁移 `retrieval.py`：chunking / BM25 / hit window / RRF，`page` → `locator` | `TODO` | 放 `core/retrieval` + `workers/retrieval`；`chunk_id` 稳定 |
| T1.3 | 用旧项目检索跑 10 题 baseline，留档指标与命令 | `TODO` | 新服务必须与这份 baseline 对比，避免“重写后不可比” |
| T1.4 | Parser：PDF → 页/行 JSONL，生成 manifest 与 `sha256` | `TODO` | 先 PDF；HTML/DOCX 后续 |
| T1.5 | 10 份文档入库：解析、chunk、metadata、索引 | `TODO` | 需先定语料许可（R3） |
| T1.6 | `POST /search` 返回 `document_id/page/line_start/line_end/score/matched_terms` | `TODO` | 契约见 T0.3/T0.4 |
| T1.7 | 新服务 10 题 retrieval eval，与 T1.3 baseline 对比 | `TODO` | 输出 Markdown 报告；记录 Hit@4/Recall@4/MRR |

### M2：Agent + 引用

目标：工具调用可追踪；答案必须带 citation；无证据拒答。

| ID | 任务 | 状态 | 验收 / 备注 |
|---|---|---|---|
| T2.1 | Go agent runtime：step 循环、`max_steps`、超时、取消 | `TODO` | 参考旧 `src/agent.py` 的 Policy/Step 思路 |
| T2.2 | 工具注册表：`search` / `read` / `financial` | `TODO` | 通用调度器与财务工具分开 |
| T2.3 | Model Gateway：OpenAI 兼容路由、重试、超时、token/成本统计 | `TODO` | 迁 `llm_config` / `llm_policy`，移除财务 prompt |
| T2.4 | Citation verifier：引用覆盖、页码/行号存在性、数字核对 | `TODO` | 失败时降级为 `insufficient_evidence` |
| T2.5 | 拒答策略与评测：`insufficient_evidence` 触发条件 | `TODO` | 纳入 negative 题；统计 false-answer rate |
| T2.6 | Trace：`trace_id` / `step_id`、工具序列、检索参数、延迟、tokens | `TODO` | 先写 JSON 日志，再接 Postgres |
| T2.7 | 10–20 题端到端评测 | `TODO` | 引用可人工核对；拒答不编造 |

### M3：100 文档 / 100 题

目标：finance vertical 有可信 benchmark，能比较 BM25 / dense / hybrid / agentic。

| ID | 任务 | 状态 | 验收 / 备注 |
|---|---|---|---|
| T3.1 | 文档扩到 100 份，维护 manifest/hash 与许可记录 | `TODO` | 公开仓库只存样例或 manifest（R3） |
| T3.2 | 100 题 Gold Evidence，双人核对 | `TODO` | 先 20 题，再扩到 100 |
| T3.3 | 检索与 Agent 消融：BM25 / dense / hybrid / agentic | `TODO` | 固定数据与参数，输出可比表格 |
| T3.4 | Benchmark 报告与复现说明 | `TODO` | 含 citation/faithfulness/abstention/成本/延迟 |

### M4：平台化

| ID | 任务 | 状态 | 验收 / 备注 |
|---|---|---|---|
| T4.1 | 异步 ingest：队列、幂等键、失败重试/死信 | `TODO` | `document_hash` 幂等；状态机 `queued → parsing → indexing → ready/failed` |
| T4.2 | 索引版本与重建 | `TODO` | 按 `document_id` 覆盖；支持回滚 |
| T4.3 | 模型 fallback、指标/日志/成本面板 | `TODO` | 端点白名单与审计不可绕过 |
| T4.4 | 基础 Web 证据面板 | `TODO` | 文档库、问答、引用/证据定位 |

---

## 5. 里程碑状态

| 里程碑 | 验收标准 | 状态 | 主要依赖 |
|---|---|---|---|
| M0 契约与骨架 | `docker compose up` 可启动；`/healthz` 可用 | 进行中 | T0.3、T0.8；D3 沙箱 |
| M1 检索切片 | 10 文档/10 题；Hit@4、Recall@4 baseline；页面/行号可回链 | 未开始 | M0；T1.3 baseline |
| M2 Agent + 引用 | 10–20 题端到端；引用可核对；无证据拒答 | 未开始 | M1；T2.1–T2.6 |
| M3 100 文档/100 题 | 100 题 Gold Evidence；四种方案对比报告 | 未开始 | M2；T3.1–T3.4 |
| M4 平台化 | 异步 ingest、索引重建、观测、基础 Web | 未开始 | M3 |

---

## 6. 决策记录

### 6.1 已定决策（来自现有设计文档）

| 日期 | 决策 | 理由 |
|---|---|---|
| 2026-11-18 | Go 负责服务边界/并发/状态/部署，Python 负责检索、embedding、解析、评测 | 兼顾服务化与 Python 生态；避免双语言职责重叠 |
| 2026-11-18 | Retrieval 先用 Python 包住已验证算法，不第一周重写 BM25 | 防止重写导致指标退化；先保 baseline |
| 2026-11-18 | 契约优先：先 JSON Schema/OpenAPI，再写服务 | Go/Python 多服务需要稳定接口 |
| 2026-11-18 | Citation fidelity / faithfulness / abstention 作为可度量指标 | “高保真”必须可验证，不能停留在营销词 |
| 2026-11-18 | 不自研向量数据库/ANN，第一版选型第三方 | 控制范围；第一版目标是可复现切片 |
| 2026-11-18 | 暂不引入 C++，只有 benchmark 证明热点后再考虑 | 避免过早优化与调试成本 |

### 6.2 待定决策

| 问题 | 备选 | 影响 |
|---|---|---|
| 向量库选型（Q3） | pgvector / Milvus / OpenSearch | 影响 Compose、索引写入、运维复杂度；建议第一版优先 pgvector 验证 |
| 先 Web 还是 API+CLI（Q4） | 先 API + 证据页 / 直接做 Web | 影响 M2/M4 排期与 demo 形态 |
| 旧项目定位（Q5） | 仅 benchmark 数据源 / 保留为 demo | 影响旧仓库冻结策略与文档叙事 |
| 环境变量前缀（D4） | 保留 `FIN_AGENT_*` / 改为 `GROUNDEDKB_*` | 影响配置、文档与部署示例 |
| 仓库布局（D1） | 维持 `../nianbao/annual-report-qa-agent` / 迁为 `../annual-report-qa-agent` | 决定文档路径如何修 |
| Go module path | 暂用 `grounded-kb.local` / 改为 `github.com/Polar12e/SourceKB-GroundedKB` | 影响所有 import，需一次性替换 |

---

## 7. 待确认问题（来自 HANDOVER §8）

| ID | 问题 | 状态 |
|---|---|---|
| Q1 | 新仓库远程地址/组织名 | 已确认：https://github.com/Polar12e/SourceKB-GroundedKB（push 待认证） |
| Q2 | 第一个 finance vertical 的文档范围（仅年报？公告？审计报告？） | 未确认 |
| Q3 | 向量库选型：Milvus / pgvector / OpenSearch | 未确认 |
| Q4 | 第一步做 Web，还是先 API + CLI | 未确认 |
| Q5 | 旧项目保留为 demo，还是只作为 benchmark 数据源 | 未确认 |
| Q6 | 旧项目与迁移方案的实际相对路径（D1） | 未确认 |

---

## 8. 下一步（按顺序）

1. **完成 Git 推送**：在宿主机终端完成 GitHub 认证（PAT 或 SSH），执行 `git push -u origin main`；Q1 已确认。
2. **确认 Docker 访问**：在宿主机终端执行 `docker info` 与 `docker run --rm hello-world`；Go 环境已固化（`make test`），Docker 仍是 M0 唯一环境阻塞（D3/T0.13）。
3. **写契约 v0**：先定 `Document`、`Chunk`、`SearchHit`、`Citation`、`EvalCase`（T0.3），再补 OpenAPI（T0.4）。
4. **契约评审并冻结**（T0.5）；通过后并行建 Go/Python 骨架与 Compose（T0.6–T0.8）。
5. **准备 M1 baseline**：用旧项目检索跑 10 题，把指标和命令留档（T1.3），作为新服务的对比基准。

---

## 9. 风险速记

| ID | 风险 | 影响 | 当前证据/触发条件 | 缓解 |
|---|---|---|---|---|
| R1 | 沙箱限制 | M0 无法验收 | Docker 已装但沙箱无法连接 socket；Go 缓存已重定向 | 宿主机终端验证 Compose（D3） |
| R2 | 文档路径漂移 | 接手人找不到旧项目/迁移方案 | D1 | 统一布局后一次性修文档，并加检查 |
| R3 | 语料/PDF 许可 | 仓库无法公开 | 旧项目含 452 页 corpus | 只存 manifest/hash 或样例；入库前确认许可 |
| R4 | 远程未备份 | 本地提交无法在 GitHub 恢复；CI 未触发 | 本机无 GitHub 凭据，push 未完成 | 完成认证后推送（D7/T0.1） |
| R5 | Gold Evidence 标注成本 | benchmark 不可信 | 100 题目标 | 先 20 题双人核对，再扩量 |
| R6 | 过早平台化 | 切片交付不了 | 目录/文档已覆盖 M4 | 先 M0/M1 单垂直，平台能力按 benchmark 需求引入 |
| R7 | 文档与实现漂移 | 交接状态失真 | README §5 状态表需随代码更新 | 每次合并更新 README §5 与本日志 |
| R8 | 配置继承旧项目 | 密钥/端点策略混乱 | `.env.example` 仍为 `FIN_AGENT_*` | T0.11 统一前缀；`.env` 永不提交 |
