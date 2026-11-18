# deploy（待建）

第一版目标：

- Docker Compose：gateway / retrieval / ingest / Postgres / Redis / vector DB；
- `.env` 注入，不提交；
- 健康检查 `/healthz`；
- 单机即可，不提前上 K8s。

后续可选：

- 索引重建任务；
- 模型网关 fallback；
- Prometheus/Grafana。
