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

### 2026-11-18 17:40 · 切换 SSH 认证

- 生成专用 ed25519 key：`.tools/ssh/id_ed25519`（权限 600，`.tools/` 已忽略）；指纹 `SHA256:5omjYIwO+ImXwE1bNk5SABaROEwI9lKzkZkP7l8TQMw`。
- 远程改为 `ssh://git@ssh.github.com:443/Polar12e/SourceKB-GroundedKB.git`（本机到 `github.com:22` 被阻断，443 可用）。
- `core.sshCommand` 使用 `-F /dev/null` 绕开系统 SSH 配置权限错误，known_hosts 放在 `.tools/ssh/known_hosts`。
- 当前仍是 `Permission denied (publickey)`：公钥尚未加入 GitHub；添加后即可 `git push -u origin main`。

### 2026-11-18 17:43 · SSH 推送成功

- SSH 认证成功：`Hi Polar12e! You've successfully authenticated...`。
- `git push -u origin main` 成功；本地 `main` 已跟踪 `origin/main`，工作树干净。
- 远程仓库：`ssh://ssh.github.com:443/Polar12e/SourceKB-GroundedKB.git`。
- D7 解除；T0.1 的 push 待办完成。后续提交直接 `git push`。

### 2026-11-18 17:50 · M0 项目框架构建

**新增**

- `contracts/`：13 个 JSON Schema（Draft 2020-12）、OpenAPI 3.1、11 个示例、`scripts/check_contracts.py`。
- `workers/retrieval/`：FastAPI 骨架（`/healthz`、`/search` 501）、4 个 pytest、requirements、Dockerfile。
- `deploy/`：`compose.yaml`（7 个服务）+ Go 通用 Dockerfile；根目录 `.dockerignore`。
- `.github/workflows/ci.yml`：Go / Python / Compose 三个 job。
- `Makefile`：`py-install`、`py-test`、`contracts`、`test-all`、`check-all`、`compose-config`。
- README / HANDOVER / architecture / workers / deploy 文档同步。

**验证**

- `make check-all`：Go vet/test 通过；Python 4 passed；contracts OK（13 schemas / 11 examples / OpenAPI 3.1.0）；compose config OK。
- retrieval 实测：`/healthz` 200；`/search` 501；空 query 422。
- CI YAML 可解析，3 个 job；`gofmt` clean。
- `.venv/`、`.tools/`、`bin/` 仍被忽略。

**未做**

- 契约 v0 尚未评审冻结（T0.5）。
- `docker compose up` 未运行（D3 沙箱限制）。
- 检索算法、ingest、Agent、benchmark 未实现。

### 2026-11-18 18:42 · T1.2 检索迁移

**新增**

- `core/text.py`：数字归一化、中文 bigram、行切分。
- `workers/retrieval/`：`chunking.py`、`windows.py`、`index.py`、`fusion.py`、`corpus.py`；BM25、hit window、RRF、JSONL corpus 加载。
- `domains/finance/retrieval.py`：旧 `bm25` 的 ratio/restatement 查询扩展 + 报表页 +18 加分。
- `app.py`：`/search` 返回 200 `SearchResponse`，支持 `RETRIEVAL_CORPUS`；`section` 为空时省略。
- 测试 30 项（含 API↔JSON Schema 契约校验）；合成 fixture `sample_pages.jsonl`。

**基线核对**

- 在新索引上跑旧 corpus：1450 chunks / 452 pages，构建约 0.11s。
- q01–q08 的页面顺序与旧 `bm25` baseline 一致；q01 命中 `legacy:p199:c0`，窗口 1–18 行；q03/q04/q06/q07/q08 首位页面均正确。
- q02 为 `[126, 199, 355, ...]`，与旧 `bm25` 一致；期望页 199 在 top 3。

**推送**

- 本机直连 `ssh.github.com:443` 被网络层重置；使用本地代理隧道 `nc -X connect -x 127.0.0.1:7897 %h %p` 后推送成功。
- 该 `core.sshCommand` 只存在于本地 `.git/config`，不入库；换网络时需调整。

**未做**

- 正式 10 题指标与命令留档（T1.3/T1.7）。
- dense/embedding 通道；完整口语词表（`src/lexicon.py`）尚未迁移。
- ingest pipeline。

---

## 2. 工作区清单（已读）

