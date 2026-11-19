# services（骨架）

Go 服务边界：

| 服务 | 职责 | 状态 |
|---|---|---|
| `gateway` | HTTP API、认证、限流、trace | 骨架 + `/search` `/ask` 代理 |
| `ingest` | 上传、任务状态、幂等、队列 | 骨架（`/healthz`） |
| `agent` | 工具注册、策略、超时、step trace | `/ask` 抽取式/受控 LLM 回答 + anchor citation / unverified |
| `model-gateway` | provider 路由、重试、成本统计 | `/v1/chat/completions` 准备；DeepSeek；默认关闭 |

当前为 M0 可运行切片：gateway → agent → retrieval；model-gateway 已有 DeepSeek 路由但默认关闭；ingest 仍只有健康检查。

第一版优先：

1. `gateway` + `retrieval` 联调；
2. `ingest` 单文档入库；
3. `agent` 只支持 search/read 两个工具。

先保持模块化单体，不提前拆微服务。
