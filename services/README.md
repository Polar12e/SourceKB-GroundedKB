# services（骨架）

Go 服务边界：

| 服务 | 职责 | 状态 |
|---|---|---|
| `gateway` | HTTP API、认证、限流、trace | 骨架（`/healthz`） |
| `ingest` | 上传、任务状态、幂等、队列 | 骨架（`/healthz`） |
| `agent` | 工具注册、策略、超时、step trace | 骨架（`/healthz`） |
| `model-gateway` | provider 路由、重试、成本统计 | 骨架（`/healthz`） |

当前为 M0 骨架：共享配置、健康检查、优雅关闭；业务接口待契约冻结后实现。

第一版优先：

1. `gateway` + `retrieval` 联调；
2. `ingest` 单文档入库；
3. `agent` 只支持 search/read 两个工具。

先保持模块化单体，不提前拆微服务。