| 路径 | 内容 | 状态 |
|---|---|---|
| [README.md](../README.md) | 项目定位、非目标、技术栈、目录规划、当前状态、文档索引 | 已完成（设计稿） |
| [HANDOVER.md](../HANDOVER.md) | 交接摘要、Go/Python 分界、存储、迁移清单、M0–M4、风险、待确认问题、安全检查清单 | 已完成（设计稿） |
| [docs/architecture.md](architecture.md) | 总体架构、服务职责、核心契约示例、入库/问答/评测流程、可观测性、第一版边界 | 设计稿 |
| [docs/migration-from-annual-report.md](migration-from-annual-report.md) | 旧项目资产分级（A–D）、迁移顺序、不要照抄的部分、验收问题 | 设计稿 |
| [contracts/README.md](../contracts/README.md) | 契约 v0：JSON Schema / OpenAPI / 示例 | 草案已落地，待评审 |
| [services/README.md](../services/README.md) | Go 服务边界与优先级 | 说明文件；Go 骨架已落地 |
| [workers/README.md](../workers/README.md) | Python worker 职责与复用来源 | BM25 已落地 |
| [core/README.md](../core/README.md) | 跨 domain 算法与协议范围 | `text.py` 已落地 |
| [domains/finance/README.md](../domains/finance/README.md) | finance vertical 迁移范围 | retrieval profile 已落地 |
| [eval/README.md](../eval/README.md) | benchmark 目标、题目字段、指标 | 占位，无实现 |
| [deploy/README.md](../deploy/README.md) | Compose、Dockerfile、端口 | 骨架已落地；未运行 |
| [tests/README.md](../tests/README.md) | unit/contract/integration/eval/smoke 分层 | 占位，无测试 |
| [.env.example](../.env.example) | 本地配置占位（仍为 `FIN_AGENT_*` 前缀） | 待整理（D4） |
| [.gitignore](../.gitignore) | 已忽略 `.env`、缓存、构建产物、评测输出、`*.npz` | 可用 |

截至 2026-11-18 18:42，`core/text.py`、`domains/finance/retrieval.py`、`workers/retrieval/`、`contracts/`、`deploy/`、`.github/workflows/` 已落地；`eval/`、`tests/` 仍为占位。工作区当前还有 `go.mod`、`Makefile`、`requirements-dev.txt`、`.dockerignore`、`.tools/`（缓存）、`.venv/`（Python 依赖）和 `bin/`（构建产物），后三者已忽略。

---

## 3. 偏差与缺口（待处理）

| ID | 现象 | 影响 | 建议处置 |
|---|---|---|---|
| D1 | README/HANDOVER/迁移文档引用 `../annual-report-qa-agent` 与 `../TRANSITION_PLAN.md`；实际位于 `../nianbao/` 下 | 接手人按文档路径找不到旧项目与迁移方案 | 先确认目标仓库布局：若维持当前嵌套，统一改为 `../nianbao/...`；若计划迁为兄弟目录，迁移后再改。两者取其一，避免长期漂移 |
| D2 | 已解决（17:37 初始化，17:43 推送）：`main` 已提交并同步到 origin | — | — |
| D3 | Docker CE 29.10 + Compose v5.8 已安装且 systemd active，但当前 DSH bwrap 沙箱剥离 docker 组权限，无法连接 `/var/run/docker.sock`（`sg` / `setpriv` / `sudo` / `danger-full-access` 均失败）；无 rootless socket 或 TCP 入口 | `docker compose up` 无法在本会话验收；Postgres/Redis/服务容器无法启动 | 在宿主机终端运行 Docker/Compose，或为会话开放 socket 访问；Compose 文件可先写，验收放到宿主机 |
| D4 | `.env.example` 仍使用旧项目前缀 `FIN_AGENT_*`，未定义 temperature，端口与服务名也未对齐新架构 | 配置继承旧命名，后续 model gateway/agent 的边界不清 | T0.11：确定新前缀（建议 `GROUNDEDKB_*`），补 temperature/超时/端点白名单；如需兼容旧变量，记录映射关系 |
| D5 | 已解决（17:50）：contracts v0 草案（13 schema + OpenAPI + examples）已落地；尚未评审冻结 | 字段仍可能变，冻结前不宜扩业务接口 | T0.5 评审并冻结 |
| D6 | Go 1.27.4 已装，但默认 `GOCACHE=/home/polarize/.cache/go-build`、`GOPATH=/home/polarize/go` 在沙箱内只读，直接 `go run` / `go build` 报 `read-only file system`（已缓解） | 代码可编译但命令需额外环境变量；本地与 CI 行为不一致 | 已由 `scripts/goenv.sh` + Makefile 重定向到 `.tools/`；直接执行 `go` 前先 source（T0.13） |
| D7 | 已解决（17:43）：SSH key 已登记，`main` 已推送；HTTPS 仍无凭据，但不再阻塞 | — | 后续使用 `git push`（SSH 443） |
| D8 | 契约 v0 已起草但未评审冻结 | 字段/端点仍可能变，先扩业务会返工 | T0.5：记录评审意见后冻结 v0 |
| D9 | 已解决（18:42）：`/search` 返回 BM25 hits；q01–q08 页面顺序与旧 `bm25` 一致 | — | dense 通道见 D10 |
| D10 | dense / embedding 通道未迁移；API 目前只用 BM25 单通道 | hybrid 与语义召回不可用 | `workers/embedding` 建立后接入 `HybridIndex` |

