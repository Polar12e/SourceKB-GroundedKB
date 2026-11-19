# deploy（骨架）

当前包含：

| 文件 | 用途 |
|---|---|
| `compose.yaml` | Postgres / Redis / retrieval / gateway / ingest / agent / model-gateway |
| `docker/go-service.Dockerfile` | Go 服务通用多阶段镜像，通过 `SERVICE` 构建参数选择服务 |

## 校验

```bash
docker compose -f deploy/compose.yaml config
```

## 启动

```bash
docker compose -f deploy/compose.yaml up --build
```

端口：gateway `8080`、retrieval `8081`、ingest `8082`、agent `8083`、model-gateway `8084`、Postgres `5432`、Redis `6379`。

## 本地数据

Compose 将 `../data` 只读挂载到 `/data`，retrieval 读取：

- `/data/private/corpus/pages.jsonl`
- `/data/manifests/documents.json`

如果本地没有 corpus，先按 `data/README.md` 解析 PDF。

## 注意

- Compose 的 Postgres/Redis 默认凭据仅用于本地开发，生产必须通过 `.env`/secret 注入。
- 当前 DSH 会话无法访问 Docker socket；`up` 需在宿主机终端执行。
- gateway 通过 `AGENT_URL`/`RETRIEVAL_URL` 访问 agent/retrieval；agent 通过 `RETRIEVAL_URL` 访问 retrieval。
- 第一版不引入 K8s、Prometheus；索引重建与模型 fallback 后续补。