---

## 4. 任务清单

### M0：契约与骨架

目标：`docker compose up` 可启动，`/healthz` 可用；契约 v0 冻结。

| ID | 任务 | 状态 | 验收 / 备注 |
|---|---|---|---|
| T0.0 | 阅读工作区并建立任务日志 | `DONE` | 本文件；README/HANDOVER 已加链接 |
| T0.1 | 初始化 Git 仓库、复核 `.gitignore`、首次提交 | `DONE` | 本地 + 远程完成：`main` + `eac5219` 已推送；SSH 443 可用 |
| T0.2 | 统一旧项目与迁移文档的相对路径（D1） | `TODO` | 取决于目标仓库布局决策 |
| T0.3 | 编写契约 JSON Schema：`Document` / `Chunk` / `SearchRequest` / `SearchHit` / `Answer` / `Citation` / `EvalCase` / `EvalResult` | `DONE` | 13 个 Draft 2020-12 schema + 11 个 examples；`make contracts` 通过 |
| T0.4 | 编写 OpenAPI：Gateway / Agent / Retrieval 端点 | `DONE` | OpenAPI 3.1；`/healthz`、`/documents`、`/search`、`/ask`；外部 `$ref` 已校验 |
| T0.5 | 契约评审并冻结 v0 | `TODO` | 草案已产出；需评审记录（D8），冻结后才能扩业务接口 |
| T0.6 | Go 服务骨架：`gateway` / `ingest` / `agent` / `model-gateway`，含 `/healthz` 与单测 | `DONE` | `make test` 4 个含测试包通过、`make vet` 通过、`make build` 四服务；`/healthz` 实测；D6 已由脚本处理 |
| T0.7 | Python retrieval worker 骨架（FastAPI + `/healthz` + pytest） | `DONE` | 初始 4 个 pytest；T1.2 后扩展为 30 个测试、`/search` 已实现 |
| T0.8 | Docker Compose：Postgres + Redis + retrieval + gateway + 健康检查 | `DOING` | 7 服务 compose + Dockerfile；`config` 通过；`up` 受 D3 阻塞 |
| T0.9 | README 快速开始与 Makefile/脚本对齐，确保 `docker compose up` 可跑 | `DOING` | README/Makefile 已更新；`up` 未在会话内验证 |
| T0.10 | CI 骨架：Go test、Python pytest、契约校验 | `DONE` | `.github/workflows/ci.yml` 含 3 个 job；待首次远程 CI 运行 |
| T0.11 | 配置基线：确定环境变量前缀、补 temperature、端点白名单占位 | `TODO` | 对应 D4；禁止提交真实 key |
| T0.12 | 向量库选型 ADR（pgvector / Milvus / OpenSearch） | `TODO` | 对应 Q3；第一版只选一个，写入 `docs/adr/` 或本日志决策表 |
| T0.13 | 环境引导：Go 缓存、venv、pip 镜像、Docker 访问方式 | `DOING` | Go/Python 环境已固化（scripts/goenv.sh、.venv、Aliyun 镜像）；Docker 访问待补 |

### M1：检索切片

目标：10 份文档、10 题 retrieval eval；Hit@4/Recall@4 有 baseline，页面/行号可回链。

| ID | 任务 | 状态 | 验收 / 备注 |
|---|---|---|---|
| T1.1 | 将旧项目 32 题 `questions.json` 迁为 `EvalCase` schema，补 `gold_evidence` | `TODO` | 先 10 题可跑，再补全 32 题 |
| T1.2 | 迁移 `retrieval.py`：chunking / BM25 / hit window / RRF，`page` → `locator` | `DONE` | 30 测试；q01–q08 与旧 `bm25` 页面顺序一致；finance profile 独立 |
| T1.3 | 用旧项目检索跑 10 题 baseline，留档指标与命令 | `DOING` | 已核对 q01–q08 页面顺序；正式 10 题指标/命令待补 |
| T1.4 | Parser：PDF → 页/行 JSONL，生成 manifest 与 `sha256` | `TODO` | 先 PDF；HTML/DOCX 后续 |
| T1.5 | 10 份文档入库：解析、chunk、metadata、索引 | `TODO` | 需先定语料许可（R3） |
| T1.6 | `POST /search` 返回 `document_id/page/line_start/line_end/score/matched_terms` | `DONE` | 支持 `RETRIEVAL_CORPUS`；响应通过契约校验；ingest 后接动态索引 |
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
| M0 契约与骨架 | `docker compose up` 可启动；`/healthz` 可用 | 进行中 | T0.5、T0.8；D3 沙箱 |
| M1 检索切片 | 10 文档/10 题；Hit@4、Recall@4 baseline；页面/行号可回链 | 进行中 | T1.3 baseline、T1.4/T1.5 ingest、T1.7 eval |
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
| Q1 | 新仓库远程地址/组织名 | 已确认并推送：https://github.com/Polar12e/SourceKB-GroundedKB |
| Q2 | 第一个 finance vertical 的文档范围（仅年报？公告？审计报告？） | 未确认 |
| Q3 | 向量库选型：Milvus / pgvector / OpenSearch | 未确认 |
| Q4 | 第一步做 Web，还是先 API + CLI | 未确认 |
| Q5 | 旧项目保留为 demo，还是只作为 benchmark 数据源 | 未确认 |
| Q6 | 旧项目与迁移方案的实际相对路径（D1） | 未确认 |

---

## 8. 下一步（按顺序）

1. **确认 Docker 访问**：在宿主机终端执行 `docker info`、`docker run --rm hello-world`，再跑 `docker compose -f deploy/compose.yaml up --build`；这是 M0 唯一环境阻塞（D3/T0.8）。
2. **评审并冻结契约 v0**（T0.5）：按 `contracts/README.md` 的待评审问题逐项确认，记录评审意见后冻结（D8）。
3. **完成正式 baseline**：用旧项目检索跑 10 题，把 Hit@4/Recall@4/MRR 与命令留档（T1.3）；新服务已核对 q01–q08 页面顺序。
4. **做 ingest**：PDF → 页/行 JSONL，10 文档入库并生成 manifest/hash（T1.4/T1.5）；索引从 `RETRIEVAL_CORPUS` 转为 ingest 写入。
5. **做 M1 评测**：新服务 10 题 retrieval eval 与 baseline 对比（T1.7）；之后再接 dense/embedding 与 RRF 多通道（D10）。

---

## 9. 风险速记

| ID | 风险 | 影响 | 当前证据/触发条件 | 缓解 |
|---|---|---|---|---|
| R1 | 沙箱限制 | M0 无法验收 | Docker 已装但沙箱无法连接 socket；Go 缓存已重定向 | 宿主机终端验证 Compose（D3） |
| R2 | 文档路径漂移 | 接手人找不到旧项目/迁移方案 | D1 | 统一布局后一次性修文档，并加检查 |
| R3 | 语料/PDF 许可 | 仓库无法公开 | 旧项目含 452 页 corpus | 只存 manifest/hash 或样例；入库前确认许可 |
| R4 | SSH 私钥丢失/泄露 | 无法推送，或 key 被滥用 | 私钥在 `.tools/ssh`，无 passphrase，未纳入 Git | 不要删除/提交；必要时重新生成并撤销旧 key |
| R5 | Gold Evidence 标注成本 | benchmark 不可信 | 100 题目标 | 先 20 题双人核对，再扩量 |
| R6 | 过早平台化 | 切片交付不了 | 目录/文档已覆盖 M4 | 先 M0/M1 单垂直，平台能力按 benchmark 需求引入 |
| R7 | 文档与实现漂移 | 交接状态失真 | README §5 状态表需随代码更新 | 每次合并更新 README §5 与本日志 |
| R8 | 配置继承旧项目 | 密钥/端点策略混乱 | `.env.example` 仍为 `FIN_AGENT_*` | T0.11 统一前缀；`.env` 永不提交 |
